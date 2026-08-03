"""Settings for local development."""

from .base import *  # noqa: F403
from .base import configure_sentry, env_bool

SECRET_KEY = SECRET_KEY or "development-only-secret-key"  # noqa: F405
DEBUG = env_bool("DEBUG", default=True)
ALLOWED_HOSTS = ALLOWED_HOSTS or [  # noqa: F405
    "localhost",
    "127.0.0.1",
    "[::1]",
    "testserver",
]

INSTALLED_APPS = [  # noqa: F405
    *INSTALLED_APPS,  # noqa: F405
    "django_extensions",
    "debug_toolbar",
    "silk",
]
MIDDLEWARE = [*MIDDLEWARE]  # noqa: F405
authentication_middleware_index = MIDDLEWARE.index(  # noqa: F405
    "django.contrib.auth.middleware.AuthenticationMiddleware"
)
MIDDLEWARE.insert(
    authentication_middleware_index + 1,
    "debug_toolbar.middleware.DebugToolbarMiddleware",
)
MIDDLEWARE.insert(
    authentication_middleware_index + 2,
    "silk.middleware.SilkyMiddleware",
)

CORS_ALLOW_ALL_ORIGINS = True

configure_sentry("development")
