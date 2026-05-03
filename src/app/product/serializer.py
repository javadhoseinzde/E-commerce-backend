from rest_framework.serializers import ModelSerializer
from .models import Category, Product, ProductImage

class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"
        
class ProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"
        
class ProductImageSerializer(ModelSerializer):
    class Meta:
        model = ProductImage
        fields = "__all__"