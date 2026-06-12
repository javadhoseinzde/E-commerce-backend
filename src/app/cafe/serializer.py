from rest_framework import serializers
from .models import Cafe, CafeUser

class CafeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Cafe
        fields = ['name','slug','is_active']


from rest_framework import serializers
from .models import CafeUser

class CafeUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = CafeUser
        fields = "__all__"