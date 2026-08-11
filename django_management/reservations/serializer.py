from rest_framework import serializers

from .models import Reservation, ReservationItem


class ReservationItemInputSerializer(serializers.Serializer):
    book_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class ReservationCreateSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    items = ReservationItemInputSerializer(many=True, allow_empty=False)

    def validate_items(self, items):
        book_ids = [item["book_id"] for item in items]
        if len(book_ids) != len(set(book_ids)):
            raise serializers.ValidationError(
                "Each book may appear only once in a reservation."
            )
        return items


class ReservationItemSerializer(serializers.ModelSerializer):
    book_id = serializers.UUIDField(source="book.external_id", read_only=True)

    class Meta:
        model = ReservationItem
        fields = ["book_id", "quantity"]


class ReservationSerializer(serializers.ModelSerializer):
    reservation_id = serializers.UUIDField(source="public_id", read_only=True)
    items = ReservationItemSerializer(many=True, read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "reservation_id",
            "order_id",
            "status",
            "cancellation_reason",
            "expires_at",
            "created_at",
            "items",
        ]


class ReservationCancelSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(
        choices=Reservation.CancellationReason.choices,
    )


class InsufficientStockDetailSerializer(serializers.Serializer):
    book_id = serializers.UUIDField()
    requested_quantity = serializers.IntegerField()
    available_quantity = serializers.IntegerField()


class InsufficientStockResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = InsufficientStockDetailSerializer(many=True)
