"""
Tests for HMAC-authenticated SaaS → Core sync endpoint.

Tests cover:
1. Valid HMAC request → accepted
2. Missing signature → rejected (401)
3. Invalid signature → rejected (401)
4. Expired timestamp → rejected (401)
5. Missing event ID → rejected (401)
6. Duplicate event ID → idempotent response
7. Malformed JSON → rejected (400)
8. Valid request without CSRF cookie → MUST be accepted
9. Normal browser/API endpoints → CSRF behavior remains unchanged
10. Plan sync via core endpoint
11. Subscription lifecycle via core endpoint
"""
import uuid
import json
import hashlib
import hmac as hmac_mod
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from app.cafe.models import Cafe, CafeUser, CafeInfo, Plan, Subscription, SyncEvent
from Temp.internal_auth import HmacSyncAuthentication

User = get_user_model()

TEST_SYNC_SECRET = "test-hmac-secret-for-core-sync-12345"


def make_hmac_signature(secret, timestamp, raw_body):
    """Compute HMAC-SHA256 signature matching the server's algorithm."""
    message = (timestamp + ".").encode("utf-8") + raw_body
    return hmac_mod.new(
        secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


class CoreSyncTestBase(TestCase):
    """Base test class with common setup for core sync tests."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/internal/integration/core/sync/"
        self.secret = TEST_SYNC_SECRET

        # Create user
        self.user = User.objects.create_user(mobile="09120000002")

        # Create cafe and cafe info
        self.cafe_external_id = uuid.uuid4()
        self.cafe = Cafe.objects.create(
            name="Core Sync Test Cafe",
            slug="core-sync-test-cafe",
            is_active=True,
            external_id=self.cafe_external_id,
        )
        self.cafe_info = CafeInfo.objects.create(cafe=self.cafe)
        self.cafe_user = CafeUser.objects.create(
            cafe=self.cafe, user=self.user, role="owner"
        )

    def make_plan_data(self, **overrides):
        data = {
            "external_id": str(uuid.uuid4()),
            "slug": "professional",
            "title": "Professional",
            "price": 500000,
            "duration_days": 30,
            "max_products": 500,
            "is_active": True,
            "version": 1,
        }
        data.update(overrides)
        return data

    def make_subscription_payload(self, **overrides):
        plan_data = overrides.pop("plan", self.make_plan_data())
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "subscription.activated",
            "subscription_id": str(uuid.uuid4()),
            "cafe_id": str(self.cafe_external_id),
            "plan": plan_data,
            "status": "ACTIVE",
            "started_at": timezone.now().isoformat(),
            "expires_at": (timezone.now() + timedelta(days=30)).isoformat(),
            "version": 1,
            "occurred_at": timezone.now().isoformat(),
        }
        payload.update(overrides)
        return payload

    def make_plan_payload(self, **overrides):
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "plan.synced",
            "plan": self.make_plan_data(),
            "occurred_at": timezone.now().isoformat(),
        }
        payload.update(overrides)
        return payload

    def sign_and_send(self, payload, timestamp=None, secret=None, event_id=None):
        """Sign a payload with HMAC and send to the core sync endpoint."""
        secret = secret or self.secret
        timestamp = timestamp or timezone.now().isoformat()
        raw_body = json.dumps(payload).encode("utf-8")
        signature = make_hmac_signature(secret, timestamp, raw_body)

        headers = {
            "HTTP_X_MENUNO_SIGNATURE": signature,
            "HTTP_X_MENUNO_TIMESTAMP": timestamp,
            "HTTP_X_MENUNO_EVENT_ID": event_id or payload.get("event_id", str(uuid.uuid4())),
        }

        return self.client.post(
            self.url,
            data=raw_body,
            content_type="application/json",
            **headers,
        )


class CoreSyncHmacAuthTest(CoreSyncTestBase):
    """Tests for HMAC authentication on the core sync endpoint."""

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_valid_hmac_request_accepted(self):
        """Test 1: Valid HMAC-signed request is accepted."""
        payload = self.make_plan_payload()

        response = self.sign_and_send(payload)

        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_missing_signature_rejected(self):
        """Test 2: Missing X-Menuno-Signature header → 401."""
        payload = self.make_plan_payload()
        raw_body = json.dumps(payload).encode("utf-8")
        timestamp = timezone.now().isoformat()

        headers = {
            "HTTP_X_MENUNO_TIMESTAMP": timestamp,
            "HTTP_X_MENUNO_EVENT_ID": payload["event_id"],
        }

        response = self.client.post(self.url, data=raw_body, content_type="application/json", **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_invalid_signature_rejected(self):
        """Test 3: Invalid HMAC signature → 401."""
        payload = self.make_plan_payload()
        timestamp = timezone.now().isoformat()

        response = self.sign_and_send(payload, timestamp=timestamp, secret="wrong-secret")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_expired_timestamp_rejected(self):
        """Test 4: Timestamp older than 5 minutes → 401."""
        payload = self.make_plan_payload()
        old_timestamp = (timezone.now() - timedelta(minutes=10)).isoformat()

        response = self.sign_and_send(payload, timestamp=old_timestamp)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_missing_event_id_rejected(self):
        """Test 5: Missing X-Menuno-Event-Id → 401."""
        payload = self.make_plan_payload()
        raw_body = json.dumps(payload).encode("utf-8")
        timestamp = timezone.now().isoformat()
        signature = make_hmac_signature(self.secret, timestamp, raw_body)

        headers = {
            "HTTP_X_MENUNO_SIGNATURE": signature,
            "HTTP_X_MENUNO_TIMESTAMP": timestamp,
        }

        response = self.client.post(self.url, data=raw_body, content_type="application/json", **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_duplicate_event_id_idempotent(self):
        """Test 6: Duplicate event_id returns same response (idempotent)."""
        plan_data = self.make_plan_data()
        event_id = str(uuid.uuid4())
        payload = self.make_plan_payload(event_id=event_id, plan=plan_data)

        response1 = self.sign_and_send(payload, event_id=event_id)
        self.assertIn(
            response1.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

        # Second request with same event_id
        response2 = self.sign_and_send(payload, event_id=event_id)
        self.assertIn(
            response2.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

        # Only one plan should exist
        self.assertEqual(
            Plan.objects.filter(external_id=uuid.UUID(plan_data["external_id"])).count(),
            1,
        )

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_malformed_json_rejected(self):
        """Test 7: Malformed JSON body → 400."""
        timestamp = timezone.now().isoformat()
        raw_body = b"not valid json {{{"
        signature = make_hmac_signature(self.secret, timestamp, raw_body)

        headers = {
            "HTTP_X_MENUNO_SIGNATURE": signature,
            "HTTP_X_MENUNO_TIMESTAMP": timestamp,
            "HTTP_X_MENUNO_EVENT_ID": str(uuid.uuid4()),
        }

        response = self.client.post(self.url, data=raw_body, content_type="application/json", **headers)
        # DRF returns 415 (Unsupported Media Type) or 400 for bad JSON
        self.assertIn(
            response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE],
        )

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_valid_request_without_csrf_cookie_accepted(self):
        """Test 8: Request without CSRF cookie MUST be accepted (server-to-server)."""
        self.client.cookies.clear()  # Ensure no CSRF cookie
        payload = self.make_plan_payload()

        response = self.sign_and_send(payload)

        # Must NOT be 403 CSRF Forbidden
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

    def test_csrf_protection_unchanged_on_other_endpoints(self):
        """Test 9: CSRF protection remains on other API endpoints."""
        from django.conf import settings
        self.assertIn(
            'django.middleware.csrf.CsrfViewMiddleware',
            settings.MIDDLEWARE,
        )

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_missing_timestamp_rejected(self):
        """Missing X-Menuno-Timestamp → 401."""
        payload = self.make_plan_payload()
        raw_body = json.dumps(payload).encode("utf-8")
        signature = make_hmac_signature(self.secret, timezone.now().isoformat(), raw_body)

        headers = {
            "HTTP_X_MENUNO_SIGNATURE": signature,
            "HTTP_X_MENUNO_EVENT_ID": payload["event_id"],
        }

        response = self.client.post(self.url, data=raw_body, content_type="application/json", **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CoreSyncPlanTest(CoreSyncTestBase):
    """Tests for plan sync via HMAC endpoint."""

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_plan_sync_creates_plan(self):
        """Valid plan sync creates a new plan."""
        plan_data = self.make_plan_data()
        payload = self.make_plan_payload(plan=plan_data)

        response = self.sign_and_send(payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "CREATED")

        result = response.data["result"]
        self.assertTrue(result["created"])
        self.assertEqual(result["slug"], "professional")

        # Verify in database
        plan = Plan.objects.get(external_id=uuid.UUID(plan_data["external_id"]))
        self.assertEqual(plan.slug, "professional")
        self.assertEqual(plan.price, 500000)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_plan_sync_updates_existing(self):
        """Re-sync updates existing plan instead of duplicating."""
        plan_data = self.make_plan_data(version=1)
        payload = self.make_plan_payload(plan=plan_data)

        self.sign_and_send(payload)

        # Update plan data
        plan_data["title"] = "Professional V2"
        plan_data["version"] = 2
        payload["event_id"] = str(uuid.uuid4())
        payload["plan"] = plan_data

        response = self.sign_and_send(payload)
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

        plan = Plan.objects.get(external_id=uuid.UUID(plan_data["external_id"]))
        self.assertEqual(plan.title, "Professional V2")
        self.assertEqual(plan.version, 2)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_plan_sync_missing_fields_returns_400(self):
        """Missing required plan fields → 400."""
        payload = self.make_plan_payload()
        payload["plan"] = {"external_id": str(uuid.uuid4())}  # Missing required fields

        response = self.sign_and_send(payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CoreSyncSubscriptionTest(CoreSyncTestBase):
    """Tests for subscription sync via HMAC endpoint."""

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_subscription_activated_creates(self):
        """Valid subscription activation creates subscription."""
        payload = self.make_subscription_payload()

        response = self.sign_and_send(payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "CREATED")

        result = response.data["result"]
        self.assertTrue(result["created"])
        self.assertEqual(result["status"], "ACTIVE")

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_subscription_expired_updates(self):
        """Subscription activation then expiration."""
        sub_id = uuid.uuid4()
        plan_data = self.make_plan_data()

        # Activate
        payload = self.make_subscription_payload(
            subscription_id=str(sub_id),
            status="ACTIVE",
            version=1,
            plan=plan_data,
        )
        self.sign_and_send(payload)

        # Expire
        payload = self.make_subscription_payload(
            subscription_id=str(sub_id),
            event_type="subscription.expired",
            status="EXPIRED",
            version=2,
            plan=plan_data,
        )
        response = self.sign_and_send(payload)
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

        sub = Subscription.objects.get(external_id=sub_id)
        self.assertEqual(sub.status, "EXPIRED")

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_subscription_cancelled_updates(self):
        """Subscription activation then cancellation."""
        sub_id = uuid.uuid4()
        plan_data = self.make_plan_data()

        # Activate
        payload = self.make_subscription_payload(
            subscription_id=str(sub_id),
            status="ACTIVE",
            version=1,
            plan=plan_data,
        )
        self.sign_and_send(payload)

        # Cancel
        payload = self.make_subscription_payload(
            subscription_id=str(sub_id),
            event_type="subscription.cancelled",
            status="CANCELLED",
            version=2,
            plan=plan_data,
        )
        response = self.sign_and_send(payload)
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

        sub = Subscription.objects.get(external_id=sub_id)
        self.assertEqual(sub.status, "CANCELLED")

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_stale_event_does_not_overwrite(self):
        """Older version event does not overwrite newer version."""
        sub_id = uuid.uuid4()
        plan_data = self.make_plan_data()

        # Sync with version 2
        payload = self.make_subscription_payload(
            subscription_id=str(sub_id),
            status="ACTIVE",
            version=2,
            plan=plan_data,
        )
        self.sign_and_send(payload)

        # Try to sync with version 1 (stale)
        payload = self.make_subscription_payload(
            subscription_id=str(sub_id),
            event_type="subscription.cancelled",
            status="CANCELLED",
            version=1,
            plan=plan_data,
        )
        self.sign_and_send(payload)

        sub = Subscription.objects.get(external_id=sub_id)
        self.assertEqual(sub.status, "ACTIVE")
        self.assertEqual(sub.version, 2)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_unknown_cafe_returns_400(self):
        """Unknown cafe external ID → 400."""
        payload = self.make_subscription_payload(cafe_id=str(uuid.uuid4()))

        response = self.sign_and_send(payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_unknown_event_type_returns_400(self):
        """Unknown event_type → 400."""
        payload = self.make_subscription_payload()
        payload["event_type"] = "unknown.event"

        response = self.sign_and_send(payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_sync_event_recorded(self):
        """SyncEvent is recorded for processed events."""
        event_id = uuid.uuid4()
        payload = self.make_subscription_payload(event_id=str(event_id))

        response = self.sign_and_send(payload, event_id=str(event_id))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        sync_event = SyncEvent.objects.get(event_id=event_id)
        self.assertEqual(sync_event.event_type, "subscription.activated")
        self.assertEqual(sync_event.status, "PROCESSED")


class CoreSyncEdgeCasesTest(CoreSyncTestBase):
    """Edge case tests for the core sync endpoint."""

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_empty_body_rejected(self):
        """Empty request body → 401 (empty body cannot be signed)."""
        timestamp = timezone.now().isoformat()
        raw_body = b""
        signature = make_hmac_signature(self.secret, timestamp, raw_body)

        headers = {
            "HTTP_X_MENUNO_SIGNATURE": signature,
            "HTTP_X_MENUNO_TIMESTAMP": timestamp,
            "HTTP_X_MENUNO_EVENT_ID": str(uuid.uuid4()),
        }

        response = self.client.post(self.url, data=raw_body, content_type="application/json", **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_timestamp_at_boundary_accepted(self):
        """Timestamp exactly at 5-minute drift boundary is accepted."""
        plan_data = self.make_plan_data()
        payload = self.make_plan_payload(plan=plan_data)
        boundary_ts = (timezone.now() - timedelta(seconds=299)).isoformat()

        response = self.sign_and_send(payload, timestamp=boundary_ts)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_timestamp_just_beyond_boundary_rejected(self):
        """Timestamp just past 5-minute drift → 401."""
        payload = self.make_plan_payload()
        old_ts = (timezone.now() - timedelta(seconds=301)).isoformat()

        response = self.sign_and_send(payload, timestamp=old_ts)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_plan_and_subscription_independent_idempotency(self):
        """Plan and subscription events have independent idempotency."""
        plan_data = self.make_plan_data()

        # Plan sync
        plan_payload = self.make_plan_payload(plan=plan_data)
        self.sign_and_send(plan_payload)

        # Subscription sync with same plan
        sub_payload = self.make_subscription_payload(plan=plan_data)
        response = self.sign_and_send(sub_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Plan still exists
        self.assertTrue(
            Plan.objects.filter(external_id=uuid.UUID(plan_data["external_id"])).exists()
        )


class RegressionTest(CoreSyncTestBase):
    """
    Regression tests to verify the CSRF fix didn't break anything else.
    """

    def test_login_endpoint_not_affected_by_csrf_change(self):
        """A: Login POST request must still work (not blocked by CSRF).
        DRF's APIView.as_view() returns csrf_exempt=True, so SimpleJWT login
        should bypass Django's CsrfViewMiddleware.
        """
        from rest_framework_simplejwt.views import TokenObtainPairView
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Create a user to login with
        user = User.objects.create_user(mobile="09120000099", password="testpass123")

        # Attempt login without CSRF cookie - must NOT get 403
        response = self.client.post(
            "/api/token/",
            data=json.dumps({"mobile": "09120000099", "password": "testpass123"}),
            content_type="application/json",
        )
        # Must not be CSRF 403 (may be 400/401 for wrong credentials, but not 403)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_core_sync_url_resolves_to_correct_view(self):
        """C: /api/internal/core/sync/ resolves to CoreSyncAPIView."""
        from django.urls import resolve
        match = resolve('/api/internal/core/sync/')
        self.assertEqual(match.func.cls.__name__, 'CoreSyncAPIView')

    def test_core_sync_requires_hmac_auth(self):
        """D: POST to core sync without HMAC headers → 401."""
        payload = self.make_plan_payload()
        # Send without HMAC headers (just plain JSON)
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_core_sync_rejects_invalid_hmac(self):
        """E: POST to core sync with invalid HMAC → 401."""
        payload = self.make_plan_payload()
        response = self.sign_and_send(payload, secret="totally-wrong-secret")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_core_sync_rejects_expired_timestamp(self):
        """F: POST to core sync with expired timestamp → 401."""
        payload = self.make_plan_payload()
        old_ts = (timezone.now() - timedelta(hours=1)).isoformat()
        response = self.sign_and_send(payload, timestamp=old_ts)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_csrf_middleware_still_enabled_globally(self):
        """Verify CsrfViewMiddleware is still in the middleware stack."""
        from django.conf import settings
        self.assertIn(
            'django.middleware.csrf.CsrfViewMiddleware',
            settings.MIDDLEWARE,
        )


class TimezoneHandlingTest(CoreSyncTestBase):
    """
    Tests for timezone-aware datetime handling in HMAC authentication.

    Regression: TypeError: can't subtract offset-naive and offset-aware datetimes.
    Caused by USE_TZ=False making timezone.now() naive while parse_datetime()
    returns aware for ISO-8601 strings with timezone offsets.
    """

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_valid_timestamp_with_plus_zero_offset_accepted(self):
        """ISO-8601 timestamp with +00:00 → accepted."""
        payload = self.make_plan_payload()
        now_utc = timezone.now()
        # Manually build the ISO-8601 string with explicit +00:00
        ts_str = now_utc.strftime('%Y-%m-%dT%H:%M:%S.%f+00:00')

        response = self.sign_and_send(payload, timestamp=ts_str)
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_valid_timestamp_with_positive_offset_accepted(self):
        """ISO-8601 timestamp with +05:30 → correctly normalized and compared."""
        payload = self.make_plan_payload()
        now_utc = timezone.now()
        # Build a timestamp that is 5h30m AHEAD of UTC (so it's 5h30m earlier in UTC)
        from datetime import timezone as dt_timezone
        plus_530 = dt_timezone(timedelta(hours=5, minutes=30))
        ts_dt = now_utc.replace(tzinfo=None).astimezone(plus_530)
        ts_str = ts_dt.strftime('%Y-%m-%dT%H:%M:%S.%f+05:30')

        response = self.sign_and_send(payload, timestamp=ts_str)
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_valid_timestamp_with_negative_offset_accepted(self):
        """ISO-8601 timestamp with -08:00 → correctly normalized and compared."""
        payload = self.make_plan_payload()
        now_utc = timezone.now()
        from datetime import timezone as dt_timezone
        minus_8 = dt_timezone(timedelta(hours=-8))
        ts_dt = now_utc.replace(tzinfo=None).astimezone(minus_8)
        ts_str = ts_dt.strftime('%Y-%m-%dT%H:%M:%S.%f-08:00')

        response = self.sign_and_send(payload, timestamp=ts_str)
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_timestamp_without_offset_treated_as_utc(self):
        """ISO-8601 timestamp without timezone → treated as UTC (naive → aware)."""
        payload = self.make_plan_payload()
        now_utc = timezone.now()
        ts_str = now_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')

        response = self.sign_and_send(payload, timestamp=ts_str)
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_expired_timestamp_rejected(self):
        """Timestamp 10 minutes old → rejected (beyond 5 min drift)."""
        payload = self.make_plan_payload()
        old_ts = (timezone.now() - timedelta(minutes=10)).isoformat()

        response = self.sign_and_send(payload, timestamp=old_ts)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_future_timestamp_outside_tolerance_rejected(self):
        """Timestamp 10 minutes in the future → rejected."""
        payload = self.make_plan_payload()
        future_ts = (timezone.now() + timedelta(minutes=10)).isoformat()

        response = self.sign_and_send(payload, timestamp=future_ts)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_malformed_timestamp_rejected(self):
        """Malformed timestamp string → 401."""
        payload = self.make_plan_payload()
        raw_body = json.dumps(payload).encode("utf-8")
        bad_ts = "not-a-timestamp"
        signature = make_hmac_signature(self.secret, bad_ts, raw_body)

        headers = {
            "HTTP_X_MENUNO_SIGNATURE": signature,
            "HTTP_X_MENUNO_TIMESTAMP": bad_ts,
            "HTTP_X_MENUNO_EVENT_ID": payload["event_id"],
        }
        response = self.client.post(self.url, data=raw_body, content_type="application/json", **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_missing_timestamp_rejected(self):
        """Missing X-Menuno-Timestamp → 401."""
        payload = self.make_plan_payload()
        raw_body = json.dumps(payload).encode("utf-8")
        signature = make_hmac_signature(self.secret, "dummy-ts", raw_body)

        headers = {
            "HTTP_X_MENUNO_SIGNATURE": signature,
            "HTTP_X_MENUNO_EVENT_ID": payload["event_id"],
        }
        response = self.client.post(self.url, data=raw_body, content_type="application/json", **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_valid_hmac_and_valid_timestamp_succeeds(self):
        """Valid HMAC signature + valid timestamp → 200/201."""
        payload = self.make_plan_payload()

        response = self.sign_and_send(payload)
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_invalid_hmac_rejected(self):
        """Invalid HMAC signature → 401 regardless of valid timestamp."""
        payload = self.make_plan_payload()

        response = self.sign_and_send(payload, secret="wrong-secret-key")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class HmacSecurityTests(CoreSyncTestBase):
    """Focused security tests for HMAC authentication."""

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_correct_secret_and_signature_accepted(self):
        """Correct secret + correct signature → 200/accepted."""
        payload = self.make_plan_payload()

        response = self.sign_and_send(payload)
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_wrong_secret_rejected(self):
        """Wrong secret → 401."""
        payload = self.make_plan_payload()

        response = self.sign_and_send(payload, secret="completely-wrong-secret")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_modified_body_rejected(self):
        """Modified body after signing → 401."""
        payload = self.make_plan_payload()
        timestamp = timezone.now().isoformat()
        raw_body = json.dumps(payload).encode("utf-8")
        signature = make_hmac_signature(self.secret, timestamp, raw_body)

        # Send with modified body (different content)
        modified_payload = payload.copy()
        modified_payload["price"] = 999999
        modified_body = json.dumps(modified_payload).encode("utf-8")

        headers = {
            "HTTP_X_MENUNO_SIGNATURE": signature,
            "HTTP_X_MENUNO_TIMESTAMP": timestamp,
            "HTTP_X_MENUNO_EVENT_ID": payload["event_id"],
        }

        response = self.client.post(
            self.url,
            data=modified_body,
            content_type="application/json",
            **headers,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_modified_timestamp_rejected(self):
        """Modified timestamp after signing → 401."""
        payload = self.make_plan_payload()
        timestamp = timezone.now().isoformat()
        raw_body = json.dumps(payload).encode("utf-8")
        signature = make_hmac_signature(self.secret, timestamp, raw_body)

        # Send with different timestamp
        modified_timestamp = (timezone.now() + timedelta(seconds=10)).isoformat()

        headers = {
            "HTTP_X_MENUNO_SIGNATURE": signature,
            "HTTP_X_MENUNO_TIMESTAMP": modified_timestamp,
            "HTTP_X_MENUNO_EVENT_ID": payload["event_id"],
        }

        response = self.client.post(
            self.url,
            data=raw_body,
            content_type="application/json",
            **headers,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_modified_event_id_rejected(self):
        """Modified event_id after signing → 401 (signature includes full body with event_id)."""
        payload = self.make_plan_payload()
        timestamp = timezone.now().isoformat()
        raw_body = json.dumps(payload).encode("utf-8")
        signature = make_hmac_signature(self.secret, timestamp, raw_body)

        # Modify event_id in payload
        modified_payload = payload.copy()
        modified_payload["event_id"] = str(uuid.uuid4())
        modified_body = json.dumps(modified_payload).encode("utf-8")

        headers = {
            "HTTP_X_MENUNO_SIGNATURE": signature,
            "HTTP_X_MENUNO_TIMESTAMP": timestamp,
            "HTTP_X_MENUNO_EVENT_ID": modified_payload["event_id"],
        }

        response = self.client.post(
            self.url,
            data=modified_body,
            content_type="application/json",
            **headers,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_missing_signature_rejected(self):
        """Missing X-Menuno-Signature → 401."""
        payload = self.make_plan_payload()
        raw_body = json.dumps(payload).encode("utf-8")
        timestamp = timezone.now().isoformat()

        headers = {
            "HTTP_X_MENUNO_TIMESTAMP": timestamp,
            "HTTP_X_MENUNO_EVENT_ID": payload["event_id"],
        }

        response = self.client.post(
            self.url,
            data=raw_body,
            content_type="application/json",
            **headers,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_malformed_signature_rejected(self):
        """Malformed signature → 401."""
        payload = self.make_plan_payload()
        timestamp = timezone.now().isoformat()

        headers = {
            "HTTP_X_MENUNO_SIGNATURE": "not-a-valid-hex-signature",
            "HTTP_X_MENUNO_TIMESTAMP": timestamp,
            "HTTP_X_MENUNO_EVENT_ID": payload["event_id"],
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_expired_timestamp_rejected(self):
        """Expired timestamp → 401."""
        payload = self.make_plan_payload()
        old_timestamp = (timezone.now() - timedelta(minutes=10)).isoformat()

        response = self.sign_and_send(payload, timestamp=old_timestamp)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_valid_timestamp_accepted(self):
        """Valid timestamp → accepted."""
        payload = self.make_plan_payload()

        response = self.sign_and_send(payload)
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_valid_request_without_csrf_cookie_accepted(self):
        """Valid request without CSRF cookie → accepted (server-to-server)."""
        self.client.cookies.clear()
        payload = self.make_plan_payload()

        response = self.sign_and_send(payload)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

    @override_settings(MENUNO_CORE_SYNC_SECRET=TEST_SYNC_SECRET)
    def test_duplicate_event_id_idempotent(self):
        """Duplicate event_id → idempotent behavior."""
        plan_data = self.make_plan_data()
        event_id = str(uuid.uuid4())
        payload = self.make_plan_payload(event_id=event_id, plan=plan_data)

        # First request
        response1 = self.sign_and_send(payload, event_id=event_id)
        self.assertIn(
            response1.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

        # Second request with same event_id
        response2 = self.sign_and_send(payload, event_id=event_id)
        self.assertIn(
            response2.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

        # Only one plan should exist
        self.assertEqual(
            Plan.objects.filter(external_id=uuid.UUID(plan_data["external_id"])).count(),
            1,
        )
