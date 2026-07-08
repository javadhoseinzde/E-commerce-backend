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
    cafe = models.OneToOneField(Cafe, on_delete=models.CASCADE, related_name="info")
    logo = models.ImageField(upload_to="cafe/logo/", null=True, blank=True)
    cover_image = models.ImageField(upload_to="cafe/cover/", null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    instagram = models.CharField(max_length=100, null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    opening_hours = models.CharField(max_length=255, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Cafe Info"
        verbose_name_plural = "Cafe Info"

    def __str__(self):
        return self.cafe.name
    
class CafeUser(BaseModel):
    ROLE_CHOICES = (
        ("owner", "Owner"),
        ("manager", "Manager"),
        ("staff", "Staff"),
    )
    cafe = models.ForeignKey(Cafe, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name="cafes")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    class Meta:
        unique_together = (
            "cafe",
            "user"
        )
    

class Plan(BaseModel):
    title = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
    duration_days = models.PositiveIntegerField()
    max_products = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
    
class Subscription(BaseModel):
    cafe = models.ForeignKey(CafeInfo, on_delete=models.CASCADE,related_name="subscriptions")
    plan = models.ForeignKey(Plan,on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.cafe.cafe.name} - {self.plan.title}"