---
name: bookshop-django-api-routing
description: Project-specific Django/DRF routing workflow for the dz_10 BookShop app. Use when changing BookShop.urls, app-level api.py files, DRF ViewSets, serializers, or API tests for accounts, books, cart, categories, and orders endpoints.
---

# BookShop Django API Routing

## Core Rules

- Keep DRF API routes outside `i18n_patterns`; mount them under `/api/` in `BookShop/urls.py`.
- Keep classic Django views inside `i18n_patterns`; preserve names used by templates and tests: `book:*`, `auth:*`, `order:*`, and `index`.
- Prefer one `DefaultRouter` per app-level `api.py` unless there is a clear reason to split routers.
- Avoid duplicated path segments. If the project URLConf mounts `path('orders/', include('orders.api'))`, the app router should register `''`, not `'orders'`.
- Set `app_name` in each `api.py` to the namespace used by `BookShop/urls.py`.
- Always set router `basename` explicitly when stable reverse names matter.

## Current API Shape

- `api:accounts:user-list` -> `/api/accounts/`
- `api:accounts:user-detail` -> `/api/accounts/<pk>/`
- `api:catalog:books-list` -> `/api/books/`
- `api:catalog:categories-list` -> `/api/categories/`
- `api:catalog:cart-list` -> `/api/cart/`
- `api:catalog:cart-add` -> `/api/cart/<pk>/add/`
- `api:catalog:cart-remove` -> `/api/cart/<pk>/remove/`
- `api:catalog:cart-clear` -> `/api/cart/clear/`
- `api:orders:orders-list` -> `/api/orders/`
- `api:orders:orders-detail` -> `/api/orders/<pk>/`
- `api:token_obtain_pair` -> `/api/token/`

## Implementation Checklist

1. Inspect `BookShop/urls.py`, the relevant app `api.py`, `views.py`, `serializer.py`, and `tests/test_api.py`.
2. Mount new app APIs in `api_urlpatterns`, not in `web_urlpatterns`.
3. Keep app routers simple:
   - `accounts/api.py`: `router.register('', UserViewSet, basename='user')`
   - `books/api.py`: register `books`, `categories`, and `cart`
   - `orders/api.py`: `router.register('', OrderViewSet, basename='orders')`
4. When adding a `ModelViewSet`, confirm its serializer includes all required model fields for create/update.
5. In `get_queryset()`, use `self.queryset` or `Model.objects`, not `super().queryset`.
6. Add or update reverse-based tests in `tests/test_api.py`; do not hard-code API paths unless testing exact public URLs.
7. Use authenticated API clients for multi-request API tests when anonymous throttling could affect the result.

## Validation

Run validation in Docker because the project is Docker-first:

```bash
docker compose exec web python manage.py show_urls
docker compose exec web pytest -q
```

Expected Compose warnings about unset `qu6`/`gc` variables and obsolete `version` are not routing failures.
