from django.urls import path
from .views import RegisterAPIView, VerifyAPIView, UserProfileAPIView
urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("verify/", VerifyAPIView.as_view(), name="verify"),
    
    path("user-profile/", UserProfileAPIView.as_view(), name="user-profile")

]

