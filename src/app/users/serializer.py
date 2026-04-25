from rest_framework.serializers import ModelSerializer
from .models import MyUser, UserProfile

class RegisterSerilizer(ModelSerializer):
    class Meta:
        model = MyUser
        fields = ["mobile", "otp"]
        
class UserProfileSerializer(ModelSerializer):
    class Meta:
        model = UserProfile
        fields = "__all__"