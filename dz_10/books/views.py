import asyncio
import os
from asgiref.sync import sync_to_async
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
from silk.profiling.profiler import silk_profile
from orders.models import OrderItem, Order
from .forms import CheckoutForm
from .models import Book
import logging
import stripe

logger = logging.getLogger(__name__)
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")


class BooksListView(ListView):
    model = Book
    context_object_name = 'books'
    template_name = 'books/books.html'
    paginate_by = 8

    @silk_profile(name='Book List View')
    def get(self, request, *args, **kwargs):
        logger.info(f'User {request.user.username} requested a list of books.')

        response = super().get(request, *args, **kwargs)

        return response

    def get_queryset(self):
        result = super(BooksListView, self).get_queryset()
        query = self.request.GET.get('search')
        if query:
            result = Book.objects.filter(Q(title__icontains=query) | Q(description__icontains=query))
        return result

    def get_context_data(self, **kwargs):
        context = super(BooksListView, self).get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context


class BookDetailView(DetailView):
    model = Book
    context_object_name = 'book'
    template_name = 'books/book.html'

    def get_context_data(self, **kwargs):
        context = super(BookDetailView, self).get_context_data(**kwargs)
        context['book'] = self.object
        return context


class AddBookView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Book
    permission_required = 'add_book'
    fields = ['title', 'author', 'price', 'description', 'stock', 'category']
    login_url = '/login/'
    raise_exception = True
    template_name = 'books/form_book.html'


async def add_to_cart(request, pk):
    pk_str = str(pk)
    cart = request.session.get('cart', {})
    cart[pk_str] = cart.get(pk_str, 0) + 1
    request.session['cart'] = cart
    request.session.modified = True
    await sync_to_async(request.session.save, thread_sensitive=True)()
    return redirect('index')

@require_POST
def remove_from_cart(request, pk):
    cart = request.session.get('cart', {})
    pk = str(pk)
    if pk in cart:
        del cart[pk]
        request.session['cart'] = cart
        request.session.modified = True

    return redirect('index')


def clear_cart(request):
    cart = request.session.get('cart', {})
    cart.clear()
    request.session['cart'] = cart
    return redirect('index')


class CheckoutView(LoginRequiredMixin, View):
    login_url = reverse_lazy('accounts:login')

    def get_cart_books(self):
        cart = self.request.session.get('cart', {})
        books = list(Book.objects.filter(pk__in=cart.keys()))

        for book in books:
            book.quantity = cart.get(str(book.pk), cart.get(book.pk, 0))

        return cart, books

    def get(self, request):
        _, books = self.get_cart_books()

        return render(request,'cart.html', {'cart_obj': books, 'form': CheckoutForm()})

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

                line_items = []
                for book in books:
                    order_item = OrderItem()
                    order_item.book = book
                    order_item.book_name = book.title
                    order_item.order = user_order_details
                    order_item.price = book.price or 0
                    order_item.quantity = book.quantity
                    order_item.save()

                    line_items.append({
                        'price_data': {
                            'currency': 'eur',
                            'product_data': {
                                'name': book.title,
                            },
                            'unit_amount': int((book.price or 0) * 100),
                        },
                        'quantity': book.quantity,
                    })

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

        return render(request,'cart.html', {'cart_obj': books, 'form': user_order_details})


async def payment_success(request):
    order_id = request.GET.get('order_id')

    if order_id:
        order = await Order.objects.aget(id=order_id)

        if not getattr(order, 'is_paid', False):
            order.is_paid = True
            await order.asave()

            user = await request.auser()

            subject = f'Заказ №{order.id} успешно оплачен!'
            message = f'Спасибо за покупку, {request.user.username}!\nСумма оплаты: {order.total_price} евро.'
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
    return redirect('index')