from django.db import models
from django.contrib.auth.models import AbstractUser
from .myusermanager import MyUserManager

class MyUser(AbstractUser):
	username = None
	mobile = models.CharField(max_length=11, unique=True, default="a")
	otp = models.PositiveIntegerField(blank=True, null=True, default="1")
	otp_create_time = models.DateTimeField(auto_now=True)

	objects = MyUserManager()

	USERNAME_FIELD = 'mobile'
	REQUIRED_FIELDS = []

	backend = 'users.mybackend.ModelBackend'
