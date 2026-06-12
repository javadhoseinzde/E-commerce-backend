from django.db import models
from django.conf import settings
from app.common.models import BaseModel
from app.product.models import Product, ProductVariant
from app.cafe.models import Cafe

class Cart(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,)
    cafe = models.ForeignKey(Cafe, on_delete=models.CASCADE, related_name='carts', null=True, blank=True)
    is_ordered = models.BooleanField(default=False)

    def __str__(self):
        return f"Cart {self.id}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.filter(is_ordered=False))
    
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items",on_delete=models.CASCADE)
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    is_ordered = models.BooleanField(default=False)
    def __str__(self):
        return self.product.title

    @property
    def total_price(self):
        return self.product.price * self.quantity