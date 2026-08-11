import csv
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.core.management import call_command
from django.utils import timezone

from BookShop.integrations.warehouse import (
    WarehouseUnavailable,
    get_warehouse_client,
)

from .models import Book


@shared_task(
    autoretry_for=(WarehouseUnavailable,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def sync_book_with_warehouse(payload):
    """Synchronize one catalog item with the Warehouse service."""
    if not settings.WAREHOUSE_INTEGRATION_ENABLED:
        return "Warehouse integration disabled"

    get_warehouse_client().sync_book(payload)
    return payload["external_id"]


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_async_email(subject, message, recipient_list):
    """Send email outside the web request and retry transient failures."""
    return send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        fail_silently=False,
    )


@shared_task
def generate_books_report():
    """Generate a timestamped CSV catalog report in MEDIA_ROOT/reports."""
    report_directory = Path(settings.MEDIA_ROOT) / "reports"
    report_directory.mkdir(parents=True, exist_ok=True)
    timestamp = timezone.now().strftime("%Y%m%d-%H%M%S-%f")
    report_path = report_directory / f"books-{timestamp}.csv"

    with report_path.open("w", encoding="utf-8", newline="") as report_file:
        writer = csv.writer(report_file)
        writer.writerow(["id", "title", "author", "price", "stock", "category"])
        for book in Book.objects.select_related("category").iterator():
            writer.writerow(
                [
                    book.pk,
                    book.title,
                    book.author,
                    book.price,
                    book.stock,
                    book.category.name if book.category else "",
                ]
            )

    return str(report_path.relative_to(settings.MEDIA_ROOT))


@shared_task
def clear_expired_sessions():
    """Run Django's backend-aware expired-session cleanup command."""
    call_command("clearsessions", verbosity=0)
    return "Expired sessions cleanup completed"
