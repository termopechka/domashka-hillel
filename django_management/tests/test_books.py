import uuid

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Book
from inventory.models import Inventory


class BookSyncAndCacheTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.service_headers = {"HTTP_X_SERVICE_API_KEY": "test-service-key"}
        self.external_id = uuid.uuid4()
        self.payload = {
            "external_id": str(self.external_id),
            "isbn": "9780135957059",
            "title": "The Pragmatic Programmer",
            "author": "David Thomas",
            "is_active": True,
        }

    def test_service_key_can_synchronize_book_idempotently(self):
        url = reverse("books-sync")

        first = self.client.post(
            url,
            self.payload,
            format="json",
            **self.service_headers,
        )
        self.payload["title"] = "The Pragmatic Programmer, 20th Anniversary"
        second = self.client.post(
            url,
            self.payload,
            format="json",
            **self.service_headers,
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        book = Book.objects.get(external_id=self.external_id)
        self.assertEqual(book.title, self.payload["title"])
        self.assertTrue(Inventory.objects.filter(book=book).exists())
        self.assertEqual(Book.objects.count(), 1)

    def test_invalid_service_key_is_rejected(self):
        response = self.client.post(
            reverse("books-sync"),
            self.payload,
            format="json",
            HTTP_X_SERVICE_API_KEY="wrong-key",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["request_id"], response["X-Request-ID"])

    def test_book_detail_cache_is_invalidated_after_sync(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                reverse("books-sync"),
                self.payload,
                format="json",
                **self.service_headers,
            )
        detail_url = reverse(
            "books-detail",
            kwargs={"external_id": self.external_id},
        )

        first = self.client.get(detail_url, **self.service_headers)
        second = self.client.get(detail_url, **self.service_headers)
        self.payload["title"] = "Updated title"
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                reverse("books-sync"),
                self.payload,
                format="json",
                **self.service_headers,
            )
        third = self.client.get(detail_url, **self.service_headers)

        self.assertEqual(first["X-Cache"], "MISS")
        self.assertEqual(second["X-Cache"], "HIT")
        self.assertEqual(third["X-Cache"], "MISS")
        self.assertEqual(third.data["title"], "Updated title")


class LocalizedDocumentationTests(TestCase):
    def test_ukrainian_schema_and_admin_are_available(self):
        schema = self.client.get("/uk/api/schema/")
        admin_login = self.client.get("/uk/admin/login/")

        self.assertEqual(schema.status_code, status.HTTP_200_OK)
        self.assertIn("API керування складом", schema.content.decode("utf-8"))
        self.assertEqual(admin_login.status_code, status.HTTP_200_OK)
        self.assertContains(admin_login, "Адміністрування складу")
