import uuid
from django.db import models
from django.utils import timezone
from app.common.models import BaseModel
from app.users.models import MyUser


class Cafe(BaseModel):
    external_id = models.UUIDField(unique=True, db_index=True, default=uuid.uuid4)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class CafeInfo(BaseModel):
    cafe = models.OneToOneField(Cafe, on_delete=models.CASCADE, related_name="info")
    logo = models.ImageField(upload_to="cafe/logo/", null=True, blank=True)
    cover_image = models.ImageField(upload_to="cafe/cover/", null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    instagram = models.CharField(max_length=100, null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    opening_hours = models.CharField(max_length=255, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Cafe Info"
        verbose_name_plural = "Cafe Info"

    def __str__(self):
        return self.cafe.name


class CafeUser(BaseModel):
    ROLE_CHOICES = (
        ("owner", "Owner"),
        ("manager", "Manager"),
        ("staff", "Staff"),
    )
    cafe = models.ForeignKey(Cafe, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name="cafes")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    class Meta:
        unique_together = (
            "cafe",
            "user"
        )


class Plan(BaseModel):
    """
    Mirror representation of SaaS Plan.
    SaaS is the source of truth; Core syncs this data for display/access control.
    """
    external_id = models.UUIDField(unique=True, db_index=True, default=uuid.uuid4)
    slug = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
    duration_days = models.PositiveIntegerField()
    max_products = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.title


class Subscription(BaseModel):
    """
    Mirror representation of SaaS Subscription.
    SaaS is the source of truth; Core uses this for access control.
    """
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("ACTIVE", "Active"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
    )
    external_id = models.UUIDField(unique=True, db_index=True, default=uuid.uuid4)
    cafe = models.ForeignKey(CafeInfo, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    started_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    # Legacy fields kept for backward compatibility
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"

    def __str__(self):
        return f"{self.cafe.cafe.name} - {self.plan.title} ({self.status})"

    @property
    def is_subscription_active(self):
        """
        Check if this subscription is currently active.
        """
        return (
            self.status == "ACTIVE"
            and self.expires_at is not None
            and self.expires_at > timezone.now()
        )


class SyncEvent(BaseModel):
    """
    Tracks processed synchronization events for idempotency.
    Prevents duplicate processing of the same event.
    """
    event_id = models.UUIDField(unique=True, db_index=True, default=uuid.uuid4)
    event_type = models.CharField(max_length=100)
    subscription_external_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=(
            ("PROCESSED", "Processed"),
            ("FAILED", "Failed"),
        ),
        default="PROCESSED",
    )
    payload_hash = models.CharField(max_length=64, blank=True)
    # processed_at is intentionally omitted: BaseModel.created_at serves the same purpose.

    class Meta:
        verbose_name = "Sync Event"
        verbose_name_plural = "Sync Events"

    def __str__(self):
        return f"{self.event_type} ({self.event_id})"