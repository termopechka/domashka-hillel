import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Book
from inventory.models import Inventory, StockMovement
from reservations.models import Reservation
from reservations.tasks import expire_reservations


class ReservationApiTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="warehouse-user",
            email="warehouse@example.com",
            password="password",
        )
        self.client.force_authenticate(user)
        self.book = Book.objects.create(
            external_id=uuid.uuid4(),
            isbn="9780132350884",
            title="Clean Code",
            author="Robert C. Martin",
        )
        self.inventory = Inventory.objects.create(
            book=self.book,
            quantity=5,
        )
        self.order_id = uuid.uuid4()
        self.payload = {
            "order_id": str(self.order_id),
            "items": [
                {
                    "book_id": str(self.book.external_id),
                    "quantity": 2,
                }
            ],
        }

    def create_reservation(self, **headers):
        return self.client.post(
            reverse("reservations-list"),
            self.payload,
            format="json",
            **headers,
        )

    def test_create_reservation_reserves_stock(self):
        response = self.create_reservation(HTTP_IDEMPOTENCY_KEY="order-reservation-1")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Reservation.Status.PENDING)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 5)
        self.assertEqual(self.inventory.reserved_quantity, 2)
        self.assertEqual(
            StockMovement.objects.filter(
                movement_type=StockMovement.MovementType.RESERVATION
            ).count(),
            1,
        )

    def test_service_api_key_can_create_reservation(self):
        self.client.force_authenticate(user=None)

        response = self.create_reservation(
            HTTP_X_SERVICE_API_KEY="test-service-key",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_reservation_returns_409_for_insufficient_stock(self):
        self.payload["items"][0]["quantity"] = 6

        response = self.create_reservation()

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "INSUFFICIENT_STOCK")
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, 0)

    def test_repeated_create_is_idempotent(self):
        first = self.create_reservation(HTTP_IDEMPOTENCY_KEY="same-key")
        second = self.create_reservation(HTTP_IDEMPOTENCY_KEY="same-key")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["reservation_id"], second.data["reservation_id"])
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, 2)
        self.assertEqual(Reservation.objects.count(), 1)

    def test_idempotency_key_rejects_a_different_payload(self):
        self.create_reservation(HTTP_IDEMPOTENCY_KEY="same-key")
        self.payload["order_id"] = str(uuid.uuid4())

        response = self.create_reservation(HTTP_IDEMPOTENCY_KEY="same-key")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "IDEMPOTENCY_CONFLICT")

    def test_reservation_can_be_retrieved_and_filtered_by_order(self):
        created = self.create_reservation()

        detail = self.client.get(
            reverse(
                "reservations-detail",
                kwargs={"reservation_id": created.data["reservation_id"]},
            )
        )
        filtered = self.client.get(
            reverse("reservations-list"),
            {"order_id": str(self.order_id)},
        )

        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(filtered.status_code, status.HTTP_200_OK)
        self.assertEqual(filtered.data["count"], 1)
        self.assertEqual(
            filtered.data["results"][0]["reservation_id"],
            created.data["reservation_id"],
        )

    def test_confirm_reservation_deducts_stock_once(self):
        created = self.create_reservation()
        confirm_url = reverse(
            "reservations-confirm",
            kwargs={"reservation_id": created.data["reservation_id"]},
        )

        first = self.client.post(confirm_url, format="json")
        second = self.client.post(confirm_url, format="json")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 3)
        self.assertEqual(self.inventory.reserved_quantity, 0)
        self.assertEqual(first.data["status"], Reservation.Status.CONFIRMED)

    def test_cancel_reservation_releases_stock(self):
        created = self.create_reservation()
        cancel_url = reverse(
            "reservations-cancel",
            kwargs={"reservation_id": created.data["reservation_id"]},
        )

        response = self.client.post(
            cancel_url,
            {"reason": Reservation.CancellationReason.PAYMENT_FAILED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Reservation.Status.CANCELLED)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 5)
        self.assertEqual(self.inventory.reserved_quantity, 0)

    def test_expired_reservation_cannot_be_confirmed(self):
        created = self.create_reservation()
        reservation = Reservation.objects.get(public_id=created.data["reservation_id"])
        reservation.expires_at = timezone.now() - timedelta(seconds=1)
        reservation.save(update_fields=["expires_at"])

        response = self.client.post(
            reverse(
                "reservations-confirm",
                kwargs={"reservation_id": reservation.public_id},
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        reservation.refresh_from_db()
        self.inventory.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.EXPIRED)
        self.assertEqual(self.inventory.reserved_quantity, 0)

    def test_expiration_task_releases_pending_stock(self):
        created = self.create_reservation()
        reservation = Reservation.objects.get(public_id=created.data["reservation_id"])
        reservation.expires_at = timezone.now() - timedelta(seconds=1)
        reservation.save(update_fields=["expires_at"])

        expired_count = expire_reservations()

        reservation.refresh_from_db()
        self.inventory.refresh_from_db()
        self.assertEqual(expired_count, 1)
        self.assertEqual(reservation.status, Reservation.Status.EXPIRED)
        self.assertEqual(self.inventory.reserved_quantity, 0)
