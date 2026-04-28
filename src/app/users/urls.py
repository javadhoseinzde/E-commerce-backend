from django.urls import path
from .views import RegisterAPIView, VerifyAPIView, UserProfileAPIView, UserAddressListAPIView, UserAddressAPIView
urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("verify/", VerifyAPIView.as_view(), name="verify"),
    
    path("user-profile/", UserProfileAPIView.as_view(), name="user-profile"),
    path("create-user-profile/", UserProfileAPIView.as_view(), name="create-user-profile"),    
    
    path("user-address/", UserAddressListAPIView.as_view(), name="user-address"),
    path("user-address-detail/<int:id>/", UserAddressAPIView.as_view(), name="user-address-detail"),

]

