from django.contrib import admin

from .models import Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "isbn", "is_active", "external_id")
    list_filter = ("is_active",)
    search_fields = ("title", "author", "isbn", "external_id")
    readonly_fields = ("external_id",)
