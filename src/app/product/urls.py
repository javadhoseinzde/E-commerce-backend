from django.urls import path
from .views import CategroyListAPIView

urlpatterns = [
    path("category-list/", CategroyListAPIView.as_view(), name="category-list")
]
