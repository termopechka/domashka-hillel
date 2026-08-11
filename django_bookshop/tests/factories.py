import factory
from factory import fuzzy  # noqa: F401
from django.contrib.auth import get_user_model
from books.models import Book, Category
from orders.models import Order, OrderItem

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.Sequence(lambda n: f"user_{n}@example.com")
    is_active = True


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category_{n}")


class BookFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Book

    title = factory.Sequence(lambda n: f"Book Title {n}")
    author = factory.Sequence(lambda n: f"Author_{n}")
    price = factory.fuzzy.FuzzyDecimal(10.00, 500.00)
    stock = 5
    category = factory.SubFactory(CategoryFactory)


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    shipping_address = factory.Sequence(lambda n: f"{n} Test Street")
    city = "Kyiv"
    postal_code = "01001"
    country = "Ukraine"
    payment_method = Order.PaymentMethod.CARD
    total_price = factory.fuzzy.FuzzyDecimal(10.00, 500.00)
    status = Order.Status.NEW
    payment_id = factory.Sequence(lambda n: f"ch_{n}xyz")


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    book = factory.SubFactory(BookFactory)
    book_name = factory.Sequence(lambda n: f"Book Title {n}")
    price = factory.fuzzy.FuzzyDecimal(10.00, 100.00)
    quantity = 1
