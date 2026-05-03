from django.db import models
from django.utils.text import slugify
from app.common.models import BaseModel

class Category(BaseModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='subcategories'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = "Categories"
        ordering = ['parent__id', 'title']

    def __str__(self):
        full_path = [self.title]
        k = self.parent
        while k is not None:
            full_path.append(k.title)
            k = k.parent
        return ' -> '.join(reversed(full_path))
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
        
        
class Product(BaseModel):
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=260, unique=True)
    description = models.TextField(blank=True)
    
    price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)

    categories = models.ManyToManyField(Category, related_name="products", blank=True)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = "Products"
        ordering = ['created_at', 'title']

    def __str__(self):
        return self.title
    
class ProductImage(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    is_main = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Image'
        verbose_name_plural = "Images"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.product.title}"