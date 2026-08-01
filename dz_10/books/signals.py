from functools import partial

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cache import invalidate_book_cache, invalidate_catalog_view_cache
from .models import Book, Category


@receiver([post_save, post_delete], sender=Book)
def handle_book_changes(sender, instance, **kwargs):
    """Invalidate all representations of a book after a committed change."""
    transaction.on_commit(partial(invalidate_book_cache, instance.pk))


@receiver([post_save, post_delete], sender=Category)
def handle_category_changes(sender, instance, **kwargs):
    """Invalidate catalog responses when category data changes."""
    transaction.on_commit(invalidate_catalog_view_cache)
