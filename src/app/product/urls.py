from django.urls import path
from .views import (
    CategroyListAPIView,
    CategoryDetailAPIView,
    ProductListAPIView,
    ProductDetailAPIView
)

urlpatterns = [
    path("category-list/", CategroyListAPIView.as_view(), name="category-list"),
    path("category-detail/<int:id>/", CategoryDetailAPIView.as_view(), name="category-detail"),
    
    path("product-list/", ProductListAPIView.as_view(), name="product-list"),
    path("product-detail/<int:id>/", ProductDetailAPIView.as_view(), name="product-detail"),


]
