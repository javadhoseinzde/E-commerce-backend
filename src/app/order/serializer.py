from rest_framework import serializers
from app.order.models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.title', read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'total_price']

    def get_total_price(self, obj):
        return obj.price * obj.quantity

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id','user','status','table_number','total_price','payment_method','is_paid','items','created_at']
        read_only_fields = ['id', 'user', 'status', 'total_price', 'is_paid', 'created_at']


class CreateOrderSerializer(serializers.Serializer):
    table_number = serializers.IntegerField(required=False, allow_null=True)
    payment_method = serializers.ChoiceField(choices=['cash', 'online'], default='cash')
