"""
Internal authentication for service-to-service communication.
Uses X-Internal-API-Key header for authentication.
"""
import hmac
from rest_framework import authentication, exceptions
from django.conf import settings


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
