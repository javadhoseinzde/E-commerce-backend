from django.core.exceptions import PermissionDenied
from .models import Cart

def get_or_create_cart(user):
    if not user.is_authenticated:
        raise PermissionDenied("User not authenticated")

    cart, _ = Cart.objects.get_or_create(user=user)
    return cart