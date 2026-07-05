import pytest
from django.urls import reverse

from books import translation


@pytest.mark.django_db
def test_book_list_view_status_code(web_client):
    url = reverse('book:list')
    response = web_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_order_list_view_permissions(auth_client):
    client, user = auth_client

    url = reverse('order:list')
    response = client.post(url)

    assert response.status_code == 403


@pytest.mark.django_db
def test_add_book_view_permissions(auth_client):
    client, user = auth_client

    url = reverse('book:add')
    data = {'title': 'New Book', 'author': 'Author'}
    response = client.post(url, data=data)

    assert response.status_code == 403


@pytest.mark.django_db
def test_book_details_view(web_client, book_factory):
    book = book_factory(title='1984', author='George Orwell')

    url = reverse('book:detail', kwargs={'pk': book.pk})
    response = web_client.get(url)

    assert response.status_code == 200

    assert response.context['book'] == book
    assert 'book' in response.context

    assert book.title in response.content.decode('utf-8')


@pytest.mark.django_db
def test_add_to_cart_view(web_client, book_factory):
    book = book_factory()

    url = reverse('book:add_to_cart', kwargs={'pk': book.pk})

    response = web_client.get(url)

    assert response.status_code == 302
    assert response.url == reverse('index')

    session = web_client.session

    assert 'cart' in session
    assert session['cart'][str(book.pk)] == 1


