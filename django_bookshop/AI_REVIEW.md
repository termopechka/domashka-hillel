## Файл: books/views.py

### Оригінальний код
```python
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
```

### AI рекомендації
- Додати `select_related('category')` у списку/деталі книг і під час читання кошика: `Book.category` є `ForeignKey`, тому при відображенні категорії шаблоном або майбутнім кодом не буде N+1 запитів.
- Не скидати queryset пошуку на `Book.objects.filter(...)`: треба фільтрувати вже підготовлений `result`, інакше втрачаються оптимізації базового queryset.
- При створенні замовлення замінити `OrderItem().save()` у циклі на `bulk_create()`: це зменшує кількість INSERT-запитів з N до 1 для позицій замовлення.
- В `payment_success` обробити неіснуючий або некоректний `order_id`: поточний код може повернути 500 на callback з битим параметром.
- У `AddBookView.permission_required` використовувати повний codename `books.add_book`; без app label перевірка дозволів працює некоректно.
- Не міняти `add_to_cart` на POST-only у цій задачі: шаблон і наявний тест використовують GET, тому така зміна зламала б поточну поведінку.
- Зовнішній виклик Stripe всередині `transaction.atomic()` бажано винести окремо в майбутньому, але це змінить rollback-поведінку при помилці Stripe, тому без тестів зараз не застосовано.

### Фінальний код (після застосування)
```python
import asyncio
import logging
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
    model = Book
    context_object_name = 'book'
    template_name = 'books/book.html'
    queryset = Book.objects.select_related('category')


class AddBookView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Book
    permission_required = 'books.add_book'
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
    return redirect('index')
```

### Що змінено і чому
- Додано `select_related('category')` для `BooksListView`, `BookDetailView` і книг у кошику, щоб зменшити ризик N+1 при доступі до категорії.
- Пошук книг тепер фільтрує базовий queryset, а не створює новий через `Book.objects`.
- Видалено дублювання `book` у `BookDetailView.get_context_data()`: `context_object_name = 'book'` вже робить те саме.
- `permission_required` виправлено на `books.add_book`, щоб `PermissionRequiredMixin` перевіряв реальний дозвіл Django.
- Позиції замовлення створюються через `OrderItem.objects.bulk_create(order_items)`, що зменшує кількість SQL INSERT.
- У `payment_success` додана обробка некоректного `order_id`, щоб callback не падав 500.
- `request.user.username` в async view замінено на вже отриманого `user.username`.
- Дрібно покращено читабельність: сучасний `super()`, lazy logging, форматування `render()` і параметрів Stripe.

## Файл: orders/views.py

### Оригінальний код
```python
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from orders.models import Order


class OrderListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Order
    template_name = 'orders.html'
    context_object_name = 'orders'
    permission_required = 'orders.view_order'
    login_url = '/login/'
    paginate_by = 20
    raise_exception = True

    def get_queryset(self):
        result = super(OrderListView, self).get_queryset()
        query = self.request.GET.get('search')
        if query:
            result = result.filter(Q(user__icontains=query) | Q(status__icontains=query))
        return result

    def get_context_data(self, **kwargs):
        context = super(OrderListView, self).get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context
```

### AI рекомендації
- Додати `select_related('user')`: шаблон виводить `{{ order.user }}`, тому без цього можливий N+1 по користувачах на сторінці списку.
- Виправити `Q(user__icontains=query)`: `user` є `ForeignKey`, тому такий lookup некоректний. Потрібно шукати по конкретних полях користувача, наприклад `user__username` і `user__email`.
- Використати `super()` без аргументів для кращої читабельності в Python 3.
- У майбутньому варто додати тест на `?search=...`, бо саме ця гілка містила дефект.

### Фінальний код (після застосування)
```python
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from orders.models import Order


class OrderListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Order
    template_name = 'orders.html'
    context_object_name = 'orders'
    permission_required = 'orders.view_order'
    login_url = '/login/'
    paginate_by = 20
    raise_exception = True

    def get_queryset(self):
        result = super().get_queryset().select_related('user')
        query = self.request.GET.get('search')
        if query:
            result = result.filter(
                Q(user__username__icontains=query)
                | Q(user__email__icontains=query)
                | Q(status__icontains=query)
            )
        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context
```

### Що змінено і чому
- Queryset замовлень тепер використовує `select_related('user')`, щоб список не робив окремий запит для кожного користувача.
- Пошук по користувачу виправлений на `user__username__icontains` і `user__email__icontains`; старий `user__icontains` для `ForeignKey` некоректний.
- Оновлено виклики `super()` для чистішого коду без зміни поведінки.

## Файл: accounts/views.py

### Оригінальний код
```python
import logging
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views import generic
from silk.profiling.profiler import silk_profile

from .forms import MyUserCreationForm
from .models import User

logger = logging.getLogger(__name__)

class RegisterView(generic.CreateView):
    form_class = MyUserCreationForm
    template_name = 'register.html'
    success_url = reverse_lazy('accounts:login')

    @silk_profile(name='Register account')
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logger.info('user %s is already logged in', request.user.username)

        response = super().get(request, *args, **kwargs)

        return response
```

### AI рекомендації
- Видалити невикористані `UserCreationForm` і `User`: вони збільшують шум і можуть вводити в оману, бо view реально працює з `MyUserCreationForm`.
- Повернути `super().get(...)` напряму: локальна змінна `response` не додає логіки.
- Можна перенаправляти вже авторизованого користувача з реєстрації, але це змінює поведінку UI; без явної вимоги і тестів це не застосовано.
- Файл не є DRF view/serializer; DRF-specific рекомендацій тут немає.

### Фінальний код (після застосування)
```python
import logging
from django.urls import reverse_lazy
from django.views import generic
from silk.profiling.profiler import silk_profile

from .forms import MyUserCreationForm

logger = logging.getLogger(__name__)


class RegisterView(generic.CreateView):
    form_class = MyUserCreationForm
    template_name = 'register.html'
    success_url = reverse_lazy('accounts:login')

    @silk_profile(name='Register account')
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logger.info('user %s is already logged in', request.user.username)

        return super().get(request, *args, **kwargs)
```

### Що змінено і чому
- Прибрано невикористані імпорти `UserCreationForm` і `User`.
- Прибрано зайву змінну `response`; метод тепер одразу повертає результат `super().get(...)`.
- Додано порожній рядок перед класом за PEP 8.

