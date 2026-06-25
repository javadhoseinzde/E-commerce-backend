from drf_spectacular.utils import extend_schema

from rest_framework.response import Response
from rest_framework.views import APIView 
from rest_framework import status

from .models import Category, Product, ProductImage, ProductVariant
from .serializer import CategorySerializer, ProductSerializer, ProductImageSerializer, ProductVariantSerializer
from Temp.message import result_message
from Temp.decorator import admin_required
from app.cafe.models import CafeUser

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView


@extend_schema(
    summary="category list",
    description="this api for get and post category.",
    responses={200: CategorySerializer},
    request=CategorySerializer
)
class CategroyListAPIView(APIView):
    
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]

        return [IsAuthenticated()]
    
    def get(self, request):
        try:
            category = Category.objects.filter(is_active=True, cafe=request.cafe)
            serializer = CategorySerializer(category, many=True, context={'request': request})
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK) 
        
        except Category.DoesNotExist:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "Category not found.")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @admin_required
    def post(self, request):
        try:

            cafe = request.cafe

            if not CafeUser.objects.filter(user=request.user, cafe=cafe).exists():
                result = result_message("ERROR", status.HTTP_403_FORBIDDEN, "You are not member of this cafe.")
                return Response(result, status=status.HTTP_403_FORBIDDEN)

            serializer = CategorySerializer(data=request.data)

            if serializer.is_valid():

                serializer.save(cafe=cafe)

                result = result_message("CREATED", status.HTTP_201_CREATED, serializer.data)
                return Response(result, status=status.HTTP_201_CREATED)

            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
@extend_schema(
    summary="category list",
    description="this api for get and post category.",
    responses={200: CategorySerializer},
    request=CategorySerializer
)
class CategoryDetailAPIView(APIView):
    def get(self, request, id):
        try:
            category = Category.objects.get(id=id)
            serializer = CategorySerializer(category)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK) 
        
        except Category.DoesNotExist:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "Category not found.")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)    
    
    @admin_required
    def put(self, request, id):
        try:
            cafe = request.cafe

            if not request.user.is_staff:
                result = result_message("ERROR", status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action.")
                return Response(result, status=status.HTTP_403_FORBIDDEN)

            if not CafeUser.objects.filter(user=request.user, cafe=cafe).exists():
                result = result_message("ERROR", status.HTTP_403_FORBIDDEN, "You are not member of this cafe.")
                return Response(result, status=status.HTTP_403_FORBIDDEN)

            category = Category.objects.get(id=id, cafe=cafe)

            serializer = CategorySerializer(category, data=request.data)
            if serializer.is_valid():
                serializer.save()

                result = result_message("UPDATED", status.HTTP_200_OK, serializer.data)
                return Response(result, status=status.HTTP_200_OK)

            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Category.DoesNotExist:
            result = result_message("NOT_FOUND", status.HTTP_404_NOT_FOUND, "Category not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
    @admin_required
    def delete(self, request, id):
        try:
            cafe = request.cafe
            
            if not request.user.is_staff:
                result = result("ERROR", status.HTTP_400_BAD_REQUESTM, "You do not have permission to perform this action.")
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

            if not CafeUser.objects.filter(user=request.user, cafe=cafe).exists():
                result = result_message("ERROR", status.HTTP_403_FORBIDDEN, "You are not member of this cafe.")
                return Response(result, status=status.HTTP_403_FORBIDDEN)          
  
            query = Category.objects.get(id=id)
            query.delete()
            result = result_message("DELETED",status.HTTP_204_NO_CONTENT,"Category delete successfully.")
            return Response(result, status=status.HTTP_204_NO_CONTENT)
        
        except Category.DoesNotExist:
            result = result_message("NOT_FOUND",status.HTTP_404_NOT_FOUND,"Category not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            result = result_message("ERROR",status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)



class CategoryReorderView(APIView):
    
    @admin_required
    def patch(self, request):
        try:
            cafe = request.cafe
            if not CafeUser.objects.filter(user=request.user, cafe=cafe).exists():
                result = result_message("ERROR", status.HTTP_403_FORBIDDEN, "You are not member of this cafe.")
                return Response(result, status=status.HTTP_403_FORBIDDEN)
            
            # expects: [{"id": 1, "order": 0}, {"id": 2, "order": 1}, ...]
            items = request.data.get("categories", [])
            if not items:
                result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "categories list is required.")
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
            # bulk update با یه query
            categories = Category.objects.filter(
                cafe=cafe,
                id__in=[item["id"] for item in items]
            )
            cat_map = {cat.id: cat for cat in categories}
            
            to_update = []
            for item in items:
                cat = cat_map.get(item["id"])
                if cat:
                    cat.order = item["order"]
                    to_update.append(cat)
            
            Category.objects.bulk_update(to_update, ["order"])
            
            result = result_message("UPDATED", status.HTTP_200_OK, "Categories reordered successfully.")
            return Response(result, status=status.HTTP_200_OK)
        
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    summary="Product list",
    description="this api for get product list and post.",
    responses={200: ProductSerializer},
    request=ProductSerializer
)
class ProductListAPIView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]

        return [IsAuthenticated()]
    
    def get(self, request):
        try:
            cafe = request.cafe
            product = Product.objects.filter(is_active=True, cafe=cafe)

            title = request.query_params.get('title')
            min_price = request.query_params.get('min_price')
            max_price = request.query_params.get('max_price')

            if title:
                product = product.filter(title__icontains=title)
            if min_price:
                product = product.filter(price__gte=min_price)
            if max_price:
                product = product.filter(price__lte=max_price)

            serializer = ProductSerializer(product, many=True, context={'request': request})
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
    @admin_required
    def post(self, request):
        try:
            cafe = request.cafe
            serializer = ProductSerializer(data=request.data)

            if serializer.is_valid():
                serializer.save(cafe=cafe)
                result = result_message("CREATED", status.HTTP_201_CREATED, serializer.data)
                return Response(result, status=status.HTTP_201_CREATED)

            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
   
@extend_schema(
    summary="Product detail",
    description="this api for get product get, put and delete.",
    responses={200: ProductSerializer},
    request=ProductSerializer
)     
class ProductDetailAPIView(APIView):
    def get(self, request, id):
        try:
            cafe = request.cafe
            product = Product.objects.get(id=id, cafe=cafe)

            serializer = ProductSerializer(product)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK)

        except Product.DoesNotExist:
            result = result_message("ERROR", status.HTTP_404_NOT_FOUND, "Product not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
    @admin_required
    def patch(self, request, id):
        try:
            cafe = request.cafe

            if not CafeUser.objects.filter(user=request.user, cafe=cafe).exists():
                result = result_message("ERROR", status.HTTP_403_FORBIDDEN, "You are not member of this cafe.")
                return Response(result, status=status.HTTP_403_FORBIDDEN)                   
            
            product = Product.objects.get(id=id, cafe=cafe)

            serializer = ProductSerializer(product, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                result = result_message("UPDATED", status.HTTP_200_OK, serializer.data)
                return Response(result, status=status.HTTP_200_OK)

            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Product.DoesNotExist:
            result = result_message("NOT_FOUND", status.HTTP_404_NOT_FOUND, "Product not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
    @admin_required
    def delete(self, request, id):
        try:
            cafe = request.cafe
            
            if not CafeUser.objects.filter(user=request.user, cafe=cafe).exists():
                result = result_message("ERROR", status.HTTP_403_FORBIDDEN, "You are not member of this cafe.")
                return Response(result, status=status.HTTP_403_FORBIDDEN)       

            product = Product.objects.get(id=id, cafe=cafe)

            product.delete()

            result = result_message("DELETED", status.HTTP_204_NO_CONTENT, "Product delete successfully.")
            return Response(result, status=status.HTTP_204_NO_CONTENT)

        except Product.DoesNotExist:
            result = result_message("NOT_FOUND", status.HTTP_404_NOT_FOUND, "Product not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
@extend_schema(
    summary="Product variant list",
    description="this api for get product variant list and post.",
    responses={200: ProductVariantSerializer},
    request=ProductVariantSerializer
)
class ProductVariantListAPIView(APIView):
    def get(self, request):
        try:
            cafe = request.cafe
            product_variant = ProductVariant.objects.filter(is_active=True, product__cafe=cafe)

            serializer = ProductVariantSerializer(product_variant, many=True)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
    @admin_required
    def post(self, request):
        try:
            cafe = request.cafe

            product = Product.objects.get(id=request.data.get("product"), cafe=cafe)

            serializer = ProductVariantSerializer(data=request.data)

            if serializer.is_valid():
                serializer.save(product=product)
                result = result_message("CREATED", status.HTTP_201_CREATED, serializer.data)
                return Response(result, status=status.HTTP_201_CREATED)

            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Product.DoesNotExist:
            result = result_message("NOT_FOUND", status.HTTP_404_NOT_FOUND, "Product not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
@extend_schema(
    summary="Product detail",
    description="this api for get product get, put and delete.",
    responses={200: ProductSerializer},
    request=ProductSerializer
)     
class ProductVariantDetailAPIView(APIView):
    def get(self, request, id):
        try:
            cafe = request.cafe
            product_variant = ProductVariant.objects.get(id=id, product__cafe=cafe)

            serializer = ProductVariantSerializer(product_variant)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK)

        except ProductVariant.DoesNotExist:
            result = result_message("NOT_FOUND", status.HTTP_404_NOT_FOUND, "Product Variant not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
   
    @admin_required
    def put(self, request, id):
        try:
            cafe = request.cafe
            product_variant = ProductVariant.objects.get(id=id, product__cafe=cafe)

            serializer = ProductVariantSerializer(product_variant, data=request.data)

            if serializer.is_valid():
                serializer.save()
                result = result_message("UPDATED", status.HTTP_200_OK, serializer.data)
                return Response(result, status=status.HTTP_200_OK)

            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except ProductVariant.DoesNotExist:
            result = result_message("NOT_FOUND", status.HTTP_404_NOT_FOUND, "Product Variant not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    @admin_required
    def delete(self, request, id):
        try:
            cafe = request.cafe
            product_variant = ProductVariant.objects.get(id=id, product__cafe=cafe)

            product_variant.delete()

            result = result_message("DELETED", status.HTTP_204_NO_CONTENT, "Product Variant delete successfully.")
            return Response(result, status=status.HTTP_204_NO_CONTENT)

        except ProductVariant.DoesNotExist:
            result = result_message("NOT_FOUND", status.HTTP_404_NOT_FOUND, "Product Variant not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    summary="Product Image",
    description="Product Image get and post api",
    responses={200: ProductImageSerializer},
    request=ProductImageSerializer
)
class ProductImageListAPIView(APIView):
    
    def get(self, request, product_id):
        try:
            cafe = request.cafe

            product_image = ProductImage.objects.filter(
                product_id=product_id,
                product__cafe=cafe
            )

            serializer = ProductImageSerializer(product_image, many=True)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
     
    @admin_required
    def post(self, request):
        try:
            cafe = request.cafe

            product = Product.objects.get(
                id=request.data.get("product"),
                cafe=cafe
            )

            serializer = ProductImageSerializer(data=request.data)

            if serializer.is_valid():
                serializer.save(product=product)
                result = result_message("CREATED", status.HTTP_201_CREATED, serializer.data)
                return Response(result, status=status.HTTP_201_CREATED)

            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Product.DoesNotExist:
            result = result_message("NOT_FOUND", status.HTTP_404_NOT_FOUND, "Product not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
     
@extend_schema(
    summary="Product Image",
    description="Product Image get and post api",
    responses={200: ProductImageSerializer},
    request=ProductImageSerializer
)   
class ProductIamgeDetailAPIView(APIView):
    def get(self, request, id):
        try:
            cafe = request.cafe

            product_image = ProductImage.objects.get(
                id=id,
                product__cafe=cafe
            )

            serializer = ProductImageSerializer(product_image)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK)

        except ProductImage.DoesNotExist:
            result = result_message("NOT_FOUND", status.HTTP_404_NOT_FOUND, "Product Image not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
    @admin_required
    def put(self, request, id):
        try:
            cafe = request.cafe

            product_image = ProductImage.objects.get(
                id=id,
                product__cafe=cafe
            )

            serializer = ProductImageSerializer(product_image, data=request.data)

            if serializer.is_valid():
                serializer.save()
                result = result_message("UPDATED", status.HTTP_200_OK, serializer.data)
                return Response(result, status=status.HTTP_200_OK)

            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except ProductImage.DoesNotExist:
            result = result_message("NOT_FOUND", status.HTTP_404_NOT_FOUND, "Product Image not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    @admin_required
    def delete(self, request, id):
        try:
            cafe = request.cafe

            product_image = ProductImage.objects.get(
                id=id,
                product__cafe=cafe
            )

            product_image.delete()

            result = result_message("DELETED", status.HTTP_204_NO_CONTENT, "Product Image delete successfully.")
            return Response(result, status=status.HTTP_204_NO_CONTENT)

        except ProductImage.DoesNotExist:
            result = result_message("NOT_FOUND", status.HTTP_404_NOT_FOUND, "Product Image not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)