from django.conf import settings
from django.core.cache import cache, caches
from django.core.cache.utils import make_template_fragment_key

BOOK_CACHE_TIMEOUT = 60 * 15
BOOK_DETAIL_FRAGMENT_NAME = "book_detail"


def get_book_cache_key(book_id):
    """Return the shared low-level cache key for one book."""
    return f"books:detail:{book_id}"


def get_book_detail_fragment_keys(book_id):
    """Return every localized template-fragment key for one book."""
    return [
        make_template_fragment_key(
            BOOK_DETAIL_FRAGMENT_NAME,
            [book_id, language_code],
        )
        for language_code, _language_name in settings.LANGUAGES
    ]


def invalidate_catalog_view_cache():
    """Clear only the cache dedicated to complete catalog responses."""
    caches["views"].clear()


def invalidate_book_cache(book_id):
    """Invalidate low-level, fragment, and view caches affected by a book."""
    cache.delete(get_book_cache_key(book_id))
    cache.delete_many(get_book_detail_fragment_keys(book_id))
    invalidate_catalog_view_cache()
