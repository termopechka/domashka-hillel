from rest_framework import serializers
from .models import Order, OrderItem


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            "id",
            "public_id",
            "user",
            "status",
            "created_at",
            "updated_at",
            "paid_at",
            "shipping_address",
            "city",
            "postal_code",
            "country",
            "payment_method",
            "payment_id",
            "warehouse_reservation_id",
            "warehouse_status",
            "total_price",
        )
        read_only_fields = (
            "id",
            "public_id",
            "created_at",
            "updated_at",
            "paid_at",
            "warehouse_reservation_id",
            "warehouse_status",
        )


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("order", "book", "book_name", "price", "quantity")
