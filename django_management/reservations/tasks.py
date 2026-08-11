from celery import shared_task
from django.utils import timezone

from .exceptions import ReservationStateConflict
from .models import Reservation
from .services import cancel_reservation


@shared_task
def expire_reservations():
    reservation_ids = list(
        Reservation.objects.filter(
            status=Reservation.Status.PENDING,
            expires_at__lte=timezone.now(),
        ).values_list("public_id", flat=True)
    )
    expired_count = 0
    for reservation_id in reservation_ids:
        try:
            reservation = cancel_reservation(
                reservation_id,
                Reservation.CancellationReason.RESERVATION_EXPIRED,
                expired=True,
            )
        except (Reservation.DoesNotExist, ReservationStateConflict):
            # Another worker or an API request changed it after the query.
            continue
        if reservation.status == Reservation.Status.EXPIRED:
            expired_count += 1
    return expired_count
