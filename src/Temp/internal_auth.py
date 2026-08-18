"""
Internal authentication for service-to-service communication.
Uses X-Internal-API-Key header for authentication.
"""
import hmac
import hashlib
import logging
from rest_framework import authentication, exceptions
from django.conf import settings

logger = logging.getLogger(__name__)


class InternalApiKeyAuthentication(authentication.BaseAuthentication):
    """
    Authentication class for internal API endpoints.
    Uses X-Internal-API-Key header for service-to-service authentication.
    """

    keyword = 'X-Internal-API-Key'

    def authenticate(self, request):
        api_key = request.headers.get(self.keyword)

        if not api_key:
            raise exceptions.AuthenticationFailed(
                'Missing internal API key.'
            )

        # Get the internal API key from settings
        valid_api_key = getattr(settings, 'INTERNAL_API_KEY', None)

        if not valid_api_key:
            raise exceptions.AuthenticationFailed(
                'Internal API key not configured on server.'
            )

        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(str(api_key), str(valid_api_key)):
            raise exceptions.AuthenticationFailed(
                'Invalid internal API key.'
            )

        # Return None for user since this is service-to-service auth
        # The view will handle the actual business logic
        return (None, api_key)

    def authenticate_header(self, request):
        return self.keyword


class HmacSyncAuthentication(authentication.BaseAuthentication):
    """
    HMAC-SHA256 authentication for SaaS → Core sync endpoint.

    Verifies:
    - X-Menuno-Signature: HMAC-SHA256(secret, timestamp + "." + raw_body)
    - X-Menuno-Timestamp: ISO-8601, must be within MAX_TIMESTAMP_DRIFT seconds
    - X-Menuno-Event-Id: UUID present for idempotency tracking

    Signature algorithm:
        HMAC-SHA256(MENUNO_CORE_SYNC_SECRET, timestamp + "." + raw_body)

    Uses constant-time comparison via hmac.compare_digest().
    """

    MAX_TIMESTAMP_DRIFT_SECONDS = 300  # 5 minutes

    def authenticate(self, request):
        secret = getattr(settings, 'MENUNO_CORE_SYNC_SECRET', None)
        if not secret:
            raise exceptions.AuthenticationFailed(
                'MENUNO_CORE_SYNC_SECRET not configured on server.'
            )

        signature = request.headers.get('X-Menuno-Signature')
        timestamp = request.headers.get('X-Menuno-Timestamp')
        event_id = request.headers.get('X-Menuno-Event-Id')

        if not signature:
            raise exceptions.AuthenticationFailed(
                'Missing X-Menuno-Signature header.'
            )
        if not timestamp:
            raise exceptions.AuthenticationFailed(
                'Missing X-Menuno-Timestamp header.'
            )
        if not event_id:
            raise exceptions.AuthenticationFailed(
                'Missing X-Menuno-Event-Id header.'
            )

        # Validate timestamp freshness
        import datetime as _dt
        from django.utils.dateparse import parse_datetime
        from django.utils import timezone

        ts = parse_datetime(timestamp)
        if ts is None:
            raise exceptions.AuthenticationFailed(
                'Invalid X-Menuno-Timestamp format. Must be ISO-8601.'
            )

        # Ensure both datetimes are timezone-aware for safe subtraction.
        # parse_datetime returns aware when input has +HH:MM, but
        # timezone.now() can be naive when USE_TZ=False.
        _utc = _dt.timezone.utc
        if timezone.is_naive(ts):
            ts = timezone.make_aware(ts, _utc)
        now = timezone.now()
        if timezone.is_naive(now):
            now = timezone.make_aware(now, _utc)

        drift = abs((now - ts).total_seconds())
        if drift > self.MAX_TIMESTAMP_DRIFT_SECONDS:
            raise exceptions.AuthenticationFailed(
                f'Request timestamp expired. Drift: {drift:.0f}s, '
                f'max allowed: {self.MAX_TIMESTAMP_DRIFT_SECONDS}s.'
            )

        # Read raw body for HMAC verification
        raw_body = request.body
        if not raw_body:
            raise exceptions.AuthenticationFailed(
                'Empty request body.'
            )

        # Compute expected signature
        message = (timestamp + ".").encode('utf-8') + raw_body
        expected = hmac.new(
            secret.encode('utf-8'),
            message,
            hashlib.sha256,
        ).hexdigest()

        # Safe diagnostic logging (no secrets exposed)
        logger.info(
            "HMAC auth diagnostic: secret_configured=%s, secret_length=%d, "
            "received_sig_length=%d, expected_sig_length=%d, sig_match=%s",
            bool(secret),
            len(secret) if secret else 0,
            len(signature),
            len(expected),
            hmac.compare_digest(signature, expected),
        )

        if not hmac.compare_digest(signature, expected):
            raise exceptions.AuthenticationFailed(
                'Invalid HMAC signature.'
            )

        return (None, {
            'event_id': event_id,
            'timestamp': timestamp,
        })

    def authenticate_header(self, request):
        return 'HMAC'
