import uuid
import qrcode
from io import BytesIO


from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile

from app.common.models import BaseModel
from app.cart.models import Cart
from app.product.models import Product, ProductVariant
from app.cafe.models import Cafe


class CafeTable(models.Model):
    cafe = models.ForeignKey(Cafe, on_delete=models.CASCADE, related_name='tables', null=True, blank=True)
    number = models.PositiveIntegerField(unique=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_active = models.BooleanField(default=True)
    qr_code = models.ImageField(upload_to='table_qr/', null=True, blank=True)

    def __str__(self):
        return f"Table {self.number}"

    def generate_qr_code(self):
        url = f"https://yourdomain.com/menu/table/{self.token}/"
        qr = qrcode.make(url)

        buffer = BytesIO()
        qr.save(buffer, format='PNG')

        file_name = f"table_{self.number}.png"
        self.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=False)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and not self.qr_code:
            self.generate_qr_code()
            super().save(update_fields=['qr_code'])


class Order(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'در انتظار تایید'),
        ('preparing', 'در حال آماده‌سازی'),
        ('ready', 'آماده تحویل'),
        ('delivered', 'تحویل داده شده'),
        ('canceled', 'لغو شده'),
        ("seen", 'دیده شد')
    ]  
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    cart = models.OneToOneField(Cart,on_delete=models.PROTECT,null=True,blank=True)
    cafe = models.ForeignKey(Cafe, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    table_number = models.PositiveIntegerField(null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, default="cash")
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Order {self.id} - {self.status}"


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total_price(self):
        return self.price * self.quantity
    
    