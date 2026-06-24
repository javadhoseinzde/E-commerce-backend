from django.contrib import admin
# Register your models here.
from .models import Cafe, CafeInfo, CafeUser

admin.site.register(Cafe)
admin.site.register(CafeInfo)
admin.site.register(CafeUser)
