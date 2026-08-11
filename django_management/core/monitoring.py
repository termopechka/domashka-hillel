"""Optional Sentry initialization for web and Celery processes."""

import os


def configure_sentry(default_environment="production"):
    sentry_dsn = os.environ.get("SENTRY_DSN", "")
    if not sentry_dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        environment=os.environ.get("SENTRY_ENVIRONMENT", default_environment),
        release=os.environ.get("SENTRY_RELEASE") or None,
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        profiles_sample_rate=float(
            os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.0")
        ),
        send_default_pii=False,
    )
