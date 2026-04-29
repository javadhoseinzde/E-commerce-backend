from drf_spectacular.utils import extend_schema

from rest_framework.response import Response
from rest_framework.views import APIView 
from rest_framework import status
from rest_framework_simplejwt.tokens import Token
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

from .models import Category
from .serializer import CategorySerializer
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
        
    
class CategoryDetailAPIView(APIView):
    def get(self, request, id):
        pass
    
    def put(self, request, id):
        pass
    
    def delete(self, request, id):
        pass