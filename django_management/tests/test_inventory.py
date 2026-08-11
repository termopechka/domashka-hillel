import uuid

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Book
from inventory.models import Inventory, StockMovement, StockReturn
from reservations.services import confirm_reservation, create_reservation


class InventoryWorkflowApiTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="inventory-user",
            email="inventory@example.com",
            password="password",
        )
        self.client.force_authenticate(user)
        self.book = Book.objects.create(
            external_id=uuid.uuid4(),
            isbn="9780201616224",
            title="The Pragmatic Programmer",
            author="Andrew Hunt",
        )
        self.inventory = Inventory.objects.create(
            book=self.book,
            quantity=5,
        )

    def confirmed_order(self, quantity=2):
        order_id = uuid.uuid4()
        result = create_reservation(
            order_id,
            [{"book_id": self.book.external_id, "quantity": quantity}],
        )
        confirm_reservation(result.reservation.public_id)
        return order_id

    def test_return_restocks_confirmed_order_idempotently(self):
        order_id = self.confirmed_order()
        payload = {
            "order_id": str(order_id),
            "items": [
                {
                    "book_id": str(self.book.external_id),
                    "quantity": 1,
                }
            ],
            "reason": StockMovement.ReturnReason.CUSTOMER_RETURN,
        }

        first = self.client.post(
            reverse("returns-list"),
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY="return-1",
        )
        second = self.client.post(
            reverse("returns-list"),
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY="return-1",
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 4)
        self.assertEqual(StockReturn.objects.count(), 1)

    def test_return_cannot_exceed_sold_quantity(self):
        order_id = self.confirmed_order(quantity=1)

        response = self.client.post(
            reverse("returns-list"),
            {
                "order_id": str(order_id),
                "items": [
                    {
                        "book_id": str(self.book.external_id),
                        "quantity": 2,
                    }
                ],
                "reason": StockMovement.ReturnReason.CUSTOMER_RETURN,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 4)

    def test_stock_movements_can_be_filtered(self):
        StockMovement.objects.create(
            book=self.book,
            movement_type=StockMovement.MovementType.RECEIPT,
            quantity=3,
            reference="SUPPLY-1",
        )
        StockMovement.objects.create(
            book=self.book,
            movement_type=StockMovement.MovementType.WRITE_OFF,
            quantity=-1,
            reason=StockMovement.WriteOffReason.DAMAGED,
        )

        response = self.client.get(
            reverse("stock-movements-list"),
            {
                "book_id": str(self.book.external_id),
                "type": StockMovement.MovementType.RECEIPT,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["content"][0]["type"], "receipt")

    def test_inventory_is_retrieved_by_external_book_id(self):
        response = self.client.get(
            reverse(
                "inventory-detail",
                kwargs={"book_id": self.book.external_id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["book_id"], str(self.book.external_id))
        self.assertEqual(response.data["available_quantity"], 5)

    def test_inventory_cache_is_invalidated_after_quantity_change(self):
        url = reverse(
            "inventory-detail",
            kwargs={"book_id": self.book.external_id},
        )
        first = self.client.get(url)
        self.inventory.quantity = 8
        with self.captureOnCommitCallbacks(execute=True):
            self.inventory.save(update_fields=["quantity"])
        second = self.client.get(url)

        self.assertEqual(first.data["available_quantity"], 5)
        self.assertEqual(second.data["available_quantity"], 8)

    def test_health_check_is_public(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(reverse("health-check"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "UP")
