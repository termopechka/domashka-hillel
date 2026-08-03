from rest_framework import serializers
from .models import Book, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = "__all__"


class CartSerializer(serializers.Serializer):
    cart = serializers.DictField(child=serializers.IntegerField(min_value=1))
    message = serializers.CharField(required=False)
    error = serializers.CharField(required=False)
