from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.authentication import ServiceAPIKeyAuthentication
from inventory.cache import book_cache_key
from inventory.models import Inventory
from .models import Book
from .serializer import BookSerializer, BookSyncSerializer
from .services import sync_book


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.select_related("inventory")
    serializer_class = BookSerializer
    pagination_class = LimitOffsetPagination
    lookup_field = "external_id"
    authentication_classes = [JWTAuthentication, ServiceAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def perform_create(self, serializer):
        book = serializer.save()

        Inventory.objects.create(
            book=book,
            quantity=0,
            reserved_quantity=0,
        )

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    def retrieve(self, request, *args, **kwargs):
        external_id = self.kwargs[self.lookup_field]
        cache_key = book_cache_key(external_id)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, headers={"X-Cache": "HIT"})

        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, dict(response.data), settings.WAREHOUSE_CACHE_TIMEOUT)
        response["X-Cache"] = "MISS"
        return response

    @extend_schema(
        summary=_("Synchronize a book from Bookshop"),
        request=BookSyncSerializer,
        responses={200: BookSerializer, 201: BookSerializer},
    )
    @action(detail=False, methods=["post"])
    def sync(self, request):
        serializer = BookSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = sync_book(**serializer.validated_data)
        response_status = (
            status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
        )
        return Response(
            BookSerializer(result.book).data,
            status=response_status,
        )
