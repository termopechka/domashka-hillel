from django.contrib import admin

from .models import Reservation, ReservationItem


class ReservationItemInline(admin.TabularInline):
    model = ReservationItem
    extra = 0
    readonly_fields = ("book", "quantity")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("public_id", "order_id", "status", "expires_at", "created_at")
    list_filter = ("status", "cancellation_reason", "created_at")
    search_fields = ("public_id", "order_id", "idempotency_key")
    readonly_fields = ("public_id", "created_at", "updated_at")
    date_hierarchy = "created_at"
    inlines = (ReservationItemInline,)
