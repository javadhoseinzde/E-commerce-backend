"""
Serializers for the internal integration API.
"""
from rest_framework import serializers


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
