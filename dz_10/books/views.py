from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView, CreateView
from silk.profiling.profiler import silk_profile

from orders.models import OrderItem
from .forms import CheckoutForm
from .models import Book
import logging

logger = logging.getLogger(__name__)

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


def add_to_cart(request, pk):
    cart = request.session.get('cart', {})
    cart[pk] = cart.get(pk, 0) + 1
    request.session['cart'] = cart
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
    def get(self, request):
        cart = self.request.session.get('cart', {})
        book_ids = [key for key in cart.keys()]
        books = Book.objects.filter(pk__in=book_ids)
        for itm in books:
            itm.quantity = cart[str(itm.pk)]
        return render(request,'cart.html', {'cart_obj': books, 'form': CheckoutForm()})

    def post(self, request):
        cart = self.request.session.get('cart', {})
        book_ids = [key for key in cart.keys()]
        books = Book.objects.filter(pk__in=book_ids)

        user_order_details = CheckoutForm(request.POST)

        if user_order_details.is_valid():
            user_order_details = user_order_details.save(commit=False)
            user_order_details.user = request.user
            user_order_details.save()

            for cart_key in cart.keys():
                order_item = OrderItem()
                order_item.book = Book.objects.get(pk=int(cart_key))
                order_item.order = user_order_details
                order_item.quantity = cart[cart_key]
                order_item.save()

            request.session['cart'] = {}
            request.session.modified = True

            return redirect('index')

        return render(request,'cart.html', {'cart_obj': books, 'form': CheckoutForm()})


