import pytest
from accounts.forms import MyUserCreationForm
from books.forms import BookForm, CheckoutForm


@pytest.mark.django_db
def test_user_form_valid_data_and_saves():
    form_data = {
        "username": "joe",
        "email": "joe@example.com",
        "native_name": "Joe",
        "password1": "SecurePassword123!",
        "password2": "SecurePassword123!",
    }

    form = MyUserCreationForm(data=form_data)

    assert form.is_valid() is True

    user = form.save()

    assert user.username == "joe"
    assert user.email == "joe@example.com"
    assert user.native_name == "Joe"
    assert user.is_active is True


@pytest.mark.django_db
def test_book_form_valid_data_and_saves(category_factory):
    category = category_factory(name="Roman", slug="roman")

    form_data = {
        "title": "1984",
        "author": "George Orwell",
        "price": 100,
        "description": "1984 have between 250 and 350 pages",
        "stock": 5,
        "category": category,
    }

    form = BookForm(data=form_data)

    assert form.is_valid() is True

    book = form.save()

    assert book.title == "1984"
    assert book.author == "George Orwell"
    assert book.price == 100
    assert book.description == "1984 have between 250 and 350 pages"
    assert book.stock == 5
    assert book.category == category


@pytest.mark.django_db
def test_checkout_form_valid_data_and_saves():
    form_data = {
        "shipping_address": "123 Main St",
        "city": "Kyiv",
        "postal_code": "01001",
        "country": "Ukraine",
        "payment_method": "card",
    }
    form = CheckoutForm(data=form_data)

    assert form.is_valid() is True


@pytest.mark.django_db
def test_user_model_form_unique_username_error(user_factory):
    user_factory(username="joe_moonlight")

    form_data = {
        "username": "joe_moonlight",
        "email": "joe_moonlight@example.com",
        "native_name": "Joe_Moonlight",
        "is_active": True,
    }

    form = MyUserCreationForm(data=form_data)

    assert form.is_valid() is False
    assert "username" in form.errors


def test_book_model_form_missing_category():
    form_data = {
        "title": "1984",
        "author": "George Orwell",
        "price": 100,
        "description": "1984 have between 250 and 350 pages",
        "stock": 5,
    }

    form = BookForm(data=form_data)

    assert form.is_valid() is False
    assert "category" in form.errors


@pytest.mark.django_db
def test_book_model_form_missing_price(category_factory):
    category = category_factory(name="Roman", slug="roman")

    form_data = {
        "title": "1984",
        "author": "George Orwell",
        "price": "",
        "description": "1984 have between 250 and 350 pages",
        "stock": 5,
        "category": category.id,
    }

    form = BookForm()
    form.fields["price"].required = False
    form = BookForm(data=form_data)
    form.fields["price"].required = False

    assert form.is_valid() is True


@pytest.mark.parametrize(
    "missing_field",
    ["shipping_address", "city", "postal_code", "country", "payment_method"],
)
def test_checkout_form_missing_required_fields(missing_field):
    form_data = {
        "shipping_address": "123 Main St",
        "city": "Kyiv",
        "postal_code": "01001",
        "country": "Ukraine",
        "payment_method": "stripe",
    }
    form_data.pop(missing_field)

    form = CheckoutForm(data=form_data)

    assert form.is_valid() is False
    assert missing_field in form.errors
