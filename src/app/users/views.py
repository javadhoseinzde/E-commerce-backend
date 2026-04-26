import random

from django.contrib.auth import authenticate

from rest_framework.response import Response
from rest_framework.views import APIView 
from rest_framework import status
from rest_framework_simplejwt.tokens import Token
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

from drf_spectacular.utils import extend_schema


from .models import MyUser, UserProfile
from Temp.message import result_message
from .serializer import RegisterSerilizer, UserProfileSerializer
from .helper import check_otp_expiration

@extend_schema(
    summary="user registeration",
    description="user registration api",
    responses={200: RegisterSerilizer},
)
class RegisterAPIView(APIView):
    """
    this API for get number fromuser user and register them send otp code

    get:
        mobile number,
    send:
        otp code 
    """
    permission_classes = [AllowAny]
    def post(self, request):
        try:
            
            code = random.randint(3, 100000)
            mobile = request.data.get("mobile")

            
            if MyUser.objects.filter(mobile=mobile).exists():
                user = MyUser.objects.get(mobile=mobile)
                user.otp = code
                user.save()
                result = result_message("CREATED", status.HTTP_200_OK, f"otp send {code}")
                return Response(result, status=status.HTTP_200_OK)

            serializer = RegisterSerilizer(data=request.data)            
            if serializer.is_valid():
                    serializer.save(otp=code)
                    result = result_message("CREATED", status.HTTP_201_CREATED, serializer.data)
                    return Response(result, status=status.HTTP_201_CREATED)
            else:
                result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors)
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"{e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
@extend_schema(
    summary="verify user",
    description="this endpoint for send otp for login user with jwt token ",
    responses={200: RegisterSerilizer},
)
class VerifyAPIView(APIView):
    """
        send otp for login user with jwt token
    """
    permission_classes = [AllowAny]
    def post(self, request):
        mobile = request.data.get("mobile")
        otp = request.data.get("otp")

        if not check_otp_expiration(mobile): # Assuming check_otp_expiration takes mobile number
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "OTP expired")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(request, mobile=str(mobile), otp=str(otp))

        if user is not None and user.is_active:
            refresh = RefreshToken.for_user(user)
            message = {
                "refresh": str(refresh),
                "token": str(refresh.access_token),
            }

            result = result_message("OK", status.HTTP_200_OK, message)
            return Response(result, status=status.HTTP_200_OK)
        else:

            try:
                user_obj = MyUser.objects.get(mobile=mobile)
                if user_obj.otp != int(otp):
                    result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "Wrong OTP")
                    return Response(result, status=status.HTTP_400_BAD_REQUEST)
                result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "Authentication failed. Please check your details.")
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            except MyUser.DoesNotExist:
                result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "User not found.")
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                 result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
                 return Response(result, status=status.HTTP_400_BAD_REQUEST)
    

@extend_schema(
    summary="user profile",
    description="this endpoint for user profile",
    responses={200: UserProfileSerializer},
    request=UserProfileSerializer
)
class UserProfileAPIView(APIView):
    def get(self, request):
        user = request.user.id
        """
            get a user profile detail
        """
        
        try:
            query = UserProfile.objects.get(user=user)
            serializer = UserProfileSerializer(query)
            result = result_message("OK", status.HTTP_200_OK, serializer.data)
            return Response(result, status=status.HTTP_200_OK) 
        
        except UserProfile.DoesNotExist:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "User Profile not found.")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        user = request.user.id
        try:
            serializer = UserProfileSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user_id=user)
                result = result_message("OK", status.HTTP_200_OK, serializer.data)
                return Response(result, status=status.HTTP_200_OK) 
            
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, serializer.errors)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, f"An error occurred: {e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request):
        user = request.user.id
        try:
            
            query = UserProfile.objects.get(user=user)
            serializer = UserProfileSerializer(query, data=request.data)
            if serializer.is_valid():
                serializer.save()
                result = result_message("UPDATED",status.HTTP_200_OK,serializer.data)
                return Response(result, status=status.HTTP_200_OK)
            
        except UserProfile.DoesNotExist:
            result = result_message("NOT_FOUND",status.HTTP_404_NOT_FOUND,"User Profile not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            result = result_message("ERROR",status.HTTP_400_BAD_REQUEST,f"{e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
    def delete(self, request):
        user = request.user.id
        try:
            query = UserProfile.objects.get(user=user)
            query.delete()
            result = result_message("DELETED",status.HTTP_204_NO_CONTENT,"User Profile delete successfully.")
            return Response(result, status=status.HTTP_204_NO_CONTENT)
        
        except UserProfile.DoesNotExist:
            result = result_message("NOT_FOUND",status.HTTP_404_NOT_FOUND,"User Profile not found.")
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            result = result_message("ERROR",status.HTTP_400_BAD_REQUEST,f"{e}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)