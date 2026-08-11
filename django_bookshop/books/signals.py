from functools import partial

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cache import invalidate_book_cache, invalidate_catalog_view_cache
from .models import Book, Category
from .tasks import sync_book_with_warehouse


@receiver([post_save, post_delete], sender=Book)
def handle_book_changes(sender, instance, **kwargs):
    """Invalidate all representations of a book after a committed change."""
    transaction.on_commit(partial(invalidate_book_cache, instance.pk))
    is_deleted = kwargs.get("signal") is post_delete
    payload = {
        "external_id": str(instance.public_id),
        "isbn": instance.isbn or None,
        "title": instance.title,
        "author": instance.author,
        "is_active": not is_deleted,
    }
    transaction.on_commit(
        partial(sync_book_with_warehouse.delay, payload)
    )


@receiver([post_save, post_delete], sender=Category)
def handle_category_changes(sender, instance, **kwargs):
    """Invalidate catalog responses when category data changes."""
    transaction.on_commit(invalidate_catalog_view_cache)
