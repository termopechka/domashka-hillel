from collections import defaultdict
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import Sum

from reservations.exceptions import Conflict, IdempotencyConflict
from reservations.models import Reservation

from .models import (
    Inventory,
    StockMovement,
    StockReturn,
    StockReturnItem,
)


@dataclass(frozen=True)
class StockReturnCreationResult:
    stock_return: StockReturn
    created: bool


def _same_return_payload(stock_return, order_id, items, reason):
    if stock_return.order_id != order_id or stock_return.reason != reason:
        return False
    existing = {
        item.book.external_id: item.quantity
        for item in stock_return.items.select_related("book")
    }
    requested = {item["book_id"]: item["quantity"] for item in items}
    return existing == requested


def _existing_return_result(idempotency_key, order_id, items, reason):
    if not idempotency_key:
        return None
    existing = (
        StockReturn.objects.prefetch_related("items__book")
        .filter(idempotency_key=idempotency_key)
        .first()
    )
    if existing is None:
        return None
    if not _same_return_payload(existing, order_id, items, reason):
        raise IdempotencyConflict()
    return StockReturnCreationResult(existing, created=False)


def _get_confirmed_reservation(order_id):
    reservation = (
        Reservation.objects.select_for_update()
        .prefetch_related("items__book")
        .filter(order_id=order_id)
        .first()
    )
    if reservation is None or reservation.status != Reservation.Status.CONFIRMED:
        raise Conflict(
            {
                "code": "ORDER_NOT_FULFILLED",
                "message": "A return requires a confirmed reservation.",
            }
        )
    return reservation


def _validate_return_quantities(reservation, order_id, items):
    sold_by_book = {
        item.book.external_id: item.quantity for item in reservation.items.all()
    }
    previously_returned = defaultdict(int)
    returned_rows = (
        StockReturnItem.objects.filter(stock_return__order_id=order_id)
        .values("book__external_id")
        .annotate(total=Sum("quantity"))
    )
    for row in returned_rows:
        previously_returned[row["book__external_id"]] = row["total"]

    invalid_items = []
    for item in items:
        sold = sold_by_book.get(item["book_id"], 0)
        remaining = sold - previously_returned[item["book_id"]]
        if item["quantity"] > remaining:
            invalid_items.append(
                {
                    "book_id": item["book_id"],
                    "requested_quantity": item["quantity"],
                    "returnable_quantity": max(remaining, 0),
                }
            )
    if invalid_items:
        raise Conflict(
            {
                "code": "INVALID_RETURN_QUANTITY",
                "message": "One or more quantities exceed the sold amount.",
                "details": invalid_items,
            }
        )


def _lock_return_inventories(items):
    book_ids = [item["book_id"] for item in items]
    inventories = list(
        Inventory.objects.select_for_update()
        .select_related("book")
        .filter(book__external_id__in=book_ids)
        .order_by("book_id")
    )
    inventory_by_book = {
        inventory.book.external_id: inventory for inventory in inventories
    }
    if len(inventory_by_book) != len(book_ids):
        raise Conflict(
            {
                "code": "INVENTORY_NOT_FOUND",
                "message": "Inventory was not found for one or more books.",
            }
        )
    return inventory_by_book


def _create_return_record(order_id, idempotency_key, reason, items):
    try:
        with transaction.atomic():
            stock_return = StockReturn.objects.create(
                order_id=order_id,
                idempotency_key=idempotency_key or None,
                reason=reason,
            )
    except IntegrityError:
        existing_result = _existing_return_result(
            idempotency_key,
            order_id,
            items,
            reason,
        )
        if existing_result is None:
            raise
        return existing_result
    return StockReturnCreationResult(stock_return, created=True)


def _apply_return(stock_return, inventory_by_book, items, reason, order_id):
    return_items = []
    movements = []
    for item in items:
        inventory = inventory_by_book[item["book_id"]]
        inventory.quantity += item["quantity"]
        inventory.save(update_fields=["quantity"])
        return_items.append(
            StockReturnItem(
                stock_return=stock_return,
                book=inventory.book,
                quantity=item["quantity"],
            )
        )
        movements.append(
            StockMovement(
                book=inventory.book,
                movement_type=StockMovement.MovementType.RETURN,
                quantity=item["quantity"],
                reason=reason,
                reference=str(order_id),
            )
        )

    StockReturnItem.objects.bulk_create(return_items)
    StockMovement.objects.bulk_create(movements)


@transaction.atomic
def create_stock_return(order_id, items, reason, idempotency_key=""):
    existing_result = _existing_return_result(
        idempotency_key,
        order_id,
        items,
        reason,
    )
    if existing_result:
        return existing_result

    reservation = _get_confirmed_reservation(order_id)

    # Recheck after acquiring the order lock. A concurrent request may have
    # created the return while this transaction was waiting.
    existing_result = _existing_return_result(
        idempotency_key,
        order_id,
        items,
        reason,
    )
    if existing_result:
        return existing_result

    _validate_return_quantities(reservation, order_id, items)
    inventory_by_book = _lock_return_inventories(items)
    creation_result = _create_return_record(
        order_id,
        idempotency_key,
        reason,
        items,
    )
    if not creation_result.created:
        return creation_result

    _apply_return(
        creation_result.stock_return,
        inventory_by_book,
        items,
        reason,
        order_id,
    )
    return creation_result
