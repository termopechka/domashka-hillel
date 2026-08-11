import uuid

from django.db import migrations, models
from django.utils import timezone


def populate_public_ids_and_statuses(apps, schema_editor):
    Reservation = apps.get_model("reservations", "Reservation")
    status_map = {
        "pending": "PENDING",
        "confirmed": "CONFIRMED",
        "cancelled": "CANCELLED",
        "expired": "EXPIRED",
    }
    for reservation in Reservation.objects.all().iterator():
        reservation.public_id = uuid.uuid4()
        reservation.status = status_map.get(
            reservation.status.lower(),
            "PENDING",
        )
        reservation.save(update_fields=["public_id", "status"])


class Migration(migrations.Migration):
    dependencies = [
        ("reservations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="reservation",
            name="public_id",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name="reservation",
            name="idempotency_key",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="cancellation_reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("PAYMENT_FAILED", "Payment failed"),
                    ("ORDER_CANCELLED", "Order cancelled"),
                    ("RESERVATION_EXPIRED", "Reservation expired"),
                    ("MANUAL", "Manual cancellation"),
                ],
                default="",
                max_length=30,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="reservation",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.RunPython(
            populate_public_ids_and_statuses,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="reservation",
            name="public_id",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="reservation",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("CONFIRMED", "Confirmed"),
                    ("CANCELLED", "Cancelled"),
                    ("EXPIRED", "Expired"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
        migrations.AlterModelOptions(
            name="reservation",
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="reservation",
            index=models.Index(
                fields=["status", "expires_at"],
                name="reserv_status_expires_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="reservationitem",
            constraint=models.UniqueConstraint(
                fields=("reservation", "book"),
                name="unique_book_per_reservation",
            ),
        ),
    ]
