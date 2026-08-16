"""
Core synchronization services.

Handles incoming synchronization events from SaaS.
SaaS is the source of truth for Plan, Subscription billing state.
Core is the source of truth for Cafe operational data.

This module receives lightweight mirrors of SaaS Plan and Subscription
to enable access control within Core without duplicating billing logic.
"""
import uuid
import hashlib
import logging
from typing import Optional

from django.db import transaction, IntegrityError
from django.utils import timezone

from app.cafe.models import Plan, Subscription, CafeInfo, SyncEvent

logger = logging.getLogger(__name__)


class PlanSyncService:
    """
    Synchronizes Plan data from SaaS to Core.
    SaaS is the source of truth for plans.
    Core maintains a lightweight mirror for display and access control.
    
    Strategy:
    - update_or_create using external_id (idempotent)
    - Version-based staleness prevention
    - Transaction-safe for concurrent requests
    """

    @staticmethod
    def sync_plan(plan_data: dict) -> tuple[Plan, bool]:
        """
        Sync a plan from SaaS to Core. Idempotent and version-safe.
        
        Args:
            plan_data: Dictionary with plan data from SaaS:
                - external_id (str/UUID): Stable cross-system identifier
                - slug (str): Plan slug
                - title (str): Plan title
                - price (int): Plan price
                - duration_days (int): Plan duration
                - max_products (int): Max products allowed
                - is_active (bool): Whether plan is active
                - version (int): Plan version (for staleness prevention)
                
        Returns:
            Tuple of (plan, created) where created is True if new plan was created
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        required_fields = ["external_id", "slug", "title", "price", "duration_days"]
        for field in required_fields:
            if field not in plan_data or plan_data[field] is None:
                raise ValueError(f"Missing required field: {field}")

        external_id = uuid.UUID(str(plan_data["external_id"]))
        incoming_version = plan_data.get("version", 1)

        with transaction.atomic():
            try:
                # Try to get existing plan
                existing_plan = Plan.objects.select_for_update().get(external_id=external_id)

                # Version check: only update if incoming version >= current version
                if incoming_version < existing_plan.version:
                    logger.info(
                        f"Plan {external_id} sync rejected: incoming version {incoming_version} "
                        f"< current version {existing_plan.version}"
                    )
                    return existing_plan, False

                # Update existing plan
                existing_plan.slug = plan_data["slug"]
                existing_plan.title = plan_data["title"]
                existing_plan.price = plan_data["price"]
                existing_plan.duration_days = plan_data["duration_days"]
                existing_plan.max_products = plan_data.get("max_products", existing_plan.max_products)
                existing_plan.is_active = plan_data.get("is_active", existing_plan.is_active)
                existing_plan.version = incoming_version
                existing_plan.save()

                logger.info(f"Plan {external_id} updated (version {incoming_version})")
                return existing_plan, False

            except Plan.DoesNotExist:
                # Create new plan
                plan = Plan.objects.create(
                    external_id=external_id,
                    slug=plan_data["slug"],
                    title=plan_data["title"],
                    price=plan_data["price"],
                    duration_days=plan_data["duration_days"],
                    max_products=plan_data.get("max_products", 100),
                    is_active=plan_data.get("is_active", True),
                    version=incoming_version,
                )
                logger.info(f"Plan {external_id} created (version {incoming_version})")
                return plan, True


class SubscriptionSyncService:
    """
    Synchronizes Subscription state from SaaS to Core.
    SaaS is the source of truth for subscription billing state.
    Core mirrors the final subscription state for access control.
    
    Strategy:
    - update_or_create using external_id (idempotent)
    - Version-based staleness prevention (prevents old events from overwriting newer state)
    - Database-level uniqueness constraints
    - Transaction-safe for concurrent requests
    - Event_id tracking for duplicate event detection
    """

    @staticmethod
    def sync_subscription(
        subscription_data: dict,
        cafe_external_id: uuid.UUID,
        plan_data: dict,
        event_id: Optional[uuid.UUID] = None,
        event_type: str = "subscription.activated",
    ) -> tuple[Subscription, bool]:
        """
        Sync a subscription from SaaS to Core. Idempotent and version-safe.
        
        Args:
            subscription_data: Dictionary with subscription data:
                - external_id (str/UUID): Stable cross-system identifier
                - status (str): PENDING, ACTIVE, EXPIRED, CANCELLED
                - started_at (str/datetime): When subscription started
                - expires_at (str/datetime): When subscription expires
                - version (int): Version for staleness prevention
            cafe_external_id (UUID): External ID of the cafe
            plan_data (dict): Plan data (will be synced first)
            event_id (UUID, optional): Unique event ID for idempotency
            event_type (str): Type of sync event
            
        Returns:
            Tuple of (subscription, created) where created is True if new
            
        Raises:
            ValueError: If required fields are missing or invalid
            CafeInfo.DoesNotExist: If cafe not found in Core
        """
        # Validate required subscription fields
        required_fields = ["external_id", "status"]
        for field in required_fields:
            if field not in subscription_data or subscription_data[field] is None:
                raise ValueError(f"Missing required field: {field}")

        subscription_external_id = uuid.UUID(str(subscription_data["external_id"]))
        incoming_status = subscription_data["status"]
        incoming_version = subscription_data.get("version", 1)

        # Validate status
        valid_statuses = dict(Subscription.STATUS_CHOICES)
        if incoming_status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{incoming_status}'. Must be one of: {list(valid_statuses.keys())}"
            )

        # Find the cafe in Core
        cafe_info = _find_cafe_by_external_id(cafe_external_id)

        # Sync the plan first
        plan, _ = PlanSyncService.sync_plan(plan_data)

        # Parse datetime fields
        started_at = _parse_datetime(subscription_data.get("started_at"))
        expires_at = _parse_datetime(subscription_data.get("expires_at"))

        # Derive is_active and legacy date fields from status
        is_active = incoming_status == "ACTIVE"

        with transaction.atomic():
            # Check for duplicate event using savepoint for SQLite compatibility
            if event_id is not None:
                event_id = uuid.UUID(str(event_id))
                event_already_exists = _record_sync_event(
                    event_id=event_id,
                    event_type=event_type,
                    subscription_external_id=subscription_external_id,
                    subscription_data=subscription_data,
                )
                if event_already_exists:
                    logger.info(f"Event {event_id} already processed, skipping")
                    try:
                        existing_sub = Subscription.objects.get(
                            external_id=subscription_external_id
                        )
                        return existing_sub, False
                    except Subscription.DoesNotExist:
                        pass

            try:
                # Try to get existing subscription
                existing_sub = Subscription.objects.select_for_update().get(
                    external_id=subscription_external_id
                )

                # Version check: only update if incoming version >= current version
                if incoming_version < existing_sub.version:
                    logger.info(
                        f"Subscription {subscription_external_id} sync rejected: "
                        f"incoming version {incoming_version} < current version {existing_sub.version}"
                    )
                    return existing_sub, False

                # Update existing subscription
                existing_sub.status = incoming_status
                existing_sub.plan = plan
                if started_at is not None:
                    existing_sub.started_at = started_at
                if expires_at is not None:
                    existing_sub.expires_at = expires_at
                existing_sub.is_active = is_active
                existing_sub.version = incoming_version

                # Sync legacy date fields
                if started_at is not None:
                    existing_sub.start_date = started_at.date() if hasattr(started_at, 'date') else started_at
                if expires_at is not None:
                    existing_sub.end_date = expires_at.date() if hasattr(expires_at, 'date') else expires_at

                existing_sub.save()

                logger.info(
                    f"Subscription {subscription_external_id} updated: "
                    f"status={incoming_status}, version={incoming_version}"
                )
                return existing_sub, False

            except Subscription.DoesNotExist:
                # Create new subscription
                sub = Subscription.objects.create(
                    external_id=subscription_external_id,
                    cafe=cafe_info,
                    plan=plan,
                    status=incoming_status,
                    started_at=started_at,
                    expires_at=expires_at,
                    is_active=is_active,
                    version=incoming_version,
                    start_date=started_at.date() if started_at else None,
                    end_date=expires_at.date() if expires_at else None,
                )

                logger.info(
                    f"Subscription {subscription_external_id} created: "
                    f"status={incoming_status}, version={incoming_version}"
                )
                return sub, True


def _find_cafe_by_external_id(cafe_external_id: uuid.UUID) -> CafeInfo:
    """
    Find a CafeInfo by the cafe's external_id.
    
    Raises:
        ValueError: If cafe not found
    """
    try:
        return CafeInfo.objects.select_related("cafe").get(
            cafe__external_id=cafe_external_id
        )
    except CafeInfo.DoesNotExist:
        raise ValueError(f"Cafe with external_id {cafe_external_id} not found in Core")


def _record_sync_event(
    event_id: uuid.UUID,
    event_type: str,
    subscription_external_id: uuid.UUID,
    subscription_data: dict,
) -> bool:
    """
    Record a sync event for idempotency tracking.
    Uses a savepoint to handle IntegrityError gracefully (especially for SQLite).
    
    Returns:
        True if event already existed (duplicate), False if newly created
    """
    try:
        # Use a savepoint so IntegrityError doesn't break the outer transaction
        with transaction.atomic():
            sid = transaction.savepoint()
            try:
                SyncEvent.objects.create(
                    event_id=event_id,
                    event_type=event_type,
                    subscription_external_id=subscription_external_id,
                    status="PROCESSED",
                    payload_hash=hashlib.sha256(
                        str(subscription_data).encode()
                    ).hexdigest(),
                )
                transaction.savepoint_commit(sid)
                return False  # Newly created
            except IntegrityError:
                transaction.savepoint_rollback(sid)
                return True  # Already exists
    except Exception:
        # If anything else goes wrong, assume event not recorded
        return False


class SubscriptionAccessService:
    """
    Helper service for Core to check subscription access.
    Clean interface for Core application code to determine if a cafe has access.
    """

    @staticmethod
    def has_active_subscription(cafe_id: int) -> bool:
        """
        Check if a cafe has an active subscription.
        
        A subscription is active if:
        - status == ACTIVE
        - expires_at > now
        
        Args:
            cafe_id: Core Cafe ID
            
        Returns:
            True if cafe has an active subscription
        """
        try:
            cafe_info = CafeInfo.objects.get(cafe_id=cafe_id)
            return Subscription.objects.filter(
                cafe=cafe_info,
                status="ACTIVE",
                expires_at__gt=timezone.now(),
            ).exists()
        except CafeInfo.DoesNotExist:
            return False

    @staticmethod
    def has_active_subscription_by_external_id(cafe_external_id: uuid.UUID) -> bool:
        """
        Check if a cafe has an active subscription using external_id.
        
        Args:
            cafe_external_id: SaaS cafe external ID
            
        Returns:
            True if cafe has an active subscription
        """
        try:
            cafe_info = CafeInfo.objects.get(cafe__external_id=cafe_external_id)
            return Subscription.objects.filter(
                cafe=cafe_info,
                status="ACTIVE",
                expires_at__gt=timezone.now(),
            ).exists()
        except CafeInfo.DoesNotExist:
            return False

    @staticmethod
    def get_current_subscription(cafe_id: int) -> Optional[Subscription]:
        """
        Get the current active subscription for a cafe.
        
        Args:
            cafe_id: Core Cafe ID
            
        Returns:
            Active Subscription or None
        """
        try:
            cafe_info = CafeInfo.objects.get(cafe_id=cafe_id)
            return Subscription.objects.filter(
                cafe=cafe_info,
                status="ACTIVE",
                expires_at__gt=timezone.now(),
            ).select_related("plan").first()
        except CafeInfo.DoesNotExist:
            return None


def _parse_datetime(value):
    """Parse a datetime value from various formats."""
    if value is None:
        return None
    if isinstance(value, timezone.datetime):
        return value
    if isinstance(value, str):
        from django.utils.dateparse import parse_datetime
        parsed = parse_datetime(value)
        if parsed is not None:
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed)
            return parsed
    return None
