from rest_framework import serializers
from .models import (
    Inventory,
    StockMovement,
    StockReturn,
    StockReturnItem,
)


class InventorySerializer(serializers.ModelSerializer):
    book_id = serializers.UUIDField(
        source="book.external_id",
        read_only=True,
    )
    available_quantity = serializers.IntegerField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Inventory
        fields = [
            "book_id",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "in_stock",
        ]


class InventoryReceiptsSerializer(serializers.Serializer):
    book_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    reference = serializers.CharField(
        max_length=255,
        allow_blank=True,
        required=False,
    )


class InventoryWriteOffsSerializer(serializers.Serializer):
    book_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    reason = serializers.ChoiceField(
        choices=StockMovement.WriteOffReason.choices,
    )
    reference = serializers.CharField(
        max_length=255,
        allow_blank=True,
        required=False,
    )


class InventoryAdjustmentSerializer(serializers.Serializer):
    book_id = serializers.UUIDField()
    new_quantity = serializers.IntegerField(min_value=0)
    reason = serializers.ChoiceField(
        choices=StockMovement.AdjustmentReason.choices,
    )
    reference = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )


class InventoryItemSerializer(serializers.Serializer):
    book_id = serializers.UUIDField()
    quantity = serializers.IntegerField(source="requested_quantity", min_value=1)


class InventoryCheckSerializer(serializers.Serializer):
    items = InventoryItemSerializer(
        many=True,
        allow_empty=False,
    )


class InventoryCheckItemResponseSerializer(serializers.Serializer):
    book_id = serializers.UUIDField()
    requested_quantity = serializers.IntegerField()
    available_quantity = serializers.IntegerField()
    available = serializers.BooleanField()


class InventoryCheckResponseSerializer(serializers.Serializer):
    available = serializers.BooleanField()
    items = InventoryCheckItemResponseSerializer(many=True)


class StockReturnItemInputSerializer(serializers.Serializer):
    book_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class StockReturnCreateSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    items = StockReturnItemInputSerializer(many=True, allow_empty=False)
    reason = serializers.ChoiceField(
        choices=StockMovement.ReturnReason.choices,
    )

    def validate_items(self, items):
        book_ids = [item["book_id"] for item in items]
        if len(book_ids) != len(set(book_ids)):
            raise serializers.ValidationError(
                "Each book may appear only once in a return."
            )
        return items


class StockReturnItemSerializer(serializers.ModelSerializer):
    book_id = serializers.UUIDField(source="book.external_id", read_only=True)

    class Meta:
        model = StockReturnItem
        fields = ["book_id", "quantity"]


class StockReturnSerializer(serializers.ModelSerializer):
    return_id = serializers.UUIDField(source="public_id", read_only=True)
    items = StockReturnItemSerializer(many=True, read_only=True)

    class Meta:
        model = StockReturn
        fields = ["return_id", "order_id", "reason", "created_at", "items"]


class StockMovementSerializer(serializers.ModelSerializer):
    book_id = serializers.UUIDField(source="book.external_id", read_only=True)
    type = serializers.CharField(source="movement_type", read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "book_id",
            "type",
            "quantity",
            "reason",
            "reference",
            "created_at",
        ]
