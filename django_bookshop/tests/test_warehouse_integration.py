import logging

import pytest
import requests
from django.test import override_settings
from django.urls import reverse

from BookShop.integrations.warehouse import (
    WarehouseClient,
    WarehouseRejected,
    WarehouseUnavailable,
)
from orders.models import Order
from orders.warehouse import reserve_order


WAREHOUSE_SETTINGS = override_settings(
    WAREHOUSE_INTEGRATION_ENABLED=True,
    WAREHOUSE_SERVICE_API_KEY="test-service-key",
)


@pytest.mark.django_db
@WAREHOUSE_SETTINGS
def test_reserve_order_sends_external_ids_and_stores_reservation(
    order_factory,
    order_item_factory,
    mocker,
):
    order = order_factory()
    item = order_item_factory(order=order, quantity=2)
    client = mocker.patch("orders.warehouse.get_warehouse_client").return_value
    client.create_reservation.return_value = {
        "reservation_id": "91e3fa3d-26d1-457d-97bf-ce276a6e45cb",
        "status": "PENDING",
    }

    reserve_order(order)

    client.create_reservation.assert_called_once_with(
        order_id=order.public_id,
        items=[
            {
                "book_id": str(item.book.public_id),
                "quantity": 2,
            }
        ],
    )
    order.refresh_from_db()
    assert str(order.warehouse_reservation_id) == (
        "91e3fa3d-26d1-457d-97bf-ce276a6e45cb"
    )
    assert order.warehouse_status == "PENDING"


@pytest.mark.django_db
@WAREHOUSE_SETTINGS
def test_checkout_reserves_before_stripe(auth_client, book_factory, mocker):
    client, _ = auth_client
    book = book_factory()
    session = client.session
    session["cart"] = {str(book.pk): 1}
    session.save()

    manager = mocker.Mock()
    reserve = mocker.patch("books.views.reserve_order")
    stripe_create = mocker.patch(
        "books.views.stripe.checkout.Session.create"
    )
    manager.attach_mock(reserve, "reserve")
    manager.attach_mock(stripe_create, "stripe")
    stripe_create.return_value.id = "cs_test_warehouse"
    stripe_create.return_value.url = "https://stripe.test/checkout"

    response = client.post(
        reverse("book:cart_view"),
        {
            "shipping_address": "1 Test Street",
            "city": "Kyiv",
            "postal_code": "01001",
            "country": "Ukraine",
            "payment_method": Order.PaymentMethod.CARD,
        },
    )

    assert response.status_code == 302
    reserve.assert_called_once()
    stripe_create.assert_called_once()
    assert [call[0] for call in manager.mock_calls[:2]] == ["reserve", "stripe"]


@pytest.mark.django_db
@WAREHOUSE_SETTINGS
def test_checkout_stops_when_warehouse_rejects_stock(
    auth_client,
    book_factory,
    mocker,
):
    client, user = auth_client
    book = book_factory()
    session = client.session
    session["cart"] = {str(book.pk): 3}
    session.save()
    mocker.patch(
        "books.views.reserve_order",
        side_effect=WarehouseRejected(
            409,
            {"message": "Not enough stock"},
        ),
    )
    stripe_create = mocker.patch("books.views.stripe.checkout.Session.create")

    response = client.post(
        reverse("book:cart_view"),
        {
            "shipping_address": "1 Test Street",
            "city": "Kyiv",
            "postal_code": "01001",
            "country": "Ukraine",
            "payment_method": Order.PaymentMethod.CARD,
        },
    )

    assert response.status_code == 200
    assert Order.objects.get(user=user).status == Order.Status.CANCELLED
    stripe_create.assert_not_called()
    assert client.session["cart"] == {str(book.pk): 3}


@pytest.mark.django_db
@WAREHOUSE_SETTINGS
@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
def test_paid_webhook_confirms_warehouse_reservation(
    web_client,
    order_factory,
    mocker,
):
    order = order_factory(
        status=Order.Status.NEW,
        payment_id="cs_test_paid",
        warehouse_reservation_id="91e3fa3d-26d1-457d-97bf-ce276a6e45cb",
    )
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": order.payment_id,
                "payment_status": "paid",
                "metadata": {"order_id": str(order.public_id)},
            }
        },
    }
    mocker.patch("books.views.stripe.Webhook.construct_event", return_value=event)
    confirm = mocker.patch("books.views.confirm_order_reservation")
    mocker.patch("books.views.send_async_email.delay")

    response = web_client.post(
        reverse("stripe-webhook"),
        data=b"{}",
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="valid",
    )

    assert response.status_code == 200
    confirm.assert_called_once()
    order.refresh_from_db()
    assert order.status == Order.Status.PAID


@pytest.mark.django_db
@WAREHOUSE_SETTINGS
@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
def test_paid_webhook_is_retried_when_warehouse_is_unavailable(
    web_client,
    order_factory,
    mocker,
):
    order = order_factory(status=Order.Status.NEW, payment_id="cs_test_retry")
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": order.payment_id,
                "payment_status": "paid",
                "metadata": {"order_id": str(order.public_id)},
            }
        },
    }
    mocker.patch("books.views.stripe.Webhook.construct_event", return_value=event)
    mocker.patch(
        "books.views.confirm_order_reservation",
        side_effect=WarehouseUnavailable("offline"),
    )

    response = web_client.post(
        reverse("stripe-webhook"),
        data=b"{}",
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="valid",
    )

    assert response.status_code == 503
    order.refresh_from_db()
    assert order.status == Order.Status.NEW


def test_warehouse_client_propagates_request_id_and_logs_success(
    mocker,
    caplog,
):
    session = mocker.Mock()
    response = mocker.Mock(
        status_code=201,
        content=b'{"reservation_id": "reservation-1"}',
        headers={"X-Request-ID": "warehouse-request-id"},
    )
    response.json.return_value = {"reservation_id": "reservation-1"}
    session.request.return_value = response
    client = WarehouseClient(
        base_url="http://warehouse.test/api/v1",
        api_key="test-key",
        timeout=(1, 2),
        session=session,
    )

    with caplog.at_level(logging.INFO, logger="BookShop.integrations.warehouse"):
        result = client.create_reservation(order_id="order-1", items=[])

    assert result == {"reservation_id": "reservation-1"}
    headers = session.request.call_args.kwargs["headers"]
    assert headers["X-Service-API-Key"] == "test-key"
    assert headers["Idempotency-Key"] == "order-1-reserve"
    assert headers["X-Request-ID"]
    assert "warehouse.request completed" in caplog.text


def test_warehouse_client_exposes_business_rejection_context(mocker):
    session = mocker.Mock()
    response = mocker.Mock(
        status_code=409,
        content=b'{"code": "INSUFFICIENT_STOCK"}',
        headers={"X-Request-ID": "request-409"},
    )
    response.json.return_value = {
        "code": "INSUFFICIENT_STOCK",
        "message": "Not enough stock",
        "details": [{"available_quantity": 1}],
    }
    session.request.return_value = response
    client = WarehouseClient(
        base_url="http://warehouse.test/api/v1",
        api_key="test-key",
        session=session,
    )

    with pytest.raises(WarehouseRejected) as error:
        client.create_reservation(order_id="order-1", items=[])

    assert error.value.status_code == 409
    assert error.value.request_id == "request-409"
    assert error.value.payload["code"] == "INSUFFICIENT_STOCK"


def test_warehouse_client_converts_network_error_to_unavailable(mocker):
    session = mocker.Mock()
    session.request.side_effect = requests.ConnectionError("offline")
    client = WarehouseClient(
        base_url="http://warehouse.test/api/v1",
        api_key="test-key",
        session=session,
    )

    with pytest.raises(WarehouseUnavailable) as error:
        client.sync_book({"external_id": "book-1"})

    assert error.value.request_id
    assert "temporarily unavailable" in str(error.value)
