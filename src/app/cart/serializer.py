from rest_framework import serializers
from .models import Cart, CartItem, ProductVariant, Product
from .services import get_or_create_cart

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.title', read_only=True)
    variant_size = serializers.CharField(source='variant.size', read_only=True, allow_null=True)
    unit_price = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'variant', 'variant_size', 'quantity', 'unit_price', 'total_price',]

    def get_unit_price(self, obj):
        if obj.variant:
            return obj.variant.price
        return obj.product.price

    def get_total_price(self, obj):
        return self.get_unit_price(obj) * obj.quantity
        
        
class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price', "is_ordered"]
        
    def get_total_price(self, obj):
        total = 0
        for item in obj.items.all():
            unit_price = item.variant.price if item.variant else item.product.price
            total += unit_price * item.quantity
        return total


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    variant_id = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        product_id = attrs.get("product_id")
        variant_id = attrs.get("variant_id")

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise serializers.ValidationError({"product_id": "Invalid product."})

        has_variant = product.variants.exists()

        if has_variant:
            if variant_id is None:
                raise serializers.ValidationError({"variant_id": "This product requires a variant."})
            try:
                variant = ProductVariant.objects.get(id=variant_id, product=product)
                attrs["variant"] = variant
            except ProductVariant.DoesNotExist:
                raise serializers.ValidationError({"variant_id": "Invalid variant for this product."})
        else:
            if variant_id is not None:
                raise serializers.ValidationError({"variant_id": "This product does not support variants."})
            attrs["variant"] = None

        attrs["product"] = product
        attrs["quantity"] = attrs.get('quantity', 1)


        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        cart = get_or_create_cart(request.user)

        product = validated_data["product"]
        variant = validated_data.get("variant")
        quantity = validated_data["quantity"]

        try:
            cart_item = CartItem.objects.get(
                cart=cart,
                product=product,
                variant=variant
            )
            cart_item.quantity = quantity
            cart_item.save()
        except CartItem.DoesNotExist:
            cart_item = CartItem.objects.create(
                cart=cart,
                product=product,
                variant=variant,
                quantity=quantity
            )

        return cart_item