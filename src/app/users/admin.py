from django.contrib import admin
from .models import MyUser, UserProfile, Address
# Register your models here.
admin.site.register(MyUser)
admin.site.register(UserProfile)
admin.site.register(Address)