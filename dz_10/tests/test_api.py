import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from orders.models import Order

User = get_user_model()


@pytest.mark.django_db
def test_get_users_list_authenticated_user(api_auth_client):
    url = reverse("api:accounts:user-list")
    response = api_auth_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_get_users_list_unauthenticated_user(api_client):
    url = reverse("api:accounts:user-list")
    response = api_client.get(url)
    assert response.status_code == 401
    assert response.data["detail"] == "Authentication credentials were not provided."


@pytest.mark.django_db
def test_create_user_with_jwt_token(api_auth_client):
    url = reverse("api:accounts:user-list")
    data = {
        "username": "user1",
        "email": "example@example.com",
        "password": "password1",
        "native_name": "",
        "phone_number": "",
    }

    response = api_auth_client.post(url, data, format="json")

    assert response.status_code == 201
    assert response.data["username"] == "user1"
    assert response.data["email"] == "example@example.com"
    assert "password" not in response.data

    assert User.objects.filter(email="example@example.com").exists()


@pytest.mark.django_db
def test_create_user_unauthorized(api_client):
    url = reverse("api:accounts:user-list")
    data = {
        "username": "user1",
        "email": "example@example.com",
        "password": "password1",
        "native_name": "",
        "phone_number": "",
    }

    response = api_client.post(url, data, format="json")

    assert response.status_code == 401


@pytest.mark.django_db
def test_update_user_authenticated_user(api_auth_client, user_factory):
    user = user_factory(username="user1")
    api_auth_client.force_authenticate(user)
    url = reverse("api:accounts:user-detail", kwargs={"pk": user.id})
    data = {
        "username": "user1",
        "email": "example@example.com",
        "native_name": "",
        "phone_number": "",
    }

    response = api_auth_client.put(url, data, format="json")

    assert response.status_code == 200
    assert response.data["username"] == "user1"
    assert response.data["email"] == "example@example.com"


@pytest.mark.django_db
def test_patch_user_authenticated_user(api_auth_client, user_factory):
    user = user_factory(username="user1")
    api_auth_client.force_authenticate(user)
    url = reverse("api:accounts:user-detail", kwargs={"pk": user.id})
    data = {
        "email": "example@example.com",
    }

    response = api_auth_client.patch(url, data, format="json")

    assert response.status_code == 200
    assert response.data["email"] == "example@example.com"
    assert response.data["username"] == "user1"


@pytest.mark.django_db
def test_update_user_put_missing_fields(api_auth_client, user_factory):
    user = user_factory(username="user1")
    api_auth_client.force_authenticate(user)
    url = reverse("api:accounts:user-detail", kwargs={"pk": user.id})
    data = {
        "email": "example@example.com",
    }

    response = api_auth_client.put(url, data, format="json")

    assert response.status_code == 400
    assert "username" in response.data


@pytest.mark.django_db
def test_update_other_user_profile_forbidden(api_auth_client, user_factory):
    other_user = user_factory(username="other_user1")
    url = reverse("api:accounts:user-detail", kwargs={"pk": other_user.id})
    data = {"username": "user1"}

    response = api_auth_client.patch(url, data, format="json")

    assert response.status_code == 403


@pytest.mark.django_db
def test_delete_user_authenticated_user(api_auth_client, user_factory):
    user = user_factory(username="user1")
    api_auth_client.force_authenticate(user)
    url = reverse("api:accounts:user-detail", kwargs={"pk": user.id})

    response = api_auth_client.delete(url, format="json")

    assert response.status_code == 204


@pytest.mark.django_db
def test_delete_user_unauthenticated_user(api_client):
    url = reverse("api:accounts:user-detail", kwargs={"pk": 99999})
    response = api_client.delete(url, format="json")
    assert response.status_code == 401


@pytest.mark.django_db
def test_delete_not_existing_user_authenticated_user(api_auth_client, user_factory):
    user = user_factory(username="user1")
    api_auth_client.force_authenticate(user)
    url = reverse("api:accounts:user-detail", kwargs={"pk": 99999})

    response = api_auth_client.delete(url, format="json")

    assert response.status_code == 404


@pytest.mark.django_db
def test_cart_api_add_list_remove_and_clear(api_auth_client, book_factory):
    book = book_factory()

    add_url = reverse("api:catalog:cart-add", kwargs={"pk": book.pk})
    response = api_auth_client.post(add_url, format="json")

    assert response.status_code == 200
    assert response.data["cart"][str(book.pk)] == 1

    list_url = reverse("api:catalog:cart-list")
    response = api_auth_client.get(list_url)

    assert response.status_code == 200
    assert response.data["cart"][str(book.pk)] == 1

    remove_url = reverse("api:catalog:cart-remove", kwargs={"pk": book.pk})
    response = api_auth_client.post(remove_url, format="json")

    assert response.status_code == 200
    assert str(book.pk) not in response.data["cart"]

    clear_url = reverse("api:catalog:cart-clear")
    response = api_auth_client.post(clear_url, format="json")

    assert response.status_code == 200
    assert response.data["cart"] == {}


@pytest.mark.django_db
def test_get_orders_list_authenticated_user(api_auth_client, order_factory):
    order_factory(user=api_auth_client.user)

    url = reverse("api:orders:orders-list")
    response = api_auth_client.get(url)

    assert response.status_code == 200


@pytest.mark.django_db
def test_get_orders_list_unauthenticated_user(api_client):
    url = reverse("api:orders:orders-list")
    response = api_client.get(url)

    assert response.status_code == 401


@pytest.mark.django_db
def test_create_order_authenticated_user(api_auth_client):
    url = reverse("api:orders:orders-list")
    data = {
        "user": api_auth_client.user.id,
        "shipping_address": "123 Main St",
        "city": "Kyiv",
        "postal_code": "01001",
        "country": "Ukraine",
        "payment_method": Order.PaymentMethod.CARD,
        "total_price": "99.99",
        "status": Order.Status.NEW,
    }

    response = api_auth_client.post(url, data, format="json")

    assert response.status_code == 201
    assert response.data["city"] == "Kyiv"
    assert response.data["payment_method"] == Order.PaymentMethod.CARD
