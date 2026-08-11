import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from books.models import Book


class Reservation(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        CONFIRMED = "CONFIRMED", _("Confirmed")
        CANCELLED = "CANCELLED", _("Cancelled")
        EXPIRED = "EXPIRED", _("Expired")

    class CancellationReason(models.TextChoices):
        PAYMENT_FAILED = "PAYMENT_FAILED", _("Payment failed")
        ORDER_CANCELLED = "ORDER_CANCELLED", _("Order cancelled")
        RESERVATION_EXPIRED = "RESERVATION_EXPIRED", _("Reservation expired")
        MANUAL = "MANUAL", _("Manual cancellation")

    public_id = models.UUIDField(
        _("Public ID"), default=uuid.uuid4, unique=True, editable=False
    )
    order_id = models.UUIDField(_("Order ID"), unique=True)
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    cancellation_reason = models.CharField(
        _("Cancellation reason"),
        max_length=30,
        choices=CancellationReason.choices,
        blank=True,
    )
    expires_at = models.DateTimeField(_("Expires at"))
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    def __str__(self):
        return f"{self.public_id} — {self.status}"

    class Meta:
        verbose_name = _("Reservation")
        verbose_name_plural = _("Reservations")
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["status", "expires_at"],
                name="reserv_status_expires_idx",
            ),
        ]


class ReservationItem(models.Model):
    reservation = models.ForeignKey(
        Reservation,
        verbose_name=_("Reservation"),
        related_name="items",
        on_delete=models.CASCADE,
    )
    book = models.ForeignKey(Book, verbose_name=_("Book"), on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(_("Quantity"))

    class Meta:
        verbose_name = _("Reservation item")
        verbose_name_plural = _("Reservation items")
        constraints = [
            models.UniqueConstraint(
                fields=["reservation", "book"],
                name="unique_book_per_reservation",
            ),
        ]
