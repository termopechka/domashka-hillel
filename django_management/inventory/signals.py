from functools import partial

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from books.models import Book

from .cache import invalidate_book_state
from .models import Inventory


@receiver([post_save, post_delete], sender=Book)
def invalidate_book_cache(sender, instance, **kwargs):
    transaction.on_commit(
        partial(invalidate_book_state, instance.external_id)
    )


@receiver(post_save, sender=Inventory)
def invalidate_inventory_cache(sender, instance, **kwargs):
    transaction.on_commit(
        partial(invalidate_book_state, instance.book.external_id)
    )
