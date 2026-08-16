"""
Serializers for the internal integration API.
"""
import uuid
from rest_framework import serializers


# ─── Customer Resolve ─────────────────────────────────────────────────────

class CustomerResolveRequestSerializer(serializers.Serializer):
    """
    Serializer for the customer/resolve request.
    Only accepts mobile number as the identifier.
    """
    mobile = serializers.CharField(
        max_length=11,
        min_length=11,
        help_text="Customer mobile number (11 digits, e.g., 09123456789)"
    )

    def validate_mobile(self, value):
        """
        Validate mobile number format.
        Must be 11 digits and start with 09.
        """
        # Remove any spaces or dashes
        value = value.replace(' ', '').replace('-', '')

        # Check if it's all digits
        if not value.isdigit():
            raise serializers.ValidationError(
                "Mobile number must contain only digits."
            )

        # Check length
        if len(value) != 11:
            raise serializers.ValidationError(
                "Mobile number must be exactly 11 digits."
            )

        # Check if it starts with 09
        if not value.startswith('09'):
            raise serializers.ValidationError(
                "Mobile number must start with 09."
            )

        return value


class UserInfoSerializer(serializers.Serializer):
    """Serializer for user information in response."""
    id = serializers.IntegerField(read_only=True)
    mobile = serializers.CharField(read_only=True)


class UserCreatedFlagSerializer(serializers.Serializer):
    """Serializer for user creation flag in response."""
    user = serializers.BooleanField(read_only=True)


class CustomerResolveResponseSerializer(serializers.Serializer):
    """
    Serializer for the customer/resolve response.
    Contains only user information and creation flag.
    """
    user = UserInfoSerializer(read_only=True)
    created = UserCreatedFlagSerializer(read_only=True)


# ─── Cafe Creation ────────────────────────────────────────────────────────

class CafeCreationRequestSerializer(serializers.Serializer):
    """
    Serializer for the cafe creation request.
    Requires user_id and cafe name.
    """
    user_id = serializers.IntegerField(
        help_text="User ID to associate with the cafe"
    )
    name = serializers.CharField(
        max_length=200,
        min_length=1,
        help_text="Name of the cafe to create"
    )

    def validate_name(self, value):
        """
        Validate cafe name.
        Must not be empty or contain only whitespace.
        """
        value = value.strip()
        if not value:
            raise serializers.ValidationError(
                "Cafe name cannot be empty."
            )
        return value


class CafeInfoResponseSerializer(serializers.Serializer):
    """Serializer for cafe information in response."""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)


class CafeUserInfoSerializer(serializers.Serializer):
    """Serializer for cafe user information in response."""
    id = serializers.IntegerField(read_only=True)
    role = serializers.CharField(read_only=True)


class CafeCreationResponseSerializer(serializers.Serializer):
    """
    Serializer for the cafe creation response.
    Contains cafe and cafe_user information.
    """
    cafe = CafeInfoResponseSerializer(read_only=True)
    cafe_user = CafeUserInfoSerializer(read_only=True)


# ─── Plan Sync ────────────────────────────────────────────────────────────

class PlanSyncRequestSerializer(serializers.Serializer):
    """
    Serializer for plan synchronization request from SaaS.
    """
    event_id = serializers.UUIDField(
        help_text="Unique event ID for idempotency"
    )
    event_type = serializers.ChoiceField(
        choices=[("plan.synced", "Plan Synced")],
        help_text="Event type",
    )
    plan = serializers.DictField(
        help_text="Plan data from SaaS"
    )
    occurred_at = serializers.DateTimeField(
        help_text="When the event occurred in SaaS"
    )

    def validate_plan(self, value):
        """Validate plan data structure."""
        required = ["external_id", "slug", "title", "price", "duration_days"]
        for field in required:
            if field not in value:
                raise serializers.ValidationError(f"Plan data missing required field: {field}")
        return value


class PlanSyncResponseSerializer(serializers.Serializer):
    """Serializer for plan sync response."""
    id = serializers.IntegerField(read_only=True)
    external_id = serializers.UUIDField(read_only=True)
    slug = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    created = serializers.BooleanField(read_only=True)


# ─── Subscription Sync ───────────────────────────────────────────────────

class SubscriptionSyncRequestSerializer(serializers.Serializer):
    """
    Serializer for subscription synchronization request from SaaS.
    """
    event_id = serializers.UUIDField(
        help_text="Unique event ID for idempotency"
    )
    event_type = serializers.ChoiceField(
        choices=[
            ("subscription.activated", "Subscription Activated"),
            ("subscription.expired", "Subscription Expired"),
            ("subscription.cancelled", "Subscription Cancelled"),
        ],
        help_text="Event type",
    )
    subscription_id = serializers.UUIDField(
        help_text="External subscription ID (stable cross-system identifier)"
    )
    cafe_id = serializers.UUIDField(
        help_text="External cafe ID (stable cross-system identifier)"
    )
    plan = serializers.DictField(
        help_text="Plan data from SaaS"
    )
    status = serializers.ChoiceField(
        choices=["PENDING", "ACTIVE", "EXPIRED", "CANCELLED"],
        help_text="Subscription status"
    )
    started_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="When the subscription started"
    )
    expires_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="When the subscription expires"
    )
    version = serializers.IntegerField(
        required=False,
        default=1,
        help_text="Event version for staleness prevention"
    )
    occurred_at = serializers.DateTimeField(
        help_text="When the event occurred in SaaS"
    )

    def validate_plan(self, value):
        """Validate plan data structure."""
        required = ["external_id", "slug", "title", "price", "duration_days"]
        for field in required:
            if field not in value:
                raise serializers.ValidationError(f"Plan data missing required field: {field}")
        return value


class SubscriptionSyncResponseSerializer(serializers.Serializer):
    """Serializer for subscription sync response."""
    id = serializers.IntegerField(read_only=True)
    external_id = serializers.UUIDField(read_only=True)
    status = serializers.CharField(read_only=True)
    version = serializers.IntegerField(read_only=True)
    created = serializers.BooleanField(read_only=True)
    plan_external_id = serializers.UUIDField(read_only=True)


# ─── Subscription Access Check ───────────────────────────────────────────

class SubscriptionAccessCheckRequestSerializer(serializers.Serializer):
    """Serializer for checking subscription access."""
    cafe_external_id = serializers.UUIDField(
        help_text="External cafe ID"
    )


class SubscriptionAccessCheckResponseSerializer(serializers.Serializer):
    """Serializer for subscription access check response."""
    has_active_subscription = serializers.BooleanField(read_only=True)
    subscription_status = serializers.CharField(read_only=True, allow_null=True)
    expires_at = serializers.DateTimeField(read_only=True, allow_null=True)
