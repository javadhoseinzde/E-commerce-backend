"""
SaaS → Core synchronization client.

This module provides the client-side logic for SaaS to push
subscription and plan state to Core after payment/subscription changes.

Communication mechanism: Authenticated HTTP API (server-to-server).
No Kafka, RabbitMQ, or complex message broker required.

Uses Python standard library (urllib) to avoid adding external dependencies.

Retry strategy:
- Automatic retry with exponential backoff
- Maximum 3 retries
- Retries only on network/timeout errors (5xx, connection errors)
- Does NOT retry on 4xx errors (client errors are not retryable)
- Payment/Order state is NEVER rolled back on sync failure

Usage in SaaS after payment success:
    from integration.saas_sync_client import SaaSCoreSyncClient

    # After payment SUCCESS → Order PAID → Subscription ACTIVE
    client = SaaSCoreSyncClient()
    result = client.sync_subscription_activated(
        subscription_id=...,
        cafe_id=...,
        plan_data={...},
        started_at=...,
        expires_at=...,
    )
    if not result.success:
        # Log the failure but DO NOT roll back payment
        # Will be retried on next cycle or manual retry
        logger.error(f"Core sync failed: {result.error}")
"""
import uuid
import json
import time
import logging
import hmac
import hashlib
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from django.conf import settings

logger = logging.getLogger(__name__)

# Default sync configuration
DEFAULT_CORE_SYNC_URL = getattr(settings, "CORE_SYNC_BASE_URL", "http://localhost:8000/api/internal")
DEFAULT_CORE_API_KEY = getattr(settings, "CORE_INTERNAL_API_KEY", getattr(settings, "INTERNAL_API_KEY", ""))
DEFAULT_CORE_SYNC_SECRET = getattr(settings, "MENUNO_CORE_SYNC_SECRET", "")
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds
DEFAULT_RETRY_BACKOFF = 2.0  # multiplier
DEFAULT_TIMEOUT = 10  # seconds


@dataclass
class SyncResult:
    """Result of a synchronization attempt."""
    success: bool
    created: bool = False
    error: Optional[str] = None
    status_code: Optional[int] = None
    response_data: Optional[Dict[str, Any]] = None


@dataclass
class SyncStatus:
    """Tracks the sync status for a subscription in SaaS."""
    core_sync_status: str = "PENDING"  # PENDING, SYNCED, FAILED
    core_synced_at: Optional[datetime] = None
    core_sync_attempts: int = 0
    core_last_sync_error: Optional[str] = None


class SaaSCoreSyncClient:
    """
    Client for SaaS → Core synchronization via authenticated HTTP API.

    This client handles:
    - Plan synchronization
    - Subscription lifecycle event synchronization
    - Automatic retry with exponential backoff
    - Proper error handling and logging
    - Payment-safe behavior (never rolls back on sync failure)

    Authentication:
    - HMAC-SHA256 signature for /api/internal/core/sync/ endpoint
    - X-Menuno-Signature: HMAC-SHA256(secret, timestamp + "." + body)
    - X-Menuno-Timestamp: ISO-8601 timestamp
    - X-Menuno-Event-Id: UUID for idempotency

    Uses Python standard library (urllib) to avoid external dependencies.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        sync_secret: Optional[str] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.base_url = (base_url or DEFAULT_CORE_SYNC_URL).rstrip("/")
        self.api_key = api_key or DEFAULT_CORE_API_KEY
        self.sync_secret = sync_secret or DEFAULT_CORE_SYNC_SECRET
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_backoff = retry_backoff
        self.timeout = timeout

    def _compute_hmac_signature(self, timestamp: str, raw_body: bytes) -> str:
        """
        Compute HMAC-SHA256 signature matching Core's verification algorithm.

        Signature algorithm:
            HMAC-SHA256(MENUNO_CORE_SYNC_SECRET, timestamp + "." + raw_body)

        Args:
            timestamp: ISO-8601 timestamp string (same as X-Menuno-Timestamp header)
            raw_body: Raw request body bytes (UTF-8 encoded JSON)

        Returns:
            Hex-encoded HMAC-SHA256 signature
        """
        message = (timestamp + ".").encode("utf-8") + raw_body
        return hmac.new(
            self.sync_secret.encode("utf-8"),
            message,
            hashlib.sha256,
        ).hexdigest()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        use_hmac: bool = False,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request with retry logic using urllib.

        Returns:
            Dict with 'status_code', 'data' (parsed JSON), 'error' (if any)
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        body = json.dumps(data).encode("utf-8") if data else None

        if use_hmac and self.sync_secret and body:
            # HMAC-authenticated request for Core sync endpoint
            event_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()
            signature = self._compute_hmac_signature(timestamp, body)

            headers = {
                "Content-Type": "application/json",
                "X-Menuno-Event-Id": event_id,
                "X-Menuno-Timestamp": timestamp,
                "X-Menuno-Signature": signature,
            }
        else:
            # API key-authenticated request (legacy)
            headers = {
                "X-Internal-API-Key": self.api_key,
                "Content-Type": "application/json",
            }

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(
                    url,
                    data=body,
                    headers=headers,
                    method=method,
                )
                
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    response_body = response.read().decode("utf-8")
                    response_data = json.loads(response_body) if response_body else {}
                    
                    return {
                        "status_code": response.status,
                        "data": response_data,
                        "error": None,
                    }
                    
            except urllib.error.HTTPError as e:
                # HTTP error response
                response_body = e.read().decode("utf-8") if e.fp else ""
                try:
                    response_data = json.loads(response_body) if response_body else {}
                except json.JSONDecodeError:
                    response_data = {"raw": response_body}
                
                # 4xx errors are not retryable
                if 400 <= e.code < 500:
                    return {
                        "status_code": e.code,
                        "data": response_data,
                        "error": f"HTTP {e.code}: {response_body}",
                    }
                
                # 5xx - retry
                last_exception = e
                response_data_result = response_data
                
            except urllib.error.URLError as e:
                # Connection error
                last_exception = e
            except Exception as e:
                # Non-retryable error
                return {
                    "status_code": None,
                    "data": None,
                    "error": str(e),
                }
            
            # Wait before retrying
            if attempt < self.max_retries:
                delay = self.retry_delay * (self.retry_backoff ** attempt)
                logger.warning(
                    f"Core sync attempt {attempt + 1}/{self.max_retries + 1} failed, "
                    f"retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
        
        # All retries exhausted
        return {
            "status_code": None,
            "data": None,
            "error": f"All {self.max_retries + 1} attempts failed: {last_exception}",
        }

    def sync_plan(
        self,
        external_id: uuid.UUID,
        slug: str,
        title: str,
        price: int,
        duration_days: int,
        max_products: int = 100,
        is_active: bool = True,
        version: int = 1,
    ) -> SyncResult:
        """
        Synchronize a plan from SaaS to Core.
        
        Args:
            external_id: Stable UUID identifier for the plan
            slug: Plan slug
            title: Plan title
            price: Plan price
            duration_days: Plan duration in days
            max_products: Maximum products allowed
            is_active: Whether plan is active
            version: Plan version for staleness prevention
            
        Returns:
            SyncResult with success status and details
        """
        event_id = uuid.uuid4()
        now = datetime.utcnow().isoformat() + "Z"
        
        payload = {
            "event_id": str(event_id),
            "event_type": "plan.synced",
            "plan": {
                "external_id": str(external_id),
                "slug": slug,
                "title": title,
                "price": price,
                "duration_days": duration_days,
                "max_products": max_products,
                "is_active": is_active,
                "version": version,
            },
            "occurred_at": now,
        }

        result = self._make_request("POST", "core/sync/", payload, use_hmac=True)
        
        if result["error"]:
            logger.error(f"Plan sync failed: {result['error']}")
            return SyncResult(
                success=False,
                error=result["error"],
                status_code=result["status_code"],
            )
        
        if result["status_code"] in (200, 201):
            data = result["data"]
            return SyncResult(
                success=True,
                created=data.get("result", {}).get("created", False),
                status_code=result["status_code"],
                response_data=data.get("result"),
            )
        else:
            return SyncResult(
                success=False,
                error=f"HTTP {result['status_code']}: {result['data']}",
                status_code=result["status_code"],
            )

    def _sync_subscription_event(
        self,
        event_type: str,
        subscription_id: uuid.UUID,
        cafe_id: uuid.UUID,
        plan_data: Dict[str, Any],
        status: str,
        started_at: Optional[str] = None,
        expires_at: Optional[str] = None,
        version: int = 1,
    ) -> SyncResult:
        """
        Send a subscription synchronization event to Core.
        
        This is the core method for subscription sync. All lifecycle events
        (activated, expired, cancelled) go through here.
        
        IMPORTANT: This method is called AFTER the SaaS payment/order/subscription
        transaction has already committed. If this fails:
        - DO NOT roll back the payment
        - DO NOT mark payment as FAILED
        - DO NOT mark order as FAILED
        - DO NOT deactivate the SaaS subscription
        - Just log the failure and retry later
        """
        event_id = uuid.uuid4()
        now = datetime.utcnow().isoformat() + "Z"
        
        payload = {
            "event_id": str(event_id),
            "event_type": event_type,
            "subscription_id": str(subscription_id),
            "cafe_id": str(cafe_id),
            "plan": plan_data,
            "status": status,
            "started_at": started_at,
            "expires_at": expires_at,
            "version": version,
            "occurred_at": now,
        }

        result = self._make_request("POST", "core/sync/", payload, use_hmac=True)
        
        if result["error"]:
            logger.error(f"Subscription sync failed ({event_type}): {result['error']}")
            return SyncResult(
                success=False,
                error=result["error"],
                status_code=result["status_code"],
            )
        
        if result["status_code"] in (200, 201):
            data = result["data"]
            return SyncResult(
                success=True,
                created=data.get("result", {}).get("created", False),
                status_code=result["status_code"],
                response_data=data.get("result"),
            )
        else:
            return SyncResult(
                success=False,
                error=f"HTTP {result['status_code']}: {result['data']}",
                status_code=result["status_code"],
            )

    def sync_subscription_activated(
        self,
        subscription_id: uuid.UUID,
        cafe_id: uuid.UUID,
        plan_data: Dict[str, Any],
        started_at: Optional[str] = None,
        expires_at: Optional[str] = None,
        version: int = 1,
    ) -> SyncResult:
        """
        Synchronize a subscription activation event to Core.
        
        Called after: Payment SUCCESS → Order PAID → Subscription ACTIVE
        """
        return self._sync_subscription_event(
            event_type="subscription.activated",
            subscription_id=subscription_id,
            cafe_id=cafe_id,
            plan_data=plan_data,
            status="ACTIVE",
            started_at=started_at,
            expires_at=expires_at,
            version=version,
        )

    def sync_subscription_expired(
        self,
        subscription_id: uuid.UUID,
        cafe_id: uuid.UUID,
        plan_data: Dict[str, Any],
        version: int = 1,
    ) -> SyncResult:
        """
        Synchronize a subscription expiration event to Core.
        """
        return self._sync_subscription_event(
            event_type="subscription.expired",
            subscription_id=subscription_id,
            cafe_id=cafe_id,
            plan_data=plan_data,
            status="EXPIRED",
            version=version,
        )

    def sync_subscription_cancelled(
        self,
        subscription_id: uuid.UUID,
        cafe_id: uuid.UUID,
        plan_data: Dict[str, Any],
        version: int = 1,
    ) -> SyncResult:
        """
        Synchronize a subscription cancellation event to Core.
        """
        return self._sync_subscription_event(
            event_type="subscription.cancelled",
            subscription_id=subscription_id,
            cafe_id=cafe_id,
            plan_data=plan_data,
            status="CANCELLED",
            version=version,
        )

    def check_subscription_access(
        self,
        cafe_external_id: uuid.UUID,
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a cafe has an active subscription in Core.
        """
        payload = {
            "cafe_external_id": str(cafe_external_id),
        }

        result = self._make_request("POST", "integration/subscription/access-check/", payload)
        
        if result["error"]:
            logger.error(f"Subscription access check failed: {result['error']}")
            return None
        
        if result["status_code"] == 200:
            return result["data"].get("result")
        
        return None
