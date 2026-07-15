import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from pytest_factoryboy import register
from django.test import Client, AsyncClient
from .factories import UserFactory, BookFactory, OrderFactory, CategoryFactory, OrderItemFactory

register(UserFactory)
register(BookFactory)
register(OrderFactory)
register(CategoryFactory)
register(OrderItemFactory)


@pytest.fixture()
def api_client():
    return APIClient()


@pytest.fixture()
def api_auth_client(api_client, user_factory):
    test_user = user_factory()

    refresh = RefreshToken.for_user(test_user)

    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    api_client.user = test_user
    return api_client


@pytest.fixture()
def web_client():
    return Client()


@pytest.fixture()
async def async_web_client():
    return AsyncClient()


@pytest.fixture()
def auth_client(web_client, user_factory):
    user = user_factory()
    web_client.force_login(user)
    return web_client, user
