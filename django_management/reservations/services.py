from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from inventory.models import Inventory, StockMovement

from .exceptions import (
    IdempotencyConflict,
    InsufficientStock,
    ReservationStateConflict,
)
from .models import Reservation, ReservationItem


@dataclass(frozen=True)
class ReservationCreationResult:
    reservation: Reservation
    created: bool


def _reservation_items(reservation):
    return list(reservation.items.select_related("book").order_by("book_id"))


def _same_payload(reservation, order_id, requested_items):
    if reservation.order_id != order_id:
        return False

    existing = {
        item.book.external_id: item.quantity for item in _reservation_items(reservation)
    }
    requested = {item["book_id"]: item["quantity"] for item in requested_items}
    return existing == requested


def _find_existing_reservation(order_id, idempotency_key):
    existing_filter = Q(order_id=order_id)
    if idempotency_key:
        existing_filter |= Q(idempotency_key=idempotency_key)
    return (
        Reservation.objects.prefetch_related("items__book")
        .filter(existing_filter)
        .first()
    )


def _existing_result(existing, order_id, requested_items):
    if not _same_payload(existing, order_id, requested_items):
        raise IdempotencyConflict()
    return ReservationCreationResult(existing, created=False)


@transaction.atomic
def create_reservation(order_id, requested_items, idempotency_key=""):
    existing = _find_existing_reservation(order_id, idempotency_key)
    if existing:
        return _existing_result(existing, order_id, requested_items)

    book_ids = [item["book_id"] for item in requested_items]
    inventories = list(
        Inventory.objects.select_for_update()
        .select_related("book")
        .filter(book__external_id__in=book_ids, book__is_active=True)
        .order_by("book_id")
    )
    inventory_by_book = {
        inventory.book.external_id: inventory for inventory in inventories
    }

    # A retry may have been waiting while the first request held these locks.
    existing = _find_existing_reservation(order_id, idempotency_key)
    if existing:
        return _existing_result(existing, order_id, requested_items)

    insufficient = []
    for requested in requested_items:
        inventory = inventory_by_book.get(requested["book_id"])
        available = inventory.available_quantity if inventory else 0
        if inventory is None or available < requested["quantity"]:
            insufficient.append(
                {
                    "book_id": requested["book_id"],
                    "requested_quantity": requested["quantity"],
                    "available_quantity": available,
                }
            )

    if insufficient:
        raise InsufficientStock(insufficient)

    try:
        # The savepoint keeps the outer transaction usable if a concurrent
        # request wins an order_id or idempotency_key uniqueness race.
        with transaction.atomic():
            reservation = Reservation.objects.create(
                order_id=order_id,
                idempotency_key=idempotency_key or None,
                expires_at=(
                    timezone.now() + timedelta(minutes=settings.RESERVATION_TTL_MINUTES)
                ),
            )
    except IntegrityError:
        existing = _find_existing_reservation(order_id, idempotency_key)
        if existing is None:
            raise
        return _existing_result(existing, order_id, requested_items)

    reservation_items = []
    movements = []
    for requested in requested_items:
        inventory = inventory_by_book[requested["book_id"]]
        quantity = requested["quantity"]
        inventory.reserved_quantity += quantity
        inventory.save(update_fields=["reserved_quantity"])
        reservation_items.append(
            ReservationItem(
                reservation=reservation,
                book=inventory.book,
                quantity=quantity,
            )
        )
        movements.append(
            StockMovement(
                book=inventory.book,
                movement_type=StockMovement.MovementType.RESERVATION,
                quantity=-quantity,
                reference=str(order_id),
            )
        )

    ReservationItem.objects.bulk_create(reservation_items)
    StockMovement.objects.bulk_create(movements)
    return ReservationCreationResult(reservation, created=True)


def _release_locked_reservation(reservation, status, reason):
    items = _reservation_items(reservation)
    inventories = list(
        Inventory.objects.select_for_update()
        .select_related("book")
        .filter(book_id__in=[item.book_id for item in items])
    )
    inventory_by_book = {inventory.book_id: inventory for inventory in inventories}

    movements = []
    for item in items:
        inventory = inventory_by_book[item.book_id]
        if inventory.reserved_quantity < item.quantity:
            raise ReservationStateConflict(
                "Reserved stock is inconsistent with the reservation."
            )
        inventory.reserved_quantity -= item.quantity
        inventory.save(update_fields=["reserved_quantity"])
        movements.append(
            StockMovement(
                book=item.book,
                movement_type=StockMovement.MovementType.RESERVATION_RELEASE,
                quantity=item.quantity,
                reference=str(reservation.order_id),
            )
        )

    StockMovement.objects.bulk_create(movements)
    reservation.status = status
    reservation.cancellation_reason = reason
    reservation.save(update_fields=["status", "cancellation_reason", "updated_at"])
    return reservation


@transaction.atomic
def confirm_reservation(public_id):
    reservation = (
        Reservation.objects.select_for_update()
        .prefetch_related("items__book")
        .get(public_id=public_id)
    )
    if reservation.status == Reservation.Status.CONFIRMED:
        return reservation
    if reservation.status in {
        Reservation.Status.CANCELLED,
        Reservation.Status.EXPIRED,
    }:
        raise ReservationStateConflict(
            f"Reservation is already {reservation.status.lower()}."
        )
    if reservation.expires_at <= timezone.now():
        return _release_locked_reservation(
            reservation,
            Reservation.Status.EXPIRED,
            Reservation.CancellationReason.RESERVATION_EXPIRED,
        )

    items = _reservation_items(reservation)
    inventories = list(
        Inventory.objects.select_for_update()
        .select_related("book")
        .filter(book_id__in=[item.book_id for item in items])
    )
    inventory_by_book = {inventory.book_id: inventory for inventory in inventories}

    movements = []
    for item in items:
        inventory = inventory_by_book[item.book_id]
        if (
            inventory.quantity < item.quantity
            or inventory.reserved_quantity < item.quantity
        ):
            raise ReservationStateConflict(
                "Stock is inconsistent with the reservation."
            )
        inventory.quantity -= item.quantity
        inventory.reserved_quantity -= item.quantity
        inventory.save(update_fields=["quantity", "reserved_quantity"])
        movements.append(
            StockMovement(
                book=item.book,
                movement_type=StockMovement.MovementType.SALE,
                quantity=-item.quantity,
                reference=str(reservation.order_id),
            )
        )

    StockMovement.objects.bulk_create(movements)
    reservation.status = Reservation.Status.CONFIRMED
    reservation.save(update_fields=["status", "updated_at"])
    return reservation


@transaction.atomic
def cancel_reservation(public_id, reason, expired=False):
    reservation = (
        Reservation.objects.select_for_update()
        .prefetch_related("items__book")
        .get(public_id=public_id)
    )
    if reservation.status == Reservation.Status.CONFIRMED:
        raise ReservationStateConflict(
            "A confirmed reservation cannot be cancelled. Use a return."
        )
    if reservation.status in {
        Reservation.Status.CANCELLED,
        Reservation.Status.EXPIRED,
    }:
        return reservation

    target_status = (
        Reservation.Status.EXPIRED if expired else Reservation.Status.CANCELLED
    )
    return _release_locked_reservation(
        reservation,
        target_status,
        reason,
    )
