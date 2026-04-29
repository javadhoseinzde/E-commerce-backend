import random
from unittest.mock import patch
from model_bakery import baker

from django.urls import reverse

from rest_framework.test import APITestCase
from rest_framework import status

from .models import MyUser
from .serializer import RegisterSerilizer

# Create your tests here.



class RegisterAPITestCase(APITestCase):
    """
        this testcase for register api view
    """
    def setUp(self):
        self.existing_user_mobile = "1235"
        self.existing_user = MyUser.objects.create(
            mobile=self.existing_user_mobile,
            otp = random.randint(1000, 10000)
        )
        self.register_url = reverse('register')
        
    def test_register_new_user(self):
        data = {'mobile': "1234"}
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.assertIn('message', response.data)
        
        self.assertTrue(MyUser.objects.filter(mobile='1235').exists())
        
        user_in_db = MyUser.objects.get(mobile='1235')
        self.assertIsNotNone(user_in_db.otp)
        
    def test_register_existing_user_updates_otp(self):
        initial_otp_for_existing_user = self.existing_user.otp
        
        data = {'mobile': self.existing_user_mobile}
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertIn('message', response.data)
        user_in_db = MyUser.objects.get(mobile='1235')

        self.assertNotEqual(initial_otp_for_existing_user, user_in_db.otp)
        
        
    def test_missing_mobile_number(self):
        data = {"mobile": ''}
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        
class VerifyAPITestCase(APITestCase):
    """
        check verify api
    """
    def setUp(self):
        #create user
        self.valid_otp = random.randint(100000, 999999)
        self.user = baker.make(MyUser, mobile="09123456789", otp=self.valid_otp, is_active=True)

        # ساخت کاربر با OTP نامعتبر (برای تست خطای OTP)
        self.wrong_otp = 123456
        self.user_wrong_otp = baker.make(MyUser, mobile="09987654321", otp=random.randint(100000, 999999), is_active=True)

        
        self.verify_url = reverse('verify')
        
    def test_verify_otp(self):
        data = {
            "mobile": self.user.mobile,
            "otp": self.valid_otp
        }
        response = self.client.post(self.verify_url, data, format='json')
                
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertIn('token', response.data['result'])
        
        
