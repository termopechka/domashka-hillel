import pytest
from datetime import timedelta
from django.utils import timezone
from accounts.models import User
from books.models import Book, Category


@pytest.mark.django_db
def test_user_string_representation(user_factory):
    user = user_factory(email='bruce_joe@example.com')
    assert str(user) == 'bruce_joe@example.com'


@pytest.mark.django_db
def test_category_string_representation(category_factory):
    category = category_factory(name='Drama')
    assert str(category) == 'Drama'


@pytest.mark.django_db
def test_book_string_representation(book_factory):
    book = book_factory(title='1984', author='George Orwell')
    assert str(book) == '1984 by George Orwell'


@pytest.mark.django_db
def test_user_meta_ordering_by_data_joined(user_factory):
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)

    user_new = user_factory(date_joined=now)
    user_medium = user_factory(date_joined=yesterday)
    user_oldest = user_factory(date_joined=two_days_ago)

    users_queryset = User.objects.all()

    assert list(users_queryset) == [user_new, user_medium, user_oldest]


@pytest.mark.django_db
def test_book_meta_ordering_by_id(book_factory):
    book_1 = book_factory()
    book_2 = book_factory()
    book_3 = book_factory()

    books_queryset = Book.objects.all()

    assert list(books_queryset) == [book_1, book_2, book_3]
    assert books_queryset[0].id < books_queryset[1].id < books_queryset[2].id


@pytest.mark.django_db
def test_book_category_relationship_foreign_key(category_factory, book_factory):
    category = category_factory(name='Sci-Fi')
    book1 = book_factory(title='1984', category=category)
    book2 = book_factory(title='Linux from Scratch', category=category)

    assert book1.category == category
    assert book1.category.name == 'Sci-Fi'

    category_books = category.books.all()

    assert category_books.count() == 2
    assert book1 in category_books
    assert book2 in category_books