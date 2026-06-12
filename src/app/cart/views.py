from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem
from app.product.models import Product
from .serializer import CartSerializer, CartItemSerializer, AddToCartSerializer
from Temp.message import result_message
from .services import get_or_create_cart

class CartAPIView(APIView):

    def get(self, request):
        try:
                
            cart = get_or_create_cart(request.user)
            print(cart)
            serializer = CartSerializer(cart)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK) 
        
        except Cart.DoesNotExist:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "Cart not found.")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
class CartItemAPIView(APIView):
    def post(self, request):
        try:
            
            serializer = AddToCartSerializer(data=request.data, context={'request': request})

            if serializer.is_valid():
                cart_item = serializer.save()

                output_serializer = CartItemSerializer(cart_item)

                result = result_message("OK", status.HTTP_200_OK, output_serializer.data)
                return Response(result, status=status.HTTP_200_OK)
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {serializer.errors}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
    def delete(self, request):
        try:
            item_id = request.data.get("item_id")

            if not item_id:
                return Response({"error": "item_id is required"},status=status.HTTP_400_BAD_REQUEST)

            cart = get_or_create_cart(request.user)

            cart_item = get_object_or_404(CartItem,id=item_id,cart=cart)

            cart_item.delete()
            result = result_message("OK", status.HTTP_200_OK, "cart item deleted successfully")
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            result = result_message("ERROR",status.HTTP_400_BAD_REQUEST,f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)