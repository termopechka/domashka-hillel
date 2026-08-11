"""DRF error response and logging policy."""

import logging

from rest_framework.views import exception_handler

from .observability import get_request_id

logger = logging.getLogger("api.errors")


def warehouse_exception_handler(exc, context):
    """Add a correlation ID without replacing the API's useful error detail."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    request_id = get_request_id()
    if isinstance(response.data, dict):
        response.data.setdefault("request_id", request_id)
    logger.warning(
        "api.request_rejected view=%s status=%s error=%s",
        context.get("view").__class__.__name__ if context.get("view") else "-",
        response.status_code,
        exc.__class__.__name__,
    )
    return response
