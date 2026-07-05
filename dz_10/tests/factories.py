import factory
from factory import fuzzy
from django.contrib.auth import get_user_model
from books.models import Book, Category
from orders.models import Order

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

    user_id = factory.SubFactory(UserFactory)
    total_price = factory.fuzzy.FuzzyDecimal(10.00, 500.00)
    status = 'pending'
    payment_id = factory.Sequence(lambda n: f"ch_{n}xyz")
