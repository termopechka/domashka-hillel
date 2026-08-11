import logging
import time

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from BookShop.observability import current_request_id

logger = logging.getLogger(__name__)


class WarehouseError(Exception):
    """Base error for Warehouse communication."""

    def __init__(self, message, *, request_id=None, status_code=None):
        self.request_id = request_id
        self.status_code = status_code
        super().__init__(message)


class WarehouseUnavailable(WarehouseError):
    """The Warehouse service could not produce a response."""


class WarehouseRejected(WarehouseError):
    """The Warehouse service rejected a valid HTTP request."""

    def __init__(self, status_code, payload, *, request_id=None):
        if not isinstance(payload, dict):
            payload = {"message": "Warehouse rejected the request.", "details": payload}
        self.payload = payload
        message = payload.get("message", "Warehouse rejected the request.")
        super().__init__(
            message,
            request_id=request_id,
            status_code=status_code,
        )


class WarehouseClient:
    def __init__(
        self,
        base_url=None,
        api_key=None,
        timeout=None,
        retries=None,
        retry_backoff=None,
        session=None,
    ):
        self.base_url = (base_url or settings.WAREHOUSE_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.WAREHOUSE_SERVICE_API_KEY
        self.timeout = timeout or settings.WAREHOUSE_HTTP_TIMEOUT
        self.session = session or requests.Session()
        if session is None:
            retry_policy = Retry(
                total=(
                    settings.WAREHOUSE_HTTP_RETRIES
                    if retries is None
                    else retries
                ),
                connect=(
                    settings.WAREHOUSE_HTTP_RETRIES
                    if retries is None
                    else retries
                ),
                read=(
                    settings.WAREHOUSE_HTTP_RETRIES
                    if retries is None
                    else retries
                ),
                status=(
                    settings.WAREHOUSE_HTTP_RETRIES
                    if retries is None
                    else retries
                ),
                backoff_factor=(
                    settings.WAREHOUSE_HTTP_RETRY_BACKOFF
                    if retry_backoff is None
                    else retry_backoff
                ),
                allowed_methods=frozenset({"GET", "POST"}),
                status_forcelist=(429, 500, 502, 503, 504),
                respect_retry_after_header=True,
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry_policy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

    def _request(
        self,
        method,
        path,
        *,
        json=None,
        idempotency_key=None,
        expected_statuses=(200,),
    ):
        request_id = current_request_id()
        log_context = {"request_id": request_id}
        headers = {
            "Accept": "application/json",
            "X-Service-API-Key": self.api_key,
            "X-Request-ID": request_id,
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        method = method.upper()
        url = f"{self.base_url}/{path.lstrip('/')}"
        started_at = time.monotonic()
        logger.info(
            "warehouse.request started method=%s path=%s",
            method,
            path,
            extra=log_context,
        )
        try:
            response = self.session.request(
                method,
                url,
                json=json,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            logger.error(
                "warehouse.request unavailable method=%s path=%s "
                "duration_ms=%s error=%s",
                method,
                path,
                round((time.monotonic() - started_at) * 1000, 2),
                exc.__class__.__name__,
                extra=log_context,
            )
            raise WarehouseUnavailable(
                "Warehouse service is temporarily unavailable.",
                request_id=request_id,
            ) from exc

        response_request_id = response.headers.get("X-Request-ID", request_id)

        try:
            raw_payload = response.json() if response.content else {}
        except ValueError:
            raw_payload = {"message": "Warehouse returned an invalid response."}
        payload = (
            raw_payload
            if isinstance(raw_payload, dict)
            else {
                "message": "Warehouse returned an invalid response.",
                "details": raw_payload,
            }
        )

        if response.status_code not in expected_statuses:
            log_method = logger.error if response.status_code >= 500 else logger.warning
            log_method(
                "warehouse.request rejected method=%s path=%s status=%s duration_ms=%s",
                method,
                path,
                response.status_code,
                round((time.monotonic() - started_at) * 1000, 2),
                extra=log_context,
            )
            if response.status_code >= 500:
                raise WarehouseUnavailable(
                    payload.get("message", "Warehouse service failed."),
                    request_id=response_request_id,
                    status_code=response.status_code,
                )
            raise WarehouseRejected(
                response.status_code,
                payload,
                request_id=response_request_id,
            )
        logger.info(
            "warehouse.request completed method=%s path=%s status=%s duration_ms=%s",
            method,
            path,
            response.status_code,
            round((time.monotonic() - started_at) * 1000, 2),
            extra=log_context,
        )
        return payload

    def sync_book(self, payload):
        return self._request(
            "POST",
            "books/sync/",
            json=payload,
            expected_statuses=(200, 201),
        )

    def create_reservation(self, *, order_id, items):
        return self._request(
            "POST",
            "reservations/",
            json={"order_id": str(order_id), "items": items},
            idempotency_key=f"{order_id}-reserve",
            expected_statuses=(200, 201),
        )

    def confirm_reservation(self, reservation_id):
        return self._request(
            "POST",
            f"reservations/{reservation_id}/confirm/",
        )

    def cancel_reservation(self, reservation_id, reason):
        return self._request(
            "POST",
            f"reservations/{reservation_id}/cancel/",
            json={"reason": reason},
        )


def get_warehouse_client():
    if not settings.WAREHOUSE_SERVICE_API_KEY:
        raise WarehouseUnavailable("Warehouse service API key is not configured.")
    return WarehouseClient()
