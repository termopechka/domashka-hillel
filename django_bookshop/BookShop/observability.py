"""Small observability helpers shared by HTTP and background work."""

import logging
import uuid
from contextvars import ContextVar


_request_id = ContextVar("request_id", default="-")


def current_request_id():
    """Return the active correlation ID, creating one for background work."""
    value = _request_id.get()
    return value if value != "-" else str(uuid.uuid4())


def bind_request_id(value=None):
    """Bind a safe request ID and return the ContextVar reset token."""
    request_id = (value or "").strip()[:128] or str(uuid.uuid4())
    return request_id, _request_id.set(request_id)


def reset_request_id(token):
    _request_id.reset(token)


class RequestIDLogFilter(logging.Filter):
    """Ensure every log record can be correlated across services."""

    def filter(self, record):
        if not getattr(record, "request_id", None):
            record.request_id = _request_id.get()
        return True
