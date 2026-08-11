"""HTTP middleware used by the Warehouse API."""

import logging
import time

from .observability import bind_request_id, reset_request_id

logger = logging.getLogger("http")


class RequestIDMiddleware:
    """Accept or create an ID that connects Project A and Project B logs."""

    header_name = "X-Request-ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id, token = bind_request_id(request.headers.get(self.header_name))
        request.request_id = request_id
        started_at = time.monotonic()
        try:
            response = self.get_response(request)
            response[self.header_name] = request_id
            logger.info(
                "request.completed method=%s path=%s status=%s duration_ms=%s",
                request.method,
                request.path,
                response.status_code,
                round((time.monotonic() - started_at) * 1000, 2),
            )
            return response
        except Exception:
            logger.exception(
                "request.failed method=%s path=%s duration_ms=%s",
                request.method,
                request.path,
                round((time.monotonic() - started_at) * 1000, 2),
            )
            raise
        finally:
            reset_request_id(token)
