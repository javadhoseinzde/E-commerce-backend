from django.urls import path
from .views import (
    CategroyListAPIView,
    CategoryDetailAPIView,
    ProductListAPIView,
    ProductDetailAPIView,
    ProductVariantListAPIView,
    ProductVariantDetailAPIView,
    ProductImageListAPIView,
    ProductIamgeDetailAPIView
)

urlpatterns = [
    path("category-list/", CategroyListAPIView.as_view(), name="category-list"),
    path("category-detail/<int:id>/", CategoryDetailAPIView.as_view(), name="category-detail"),
    
    path("product-list/", ProductListAPIView.as_view(), name="product-list"),
    path("product-detail/<int:id>/", ProductDetailAPIView.as_view(), name="product-detail"),
    
    path("product-variant-list/", ProductVariantListAPIView.as_view(), name="product-variant-list"),
    path("product-variant-detail/<int:id>/", ProductVariantDetailAPIView.as_view(), name="product-variant-detail"),
    
    path("product-image-list/<int:product_id>/", ProductImageListAPIView.as_view(), name="product-image-list"),
    path("product-image-detail/<int:id>/", ProductIamgeDetailAPIView.as_view(), name="product-image-list"),


]
