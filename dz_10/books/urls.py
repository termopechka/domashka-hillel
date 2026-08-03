from django.urls import path
from .views import (
    BooksListView,
    BookDetailView,
    AddBookView,
    add_to_cart,
    remove_from_cart,
    clear_cart,
    CheckoutView,
    payment_success,
    payment_cancel,
)

app_name = "book"

urlpatterns = [
    path("cart/<int:pk>/remove_from_cart", remove_from_cart, name="remove_from_cart"),
    path("", BooksListView.as_view(), name="list"),
    path("<int:pk>/", BookDetailView.as_view(), name="detail"),
    path("add/", AddBookView.as_view(), name="add"),
    path("<int:pk>/to_cart", add_to_cart, name="add_to_cart"),
    path("cart/", CheckoutView.as_view(), name="cart_view"),
    path("cart/clear", clear_cart, name="clear_cart"),
    path("payment/success", payment_success, name="payment_success"),
    path("payment/cancel", payment_cancel, name="payment_cancel"),
]
