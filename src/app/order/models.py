from django.db import models
from django.conf import settings
from app.common.models import BaseModel
from app.cart.models import Cart
from app.product.models import Product

class Order(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'در انتظار تایید'),
        ('preparing', 'در حال آماده‌سازی'),
        ('ready', 'آماده تحویل'),
        ('delivered', 'تحویل داده شده'),
        ('canceled', 'لغو شده'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)

    cart = models.OneToOneField(Cart,on_delete=models.PROTECT,null=True,blank=True)


    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    table_number = models.PositiveIntegerField(null=True, blank=True)

    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    payment_method = models.CharField(max_length=20, default="cash")
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Order {self.id} - {self.status}"


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total_price(self):
        return self.price * self.quantity