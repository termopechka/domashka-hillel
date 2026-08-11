from django.conf import settings
from django.core.cache import cache

from .models import Inventory


def book_cache_key(external_id):
    return f"book:{external_id}"


def inventory_cache_key(external_id):
    return f"inventory:{external_id}"


def invalidate_book_state(external_id):
    cache.delete_many(
        [
            book_cache_key(external_id),
            inventory_cache_key(external_id),
        ]
    )


def inventory_snapshot(inventory):
    return {
        "book_id": str(inventory.book.external_id),
        "quantity": inventory.quantity,
        "reserved_quantity": inventory.reserved_quantity,
        "available_quantity": inventory.available_quantity,
        "in_stock": inventory.in_stock,
    }


def get_inventory_snapshots(book_ids):
    key_by_book_id = {
        str(book_id): inventory_cache_key(book_id) for book_id in book_ids
    }
    cached_by_key = cache.get_many(key_by_book_id.values())
    snapshots = {
        book_id: cached_by_key[cache_key]
        for book_id, cache_key in key_by_book_id.items()
        if cache_key in cached_by_key
    }

    missing_ids = set(key_by_book_id) - set(snapshots)
    if missing_ids:
        inventories = Inventory.objects.select_related("book").filter(
            book__external_id__in=missing_ids,
            book__is_active=True,
        )
        to_cache = {}
        for inventory in inventories:
            book_id = str(inventory.book.external_id)
            snapshot = inventory_snapshot(inventory)
            snapshots[book_id] = snapshot
            to_cache[key_by_book_id[book_id]] = snapshot
        if to_cache:
            cache.set_many(to_cache, settings.WAREHOUSE_CACHE_TIMEOUT)

    return snapshots
