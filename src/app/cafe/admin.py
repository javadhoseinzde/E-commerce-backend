from django.contrib import admin
from .models import Cafe, CafeInfo, CafeUser, Plan, Subscription, SyncEvent


@admin.register(Cafe)
class CafeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "is_active")
    search_fields = ("name", "slug")
    list_filter = ("is_active",)


@admin.register(CafeInfo)
class CafeInfoAdmin(admin.ModelAdmin):
    list_display = ("id", "cafe", "is_verified")
    list_filter = ("is_verified",)


@admin.register(CafeUser)
class CafeUserAdmin(admin.ModelAdmin):
    list_display = ("id", "cafe", "user", "role")
    list_filter = ("role",)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("id", "external_id", "slug", "title", "price", "duration_days", "is_active", "version")
    search_fields = ("title", "slug")
    list_filter = ("is_active",)
    readonly_fields = ("external_id", "version")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "external_id", "cafe", "plan", "status", "started_at", "expires_at", "version")
    list_filter = ("status",)
    readonly_fields = ("external_id", "version")


@admin.register(SyncEvent)
class SyncEventAdmin(admin.ModelAdmin):
    list_display = ("id", "event_id", "event_type", "status", "created_at")
    list_filter = ("event_type", "status")
    readonly_fields = ("event_id", "event_type", "subscription_external_id", "status", "payload_hash", "created_at")
