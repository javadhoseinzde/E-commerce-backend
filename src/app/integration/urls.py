"""
URL configuration for the internal integration API.
"""
from django.urls import path
from .views import CustomerResolveAPIView, CafeCreationAPIView
from .views_sync import (
    PlanSyncAPIView,
    SubscriptionSyncAPIView,
    SubscriptionAccessCheckAPIView,
    CoreSyncAPIView,
)

urlpatterns = [
    # User and cafe creation (existing)
    path(
        "customer/resolve/",
        CustomerResolveAPIView.as_view(),
        name="customer-resolve"
    ),
    path(
        "cafes/",
        CafeCreationAPIView.as_view(),
        name="cafe-create"
    ),

    # SaaS ↔ Core synchronization (existing, X-Internal-API-Key auth)
    path(
        "sync/plan/",
        PlanSyncAPIView.as_view(),
        name="plan-sync"
    ),
    path(
        "sync/subscription/",
        SubscriptionSyncAPIView.as_view(),
        name="subscription-sync"
    ),
    path(
        "subscription/access-check/",
        SubscriptionAccessCheckAPIView.as_view(),
        name="subscription-access-check"
    ),

    # SaaS → Core sync (HMAC-authenticated, CSRF-exempt)
    path(
        "core/sync/",
        CoreSyncAPIView.as_view(),
        name="core-sync",
    ),
]
