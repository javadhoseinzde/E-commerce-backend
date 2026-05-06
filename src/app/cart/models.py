from django.db import models
from django.conf import settings
from app.common.models import BaseModel
from app.product.models import Product

class Cart(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,)

    def __str__(self):
        return f"Cart {self.id}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())
    
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items",on_delete=models.CASCADE)
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.product.title

    @property
    def total_price(self):
        return self.product.price * self.quantity