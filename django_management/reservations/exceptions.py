from rest_framework.exceptions import APIException


class Conflict(APIException):
    status_code = 409
    default_code = "conflict"
    default_detail = "The request conflicts with the current resource state."


class InsufficientStock(Conflict):
    default_code = "insufficient_stock"

    def __init__(self, details):
        super().__init__(
            {
                "code": "INSUFFICIENT_STOCK",
                "message": "Not enough stock for one or more books.",
                "details": details,
            }
        )


class ReservationStateConflict(Conflict):
    def __init__(self, message):
        super().__init__(
            {
                "code": "INVALID_RESERVATION_STATE",
                "message": message,
            }
        )


class IdempotencyConflict(Conflict):
    def __init__(self):
        super().__init__(
            {
                "code": "IDEMPOTENCY_CONFLICT",
                "message": (
                    "The order or Idempotency-Key was already used with "
                    "different reservation data."
                ),
            }
        )
