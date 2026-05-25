from django.contrib import admin
from .models import Book, Category, User


class CategoryInLine(admin.TabularInline):
    model = Category
    extra = 1


class BookAdmin(admin.ModelAdmin):
    model = Book
    list_filter = ('category', 'category__name')
    search_fields = ('title', 'description')



class CategoryAdmin(admin.ModelAdmin):
    inlines = [CategoryInLine]


admin.site.register(Book, BookAdmin)
admin.site.register(Category)
admin.site.register(User)