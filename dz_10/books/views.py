import asyncio
import logging
import os
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView, CreateView
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from silk.profiling.profiler import silk_profile
from orders.models import OrderItem, Order
from .forms import CheckoutForm
from .models import Book, Category
import stripe
from .serializer import BookSerializer, CategorySerializer

logger = logging.getLogger(__name__)
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")


class BooksViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    pagination_class = LimitOffsetPagination

    @silk_profile(name='Book List View')
    def list(self, request, *args, **kwargs):
        logger.info('User %s requested a list of books.', request.user.get_username())
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        result = self.queryset.select_related('category')
        query = self.request.GET.get('search')
        if query:
            result = result.filter(Q(title__icontains=query) | Q(description__icontains=query))
        return result

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['search_query'] = self.request.GET.get('search', '')
        return context


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = LimitOffsetPagination


class CartViewSet(viewsets.ViewSet):
    def list(self, request):
        cart = request.session.get('cart', {})
        return Response({'cart': cart}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def add(self, request, pk=None):
        pk_str = str(pk)
        cart = request.session.get('cart', {})

        cart[pk_str] = cart.get(pk_str, 0) + 1
        request.session['cart'] = cart
        request.session.modified = True

        return Response({
            'message': f'Book {pk} added to cart.',
            'cart': cart
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def remove(self, request, pk=None):
        pk_str = str(pk)
        cart = request.session.get('cart', {})

        if pk_str in cart:
            del cart[pk_str]
            request.session['cart'] = cart
            request.session.modified = True
            return Response({
                'message': f'Book {pk} removed from cart.',
                'cart': cart
            }, status=status.HTTP_200_OK)

        return Response({'error': 'Book not found in cart.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def clear(self, request):
        cart = request.session.get('cart', {})
        cart.clear()
        request.session['cart'] = cart
        request.session.modified = True

        return Response({'message': 'Cart cleared.', 'cart': cart}, status=status.HTTP_200_OK)


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
    context_object_name = 'books'
    template_name = 'books/books.html'
    paginate_by = 8

    @silk_profile(name='Book List View')
    def get(self, request, *args, **kwargs):
        logger.info('User %s requested a list of books.', request.user.get_username())

        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        result = super().get_queryset().select_related('category')
        query = self.request.GET.get('search')
        if query:
            result = result.filter(Q(title__icontains=query) | Q(description__icontains=query))
        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
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
    context_object_name = 'book'
    template_name = 'books/book.html'
    queryset = Book.objects.select_related('category')


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
    permission_required = 'books.add_book'
    fields = ['title', 'author', 'price', 'description', 'stock', 'category']
    login_url = reverse_lazy('auth:login')
    raise_exception = True
    template_name = 'books/form_book.html'


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
    cart = request.session.get('cart', {})
    cart[pk_str] = cart.get(pk_str, 0) + 1
    request.session['cart'] = cart
    request.session.modified = True
    return redirect('index')


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

    cart = request.session.get('cart', {})
    pk = str(pk)
    if pk in cart:
        del cart[pk]
        request.session['cart'] = cart
        request.session.modified = True

    return redirect('index')


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

    cart = request.session.get('cart', {})
    cart.clear()
    request.session['cart'] = cart
    return redirect('index')


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

    login_url = reverse_lazy('auth:login')

    def get_cart_books(self):
        cart = self.request.session.get('cart', {})
        books = list(Book.objects.filter(pk__in=cart.keys()).select_related('category'))

        for book in books:
            book.quantity = cart.get(str(book.pk), cart.get(book.pk, 0))

        return cart, books

    def get(self, request):
        _, books = self.get_cart_books()

        return render(request, 'cart.html', {'cart_obj': books, 'form': CheckoutForm()})

    def post(self, request):
        cart, books = self.get_cart_books()

        user_order_details = CheckoutForm(request.POST)

        if user_order_details.is_valid():
            with transaction.atomic():
                user_order_details = user_order_details.save(commit=False)
                user_order_details.user = request.user
                user_order_details.total_price = sum(
                    (book.price or 0) * book.quantity for book in books
                )
                user_order_details.save()

                order_items = []
                line_items = []
                for book in books:
                    price = book.price or 0
                    order_items.append(OrderItem(
                        book=book,
                        book_name=book.title,
                        order=user_order_details,
                        price=price,
                        quantity=book.quantity,
                    ))

                    line_items.append({
                        'price_data': {
                            'currency': 'eur',
                            'product_data': {
                                'name': book.title,
                            },
                            'unit_amount': int(price * 100),
                        },
                        'quantity': book.quantity,
                    })

                OrderItem.objects.bulk_create(order_items)

                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=line_items,
                    mode='payment',
                    success_url=request.build_absolute_uri(reverse('book:payment_success')) + f"?session_id={{CHECKOUT_SESSION_ID}}&order_id={user_order_details.id}",
                    cancel_url=request.build_absolute_uri(reverse('book:payment_cancel')),
                    metadata={'order_id': user_order_details.id},
                )

                request.session['cart'] = {}
                request.session.modified = True

                return redirect(checkout_session.url, code=303)

        # return redirect('index')

        return render(request, 'cart.html', {'cart_obj': books, 'form': user_order_details})


async def payment_success(request):
    """Handle the Stripe success redirect for a completed payment.

    Handles:
        GET: Reads order metadata from the query string, marks the order as
        paid when possible, sends a confirmation email, and redirects home.

    Args:
        request: Django ``HttpRequest`` handled asynchronously.

    Query Parameters:
        order_id (int, optional): Order primary key to update.
        session_id (str, optional): Stripe checkout session identifier. The
            current implementation accepts it in the URL but does not read it.

    Path Parameters:
        None.

    Body:
        None.

    Returns:
        HttpResponseRedirect: Redirects to ``index`` with HTTP 302 after
        processing. Invalid or missing ``order_id`` also redirects to
        ``index``.

    Permissions:
        Public callback endpoint. It uses the current request user for the
        confirmation email when an order is updated.
    """

    order_id = request.GET.get('order_id')

    if order_id:
        try:
            order = await Order.objects.aget(id=order_id)
        except (Order.DoesNotExist, ValueError, TypeError):
            logger.warning('Payment success callback received invalid order_id=%s', order_id)
            return redirect('index')

        if not getattr(order, 'is_paid', False):
            order.is_paid = True
            await order.asave()

            user = await request.auser()

            subject = f'Заказ №{order.id} успешно оплачен!'
            message = f'Спасибо за покупку, {user.username}!\nСумма оплаты: {order.total_price} евро.'
            recipient_list = [user.email]

            await asyncio.to_thread(
                send_mail,
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                fail_silently=False,
            )

    return redirect('index')


async def payment_cancel(request):
    """Handle the Stripe cancellation redirect.

    Handles:
        GET: Redirects the user back to the home page.

    Args:
        request: Django ``HttpRequest`` handled asynchronously.

    Query Parameters:
        None.

    Path Parameters:
        None.

    Body:
        None.

    Returns:
        HttpResponseRedirect: Redirects to ``index`` with HTTP 302.

    Permissions:
        Public callback endpoint. Authentication is not required.
    """

    return redirect('index')
