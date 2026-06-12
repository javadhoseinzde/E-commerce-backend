from drf_spectacular.utils import extend_schema

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from Temp.message import result_message
from .models import Cafe
from .serializer import CafeSerializer
from Temp.decorator import admin_required

@extend_schema(
    summary="cafe list",
    description="this api for get and post cafe.",
    responses={200: CafeSerializer},
    request=CafeSerializer
)
class CafeListAPIView(APIView):
    def get(self, request):
        try:
            category = Cafe.objects.filter(is_active=True)
            serializer = CafeSerializer(category, many=True)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK) 
        
        except Cafe.DoesNotExist:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "Cafe not found.")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @admin_required
    def post(self, request):
        try:
            serializer = CafeSerializer(data=request.data)
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
    summary="cafe list",
    description="this api for get and post cafe.",
    responses={200: CafeSerializer},
    request=CafeSerializer
)
class CafeDetailAPIView(APIView):
    def get(self, request, id):
        try:
            category = Cafe.objects.get(id=id)
            serializer = CafeSerializer(category)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK) 
        
        except Cafe.DoesNotExist:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "Cafe not found.")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)    
    
    @admin_required
    def put(self, request, id):
        try:
            category = Cafe.objects.get(id=id)
            serializer = CafeSerializer(category, data=request.data)
            if serializer.is_valid():
                serializer.save()
                result = result_message("CREATED", status.HTTP_200_OK, serializer.data)
                return Response(result, status=status.HTTP_200_OK) 
            
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
    @admin_required
    def delete(self, request, id):
        try:
            
            if not request.user.is_staff:
                result = result("ERROR", status.HTTP_400_BAD_REQUESTM, "You do not have permission to perform this action.")
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
            query = Cafe.objects.get(id=id)
            query.delete()
            result = result_message("DELETED",status.HTTP_204_NO_CONTENT,"Cafe delete successfully.")
            return Response(result, status=status.HTTP_204_NO_CONTENT)
        
        except Cafe.DoesNotExist:
            result = result_message("NOT_FOUND",status.HTTP_404_NOT_FOUND,"Cafe not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            result = result_message("ERROR",status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
