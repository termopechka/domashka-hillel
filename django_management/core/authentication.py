import secrets
from dataclasses import dataclass

from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


@dataclass(frozen=True)
class ServicePrincipal:
    username: str = "bookshop-service"
    is_authenticated: bool = True
    is_anonymous: bool = False

    def get_username(self):
        return self.username


class ServiceAPIKeyAuthentication(BaseAuthentication):
    header_name = "X-Service-API-Key"

    def authenticate(self, request):
        supplied_key = request.headers.get(self.header_name)
        if supplied_key is None:
            return None

        expected_key = settings.WAREHOUSE_SERVICE_API_KEY
        if not expected_key or not secrets.compare_digest(
            supplied_key,
            expected_key,
        ):
            raise AuthenticationFailed("Invalid service API key.")
        return ServicePrincipal(), "service-api-key"

    def authenticate_header(self, request):
        return self.header_name


class ServiceAPIKeyScheme(OpenApiAuthenticationExtension):
    target_class = ServiceAPIKeyAuthentication
    name = "serviceApiKey"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": ServiceAPIKeyAuthentication.header_name,
        }
