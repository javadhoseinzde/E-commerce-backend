"""
URL configuration for the internal integration API.
"""
from django.urls import path
from .views import CustomerResolveAPIView, CafeCreationAPIView

urlpatterns = [
    path(
        "customer/resolve/",
        CustomerResolveAPIView.as_view(),
        name="customer-resolve"
    ),
    path(
        "cafes/",
        CafeCreationAPIView.as_view(),
        name="cafe-create"
    ),
]
