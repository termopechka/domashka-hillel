from django.core.management.base import BaseCommand

from BookShop.integrations.warehouse import get_warehouse_client
from books.models import Book


class Command(BaseCommand):
    help = "Synchronize the complete Bookshop catalog with Warehouse"

    def handle(self, *args, **options):
        client = get_warehouse_client()
        synchronized = 0
        for book in Book.objects.iterator():
            client.sync_book(
                {
                    "external_id": str(book.public_id),
                    "isbn": book.isbn or None,
                    "title": book.title,
                    "author": book.author,
                    "is_active": True,
                }
            )
            synchronized += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Synchronized {synchronized} books with Warehouse."
            )
        )
