import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import Client
from django.urls import reverse


def test_health_check(web_client):
    response = web_client.get(reverse("health-check"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_register_page_links_to_login(web_client):
    response = web_client.get(reverse("auth:register"))

    assert response.status_code == 200
    assert f'href="{reverse("auth:login")}"' in response.content.decode()


@pytest.mark.django_db
def test_book_list_view_status_code(web_client):
    url = reverse("book:list")
    response = web_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_book_list_without_page_parameter_uses_first_page(web_client, book_factory):
    cache.clear()
    expected_book = book_factory(title="First page book")

    response = web_client.get(reverse("book:list"))

    assert response.status_code == 200
    assert response.context["page_obj"].number == 1
    assert expected_book in response.context["page_obj"].object_list
    assert expected_book.title in response.content.decode()


@pytest.mark.django_db
def test_navbar_changes_after_login(web_client, user_factory):
    cache.clear()
    index_url = reverse("index")
    user = user_factory(username="navbar-user")

    anonymous_response = web_client.get(index_url)
    assert "Sign In" in anonymous_response.content.decode()
    assert "Sign Up" in anonymous_response.content.decode()

    web_client.force_login(user)
    authenticated_content = web_client.get(index_url).content.decode()

    assert user.username in authenticated_content
    assert "Log Out" in authenticated_content
    assert "Sign In" not in authenticated_content
    assert "Sign Up" not in authenticated_content


@pytest.mark.django_db
def test_language_form_has_valid_csrf_token_after_anonymous_request():
    cache.clear()
    book_list_url = reverse("book:list")

    Client().get(book_list_url)
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.get(book_list_url)

    csrf_token = csrf_client.cookies["csrftoken"].value
    response = csrf_client.post(
        reverse("set_language"),
        {"language": "uk", "next": book_list_url, "csrfmiddlewaretoken": csrf_token},
    )

    assert response.status_code == 302


@pytest.mark.django_db
def test_add_book_link_is_consistent_on_cart_and_book_list(auth_client):
    client, user = auth_client
    user.user_permissions.add(Permission.objects.get(codename="add_book"))

    cart_content = client.get(reverse("book:cart_view")).content.decode()
    book_list_content = client.get(reverse("book:list")).content.decode()

    assert "Add Book" in cart_content
    assert "Add Book" in book_list_content


@pytest.mark.django_db
def test_order_list_view_permissions(auth_client):
    client, user = auth_client

    url = reverse("order:list")
    response = client.post(url)

    assert response.status_code == 403


@pytest.mark.django_db
def test_add_book_view_permissions(auth_client):
    client, user = auth_client

    url = reverse("book:add")
    data = {"title": "New Book", "author": "Author"}
    response = client.post(url, data=data)

    assert response.status_code == 403


@pytest.mark.django_db
def test_book_details_view(web_client, book_factory):
    book = book_factory(title="1984", author="George Orwell")

    url = reverse("book:detail", kwargs={"pk": book.pk})
    response = web_client.get(url)

    assert response.status_code == 200

    assert response.context["book"] == book
    assert "book" in response.context

    assert book.title in response.content.decode("utf-8")


@pytest.mark.django_db
def test_add_to_cart_view(web_client, book_factory):
    book = book_factory()

    url = reverse("book:add_to_cart", kwargs={"pk": book.pk})

    response = web_client.get(url)

    assert response.status_code == 302
    assert response.url == reverse("index")

    session = web_client.session

    assert "cart" in session
    assert session["cart"][str(book.pk)] == 1
