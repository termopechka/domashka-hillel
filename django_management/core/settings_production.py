"""Strict settings for the Warehouse production container."""

import os

from django.core.exceptions import ImproperlyConfigured

from .monitoring import configure_sentry
from .settings import *  # noqa: F401,F403
from .settings import env_bool, env_list

DEBUG = False

render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
if render_hostname and render_hostname not in ALLOWED_HOSTS:  # noqa: F405
    ALLOWED_HOSTS.append(render_hostname)  # noqa: F405

if not SECRET_KEY:  # noqa: F405
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production")
if not os.environ.get("DJANGO_ALLOWED_HOSTS", "").strip() and not render_hostname:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set in production")
if not WAREHOUSE_SERVICE_API_KEY:  # noqa: F405
    raise ImproperlyConfigured("WAREHOUSE_SERVICE_API_KEY must be set in production")

MIDDLEWARE = [*MIDDLEWARE]  # noqa: F405
security_index = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
MIDDLEWARE.insert(
    security_index + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
WHITENOISE_AUTOREFRESH = False
WHITENOISE_USE_FINDERS = False
WHITENOISE_KEEP_ONLY_HASHED_FILES = True

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
if render_hostname:
    render_origin = f"https://{render_hostname}"
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

configure_sentry()
