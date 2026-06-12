from rest_framework import serializers
from .models import MyUser, UserProfile, Address

class RegisterSerilizer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ["mobile", "otp"]
        
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = "__all__"
        read_only_fields = ('user',)

class UserAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"
        read_only_fields = ['user_profile']


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()