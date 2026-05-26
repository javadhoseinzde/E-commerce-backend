from django.db import models
from app.common.models import BaseModel

class Cafe(BaseModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
