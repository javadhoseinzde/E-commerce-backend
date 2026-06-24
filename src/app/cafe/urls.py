from django.urls import path
from .views import CafeListAPIView, CafeDetailAPIView
urlpatterns = [
    path("cafe-list/", CafeListAPIView.as_view(), name="cafe"),
    path("cafe-detail/", CafeDetailAPIView.as_view(), name="cafe-detail")
]
