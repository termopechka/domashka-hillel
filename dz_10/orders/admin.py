from django.contrib import admin
from .models import Order


class OrderAdmin(admin.ModelAdmin):
    model = Order
    list_filter = ('user',)
    search_fields = ('user', 'status')


admin.site.register(Order, OrderAdmin)
