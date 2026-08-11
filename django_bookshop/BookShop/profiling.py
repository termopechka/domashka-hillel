"""Optional profiling decorators that become no-ops outside development."""

from django.conf import settings

if "silk" in settings.INSTALLED_APPS:
    from silk.profiling.profiler import silk_profile
else:

    def silk_profile(name=None):
        """Return a no-op decorator when Silk is not installed."""

        def decorator(func):
            return func

        return decorator
