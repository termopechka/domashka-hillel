"""Settings for Docker and Render production deployments."""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import configure_sentry, env_bool, env_list

DEBUG = False

render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
if render_hostname and render_hostname not in ALLOWED_HOSTS:  # noqa: F405
    ALLOWED_HOSTS.append(render_hostname)  # noqa: F405

if not SECRET_KEY:  # noqa: F405
    raise ImproperlyConfigured("SECRET_KEY must be set in production")

if not ALLOWED_HOSTS:  # noqa: F405
    raise ImproperlyConfigured("ALLOWED_HOSTS must be set in production")

MIDDLEWARE = [*MIDDLEWARE]  # noqa: F405
security_middleware_index = MIDDLEWARE.index(
    "django.middleware.security.SecurityMiddleware"
)
MIDDLEWARE.insert(
    security_middleware_index + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
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

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)

configure_sentry("production")
