from django.urls import path
from .views import RegisterAPIView, VerifyAPIView
urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("verify/", VerifyAPIView.as_view(), name="verify")

]

