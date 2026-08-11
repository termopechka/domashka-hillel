import uuid

from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

from books.models import Book


class Inventory(models.Model):
    book = models.OneToOneField(
        Book,
        verbose_name=_("Book"),
        related_name="inventory",
        on_delete=models.PROTECT,
    )
    quantity = models.PositiveIntegerField(_("Quantity"), default=0)
    reserved_quantity = models.PositiveIntegerField(
        _("Reserved quantity"), default=0
    )

    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity

    @property
    def in_stock(self):
        return self.available_quantity > 0

    def can_fulfill(self, requested_quantity):
        return self.available_quantity >= requested_quantity

    def __str__(self):
        return f"{self.book}: {self.available_quantity}/{self.quantity}"

    class Meta:
        verbose_name = _("Inventory")
        verbose_name_plural = _("Inventory")
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=F("reserved_quantity")),
                name="inventory_quantity_gte_reserved",
            ),
        ]


class StockMovement(models.Model):
    class AdjustmentReason(models.TextChoices):
        STOCKTAKE_CORRECTION = (
            "stocktake_correction",
            _("Stocktake correction"),
        )
        DATA_CORRECTION = "data_correction", _("Data correction")
        FOUND_STOCK = "found_stock", _("Found stock")

    class MovementType(models.TextChoices):
        RECEIPT = "receipt", _("Receipt")
        RESERVATION = "reservation", _("Reservation")
        RESERVATION_RELEASE = "reservation_release", _("Reservation release")
        SALE = "sale", _("Sale")
        RETURN = "return", _("Return")
        WRITE_OFF = "write_off", _("Write-off")
        ADJUSTMENT = "adjustment", _("Adjustment")

    class WriteOffReason(models.TextChoices):
        DAMAGED = "damaged", _("Damaged")
        LOST = "lost", _("Lost")
        STOLEN = "stolen", _("Stolen")
        DEFECTIVE = "defective", _("Defective")
        OBSOLETE = "obsolete", _("Obsolete")
        OTHER = "other", _("Other")

    class ReturnReason(models.TextChoices):
        CUSTOMER_RETURN = "customer_return", _("Customer return")
        DAMAGED_RETURN = "damaged_return", _("Damaged return")
        WRONG_ITEM = "wrong_item", _("Wrong item")

    book = models.ForeignKey(
        Book,
        verbose_name=_("Book"),
        related_name="stock_movements",
        on_delete=models.PROTECT,
    )
    movement_type = models.CharField(
        _("Movement type"),
        max_length=30,
        choices=MovementType.choices,
    )
    quantity = models.IntegerField(_("Quantity"))
    reason = models.CharField(
        _("Reason"),
        max_length=30,
        choices=(
            WriteOffReason.choices + AdjustmentReason.choices + ReturnReason.choices
        ),
        blank=True,
    )
    reference = models.CharField(_("Reference"), max_length=255, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    def __str__(self):
        return f"{self.book}: {self.movement_type} {self.quantity:+d}"

    class Meta:
        verbose_name = _("Stock movement")
        verbose_name_plural = _("Stock movements")
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["movement_type", "created_at"]),
            models.Index(fields=["book", "created_at"]),
        ]


class StockReturn(models.Model):
    public_id = models.UUIDField(
        _("Public ID"), default=uuid.uuid4, unique=True, editable=False
    )
    order_id = models.UUIDField(_("Order ID"))
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
    reason = models.CharField(
        _("Reason"),
        max_length=30,
        choices=StockMovement.ReturnReason.choices,
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    def __str__(self):
        return f"{self.public_id} ({self.order_id})"

    class Meta:
        verbose_name = _("Return")
        verbose_name_plural = _("Returns")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["order_id", "created_at"])]


class StockReturnItem(models.Model):
    stock_return = models.ForeignKey(
        StockReturn,
        verbose_name=_("Return"),
        related_name="items",
        on_delete=models.CASCADE,
    )
    book = models.ForeignKey(Book, verbose_name=_("Book"), on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(_("Quantity"))

    class Meta:
        verbose_name = _("Return item")
        verbose_name_plural = _("Return items")
        constraints = [
            models.UniqueConstraint(
                fields=["stock_return", "book"],
                name="unique_book_per_stock_return",
            ),
        ]
