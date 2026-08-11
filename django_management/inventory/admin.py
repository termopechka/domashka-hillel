from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Inventory, StockMovement, StockReturn, StockReturnItem


class StockReturnItemInline(admin.TabularInline):
    model = StockReturnItem
    extra = 0
    readonly_fields = ("book", "quantity")


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = (
        "book",
        "quantity",
        "reserved_quantity",
        "available_stock",
    )
    search_fields = ("book__title", "book__author", "book__external_id")
    list_select_related = ("book",)

    @admin.display(description=_("Available quantity"))
    def available_stock(self, obj):
        return obj.available_quantity


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "book",
        "movement_type",
        "quantity",
        "reason",
        "reference",
    )
    list_filter = ("movement_type", "reason", "created_at")
    search_fields = ("book__title", "book__external_id", "reference")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(StockReturn)
class StockReturnAdmin(admin.ModelAdmin):
    list_display = ("public_id", "order_id", "reason", "created_at")
    list_filter = ("reason", "created_at")
    search_fields = ("public_id", "order_id", "idempotency_key")
    readonly_fields = ("public_id", "created_at")
    inlines = (StockReturnItemInline,)
