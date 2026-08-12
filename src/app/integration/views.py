"""
Internal integration API views.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from Temp.internal_auth import InternalApiKeyAuthentication
from Temp.message import result_message
from app.users.models import MyUser
from .serializer import (
    CustomerResolveRequestSerializer,
    CustomerResolveResponseSerializer,
    CafeCreationRequestSerializer,
    CafeCreationResponseSerializer
)
from .services import CustomerResolutionService, CafeCreationService


class CustomerResolveAPIView(APIView):
    """
    Internal API endpoint to resolve or create a user in Menu.
    
    This endpoint ONLY handles user creation/resolution.
    It does NOT create Cafe or CafeUser.
    
    Authentication:
        Requires X-Internal-API-Key header for service-to-service communication.
    
    Request:
        POST /api/internal/integration/customer/resolve/
        {
            "mobile": "09123456789"
        }
    
    Response for newly created user:
        {
            "message": "CREATED",
            "status": 201,
            "result": {
                "user": {"id": 3, "mobile": "09123456789"},
                "created": {"user": true}
            }
        }
    
    Response for existing user:
        {
            "message": "OK",
            "status": 200,
            "result": {
                "user": {"id": 3, "mobile": "09123456789"},
                "created": {"user": false}
            }
        }
    """
    
    authentication_classes = [InternalApiKeyAuthentication]
    permission_classes = []
    
    @extend_schema(
        summary="Resolve or create a user",
        description="Internal endpoint for SaaS backend to resolve or create a user based on mobile number. Only handles user creation - does NOT create Cafe or CafeUser.",
        request=CustomerResolveRequestSerializer,
        responses={
            200: CustomerResolveResponseSerializer,
            201: CustomerResolveResponseSerializer,
            400: "Invalid request data",
            401: "Invalid or missing internal API key",
        },
        tags=["Internal Integration"],
        parameters=[
            OpenApiParameter(
                name="X-Internal-API-Key",
                type=str,
                required=True,
                location=OpenApiParameter.HEADER,
                description="Internal API key for service-to-service authentication"
            )
        ]
    )
    
    def post(self, request):
        """
        Resolve or create a user based on mobile number.
        
        This endpoint is idempotent and handles concurrent requests safely
        using database transactions and get_or_create with IntegrityError handling.
        """
        # Validate request data
        serializer = CustomerResolveRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        mobile = serializer.validated_data['mobile']
        
        # Resolve or create user (ONLY user, no cafe or cafe_user)
        try:
            user, user_created = CustomerResolutionService.resolve_or_create_user(mobile)
        except Exception as e:
            return Response(
                result_message("ERROR", status.HTTP_500_INTERNAL_SERVER_ERROR, str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Prepare response - ONLY user and created flag
        response_data = {
            "user": {
                "id": user.id,
                "mobile": user.mobile
            },
            "created": {
                "user": user_created
            }
        }
        
        if user_created:
            return Response(
                result_message("CREATED", status.HTTP_201_CREATED, response_data),
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                result_message("OK", status.HTTP_200_OK, response_data),
                status=status.HTTP_200_OK
            )


class CafeCreationAPIView(APIView):
    """
    Internal API endpoint to create a cafe in Menu.
    
    This endpoint is called by SaaS after the user has logged in and explicitly entered their cafe name.
    It creates both the Cafe and CafeUser records atomically.
    
    Authentication:
        Requires X-Internal-API-Key header for service-to-service communication.
    
    Request:
        POST /api/internal/integration/cafes/
        {
            "user_id": 3,
            "name": "کافه ناتی"
        }
    
    Response:
        {
            "message": "CREATED",
            "status": 201,
            "result": {
                "cafe": {
                    "id": 7,
                    "name": "کافه ناتی",
                    "slug": "cafe-nati",
                    "is_active": true
                },
                "cafe_user": {
                    "id": 7,
                    "role": "owner"
                }
            }
        }
    """
    
    authentication_classes = [InternalApiKeyAuthentication]
    permission_classes = []
    
    @extend_schema(
        summary="Create a cafe",
        description="Internal endpoint for SaaS backend to create a cafe. Creates both Cafe and CafeUser records atomically.",
        request=CafeCreationRequestSerializer,
        responses={
            201: CafeCreationResponseSerializer,
            400: "Invalid request data",
            404: "User not found",
            401: "Invalid or missing internal API key",
        },
        tags=["Internal Integration"],
        parameters=[
            OpenApiParameter(
                name="X-Internal-API-Key",
                type=str,
                required=True,
                location=OpenApiParameter.HEADER,
                description="Internal API key for service-to-service authentication"
            )
        ]
    )
    
    def post(self, request):
        """
        Create a cafe and CafeUser atomically.
        
        This endpoint is NOT idempotent - calling it twice with the same user_id
        will create two separate cafes for the same user.
        """
        # Validate request data
        serializer = CafeCreationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_id = serializer.validated_data['user_id']
        cafe_name = serializer.validated_data['name']
        
        # Create cafe and cafe_user
        try:
            cafe, cafe_user = CafeCreationService.create_cafe(user_id, cafe_name)
        except MyUser.DoesNotExist:
            return Response(
                result_message("NOT_FOUND", status.HTTP_404_NOT_FOUND, "User not found"),
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                result_message("ERROR", status.HTTP_400_BAD_REQUEST, str(e)),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                result_message("ERROR", status.HTTP_500_INTERNAL_SERVER_ERROR, str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Prepare response
        response_data = {
            "cafe": {
                "id": cafe.id,
                "name": cafe.name,
                "slug": cafe.slug,
                "is_active": cafe.is_active
            },
            "cafe_user": {
                "id": cafe_user.id,
                "role": cafe_user.role
            }
        }
        
        return Response(
            result_message("CREATED", status.HTTP_201_CREATED, response_data),
            status=status.HTTP_201_CREATED
        )
