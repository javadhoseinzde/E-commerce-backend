from django.db import transaction
from rest_framework.exceptions import ValidationError
from app.cart.models import Cart
from app.order.models import Order, OrderItem


@transaction.atomic
def create_order_from_cart(user, table_number=None, payment_method='cash'):
    cart = Cart.objects.filter(user=user, is_ordered=False).prefetch_related('items__product').first()
    if not cart:
        raise ValidationError("active Cart not found")

    cart_items = cart.items.filter(is_ordered=False)

    if not cart_items.exists():
        raise ValidationError("cart is empty")
    order = Order.objects.create(user=user, cart=cart, table_number=table_number, total_price=cart.total_price, payment_method=payment_method, is_paid=False if payment_method == 'cash' else False,status='pending')

    order_items = []
    for item in cart_items:
        order_items.append(
            OrderItem(order=order, product=item.product, quantity=item.quantity, price=item.product.price)
        )
        print(item)

    OrderItem.objects.bulk_create(order_items)
    cart_items.update(is_ordered=True)
    cart.is_ordered = True
    cart.save(update_fields=['is_ordered'])
    return order
