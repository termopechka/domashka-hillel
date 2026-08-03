from django.conf import settings
from django.db import models
from books.models import Book


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новий"
        PAID = "paid", "Оплачений"
        SHIPPED = "shipped", "Відправлений"
        DELIVERED = "delivered", "Доставлений"
        CANCELLED = "cancelled", "Скасований"

    class PaymentMethod(models.TextChoices):
        CARD = "card", "Картка"
        CASH = "cash", "Готівка"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="orders",
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    shipping_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    payment_method = models.CharField(max_length=100, choices=PaymentMethod.choices)
    payment_id = models.CharField(max_length=255, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} - {self.user} - {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True)

    book_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def total(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.book_name} x{self.quantity}"
