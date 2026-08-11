"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from .views import health_check

urlpatterns = [
    # User & Auth endpoints
    path("api/v1/auth/", include("users.urls")),
    # Book endpoints
    path("api/v1/", include("books.urls")),
    # Inventory endpoints
    path("api/v1/", include("inventory.urls")),
    # Reservation endpoints
    path("api/v1/", include("reservations.urls")),
    # Health endpoint
    path("actuator/health", health_check, name="health-check"),
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", RedirectView.as_view(url="/en/admin/", permanent=False)),
    path(
        "api/docs/",
        RedirectView.as_view(url="/en/api/docs/", permanent=False),
    ),
    path(
        "api/schema/",
        RedirectView.as_view(url="/en/api/schema/", permanent=False),
    ),
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(), name="swagger-ui"),
    path("api/docs/redoc/", SpectacularRedocView.as_view(), name="redoc"),
)

admin.site.site_header = _("Warehouse administration")
admin.site.site_title = _("Warehouse admin")
admin.site.index_title = _("Inventory management")
