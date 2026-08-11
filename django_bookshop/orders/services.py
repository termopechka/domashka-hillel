from dataclasses import dataclass

from django.db import transaction

from .models import OrderItem


@dataclass(frozen=True)
class CheckoutCreationResult:
    order: object
    stripe_line_items: list


@transaction.atomic
def create_checkout_order(checkout_form, user, books):
    """Persist an order snapshot before any external network request."""
    order = checkout_form.save(commit=False)
    order.user = user
    order.total_price = sum((book.price or 0) * book.quantity for book in books)
    order.save()

    order_items = []
    stripe_line_items = []
    for book in books:
        price = book.price or 0
        order_items.append(
            OrderItem(
                book=book,
                book_name=book.title,
                order=order,
                price=price,
                quantity=book.quantity,
            )
        )
        stripe_line_items.append(
            {
                "price_data": {
                    "currency": "eur",
                    "product_data": {"name": book.title},
                    "unit_amount": int(price * 100),
                },
                "quantity": book.quantity,
            }
        )

    OrderItem.objects.bulk_create(order_items)
    return CheckoutCreationResult(order, stripe_line_items)
