"""
Tests for SaaS ↔ Core synchronization endpoints.

Core sync tests cover:
1. Valid SaaS synchronization request (plan + subscription)
2. Invalid authentication → 401
3. Invalid payload → 400
4. New subscription is created
5. Existing subscription is updated instead of duplicated
6. Duplicate event is idempotent (same event_id)
7. Concurrent duplicate events do not create duplicate subscriptions
8. ACTIVE → EXPIRED synchronization
9. ACTIVE → CANCELLED synchronization
10. Out-of-order stale events do not overwrite newer state
11. Plan synchronization is idempotent
12. Unknown cafe/external ID is handled safely
"""
import uuid
from unittest.mock import patch
from datetime import timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from app.cafe.models import Cafe, CafeUser, CafeInfo, Plan, Subscription, SyncEvent

User = get_user_model()


class SyncTestBase(TestCase):
    """Base test class with common setup for sync tests."""

    def setUp(self):
        self.client = APIClient()
        self.valid_api_key = "test-sync-api-key-12345"
        self.settings_patcher = patch(
            "django.conf.settings.INTERNAL_API_KEY", self.valid_api_key
        )
        self.settings_patcher.start()

        # Create user
        self.user = User.objects.create_user(mobile="09120000001")

        # Create cafe and cafe info (simulates what the integration/cafe creation does)
        self.cafe_external_id = uuid.uuid4()
        self.cafe = Cafe.objects.create(
            name="Test Sync Cafe",
            slug="test-sync-cafe",
            is_active=True,
            external_id=self.cafe_external_id,
        )
        self.cafe_info = CafeInfo.objects.create(cafe=self.cafe)
        self.cafe_user = CafeUser.objects.create(
            cafe=self.cafe, user=self.user, role="owner"
        )

    def tearDown(self):
        self.settings_patcher.stop()

    def get_headers(self, api_key=None):
        if api_key is None:
            api_key = self.valid_api_key
        return {"HTTP_X_INTERNAL_API_KEY": api_key}

    def make_plan_data(self, **overrides):
        """Helper to create plan data dict."""
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


class PlanSyncAPITest(SyncTestBase):
    """Tests for plan synchronization endpoint."""

    def setUp(self):
        super().setUp()
        self.url = "/api/internal/integration/sync/plan/"

    def test_valid_plan_sync_creates_plan(self):
        """Test 1: Valid plan sync creates a new plan."""
        plan_data = self.make_plan_data()
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "plan.synced",
            "plan": plan_data,
            "occurred_at": timezone.now().isoformat(),
        }

        response = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "CREATED")

        result = response.data["result"]
        self.assertTrue(result["created"])
        self.assertEqual(result["slug"], "professional")
        self.assertEqual(result["title"], "Professional")

        # Verify in database
        plan = Plan.objects.get(external_id=uuid.UUID(plan_data["external_id"]))
        self.assertEqual(plan.slug, "professional")
        self.assertEqual(plan.price, 500000)
        self.assertEqual(plan.version, 1)

    def test_plan_sync_idempotent_on_duplicate_event(self):
        """Test 2: Duplicate event_id is handled safely."""
        event_id = uuid.uuid4()
        plan_data = self.make_plan_data()
        payload = {
            "event_id": str(event_id),
            "event_type": "plan.synced",
            "plan": plan_data,
            "occurred_at": timezone.now().isoformat(),
        }

        # First request - creates plan
        response1 = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second request with same event_id - should still succeed (idempotent)
        response2 = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        # Should return 200 (not created again) or 201 (idempotent creation)
        self.assertIn(
            response2.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

        # Only one plan should exist
        self.assertEqual(
            Plan.objects.filter(external_id=uuid.UUID(plan_data["external_id"])).count(),
            1,
        )

    def test_plan_sync_updates_existing_plan(self):
        """Test 3: Re-sync updates existing plan instead of duplicating."""
        plan_data = self.make_plan_data(version=1)
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "plan.synced",
            "plan": plan_data,
            "occurred_at": timezone.now().isoformat(),
        }

        # First sync
        response1 = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Update plan data with new version
        plan_data["title"] = "Professional V2"
        plan_data["price"] = 600000
        plan_data["version"] = 2
        payload["event_id"] = str(uuid.uuid4())  # New event
        payload["plan"] = plan_data

        response2 = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertIn(
            response2.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

        # Verify plan was updated, not duplicated
        plan = Plan.objects.get(external_id=uuid.UUID(plan_data["external_id"]))
        self.assertEqual(plan.title, "Professional V2")
        self.assertEqual(plan.price, 600000)
        self.assertEqual(plan.version, 2)
        self.assertEqual(Plan.objects.filter(external_id=uuid.UUID(plan_data["external_id"])).count(), 1)

    def test_plan_sync_stale_event_rejected(self):
        """Test 4: Older version event does not overwrite newer version."""
        plan_data = self.make_plan_data(version=2)
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "plan.synced",
            "plan": plan_data,
            "occurred_at": timezone.now().isoformat(),
        }

        # Sync with version 2
        response1 = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Try to sync with version 1 (stale event)
        plan_data["title"] = "Old Title"
        plan_data["version"] = 1
        payload["event_id"] = str(uuid.uuid4())
        payload["plan"] = plan_data

        response2 = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertIn(
            response2.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

        # Plan should still have version 2 data
        plan = Plan.objects.get(external_id=uuid.UUID(plan_data["external_id"]))
        self.assertEqual(plan.version, 2)
        self.assertNotEqual(plan.title, "Old Title")

    def test_missing_api_key_returns_401(self):
        """Test 5: Missing API key returns 401."""
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "plan.synced",
            "plan": self.make_plan_data(),
            "occurred_at": timezone.now().isoformat(),
        }

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_api_key_returns_401(self):
        """Test 6: Invalid API key returns 401."""
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "plan.synced",
            "plan": self.make_plan_data(),
            "occurred_at": timezone.now().isoformat(),
        }

        response = self.client.post(
            self.url, payload, format="json", **self.get_headers("wrong-key")
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_required_fields_returns_400(self):
        """Test 7: Missing required fields returns 400."""
        # Missing plan data
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "plan.synced",
            "occurred_at": timezone.now().isoformat(),
        }

        response = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_plan_data_returns_400(self):
        """Test 8: Invalid plan data returns 400."""
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "plan.synced",
            "plan": {
                "external_id": str(uuid.uuid4()),
                # Missing required fields: slug, title, price, duration_days
            },
            "occurred_at": timezone.now().isoformat(),
        }

        response = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SubscriptionSyncAPITest(SyncTestBase):
    """Tests for subscription synchronization endpoint."""

    def setUp(self):
        super().setUp()
        self.url = "/api/internal/integration/sync/subscription/"

    def make_subscription_payload(self, **overrides):
        """Helper to create subscription sync payload."""
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

    def test_valid_subscription_sync_creates_subscription(self):
        """Test 1: Valid subscription sync creates a new subscription."""
        payload = self.make_subscription_payload()

        response = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "CREATED")

        result = response.data["result"]
        self.assertTrue(result["created"])
        self.assertEqual(result["status"], "ACTIVE")

        # Verify in database
        sub = Subscription.objects.get(
            external_id=uuid.UUID(payload["subscription_id"])
        )
        self.assertEqual(sub.status, "ACTIVE")
        self.assertTrue(sub.is_active)

    def test_subscription_sync_creates_plan_if_needed(self):
        """Test 2: Subscription sync also creates the plan if it doesn't exist."""
        plan_data = self.make_plan_data()
        payload = self.make_subscription_payload(plan=plan_data)

        # Verify plan doesn't exist yet
        self.assertFalse(
            Plan.objects.filter(
                external_id=uuid.UUID(plan_data["external_id"])
            ).exists()
        )

        response = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Plan should now exist
        plan = Plan.objects.get(external_id=uuid.UUID(plan_data["external_id"]))
        self.assertEqual(plan.title, "Professional")

    def test_subscription_sync_idempotent_on_duplicate_event(self):
        """Test 3: Duplicate event_id is handled safely."""
        event_id = uuid.uuid4()
        payload = self.make_subscription_payload(event_id=str(event_id))

        # First request
        response1 = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second request with same event_id
        response2 = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertIn(
            response2.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

        # Only one subscription should exist
        self.assertEqual(
            Subscription.objects.filter(
                external_id=uuid.UUID(payload["subscription_id"])
            ).count(),
            1,
        )

    def test_subscription_sync_updates_existing(self):
        """Test 4: Re-sync updates existing subscription instead of duplicating."""
        sub_external_id = uuid.uuid4()
        plan_data = self.make_plan_data()  # Consistent plan data for both requests

        # First sync - ACTIVE
        payload = self.make_subscription_payload(
            subscription_id=str(sub_external_id),
            status="ACTIVE",
            version=1,
            plan=plan_data,
        )
        response1 = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second sync - EXPIRED with higher version (same plan)
        payload = self.make_subscription_payload(
            subscription_id=str(sub_external_id),
            event_type="subscription.expired",
            status="EXPIRED",
            version=2,
            plan=plan_data,
        )
        response2 = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertIn(
            response2.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

        # Should still be only one subscription
        self.assertEqual(
            Subscription.objects.filter(external_id=sub_external_id).count(), 1
        )

        # Should be updated to EXPIRED
        sub = Subscription.objects.get(external_id=sub_external_id)
        self.assertEqual(sub.status, "EXPIRED")
        self.assertFalse(sub.is_active)

    def test_subscription_activated_to_expired(self):
        """Test 5: ACTIVE → EXPIRED synchronization."""
        sub_external_id = uuid.uuid4()
        plan_data = self.make_plan_data()  # Consistent plan data

        # Activate
        payload = self.make_subscription_payload(
            subscription_id=str(sub_external_id),
            status="ACTIVE",
            version=1,
            plan=plan_data,
        )
        self.client.post(self.url, payload, format="json", **self.get_headers())

        # Expire
        payload = self.make_subscription_payload(
            subscription_id=str(sub_external_id),
            event_type="subscription.expired",
            status="EXPIRED",
            version=2,
            plan=plan_data,
        )
        response = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

        sub = Subscription.objects.get(external_id=sub_external_id)
        self.assertEqual(sub.status, "EXPIRED")

    def test_subscription_activated_to_cancelled(self):
        """Test 6: ACTIVE → CANCELLED synchronization."""
        sub_external_id = uuid.uuid4()
        plan_data = self.make_plan_data()  # Consistent plan data

        # Activate
        payload = self.make_subscription_payload(
            subscription_id=str(sub_external_id),
            status="ACTIVE",
            version=1,
            plan=plan_data,
        )
        self.client.post(self.url, payload, format="json", **self.get_headers())

        # Cancel
        payload = self.make_subscription_payload(
            subscription_id=str(sub_external_id),
            event_type="subscription.cancelled",
            status="CANCELLED",
            version=2,
            plan=plan_data,
        )
        response = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

        sub = Subscription.objects.get(external_id=sub_external_id)
        self.assertEqual(sub.status, "CANCELLED")

    def test_stale_event_does_not_overwrite_newer_state(self):
        """Test 7: Out-of-order stale events do not overwrite newer state."""
        sub_external_id = uuid.uuid4()
        plan_data = self.make_plan_data()  # Consistent plan data

        # Sync with version 2 (ACTIVE)
        payload = self.make_subscription_payload(
            subscription_id=str(sub_external_id),
            status="ACTIVE",
            version=2,
            plan=plan_data,
        )
        self.client.post(self.url, payload, format="json", **self.get_headers())

        # Try to sync with version 1 (CANCELLED) - stale event
        payload = self.make_subscription_payload(
            subscription_id=str(sub_external_id),
            event_type="subscription.cancelled",
            status="CANCELLED",
            version=1,
            plan=plan_data,
        )
        response = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )

        # Should still be ACTIVE (version 2)
        sub = Subscription.objects.get(external_id=sub_external_id)
        self.assertEqual(sub.status, "ACTIVE")
        self.assertEqual(sub.version, 2)

    def test_unknown_cafe_returns_400(self):
        """Test 8: Unknown cafe external ID returns 400."""
        payload = self.make_subscription_payload(
            cafe_id=str(uuid.uuid4()),  # Non-existent cafe
        )

        response = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_api_key_returns_401(self):
        """Test 9: Missing API key returns 401."""
        payload = self.make_subscription_payload()

        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_status_returns_400(self):
        """Test 10: Invalid status returns 400."""
        payload = self.make_subscription_payload(status="INVALID_STATUS")

        response = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_concurrent_duplicate_events_safety(self):
        """Test 11: Concurrent duplicate events don't create duplicates.
        
        NOTE: SQLite doesn't support proper SELECT FOR UPDATE locking.
        This test verifies the application-level idempotency.
        For production, PostgreSQL row-level locking would be used.
        """
        sub_external_id = uuid.uuid4()
        event_id = uuid.uuid4()

        # Simulate rapid duplicate requests
        payload = self.make_subscription_payload(
            subscription_id=str(sub_external_id),
            event_id=str(event_id),
        )

        responses = []
        for _ in range(5):
            response = self.client.post(
                self.url, payload, format="json", **self.get_headers()
            )
            responses.append(response.status_code)

        # All should succeed
        for code in responses:
            self.assertIn(
                code,
                [status.HTTP_200_OK, status.HTTP_201_CREATED],
            )

        # Only one subscription should exist
        self.assertEqual(
            Subscription.objects.filter(external_id=sub_external_id).count(), 1
        )

    def test_sync_event_recorded(self):
        """Test 12: SyncEvent is recorded for processed events."""
        event_id = uuid.uuid4()
        payload = self.make_subscription_payload(event_id=str(event_id))

        response = self.client.post(
            self.url, payload, format="json", **self.get_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify SyncEvent was recorded
        sync_event = SyncEvent.objects.get(event_id=event_id)
        self.assertEqual(sync_event.event_type, "subscription.activated")
        self.assertEqual(sync_event.status, "PROCESSED")
        self.assertIsNotNone(sync_event.created_at)  # Uses BaseModel.created_at

    def test_subscription_access_check(self):
        """Test 13: Subscription access check endpoint works."""
        access_url = "/api/internal/integration/subscription/access-check/"

        # Create an active subscription first
        sub_external_id = uuid.uuid4()
        payload = self.make_subscription_payload(
            subscription_id=str(sub_external_id),
            status="ACTIVE",
            started_at=timezone.now().isoformat(),
            expires_at=(timezone.now() + timedelta(days=30)).isoformat(),
        )
        self.client.post(self.url, payload, format="json", **self.get_headers())

        # Check access
        access_payload = {"cafe_external_id": str(self.cafe_external_id)}
        response = self.client.post(
            access_url, access_payload, format="json", **self.get_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["result"]["has_active_subscription"])


class SubscriptionAccessServiceTest(SyncTestBase):
    """Tests for SubscriptionAccessService helper."""

    def test_has_active_subscription_true(self):
        """Test: Returns True when cafe has active subscription."""
        from app.cafe.sync_services import SubscriptionAccessService

        # Create active subscription
        Plan.objects.create(
            external_id=uuid.uuid4(),
            slug="test-plan",
            title="Test Plan",
            price=100000,
            duration_days=30,
        )
        plan = Plan.objects.first()
        Subscription.objects.create(
            external_id=uuid.uuid4(),
            cafe=self.cafe_info,
            plan=plan,
            status="ACTIVE",
            started_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=30),
            is_active=True,
        )

        result = SubscriptionAccessService.has_active_subscription(self.cafe.id)
        self.assertTrue(result)

    def test_has_active_subscription_false_no_sub(self):
        """Test: Returns False when cafe has no subscription."""
        from app.cafe.sync_services import SubscriptionAccessService

        result = SubscriptionAccessService.has_active_subscription(self.cafe.id)
        self.assertFalse(result)

    def test_has_active_subscription_false_expired(self):
        """Test: Returns False when subscription is expired."""
        from app.cafe.sync_services import SubscriptionAccessService

        plan = Plan.objects.create(
            external_id=uuid.uuid4(),
            slug="test-plan",
            title="Test Plan",
            price=100000,
            duration_days=30,
        )
        Subscription.objects.create(
            external_id=uuid.uuid4(),
            cafe=self.cafe_info,
            plan=plan,
            status="ACTIVE",
            started_at=timezone.now() - timedelta(days=60),
            expires_at=timezone.now() - timedelta(days=30),  # Expired
            is_active=False,
        )

        result = SubscriptionAccessService.has_active_subscription(self.cafe.id)
        self.assertFalse(result)

    def test_has_active_subscription_false_cancelled(self):
        """Test: Returns False when subscription is cancelled."""
        from app.cafe.sync_services import SubscriptionAccessService

        plan = Plan.objects.create(
            external_id=uuid.uuid4(),
            slug="test-plan",
            title="Test Plan",
            price=100000,
            duration_days=30,
        )
        Subscription.objects.create(
            external_id=uuid.uuid4(),
            cafe=self.cafe_info,
            plan=plan,
            status="CANCELLED",
            started_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=30),
            is_active=False,
        )

        result = SubscriptionAccessService.has_active_subscription(self.cafe.id)
        self.assertFalse(result)

    def test_get_current_subscription(self):
        """Test: Returns the current active subscription."""
        from app.cafe.sync_services import SubscriptionAccessService

        plan = Plan.objects.create(
            external_id=uuid.uuid4(),
            slug="test-plan",
            title="Test Plan",
            price=100000,
            duration_days=30,
        )
        sub = Subscription.objects.create(
            external_id=uuid.uuid4(),
            cafe=self.cafe_info,
            plan=plan,
            status="ACTIVE",
            started_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=30),
            is_active=True,
        )

        result = SubscriptionAccessService.get_current_subscription(self.cafe.id)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, sub.id)
