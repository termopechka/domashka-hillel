from django.db import connection
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    database = serializers.CharField()


@extend_schema(
    summary=_("Service health check"),
    responses={
        200: HealthSerializer,
        503: HealthSerializer,
    }
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return Response(
            {"status": "DOWN", "database": "DOWN"},
            status=503,
        )
    return Response({"status": "UP", "database": "UP"})
