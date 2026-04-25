from django.db import models
from django.contrib.auth.models import AbstractUser
from .myusermanager import MyUserManager
from django.contrib.auth import get_user_model

class MyUser(AbstractUser):
	username = None
	mobile = models.CharField(max_length=11, unique=True, default="a")
	otp = models.PositiveIntegerField(blank=True, null=True, default="1")
	otp_create_time = models.DateTimeField(auto_now=True)

	objects = MyUserManager()

	USERNAME_FIELD = 'mobile'
	REQUIRED_FIELDS = []

	backend = 'users.mybackend.ModelBackend'

	def __str__(self):
		return self.mobile

class UserProfile(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=15, blank=True, null=True)
    
    def __str__(self):
        return self.full_name
    
