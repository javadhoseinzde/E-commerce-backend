from django.urls import path
from .views import CartAPIView, CartItemAPIView

urlpatterns = [
    path("cart/", CartAPIView.as_view(), name="cart"),
    path("cart-item/", CartItemAPIView.as_view(), name="cart-item"),

]