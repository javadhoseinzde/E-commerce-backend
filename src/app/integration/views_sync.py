"""
Internal integration API views for SaaS ↔ Core synchronization.

These endpoints receive plan and subscription state from SaaS.
SaaS is the SOURCE OF TRUTH for billing and subscription state.
Core mirrors this state for access control.

All endpoints:
- Require InternalApiKeyAuthentication (X-Internal-API-Key header) or
  HmacSyncAuthentication (X-Menuno-Signature, X-Menuno-Timestamp, X-Menuno-Event-Id)
- Are idempotent (duplicate events are safely handled)
- Use database-level constraints for safety
- Return standardized response format via result_message
"""
import logging
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from Temp.internal_auth import InternalApiKeyAuthentication, HmacSyncAuthentication
from Temp.message import result_message
from app.cafe.sync_services import (
    PlanSyncService,
    SubscriptionSyncService,
    SubscriptionAccessService,
)
from .serializer import (
    PlanSyncRequestSerializer,
    PlanSyncResponseSerializer,
    SubscriptionSyncRequestSerializer,
    SubscriptionSyncResponseSerializer,
    SubscriptionAccessCheckRequestSerializer,
    SubscriptionAccessCheckResponseSerializer,
)

logger = logging.getLogger(__name__)


class PlanSyncAPIView(APIView):
    """
    Internal API endpoint to synchronize plan data from SaaS to Core.

    This endpoint is called by SaaS when a plan is created or updated.
    Core maintains a lightweight mirror of SaaS plans for display and access control.

    Authentication:
        Requires X-Internal-API-Key header for service-to-service communication.

    Request:
        POST /api/internal/integration/sync/plan/
        {
            "event_id": "UUID",
            "event_type": "plan.synced",
            "plan": {
                "external_id": "UUID",
                "slug": "professional",
                "title": "Professional",
                "price": 500000,
                "duration_days": 30,
                "max_products": 500,
                "is_active": true,
                "version": 1
            },
            "occurred_at": "2026-08-13T12:00:00Z"
        }

    Response:
        {
            "message": "CREATED" | "OK",
            "status": 201 | 200,
            "result": {
                "id": 1,
                "external_id": "UUID",
                "slug": "professional",
                "title": "Professional",
                "created": true | false
            }
        }
    """

    authentication_classes = [InternalApiKeyAuthentication]
    permission_classes = []

    @extend_schema(
        summary="Synchronize plan from SaaS",
        description=(
            "Internal endpoint for SaaS to synchronize plan data to Core. "
            "Idempotent: duplicate events are safely ignored."
        ),
        request=PlanSyncRequestSerializer,
        responses={
            200: PlanSyncResponseSerializer,
            201: PlanSyncResponseSerializer,
            400: "Invalid request data",
            401: "Invalid or missing internal API key",
        },
        tags=["Internal Integration - Sync"],
        parameters=[
            OpenApiParameter(
                name="X-Internal-API-Key",
                type=str,
                required=True,
                location=OpenApiParameter.HEADER,
                description="Internal API key for service-to-service authentication",
            )
        ],
    )
    def post(self, request):
        serializer = PlanSyncRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan_data = serializer.validated_data["plan"]

        try:
            plan, created = PlanSyncService.sync_plan(plan_data)
        except ValueError as e:
            return Response(
                result_message("ERROR", status.HTTP_400_BAD_REQUEST, str(e)),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception(f"Plan sync error: {e}")
            return Response(
                result_message("ERROR", status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal sync error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_data = {
            "id": plan.id,
            "external_id": str(plan.external_id),
            "slug": plan.slug,
            "title": plan.title,
            "created": created,
        }

        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        message = "CREATED" if created else "OK"

        return Response(
            result_message(message, http_status, response_data),
            status=http_status,
        )


class SubscriptionSyncAPIView(APIView):
    """
    Internal API endpoint to synchronize subscription state from SaaS to Core.

    This endpoint is called by SaaS after payment success, subscription changes,
    cancellations, or expirations.

    Authentication:
        Requires X-Internal-API-Key header for service-to-service communication.

    Idempotency:
        - Uses event_id for duplicate event detection (database unique constraint)
        - Uses external_id for subscription identity (database unique constraint)
        - Uses version field for stale event prevention (version check)

    Request:
        POST /api/internal/integration/sync/subscription/
        {
            "event_id": "UUID",
            "event_type": "subscription.activated",
            "subscription_id": "UUID",
            "cafe_id": "UUID",
            "plan": {
                "external_id": "UUID",
                "slug": "professional",
                "title": "Professional",
                "price": 500000,
                "duration_days": 30,
                "max_products": 500,
                "is_active": true,
                "version": 1
            },
            "status": "ACTIVE",
            "started_at": "2026-08-13T12:00:00Z",
            "expires_at": "2026-09-12T12:00:00Z",
            "version": 1,
            "occurred_at": "2026-08-13T12:00:00Z"
        }
    """

    authentication_classes = [InternalApiKeyAuthentication]
    permission_classes = []

    @extend_schema(
        summary="Synchronize subscription from SaaS",
        description=(
            "Internal endpoint for SaaS to synchronize subscription state to Core. "
            "Handles activated, expired, and cancelled events. "
            "Idempotent: duplicate events are safely ignored."
        ),
        request=SubscriptionSyncRequestSerializer,
        responses={
            200: SubscriptionSyncResponseSerializer,
            201: SubscriptionSyncResponseSerializer,
            400: "Invalid request data",
            401: "Invalid or missing internal API key",
        },
        tags=["Internal Integration - Sync"],
        parameters=[
            OpenApiParameter(
                name="X-Internal-API-Key",
                type=str,
                required=True,
                location=OpenApiParameter.HEADER,
                description="Internal API key for service-to-service authentication",
            )
        ],
    )
    def post(self, request):
        serializer = SubscriptionSyncRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        subscription_data = {
            "external_id": str(data["subscription_id"]),
            "status": data["status"],
            "started_at": data.get("started_at"),
            "expires_at": data.get("expires_at"),
            "version": data.get("version", 1),
        }

        try:
            sub, created = SubscriptionSyncService.sync_subscription(
                subscription_data=subscription_data,
                cafe_external_id=data["cafe_id"],
                plan_data=data["plan"],
                event_id=data["event_id"],
                event_type=data["event_type"],
            )
        except ValueError as e:
            return Response(
                result_message("ERROR", status.HTTP_400_BAD_REQUEST, str(e)),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception(f"Subscription sync error: {e}")
            return Response(
                result_message("ERROR", status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal sync error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_data = {
            "id": sub.id,
            "external_id": str(sub.external_id),
            "status": sub.status,
            "version": sub.version,
            "created": created,
            "plan_external_id": str(sub.plan.external_id),
        }

        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        message = "CREATED" if created else "OK"

        return Response(
            result_message(message, http_status, response_data),
            status=http_status,
        )


class SubscriptionAccessCheckAPIView(APIView):
    """
    Internal API endpoint to check if a cafe has an active subscription.

    This can be used by SaaS or other internal services to verify
    a cafe's subscription status in Core.

    Authentication:
        Requires X-Internal-API-Key header for service-to-service communication.

    Request:
        POST /api/internal/integration/subscription/access-check/
        {
            "cafe_external_id": "UUID"
        }
    """

    authentication_classes = [InternalApiKeyAuthentication]
    permission_classes = []

    @extend_schema(
        summary="Check cafe subscription access",
        description="Internal endpoint to check if a cafe has an active subscription.",
        request=SubscriptionAccessCheckRequestSerializer,
        responses={
            200: SubscriptionAccessCheckResponseSerializer,
            400: "Invalid request data",
            401: "Invalid or missing internal API key",
        },
        tags=["Internal Integration - Sync"],
        parameters=[
            OpenApiParameter(
                name="X-Internal-API-Key",
                type=str,
                required=True,
                location=OpenApiParameter.HEADER,
                description="Internal API key for service-to-service authentication",
            )
        ],
    )
    def post(self, request):
        serializer = SubscriptionAccessCheckRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        cafe_external_id = serializer.validated_data["cafe_external_id"]

        has_active = SubscriptionAccessService.has_active_subscription_by_external_id(
            cafe_external_id
        )

        # Get current subscription details if exists
        sub = None
        from app.cafe.models import CafeInfo, Subscription
        from django.utils import timezone
        try:
            cafe_info = CafeInfo.objects.get(cafe__external_id=cafe_external_id)
            sub = Subscription.objects.filter(
                cafe=cafe_info,
                status="ACTIVE",
                expires_at__gt=timezone.now(),
            ).first()
        except CafeInfo.DoesNotExist:
            pass

        response_data = {
            "has_active_subscription": has_active,
            "subscription_status": sub.status if sub else None,
            "expires_at": sub.expires_at if sub else None,
        }

        return Response(
            result_message("OK", status.HTTP_200_OK, response_data),
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name='dispatch')
class CoreSyncAPIView(APIView):
    """
    HMAC-authenticated server-to-server endpoint for SaaS → Core sync.

    This endpoint is called ONLY by SaaS (server-to-server).
    CSRF is exempt because this is not a browser-facing endpoint.

    Authentication:
        HMAC-SHA256 signature verified via HmacSyncAuthentication.
        Headers required:
            X-Menuno-Event-Id: UUID for idempotency
            X-Menuno-Timestamp: ISO-8601 timestamp (max 5 min drift)
            X-Menuno-Signature: HMAC-SHA256(secret, timestamp + "." + body)

    Supports both plan.sync and subscription.* events via event_type.
    """

    authentication_classes = [HmacSyncAuthentication]
    permission_classes = []

    @extend_schema(
        summary="SaaS → Core sync (HMAC-authenticated)",
        description=(
            "Server-to-server endpoint for SaaS to synchronize subscription "
            "and plan state to Core. Protected by HMAC-SHA256 signature. "
            "CSRF exempt (not browser-facing)."
        ),
        request=SubscriptionSyncRequestSerializer,
        responses={
            200: SubscriptionSyncResponseSerializer,
            201: SubscriptionSyncResponseSerializer,
            400: "Invalid request data",
            401: "Invalid HMAC signature or missing headers",
        },
        tags=["Internal Integration - Core Sync"],
        parameters=[
            OpenApiParameter(
                name="X-Menuno-Event-Id",
                type=str,
                required=True,
                location=OpenApiParameter.HEADER,
                description="Unique event ID for idempotency",
            ),
            OpenApiParameter(
                name="X-Menuno-Timestamp",
                type=str,
                required=True,
                location=OpenApiParameter.HEADER,
                description="ISO-8601 timestamp of the request",
            ),
            OpenApiParameter(
                name="X-Menuno-Signature",
                type=str,
                required=True,
                location=OpenApiParameter.HEADER,
                description="HMAC-SHA256(secret, timestamp + '.' + body)",
            ),
        ],
    )
    def post(self, request):
        event_type = request.data.get("event_type")

        if event_type == "plan.synced":
            return self._sync_plan(request)
        elif event_type in ("subscription.activated", "subscription.expired", "subscription.cancelled"):
            return self._sync_subscription(request)
        else:
            return Response(
                result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"Unknown event_type: {event_type}"),
                status=status.HTTP_400_BAD_REQUEST,
            )

    def _sync_plan(self, request):
        serializer = PlanSyncRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan_data = serializer.validated_data["plan"]

        try:
            plan, created = PlanSyncService.sync_plan(plan_data)
        except ValueError as e:
            return Response(
                result_message("ERROR", status.HTTP_400_BAD_REQUEST, str(e)),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception(f"Core sync plan error: {e}")
            return Response(
                result_message("ERROR", status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal sync error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_data = {
            "id": plan.id,
            "external_id": str(plan.external_id),
            "slug": plan.slug,
            "title": plan.title,
            "created": created,
        }

        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        message = "CREATED" if created else "OK"

        return Response(
            result_message(message, http_status, response_data),
            status=http_status,
        )

    def _sync_subscription(self, request):
        serializer = SubscriptionSyncRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        subscription_data = {
            "external_id": str(data["subscription_id"]),
            "status": data["status"],
            "started_at": data.get("started_at"),
            "expires_at": data.get("expires_at"),
            "version": data.get("version", 1),
        }

        try:
            sub, created = SubscriptionSyncService.sync_subscription(
                subscription_data=subscription_data,
                cafe_external_id=data["cafe_id"],
                plan_data=data["plan"],
                event_id=data["event_id"],
                event_type=data["event_type"],
            )
        except ValueError as e:
            return Response(
                result_message("ERROR", status.HTTP_400_BAD_REQUEST, str(e)),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception(f"Core sync subscription error: {e}")
            return Response(
                result_message("ERROR", status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal sync error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_data = {
            "id": sub.id,
            "external_id": str(sub.external_id),
            "status": sub.status,
            "version": sub.version,
            "created": created,
            "plan_external_id": str(sub.plan.external_id),
        }

        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        message = "CREATED" if created else "OK"

        return Response(
            result_message(message, http_status, response_data),
            status=http_status,
        )
