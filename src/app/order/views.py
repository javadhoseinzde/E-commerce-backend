from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from app.order.models import Order
from app.order.serializer import OrderSerializer, CreateOrderSerializer, OrderUpdateSerializer
from app.order.services import create_order_from_cart
from Temp.message import result_message
from Temp.permissions import IsSuperUser
from Temp.decorator import admin_required


class OrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            orders = Order.objects.filter(user=request.user).prefetch_related('items__product').order_by('-created_at')
            serializer = OrderSerializer(orders, many=True)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK) 
        
        except Order.DoesNotExist:
            result = result_message("ERROR", status.HTTP_404_NOT_FOUND, "Order not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
    def post(self, request):
        try:
            serializer = CreateOrderSerializer(data=request.data)
            if serializer.is_valid():
                order = create_order_from_cart(
                    user=request.user,
                    table_number=serializer.validated_data.get('table_number'),
                    payment_method=serializer.validated_data.get('payment_method', 'cash')
                )

                serializer = OrderSerializer(order)
                result = result_message("OK", status.HTTP_200_OK, serializer.data)
                return Response(result, status=status.HTTP_200_OK) 
                    
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
     
     
class OrderListAPIView(APIView):
    def get(self, request):
        try:
            orders = Order.objects.all().order_by('-created_at')
            serializer = OrderSerializer(orders, many=True)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK) 
        
        except Order.DoesNotExist:
            result = result_message("ERROR", status.HTTP_404_NOT_FOUND, "Order not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        

class OrderDetailAPIView(APIView):
    @admin_required
    def put(self, request, id):
        try:
            order = Order.objects.get(id=id)
            serializer = OrderUpdateSerializer(order, data=request.data)
            if serializer.is_valid():
                if request.data['status'] == "seen":
                    print("send sms")
                serializer.save()
                result = result_message("UPDATED",status.HTTP_200_OK, serializer.data)
                return Response(result, status=status.HTTP_200_OK)
            
        except Order.DoesNotExist:
            result = result_message("NOT_FOUND",status.HTTP_404_NOT_FOUND,"Order not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            result = result_message("ERROR",status.HTTP_400_BAD_REQUEST,f"{e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
