import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key")
os.environ.setdefault("REDIS_PASSWORD", "test-password")

from .settings import *  # noqa: F401,F403,E402

ALLOWED_HOSTS = ["testserver"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
WAREHOUSE_SERVICE_API_KEY = "test-service-key"
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "warehouse-tests",
    }
}
LOGGING["root"]["level"] = "WARNING"  # noqa: F405
