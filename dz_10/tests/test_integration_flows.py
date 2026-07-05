import pytest
from django.urls import reverse
from unittest.mock import MagicMock
from orders.models import Order


@pytest.mark.django_db
def test_web_checkout_flow_success(auth_client, mocker):
    client, user = auth_client
    test_stripe_url = "https://stripe.com"

    mock_stripe = mocker.patch("stripe.checkout.Session.create")

    mock_session_instance = MagicMock()
    mock_session_instance.id = "cs_test_12345"
    mock_session_instance.url = test_stripe_url
    mock_session_instance.payment_status = "unpaid"
    mock_session_instance.client_secret = "pi_123_secret_456"
    mock_stripe.return_value = mock_session_instance

    mock_send_mail = mocker.patch("django.core.mail.send_mail")

    form_data = {
        "shipping_address": "ул. Крещатик, 1",
        "city": "Киев",
        "postal_code": "01001",
        "country": "Украина",
        "payment_method": "card",
    }

    url = reverse("book:cart_view")
    response = client.post(url, data=form_data)

    assert response.status_code == 302
    assert response.url == test_stripe_url

    assert Order.objects.filter(user=user, city="Киев").exists()

    mock_stripe.assert_called_once()
    # mock_send_mail.assert_called_once()