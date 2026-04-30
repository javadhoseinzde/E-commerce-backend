from django.urls import path
from .views import CategroyListAPIView, CategoryDetailAPIView

urlpatterns = [
    path("category-list/", CategroyListAPIView.as_view(), name="category-list"),
    path("category-list/", CategroyListAPIView.as_view(), name="category-list"),
    path("category-detail/<int:id>/", CategoryDetailAPIView.as_view(), name="category-detail")
]
