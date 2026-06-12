from django.urls import path
from .views import OrderAPIView, OrderListAPIView, OrderDetailAPIView

urlpatterns = [
    path("order/", OrderAPIView.as_view(), name="order"),
    path("order-list/", OrderListAPIView.as_view(), name="order-list"),
    path("order-detail/<int:id>/", OrderDetailAPIView.as_view(), name="order-detail"),
    
]
