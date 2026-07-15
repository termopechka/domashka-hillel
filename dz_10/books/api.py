from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BooksViewSet, CategoryViewSet, CartViewSet

app_name = 'catalog'

router = DefaultRouter()
router.register('books', BooksViewSet, basename='books')
router.register('categories', CategoryViewSet, basename='categories')
router.register('cart', CartViewSet, basename='cart')

urlpatterns = [
    path('', include(router.urls)),
]
