import pytest
from django.test import override_settings
from django.urls import reverse

from orders.models import Order


def stripe_event(order, event_type="checkout.session.completed", payment_status="paid"):
    return {
        "type": event_type,
        "data": {
            "object": {
                "id": order.payment_id,
                "payment_status": payment_status,
                "metadata": {"order_id": str(order.public_id)},
            }
        },
    }


@pytest.mark.django_db
def test_cash_checkout_creates_order_without_stripe(auth_client, book_factory, mocker):
    client, user = auth_client
    book = book_factory()
    session = client.session
    session["cart"] = {str(book.pk): 1}
    session.save()
    create_stripe_session = mocker.patch("books.views.stripe.checkout.Session.create")

    response = client.post(
        reverse("book:cart_view"),
        {
            "shipping_address": "1 Test Street",
            "city": "Kyiv",
            "postal_code": "01001",
            "country": "Ukraine",
            "payment_method": Order.PaymentMethod.CASH,
        },
    )

    assert response.status_code == 302
    order = Order.objects.get(user=user)
    assert order.status == Order.Status.NEW
    assert order.payment_id == ""
    assert client.session["cart"] == {}
    create_stripe_session.assert_not_called()


@pytest.mark.django_db
@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
def test_stripe_webhook_marks_order_paid_idempotently(
    web_client, order_factory, mocker
):
    order = order_factory(status=Order.Status.NEW, payment_id="cs_test_paid")
    event = stripe_event(order)
    mocker.patch("books.views.stripe.Webhook.construct_event", return_value=event)
    send_email = mocker.patch("books.views.send_async_email.delay")

    url = reverse("stripe-webhook")
    response = web_client.post(
        url,
        data=b"{}",
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="valid-signature",
    )

    assert response.status_code == 200
    order.refresh_from_db()
    assert order.status == Order.Status.PAID
    assert order.paid_at is not None
    send_email.assert_called_once()

    second_response = web_client.post(
        url,
        data=b"{}",
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="valid-signature",
    )

    assert second_response.status_code == 200
    send_email.assert_called_once()


@pytest.mark.django_db
@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
def test_stripe_webhook_rejects_invalid_signature(web_client, mocker):
    mocker.patch(
        "books.views.stripe.Webhook.construct_event",
        side_effect=ValueError("invalid payload"),
    )

    response = web_client.post(
        reverse("stripe-webhook"),
        data=b"invalid",
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="invalid-signature",
    )

    assert response.status_code == 400


@pytest.mark.django_db
@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
def test_expired_stripe_session_cancels_new_order(web_client, order_factory, mocker):
    order = order_factory(status=Order.Status.NEW, payment_id="cs_test_expired")
    event = stripe_event(order, event_type="checkout.session.expired")
    mocker.patch("books.views.stripe.Webhook.construct_event", return_value=event)

    response = web_client.post(
        reverse("stripe-webhook"),
        data=b"{}",
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="valid-signature",
    )

    assert response.status_code == 200
    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED


@pytest.mark.django_db
def test_success_redirect_cannot_mark_order_paid(web_client, order_factory):
    order = order_factory(status=Order.Status.NEW)

    response = web_client.get(
        reverse("book:payment_success"),
        {"order_id": order.id, "session_id": order.payment_id},
    )

    assert response.status_code == 302
    order.refresh_from_db()
    assert order.status == Order.Status.NEW
    assert order.paid_at is None
