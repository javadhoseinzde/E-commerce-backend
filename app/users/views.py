import random

from rest_framework.response import Response
from rest_framework.views import APIView 
from rest_framework import status

from .models import MyUser
from Temp.message import result_message
from .serializer import RegisterSerilizer
from .helper import check_otp_expiration

class RegisterAPIView(APIView):
    """
    this API for get number from user and register them send otp code

    get:
        mobile number,
    send:
        otp code 
    """
    
    def post(self, request):
        try:
            
            code = random.randint(3, 100000)
            mobile = request.data.get("mobile")

            
            if MyUser.objects.filter(mobile=mobile).exists():
                user = MyUser.objects.get(mobile=mobile)
                user.otp = code
                user.save()
                result = result_message("CREATED", status.HTTP_200_OK, "otp send")
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
        

class VerifyAPIView(APIView):
    """
        send otp for login user with jwt token
    

    get:
        mobile number,
        otp code,
    """
    
    def post(self, request):
        
        mobile = request.data.get("mobile")
        otp = request.data.get("otp")

        user = MyUser.objects.get(mobile=mobile)
        
        if not check_otp_expiration(user.mobile):
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "expire OTP")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        if user.otp != int(otp):
            result = result_message("ERROR", status.HTTP_400_BAD_REQUEST, "wrong OTP")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
                
        result = result_message("ERROR", status.HTTP_200_OK, "token=asjdhajhdjasdjashdjahsj")
        return Response(result, status=status.HTTP_200_OK)            