from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem
from app.product.models import Product
from .serializer import CartSerializer, CartItemSerializer
from Temp.message import result_message


def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        return Response("not authenticated")
    
    return cart

class CartAPIView(APIView):

    def get(self, request):
        try:
                
            cart = get_or_create_cart(request)
            serializer = CartSerializer(cart)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK) 
        
        except Cart.DoesNotExist:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "Cart not found.")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)