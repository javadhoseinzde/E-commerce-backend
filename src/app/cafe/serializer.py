from rest_framework import serializers
from .models import Cafe, CafeUser, Subscription

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
        
from rest_framework import serializers

class SubscriptionSerializer(serializers.ModelSerializer):
    plan_title = serializers.CharField(source="plan.title", read_only=True)
    price = serializers.IntegerField(source="plan.price", read_only=True)
    duration_days = serializers.IntegerField(source="plan.duration_days", read_only=True)
    max_products = serializers.IntegerField(source="plan.max_products", read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "plan_title",
            "price",
            "duration_days",
            "max_products",
            "start_date",
            "end_date",
            "is_active",
        )