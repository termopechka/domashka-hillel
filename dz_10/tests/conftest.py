import pytest
from pytest_factoryboy import register
from django.test import Client, AsyncClient
from .factories import UserFactory, BookFactory, OrderFactory, CategoryFactory, OrderItemFactory

register(UserFactory)
register(BookFactory)
register(OrderFactory)
register(CategoryFactory)
register(OrderItemFactory)


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
