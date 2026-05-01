from django.urls import path
from .views import CategroyListAPIView, CategoryDetailAPIView, ProductListAPIView

urlpatterns = [
    path("category-list/", CategroyListAPIView.as_view(), name="category-list"),
    path("category-detail/<int:id>/", CategoryDetailAPIView.as_view(), name="category-detail"),
    
    path("product-list/", ProductListAPIView.as_view(), name="product-list")

]
