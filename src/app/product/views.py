from drf_spectacular.utils import extend_schema

from rest_framework.response import Response
from rest_framework.views import APIView 
from rest_framework import status
from rest_framework_simplejwt.tokens import Token
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

from .models import Category, Product, ProductImage
from .serializer import CategorySerializer, ProductSerializer, ProductImageSerializer
from Temp.message import result_message


@extend_schema(
    summary="category list",
    description="this api for get and post category.",
    responses={200: CategorySerializer},
    request=CategorySerializer
)
class CategroyListAPIView(APIView):
    def get(self, request):
        try:
            category = Category.objects.all()
            serializer = CategorySerializer(category, many=True)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK) 
        
        except Category.DoesNotExist:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "Category not found.")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    
    def post(self, request):
        try:
            serializer = CategorySerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                result = result_message("CREATED", status.HTTP_200_OK, serializer.data)
                return Response(result, status=status.HTTP_200_OK) 
            
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
    def put(self, request, id):
        try:
            category = Category.objects.get(id=id)
            serializer = CategorySerializer(category, data=request.data)
            if serializer.is_valid():
                serializer.save()
                result = result_message("CREATED", status.HTTP_200_OK, serializer.data)
                return Response(result, status=status.HTTP_200_OK) 
            
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        try:
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

@extend_schema(
    summary="Product list",
    description="this api for get product list and post.",
    responses={200: ProductSerializer},
    request=ProductSerializer
)
class ProductListAPIView(APIView):
    def get(self, request):
        try:
            product = Product.objects.all()
            serializer = ProductSerializer(product, many=True)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK) 
        
        except Product.DoesNotExist:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "Product not found.")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request):
        try:
            serializer = ProductSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                result = result_message("OK", status.HTTP_200_OK, serializer.data)
                return Response(result, status=status.HTTP_200_OK) 
            
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
            product = Product.objects.get(id=id)
            serializer = ProductSerializer(product)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK) 
        
        except Product.DoesNotExist:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "Product not found.")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, id):
        try:
            product = Product.objects.get(id=id)
            serializer = ProductSerializer(product, data=request.data)
            if serializer.is_valid():
                serializer.save()
                result = result_message("UPDATED",status.HTTP_200_OK,serializer.data)
                return Response(result, status=status.HTTP_200_OK)
            
        except Product.DoesNotExist:
            result = result_message("NOT_FOUND",status.HTTP_404_NOT_FOUND,"Product not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            result = result_message("ERROR",status.HTTP_400_BAD_REQUEST,f"{e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
    def delete(self, request, id):
        try:
            product = Product.objects.get(id=id)
            product.delete()
            result = result_message("DELETED",status.HTTP_204_NO_CONTENT,"Product delete successfully.")
            return Response(result, status=status.HTTP_204_NO_CONTENT)
        
        except Product.DoesNotExist:
            result = result_message("NOT_FOUND",status.HTTP_404_NOT_FOUND,"Product not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            result = result_message("ERROR",status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
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
            product_image = ProductImage.objects.all(product_id=product_id)
            serializer = ProductImageSerializer(product_image, many=True)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK) 
        
        except ProductImage.DoesNotExist:
            result = result_message("ERROR", status.HTTP_404_NOT_FOUND, "Product Image not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)