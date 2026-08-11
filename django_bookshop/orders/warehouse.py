from django.conf import settings

from BookShop.integrations.warehouse import get_warehouse_client


def reserve_order(order):
    if not settings.WAREHOUSE_INTEGRATION_ENABLED:
        return None

    items = [
        {
            "book_id": str(item.book.public_id),
            "quantity": item.quantity,
        }
        for item in order.items.select_related("book")
        if item.book is not None
    ]
    response = get_warehouse_client().create_reservation(
        order_id=order.public_id,
        items=items,
    )
    order.warehouse_reservation_id = response["reservation_id"]
    order.warehouse_status = response["status"]
    order.save(
        update_fields=[
            "warehouse_reservation_id",
            "warehouse_status",
            "updated_at",
        ]
    )
    return response


def confirm_order_reservation(order):
    if not settings.WAREHOUSE_INTEGRATION_ENABLED:
        return None
    if not order.warehouse_reservation_id:
        reserve_order(order)

    response = get_warehouse_client().confirm_reservation(
        order.warehouse_reservation_id
    )
    order.warehouse_status = response["status"]
    order.save(update_fields=["warehouse_status", "updated_at"])
    return response


def cancel_order_reservation(order, reason):
    if (
        not settings.WAREHOUSE_INTEGRATION_ENABLED
        or not order.warehouse_reservation_id
    ):
        return None

    response = get_warehouse_client().cancel_reservation(
        order.warehouse_reservation_id,
        reason,
    )
    order.warehouse_status = response["status"]
    order.save(update_fields=["warehouse_status", "updated_at"])
    return response
