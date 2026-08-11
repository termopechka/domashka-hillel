from django.contrib import admin
from .models import Order


class OrderAdmin(admin.ModelAdmin):
    model = Order
    list_display = (
        "id",
        "public_id",
        "user",
        "status",
        "warehouse_status",
        "created_at",
    )
    list_filter = ("status", "warehouse_status", "payment_method")
    search_fields = (
        "public_id",
        "user__username",
        "user__email",
        "warehouse_reservation_id",
    )
    readonly_fields = ("public_id", "warehouse_reservation_id", "warehouse_status")


admin.site.register(Order, OrderAdmin)
