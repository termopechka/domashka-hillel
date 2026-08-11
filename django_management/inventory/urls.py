from rest_framework.routers import DefaultRouter

from .views import (
    InventoryViewSet,
    StockMovementViewSet,
    StockReturnViewSet,
)

router = DefaultRouter()
router.register(r"inventory", InventoryViewSet, basename="inventory")
router.register(r"returns", StockReturnViewSet, basename="returns")
router.register(
    r"stock-movements",
    StockMovementViewSet,
    basename="stock-movements",
)

urlpatterns = router.urls
