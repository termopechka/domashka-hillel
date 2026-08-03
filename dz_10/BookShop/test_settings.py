from .settings.base import *  # noqa: F401,F403

SECRET_KEY = "test-secret-key-not-for-production-32-bytes"
DEBUG = False
ALLOWED_HOSTS = ["testserver"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "bookshop-test-default",
    },
    "views": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "bookshop-test-views",
    },
    "sessions": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "bookshop-test-sessions",
    },
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
