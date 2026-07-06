from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from books.models import Book
from orders.models import Order, OrderItem


@pytest.mark.django_db
def test_book_get_absolute_url_uses_detail_route(book_factory):
    # Generated with AI, reviewed and modified
    book = book_factory()

    assert book.get_absolute_url() == f"/en/book/{book.pk}/"


@pytest.mark.django_db
def test_order_creation_defaults_and_string_representation(order_factory):
    # Generated with AI, reviewed and modified
    order = order_factory(
        user__email="customer@example.com",
        shipping_address="12 Test Avenue",
        city="Lviv",
        postal_code="79000",
        country="Ukraine",
        payment_method=Order.PaymentMethod.CASH,
        total_price=Decimal("125.50"),
    )

    assert order.status == Order.Status.NEW
    assert order.payment_method == Order.PaymentMethod.CASH
    assert order.total_price == Decimal("125.50")
    assert order.created_at is not None
    assert order.updated_at is not None
    assert str(order) == f"Order #{order.pk} - customer@example.com - new"


@pytest.mark.django_db
def test_order_allows_nullable_user_and_keeps_string_readable(order_factory):
    # Generated with AI, reviewed and modified
    order = order_factory(user=None)

    assert order.user is None
    assert str(order) == f"Order #{order.pk} - None - new"


@pytest.mark.django_db
@pytest.mark.parametrize("field,value", [
    ("shipping_address", ""),
    ("city", ""),
    ("postal_code", ""),
    ("country", ""),
])
def test_order_required_shipping_fields_reject_blank_values(order_factory, field, value):
    # Generated with AI, reviewed and modified
    order = order_factory.build(**{field: value})

    with pytest.raises(ValidationError) as exc_info:
        order.full_clean()

    assert field in exc_info.value.message_dict


@pytest.mark.django_db
def test_order_rejects_invalid_status_choice(order_factory):
    # Generated with AI, reviewed and modified
    order = order_factory.build(status="pending")

    with pytest.raises(ValidationError) as exc_info:
        order.full_clean()

    assert "status" in exc_info.value.message_dict


@pytest.mark.django_db
def test_order_rejects_invalid_payment_method_choice(order_factory):
    # Generated with AI, reviewed and modified
    order = order_factory.build(payment_method="bitcoin")

    with pytest.raises(ValidationError) as exc_info:
        order.full_clean()

    assert "payment_method" in exc_info.value.message_dict


@pytest.mark.django_db
def test_order_items_related_name_returns_items(order_factory, order_item_factory):
    # Generated with AI, reviewed and modified
    order = order_factory()
    first_item = order_item_factory(order=order, book_name="Clean Code")
    second_item = order_item_factory(order=order, book_name="Refactoring")

    assert list(order.items.order_by("id")) == [first_item, second_item]


@pytest.mark.django_db
def test_order_item_total_multiplies_price_by_quantity(order_item_factory):
    # Generated with AI, reviewed and modified
    item = order_item_factory(price=Decimal("19.99"), quantity=3)

    assert item.total == Decimal("59.97")


@pytest.mark.django_db
def test_order_item_string_representation(order_item_factory):
    # Generated with AI, reviewed and modified
    item = order_item_factory(book_name="Domain-Driven Design", quantity=2)

    assert str(item) == "Domain-Driven Design x2"


@pytest.mark.django_db
def test_order_item_allows_book_to_be_null_after_book_delete(order_item_factory):
    # Generated with AI, reviewed and modified
    item = order_item_factory()
    item.book.delete()
    item.refresh_from_db()

    assert item.book is None


@pytest.mark.django_db
def test_order_delete_cascades_order_items(order_factory, order_item_factory):
    # Generated with AI, reviewed and modified
    order = order_factory()
    item = order_item_factory(order=order)

    order.delete()

    assert not OrderItem.objects.filter(pk=item.pk).exists()


@pytest.mark.django_db
def test_order_item_rejects_negative_quantity(order_item_factory):
    # Generated with AI, reviewed and modified
    item = order_item_factory.build(quantity=-1)

    with pytest.raises(ValidationError) as exc_info:
        item.full_clean()

    assert "quantity" in exc_info.value.message_dict


@pytest.mark.django_db
def test_order_item_requires_book_name(order_item_factory):
    # Generated with AI, reviewed and modified
    item = order_item_factory.build(book_name="")

    with pytest.raises(ValidationError) as exc_info:
        item.full_clean()

    assert "book_name" in exc_info.value.message_dict
