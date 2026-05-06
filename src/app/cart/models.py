from django.db import models
from django.conf import settings
from app.common.models import BaseModel

class Cart(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,)

    def __str__(self):
        return f"Cart {self.id}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())
