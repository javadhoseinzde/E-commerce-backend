from django.db import models
from django.utils.text import slugify
from app.common.models import BaseModel
from app.cafe.models import Cafe
import uuid

class Category(BaseModel):
    cafe = models.ForeignKey(Cafe, on_delete=models.CASCADE, related_name='category', null=True, blank=True)
    title = models.CharField(max_length=200)
    # slug = models.SlugField(max_length=220)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
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
        super().save(*args, **kwargs)
        
        
class Product(BaseModel):
    cafe = models.ForeignKey(Cafe, on_delete=models.CASCADE, related_name='product', null=True, blank=True)
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=260, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)
    categories = models.ManyToManyField(Category, related_name="products", blank=True)
    image = models.ImageField(upload_to="products/")


    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = "Products"
        ordering = ['created_at', 'title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)

            unique_id = uuid.uuid4().hex[:8]

            self.slug = f"{base_slug}-{unique_id}"

            while Product.objects.filter(slug=self.slug).exists():
                unique_id = uuid.uuid4().hex[:8]
                self.slug = f"{base_slug}-{unique_id}"

        super().save(*args, **kwargs)
        
class ProductVariant(BaseModel):
    cafe = models.ForeignKey(Cafe, on_delete=models.CASCADE, related_name='product_variant', null=True, blank=True)
    product = models.ForeignKey( Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=25)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.title}"
    
class ProductImage(BaseModel):
    cafe = models.ForeignKey(Cafe, on_delete=models.CASCADE, related_name='product_image', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    is_main = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Image'
        verbose_name_plural = "Images"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.product.title}"