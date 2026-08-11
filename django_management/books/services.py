from dataclasses import dataclass

from django.db import transaction

from inventory.models import Inventory

from .models import Book


@dataclass(frozen=True)
class BookSyncResult:
    book: Book
    created: bool


@transaction.atomic
def sync_book(*, external_id, title, author, isbn=None, is_active=True):
    book = (
        Book.objects.select_for_update()
        .filter(external_id=external_id)
        .first()
    )
    created = book is None
    if created:
        book = Book.objects.create(
            external_id=external_id,
            isbn=isbn,
            title=title,
            author=author,
            is_active=is_active,
        )
    else:
        book.isbn = isbn
        book.title = title
        book.author = author
        book.is_active = is_active
        book.save(update_fields=["isbn", "title", "author", "is_active"])

    Inventory.objects.get_or_create(book=book)
    return BookSyncResult(book=book, created=created)
