from rest_framework.serializers import ModelSerializer
from .models import MyUser
class RegisterSerilizer(ModelSerializer):
    class Meta:
        model = MyUser
        fields = ["mobile", "otp"]