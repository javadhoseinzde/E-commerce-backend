from django.core.exceptions import PermissionDenied
from .models import Cart

# def get_or_create_cart(user):
#     if not user.is_authenticated:
#         raise PermissionDenied("User not authenticated")

#     cart, _ = Cart.objects.get_or_create(user=user, is_active=True)
#     return cart

def get_or_create_cart(user):
    if not user.is_authenticated:
        raise PermissionDenied("User not authenticated")

    # فقط سبد فعال رو بگیر
    cart = Cart.objects.filter(user=user, is_ordered=False).first()

    if cart:
        return cart

    # اگر سبد فعال نداشت، یکی بساز
    return Cart.objects.create(user=user, is_ordered=False)