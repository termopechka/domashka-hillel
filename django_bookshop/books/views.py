import logging

import stripe
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView, CreateView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from BookShop.profiling import silk_profile
from BookShop.integrations.warehouse import (
    WarehouseRejected,
    WarehouseUnavailable,
)
from orders.models import Order
from orders.services import create_checkout_order
from orders.warehouse import (
    cancel_order_reservation,
    confirm_order_reservation,
    reserve_order,
)
from .cache import BOOK_CACHE_TIMEOUT, get_book_cache_key
from .forms import CheckoutForm
from .tasks import send_async_email
from .models import Book, Category
from .serializer import BookSerializer, CartSerializer, CategorySerializer

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY
STRIPE_ORDER_EVENTS = {
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
    "checkout.session.expired",
}


class BooksViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    pagination_class = LimitOffsetPagination

    @method_decorator(
        cache_page(BOOK_CACHE_TIMEOUT, cache="views", key_prefix="books-api-list")
    )
    @silk_profile(name="Book List View")
    def list(self, request, *args, **kwargs):
        logger.info("User %s requested a list of books.", request.user.get_username())
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        result = self.queryset.select_related("category")
        query = self.request.GET.get("search")
        if query:
            result = result.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        return result

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["search_query"] = self.request.GET.get("search", "")
        return context


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = LimitOffsetPagination


class CartViewSet(viewsets.ViewSet):
    serializer_class = CartSerializer

    def list(self, request):
        cart = request.session.get("cart", {})
        return Response({"cart": cart}, status=status.HTTP_200_OK)

    @extend_schema(
        parameters=[
            OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH)
        ]
    )
    @action(detail=True, methods=["post"])
    def add(self, request, pk=None):
        pk_str = str(pk)
        cart = request.session.get("cart", {})

        cart[pk_str] = cart.get(pk_str, 0) + 1
        request.session["cart"] = cart
        request.session.modified = True

        return Response(
            {"message": f"Book {pk} added to cart.", "cart": cart},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH)
        ]
    )
    @action(detail=True, methods=["post"])
    def remove(self, request, pk=None):
        pk_str = str(pk)
        cart = request.session.get("cart", {})

        if pk_str in cart:
            del cart[pk_str]
            request.session["cart"] = cart
            request.session.modified = True
            return Response(
                {"message": f"Book {pk} removed from cart.", "cart": cart},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"error": "Book not found in cart."}, status=status.HTTP_404_NOT_FOUND
        )

    @action(detail=False, methods=["post"])
    def clear(self, request):
        cart = request.session.get("cart", {})
        cart.clear()
        request.session["cart"] = cart
        request.session.modified = True

        return Response(
            {"message": "Cart cleared.", "cart": cart}, status=status.HTTP_200_OK
        )


class BooksListView(ListView):
    """Display the paginated catalog of books.

    Handles:
        GET: Renders the list of books.

    Args:
        request: Django ``HttpRequest`` handled by ``ListView``.

    Query Parameters:
        search (str, optional): Filters books by title or description using a
            case-insensitive contains lookup.
        page (int, optional): Page number for pagination.

    Path Parameters:
        None.

    Body:
        None.

    Returns:
        HttpResponse: Rendered ``books/books.html`` template with ``books``
        and ``search_query`` context values. Returns HTTP 200 for valid pages
        and Django's standard pagination error response for invalid pages.

    Permissions:
        Public endpoint. Authentication is not required.
    """

    model = Book
    context_object_name = "books"
    template_name = "books/books.html"
    paginate_by = 8

    @silk_profile(name="Book List View")
    def get(self, request, *args, **kwargs):
        logger.info("User %s requested a list of books.", request.user.get_username())

        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        result = super().get_queryset().select_related("category")
        query = self.request.GET.get("search")
        if query:
            result = result.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        return context


class BookDetailView(DetailView):
    """Display details for a single book.

    Handles:
        GET: Renders the selected book detail page.

    Args:
        request: Django ``HttpRequest`` handled by ``DetailView``.

    Query Parameters:
        None.

    Path Parameters:
        pk (int): Primary key of the requested book.

    Body:
        None.

    Returns:
        HttpResponse: Rendered ``books/book.html`` template with ``book`` in
        context and HTTP 200.
        Http404: Returned by Django when no book exists for ``pk``.

    Permissions:
        Public endpoint. Authentication is not required.
    """

    model = Book
    context_object_name = "book"
    template_name = "books/book.html"
    queryset = Book.objects.select_related("category")

    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg)
        cache_key = get_book_cache_key(pk)

        # Try to get the object from the cache
        obj = cache.get(cache_key)

        if obj is None:
            # Fall back to the standard database query
            obj = super().get_object(queryset)
            # Store the object in cache for 15 minutes (900 seconds)
            cache.set(cache_key, obj, BOOK_CACHE_TIMEOUT)

        return obj


class AddBookView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create a new book entry.

    Handles:
        GET: Renders the book creation form.
        POST: Validates submitted book data and creates a book.

    Args:
        request: Django ``HttpRequest`` handled by ``CreateView``.

    Query Parameters:
        None.

    Path Parameters:
        None.

    Body:
        title (str): Book title.
        author (str): Book author.
        price (Decimal, optional): Book price.
        description (str): Book description.
        stock (int): Available stock count.
        category (int, optional): Category primary key.

    Returns:
        HttpResponse: Rendered ``books/form_book.html`` with HTTP 200 for GET
        or invalid POST data.
        HttpResponseRedirect: Redirect to the model success URL after a valid
        POST.
        HttpResponseForbidden: HTTP 403 when an authenticated user lacks
        ``books.add_book`` permission.

    Permissions:
        Requires authentication and ``books.add_book`` permission. Anonymous
        users are redirected to the ``auth:login`` route.
    """

    model = Book
    permission_required = "books.add_book"
    fields = ["title", "author", "price", "description", "stock", "category"]
    login_url = reverse_lazy("auth:login")
    raise_exception = True
    template_name = "books/form_book.html"


def add_to_cart(request, pk):
    """Add one book unit to the session cart.

    Handles:
        GET: Increments the selected book quantity in ``request.session``.

    Args:
        request: Django ``HttpRequest`` with session support.
        pk (int): Primary key of the book to add.

    Query Parameters:
        None.

    Path Parameters:
        pk (int): Book primary key from the URL.

    Body:
        None.

    Returns:
        HttpResponseRedirect: Redirects to ``index`` with HTTP 302 after the
        cart session value is updated.

    Permissions:
        Public endpoint. Authentication is not required.
    """

    pk_str = str(pk)
    cart = request.session.get("cart", {})
    cart[pk_str] = cart.get(pk_str, 0) + 1
    request.session["cart"] = cart
    request.session.modified = True
    return redirect("index")


@require_POST
def remove_from_cart(request, pk):
    """Remove a book from the session cart.

    Handles:
        POST: Deletes the selected book key from ``request.session['cart']``.

    Args:
        request: Django ``HttpRequest`` with session support.
        pk (int): Primary key of the book to remove.

    Query Parameters:
        None.

    Path Parameters:
        pk (int): Book primary key from the URL.

    Body:
        None.

    Returns:
        HttpResponseRedirect: Redirects to ``index`` with HTTP 302.
        HttpResponseNotAllowed: HTTP 405 for non-POST requests, enforced by
        ``require_POST``.

    Permissions:
        Public endpoint. Authentication is not required.
    """

    cart = request.session.get("cart", {})
    pk = str(pk)
    if pk in cart:
        del cart[pk]
        request.session["cart"] = cart
        request.session.modified = True

    return redirect("index")


def clear_cart(request):
    """Clear all items from the session cart.

    Handles:
        GET: Empties ``request.session['cart']``.

    Args:
        request: Django ``HttpRequest`` with session support.

    Query Parameters:
        None.

    Path Parameters:
        None.

    Body:
        None.

    Returns:
        HttpResponseRedirect: Redirects to ``index`` with HTTP 302.

    Permissions:
        Public endpoint. Authentication is not required.
    """

    cart = request.session.get("cart", {})
    cart.clear()
    request.session["cart"] = cart
    return redirect("index")


class CheckoutView(LoginRequiredMixin, View):
    """Display the cart and create Stripe checkout sessions for orders.

    Handles:
        GET: Renders the current cart and checkout form.
        POST: Validates shipping/payment data, creates an order and order
        items, creates a Stripe checkout session, clears the cart, and
        redirects to Stripe.

    Args:
        request: Django ``HttpRequest`` handled by ``View``.

    Query Parameters:
        None.

    Path Parameters:
        None.

    Body:
        shipping_address (str): Delivery street address.
        city (str): Delivery city.
        postal_code (str): Delivery postal code.
        country (str): Delivery country.
        payment_method (str): Selected payment method from ``Order`` choices.

    Returns:
        HttpResponse: Rendered ``cart.html`` with ``cart_obj`` and ``form`` on
        GET or invalid POST data.
        HttpResponseRedirect: Redirects to Stripe checkout with HTTP 303 after
        a valid POST.

    Permissions:
        Requires authentication. Anonymous users are redirected to the
        ``auth:login`` route.
    """

    login_url = reverse_lazy("auth:login")

    def get_cart_books(self):
        cart = self.request.session.get("cart", {})
        books = list(Book.objects.filter(pk__in=cart.keys()).select_related("category"))

        for book in books:
            book.quantity = cart.get(str(book.pk), cart.get(book.pk, 0))

        return cart, books

    def get(self, request):
        _, books = self.get_cart_books()

        return render(request, "cart.html", {"cart_obj": books, "form": CheckoutForm()})

    def render_checkout(self, request, books, form):
        return render(
            request,
            "cart.html",
            {"cart_obj": books, "form": form},
        )

    def clear_cart(self, request):
        request.session["cart"] = {}
        request.session.modified = True

    def prepare_warehouse(self, order):
        reserve_order(order)
        if order.payment_method == Order.PaymentMethod.CASH:
            confirm_order_reservation(order)

    def warehouse_checkout_failure(self, request, books, form, order, exc):
        logger.warning(
            "Warehouse rejected checkout for order %s: %s",
            order.public_id,
            exc,
        )
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        form.add_error(
            None,
            _(
                "The requested books are unavailable or the warehouse "
                "service cannot be reached. Please try again."
            ),
        )
        return self.render_checkout(request, books, form)

    def create_stripe_session(self, request, order, line_items):
        return stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            success_url=request.build_absolute_uri(
                reverse("book:payment_success")
            )
            + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri(reverse("book:payment_cancel")),
            metadata={"order_id": str(order.public_id)},
        )

    def stripe_checkout_failure(self, request, books, form, order):
        logger.exception(
            "Stripe session creation failed for order %s",
            order.public_id,
        )
        try:
            cancel_order_reservation(order, "PAYMENT_FAILED")
        except (WarehouseRejected, WarehouseUnavailable):
            logger.exception(
                "Could not release reservation for order %s",
                order.public_id,
            )
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        form.add_error(
            None,
            _("Payment provider is unavailable. Please try again."),
        )
        return self.render_checkout(request, books, form)

    def post(self, request):
        _, books = self.get_cart_books()

        checkout_form = CheckoutForm(request.POST)
        if not checkout_form.is_valid():
            return self.render_checkout(request, books, checkout_form)
        if not books:
            checkout_form.add_error(None, _("Your cart is empty."))
            return self.render_checkout(request, books, checkout_form)

        creation = create_checkout_order(checkout_form, request.user, books)
        order = creation.order
        try:
            self.prepare_warehouse(order)
        except (WarehouseRejected, WarehouseUnavailable) as exc:
            return self.warehouse_checkout_failure(
                request, books, checkout_form, order, exc
            )

        if order.payment_method == Order.PaymentMethod.CASH:
            self.clear_cart(request)
            return redirect("index")

        try:
            checkout_session = self.create_stripe_session(
                request,
                order,
                creation.stripe_line_items,
            )
        except stripe.StripeError:
            return self.stripe_checkout_failure(
                request, books, checkout_form, order
            )

        order.payment_id = checkout_session.id
        order.save(update_fields=["payment_id", "updated_at"])
        self.clear_cart(request)
        return redirect(checkout_session.url, code=303)


def payment_success(request):
    """Return from Stripe without trusting the browser as payment proof."""
    return redirect("index")


def payment_cancel(request):
    """Return from Stripe without changing the order's payment state."""
    return redirect("index")


def _expire_stripe_order(order):
    if order.status in {Order.Status.PAID, Order.Status.CANCELLED}:
        return HttpResponse(status=200), None
    try:
        cancel_order_reservation(order, "PAYMENT_FAILED")
    except WarehouseUnavailable:
        return HttpResponse(status=503), None
    except WarehouseRejected:
        return HttpResponse(status=409), None

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.status == Order.Status.NEW:
            order.status = Order.Status.CANCELLED
            order.save(update_fields=["status", "updated_at"])
    return HttpResponse(status=200), None


def _confirm_paid_stripe_order(order, session_id):
    if order.status == Order.Status.PAID:
        return HttpResponse(status=200), None
    if order.status == Order.Status.CANCELLED:
        return HttpResponse(status=409), None

    try:
        confirm_order_reservation(order)
    except WarehouseUnavailable:
        return HttpResponse(status=503), None
    except WarehouseRejected:
        return HttpResponse(status=409), None

    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .select_related("user")
            .get(pk=order.pk)
        )
        if order.status == Order.Status.PAID:
            return HttpResponse(status=200), None
        if order.status != Order.Status.NEW:
            return HttpResponse(status=409), None
        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.payment_id = session_id
        order.save(update_fields=["status", "paid_at", "payment_id", "updated_at"])
        email_data = (
            order.user.username if order.user else "customer",
            order.user.email if order.user else "",
            order.id,
            order.total_price,
        )
        return None, email_data


def _apply_stripe_order_event(event_type, session, order_id):
    """Apply one validated Stripe event and return response or email data."""
    try:
        order = (
            Order.objects.select_related("user")
            .filter(public_id=order_id)
            .first()
        )
    except (ValidationError, TypeError, ValueError):
        logger.warning("Stripe webhook contains invalid order_id=%s", order_id)
        return HttpResponse(status=400), None

    if order is None:
        logger.warning("Stripe webhook references unknown order %s", order_id)
        return HttpResponse(status=404), None

    session_id = session.get("id", "")
    if order.payment_id and order.payment_id != session_id:
        logger.error(
            "Stripe session mismatch for order %s: expected %s, received %s",
            order.public_id,
            order.payment_id,
            session_id,
        )
        return HttpResponse(status=409), None

    if event_type == "checkout.session.expired":
        return _expire_stripe_order(order)
    if session.get("payment_status") != "paid":
        return HttpResponse(status=200), None
    return _confirm_paid_stripe_order(order, session_id)


def _send_payment_confirmation(email_data, order_id):
    username, email, local_order_id, total_price = email_data
    if not email:
        return

    try:
        send_async_email.delay(
            subject=f"Заказ №{local_order_id} успешно оплачен!",
            message=(
                f"Спасибо за покупку, {username}!\n"
                f"Сумма оплаты: {total_price} евро."
            ),
            recipient_list=[email],
        )
    except Exception:
        logger.exception("Could not enqueue confirmation email for order %s", order_id)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Process signed Stripe Checkout events idempotently."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET is not configured")
        return HttpResponse(status=503)

    try:
        event = stripe.Webhook.construct_event(
            request.body,
            request.META.get("HTTP_STRIPE_SIGNATURE", ""),
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.SignatureVerificationError):
        logger.warning("Rejected Stripe webhook with an invalid payload or signature")
        return HttpResponse(status=400)

    event_type = event.get("type")
    if event_type not in STRIPE_ORDER_EVENTS:
        return HttpResponse(status=200)

    session = event["data"]["object"]
    metadata = session.get("metadata") or {}
    order_id = metadata.get("order_id")
    if not order_id:
        logger.warning("Stripe Checkout session %s has no order_id", session.get("id"))
        return HttpResponse(status=400)

    response, email_data = _apply_stripe_order_event(event_type, session, order_id)
    if response is not None:
        return response

    _send_payment_confirmation(email_data, order_id)

    return HttpResponse(status=200)
