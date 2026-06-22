from django.contrib import admin

from orders.models import OrderItem
from .models import Category, Book

class CategoryInLine(admin.TabularInline):
    model = Category
    extra = 1


class BookAdmin(admin.ModelAdmin):
    model = Book
    list_filter = ('category', 'category__name')
    search_fields = ('title', 'description')



class CategoryAdmin(admin.ModelAdmin):
    inlines = [CategoryInLine]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

admin.site.register(Book, BookAdmin)
admin.site.register(Category)
admin.site.register(OrderItem)
