from rest_framework.serializers import ModelSerializer
from .models import MyUser, UserProfile, Address

class RegisterSerilizer(ModelSerializer):
    class Meta:
        model = MyUser
        fields = ["mobile", "otp"]
        
class UserProfileSerializer(ModelSerializer):
    class Meta:
        model = UserProfile
        fields = "__all__"
        read_only_fields = ('user',)

class UserAddressSerializer(ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"
