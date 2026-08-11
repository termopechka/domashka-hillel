from django.db import transaction
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.authentication import ServiceAPIKeyAuthentication

from .cache import get_inventory_snapshots, inventory_snapshot
from .models import Inventory, StockMovement, StockReturn
from .serializer import (
    InventoryAdjustmentSerializer,
    InventoryCheckResponseSerializer,
    InventoryCheckSerializer,
    InventoryReceiptsSerializer,
    InventorySerializer,
    InventoryWriteOffsSerializer,
    StockMovementSerializer,
    StockReturnCreateSerializer,
    StockReturnSerializer,
)
from .services import create_stock_return


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Inventory.objects.select_related("book")
    serializer_class = InventorySerializer
    lookup_url_kwarg = "book_id"
    authentication_classes = [JWTAuthentication, ServiceAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        book_id = self.kwargs[self.lookup_url_kwarg]
        snapshot = get_inventory_snapshots([book_id]).get(str(book_id))
        if snapshot is None:
            inventory = get_object_or_404(
                self.get_queryset(),
                book__external_id=book_id,
                book__is_active=True,
            )
            snapshot = inventory_snapshot(inventory)
        return Response(snapshot)

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        inventory = get_object_or_404(
            queryset,
            book__external_id=self.kwargs[self.lookup_url_kwarg],
        )
        self.check_object_permissions(self.request, inventory)
        return inventory

    @extend_schema(
        summary=_("Check book availability"),
        request=InventoryCheckSerializer,
        responses={200: InventoryCheckResponseSerializer},
    )
    @action(detail=False, methods=["post"])
    def check(self, request):
        serializer = InventoryCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        requested_items = serializer.validated_data["items"]
        book_ids = [item["book_id"] for item in requested_items]
        snapshots = get_inventory_snapshots(book_ids)

        results = []
        for item in requested_items:
            book_id = item["book_id"]
            requested_quantity = item["requested_quantity"]
            snapshot = snapshots.get(str(book_id))
            available_quantity = (
                snapshot["available_quantity"] if snapshot else 0
            )
            available = available_quantity >= requested_quantity
            results.append(
                {
                    "book_id": book_id,
                    "requested_quantity": requested_quantity,
                    "available_quantity": available_quantity,
                    "available": available,
                }
            )

        return Response(
            {
                "available": all(item["available"] for item in results),
                "items": results,
            }
        )

    @extend_schema(
        summary=_("Receive stock"),
        request=InventoryReceiptsSerializer,
        responses={200: InventorySerializer},
    )
    @action(detail=False, methods=["post"])
    def receipts(self, request):
        serializer = InventoryReceiptsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book_id = serializer.validated_data["book_id"]
        quantity = serializer.validated_data["quantity"]
        reference = serializer.validated_data.get("reference", "")

        with transaction.atomic():
            inventory = get_object_or_404(
                Inventory.objects.select_for_update().select_related("book"),
                book__external_id=book_id,
            )
            inventory.quantity += quantity
            inventory.save(update_fields=["quantity"])
            StockMovement.objects.create(
                book=inventory.book,
                movement_type=StockMovement.MovementType.RECEIPT,
                quantity=quantity,
                reference=reference,
            )

        return Response(InventorySerializer(inventory).data)

    @extend_schema(
        summary=_("Write off stock"),
        request=InventoryWriteOffsSerializer,
        responses={200: InventorySerializer},
    )
    @action(detail=False, methods=["post"], url_path="write-offs")
    def write_offs(self, request):
        serializer = InventoryWriteOffsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book_id = serializer.validated_data["book_id"]
        quantity = serializer.validated_data["quantity"]
        reason = serializer.validated_data["reason"]
        reference = serializer.validated_data.get("reference", "")

        with transaction.atomic():
            inventory = get_object_or_404(
                Inventory.objects.select_for_update().select_related("book"),
                book__external_id=book_id,
            )
            if not inventory.can_fulfill(quantity):
                raise ValidationError(
                    {
                        "quantity": (
                            "Not enough unreserved stock. "
                            f"Available quantity: {inventory.available_quantity}."
                        )
                    }
                )
            inventory.quantity -= quantity
            inventory.save(update_fields=["quantity"])
            StockMovement.objects.create(
                book=inventory.book,
                movement_type=StockMovement.MovementType.WRITE_OFF,
                quantity=-quantity,
                reason=reason,
                reference=reference,
            )

        return Response(InventorySerializer(inventory).data)

    @extend_schema(
        summary=_("Adjust stock quantity"),
        request=InventoryAdjustmentSerializer,
        responses={200: InventorySerializer},
    )
    @action(detail=False, methods=["post"])
    def adjustments(self, request):
        serializer = InventoryAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book_id = serializer.validated_data["book_id"]
        new_quantity = serializer.validated_data["new_quantity"]
        reason = serializer.validated_data["reason"]
        reference = serializer.validated_data.get("reference", "")

        with transaction.atomic():
            inventory = get_object_or_404(
                Inventory.objects.select_for_update().select_related("book"),
                book__external_id=book_id,
            )
            if new_quantity < inventory.reserved_quantity:
                raise ValidationError(
                    {
                        "new_quantity": (
                            "New quantity cannot be lower than reserved quantity. "
                            f"Reserved quantity: {inventory.reserved_quantity}."
                        )
                    }
                )
            difference = new_quantity - inventory.quantity
            if difference == 0:
                raise ValidationError(
                    {
                        "new_quantity": (
                            "The new quantity is the same as the current quantity."
                        )
                    }
                )
            inventory.quantity = new_quantity
            inventory.save(update_fields=["quantity"])
            StockMovement.objects.create(
                book=inventory.book,
                movement_type=StockMovement.MovementType.ADJUSTMENT,
                quantity=difference,
                reason=reason,
                reference=reference,
            )

        return Response(InventorySerializer(inventory).data)


class StockReturnViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = StockReturn.objects.prefetch_related("items__book")
    serializer_class = StockReturnSerializer
    lookup_field = "public_id"
    lookup_url_kwarg = "return_id"
    http_method_names = ["get", "post", "head", "options"]
    authentication_classes = [JWTAuthentication, ServiceAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary=_("Register a customer return"),
        request=StockReturnCreateSerializer,
        responses={200: StockReturnSerializer, 201: StockReturnSerializer},
    )
    def create(self, request):
        serializer = StockReturnCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        idempotency_key = request.headers.get("Idempotency-Key", "")
        if len(idempotency_key) > 255:
            raise ValidationError(
                {"Idempotency-Key": "Must not exceed 255 characters."}
            )
        result = create_stock_return(
            order_id=serializer.validated_data["order_id"],
            items=serializer.validated_data["items"],
            reason=serializer.validated_data["reason"],
            idempotency_key=idempotency_key,
        )
        response_status = (
            status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
        )
        return Response(
            StockReturnSerializer(result.stock_return).data,
            status=response_status,
        )


class StockMovementPagination(LimitOffsetPagination):
    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        response.data["content"] = response.data.pop("results")
        return response


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.select_related("book")
    serializer_class = StockMovementSerializer
    pagination_class = StockMovementPagination
    authentication_classes = [JWTAuthentication, ServiceAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary=_("List stock movements"),
        parameters=[
            OpenApiParameter(
                name="book_id",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by the external book UUID.",
            ),
            OpenApiParameter(
                name="type",
                type=str,
                enum=StockMovement.MovementType.values,
                location=OpenApiParameter.QUERY,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        book_id = self.request.query_params.get("book_id")
        movement_type = self.request.query_params.get("type")
        if book_id:
            queryset = queryset.filter(book__external_id=book_id)
        if movement_type:
            valid_types = set(StockMovement.MovementType.values)
            if movement_type not in valid_types:
                raise ValidationError(
                    {"type": (f'Must be one of: {", ".join(sorted(valid_types))}.')}
                )
            queryset = queryset.filter(movement_type=movement_type)
        return queryset
