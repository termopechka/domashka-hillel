"""Correlation IDs and logging helpers for the Warehouse service."""

import logging
import uuid
from contextvars import ContextVar

_request_id = ContextVar("request_id", default="-")


def get_request_id():
    return _request_id.get()


def bind_request_id(value=None):
    request_id = (value or "").strip()[:128] or str(uuid.uuid4())
    return request_id, _request_id.set(request_id)


def reset_request_id(token):
    _request_id.reset(token)


class RequestIDLogFilter(logging.Filter):
    def filter(self, record):
        record.request_id = get_request_id()
        return True
