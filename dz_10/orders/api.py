from django.urls import path, include
from rest_framework.routers import DefaultRouter

from orders.views import OrderViewSet

app_name = "orders"

router = DefaultRouter()
router.register("", OrderViewSet, basename="orders")

urlpatterns = [
    path("", include(router.urls)),
]
