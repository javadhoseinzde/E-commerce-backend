from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from .models import Category, Product, ProductImage, ProductVariant

class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"
        
        
class ProductImageSerializer(ModelSerializer):
    class Meta:
        model = ProductImage
        fields = "__all__"
        
class ProductVariantSerializer(ModelSerializer):
    size_display = serializers.CharField(source='get_size_display', read_only=True)

    class Meta:
        model = ProductVariant
        fields = ['id', 'size', 'size_display', 'price', 'is_active']
        
class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = "__all__"
        