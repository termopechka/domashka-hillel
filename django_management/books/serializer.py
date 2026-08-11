from rest_framework import serializers
from .models import Book


class NormalizeISBNMixin:
    def validate_isbn(self, value):
        return value or None


class BookSerializer(NormalizeISBNMixin, serializers.ModelSerializer):
    quantity = serializers.IntegerField(
        source='inventory.quantity',
        read_only=True,
    )
    reserved_quantity = serializers.IntegerField(
        source='inventory.reserved_quantity',
        read_only=True,
    )
    available_quantity = serializers.IntegerField(
        source='inventory.available_quantity',
        read_only=True,
    )

    class Meta:
        model = Book
        fields = [
            'external_id',
            'isbn',
            'title',
            'author',
            'quantity',
            'reserved_quantity',
            'available_quantity',
            'is_active',
        ]


class BookSyncSerializer(NormalizeISBNMixin, serializers.Serializer):
    external_id = serializers.UUIDField()
    isbn = serializers.CharField(
        max_length=13,
        allow_blank=True,
        allow_null=True,
        required=False,
    )
    title = serializers.CharField(max_length=255)
    author = serializers.CharField(max_length=255)
    is_active = serializers.BooleanField(default=True)

    def validate(self, attrs):
        isbn = attrs.get("isbn")
        external_id = attrs["external_id"]
        if (
            isbn
            and Book.objects.exclude(external_id=external_id)
            .filter(isbn=isbn)
            .exists()
        ):
            raise serializers.ValidationError(
                {"isbn": "A different book already uses this ISBN."}
            )
        return attrs
