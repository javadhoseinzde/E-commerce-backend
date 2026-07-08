from django.contrib import admin
# Register your models here.
from .models import Cafe, CafeInfo, CafeUser, Plan, Subscription

admin.site.register(Cafe)
admin.site.register(CafeInfo)
admin.site.register(CafeUser)
admin.site.register(Plan)
admin.site.register(Subscription)
