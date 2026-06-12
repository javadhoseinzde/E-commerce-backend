from django.db import models
from app.common.models import BaseModel
from app.users.models import MyUser

class Cafe(BaseModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class CafeInfo(BaseModel):
    owner = models.OneToOneField(MyUser,on_delete=models.CASCADE,related_name="CafeInfo")
    title = models.CharField(max_length=250)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
    
class Plan(BaseModel):
    title = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
    duration_days = models.PositiveIntegerField()
    max_products = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
    
class Subscription(BaseModel):
    cafe = models.ForeignKey(CafeInfo,on_delete=models.CASCADE,related_name="subscriptions")
    plan = models.ForeignKey(Plan,on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.cafe.title} - {self.plan.title}"