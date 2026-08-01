---
name: bookshop-django-platform
description: Project-specific workflow for the dz_10 Django BookShop application. Use when changing its Django/DRF routes, authentication templates, Redis caches and invalidation signals, Celery tasks or Beat schedules, Gunicorn/NGINX/Sentry deployment, Docker Compose services, or related tests.
---

# BookShop Django Platform

## Start Here

1. Work from `dz_10/`; treat the project as Docker-first.
2. Inspect the relevant settings, view, template, signal/task, Compose, and test files before editing.
3. Preserve user changes in the dirty worktree and avoid generated `staticfiles`, coverage, and Beat artifacts.
4. Keep request-specific HTML correct before optimizing it with caches.

## Routing

- Keep DRF routes outside `i18n_patterns` under `/api/`.
- Keep classic Django routes inside `i18n_patterns`; preserve `book:*`, `auth:*`, `order:*`, and `index` names.
- Use one `DefaultRouter` per app-level `api.py`, explicit stable `basename` values, and no duplicated mount segments.
- Preserve these public API names:
  - `api:accounts:user-list` and `user-detail`
  - `api:catalog:books-list`, `categories-list`, and `cart-*`
  - `api:orders:orders-list` and `orders-detail`
  - `api:token_obtain_pair`
- Use reverse-based tests. Use authenticated API clients for multi-request tests that could hit anonymous throttling.

## Redis Caching

Keep Redis databases isolated by responsibility:

- DB 0: Celery broker
- DB 1 / `default`: low-level and template-fragment cache
- DB 2 / `sessions`: Django sessions
- DB 3 / `views`: complete response cache
- DB 4: Celery results

Follow these rules:

- Do not full-page-cache HTML containing authentication, permissions, sessions, or CSRF forms.
- Use `cache_page(..., cache="views")` only for safe shared responses such as the public books API list.
- Never cache the session-backed cart response globally.
- Centralize book cache keys and timeouts in `books/cache.py`; do not recreate string keys in views or signals.
- Cache book details at low level with `books:detail:<pk>`.
- Vary translated fragments by `LANGUAGE_CODE`; vary book fragments by both `book.pk` and language.
- Keep the footer and welcome fragments language-specific.

## Cache Invalidation

- Register signals from `BooksConfig.ready()`.
- Handle `Book` save/delete and `Category` save/delete.
- Schedule invalidation with `transaction.on_commit()` so rolled-back writes do not evict valid data.
- On a book change, delete its low-level key, every localized detail-fragment key, and clear the dedicated `views` cache.
- On a category change, clear catalog view responses.
- Add regression tests proving that two book detail pages cannot share fragment HTML and that API list caches refresh after model changes.

## Authentication and Templates

- Rely on `django.contrib.auth.context_processors.auth` for `user` and `perms`.
- Use real permission strings: `perms.books.add_book` and `perms.orders.view_order`.
- Keep language and logout forms as POST forms with `{% csrf_token %}`.
- Preserve `search` while building every pagination link; Django `ListView` already defaults a missing `page` query parameter to page 1.

## Celery and Beat

- Load the Celery app from `BookShop/__init__.py` and autodiscover tasks.
- Keep these task names stable:
  - `books.tasks.send_async_email`
  - `books.tasks.generate_books_report`
  - `books.tasks.clear_expired_sessions`
- Send payment confirmation email with `.delay()`.
- Write CSV reports under `MEDIA_ROOT/reports`; mount the media volume into both `web` and `celery`.
- Schedule the report at 02:00 UTC and expired-session cleanup at 03:00 UTC.
- Keep the Beat schedule in a non-root writable path such as `/tmp/celerybeat-schedule`.
- Run workers with bounded concurrency and confirm the three tasks appear in worker startup logs.

## Deployment

- Run Django with Gunicorn WSGI on port 8000; do not use `runserver` or Uvicorn in Compose.
- Expose the application publicly only through NGINX on port 80.
- Let NGINX proxy application requests and serve `/static/` and `/media/` from shared read-only volumes.
- Forward `Host`, `X-Real-IP`, `X-Forwarded-For`, and `X-Forwarded-Proto`.
- Run `web`, `celery`, and `celery-beat` as the non-root `appuser`.
- Run migrations and `collectstatic` only when `RUN_DJANGO_SETUP=1` (the web service), not on every worker startup.
- Keep Compose service names `web`, `celery`, `celery-beat`, and `nginx`.
- Preserve dollar signs in `.env` secrets by single-quoting values that contain `$`.

## Sentry

- Initialize Sentry only when `SENTRY_DSN` is non-empty.
- Include both `DjangoIntegration` and `CeleryIntegration`.
- Configure environment and trace sampling through `SENTRY_ENVIRONMENT` and `SENTRY_TRACES_SAMPLE_RATE`.
- Never print or commit DSNs, secret keys, database passwords, Redis passwords, or Stripe keys.

## Tests

- Put cache/task regressions in `tests/test_cache_and_tasks.py`.
- Give `BookShop/test_settings.py` separate local-memory aliases for `default`, `sessions`, and `views`.
- Use transactional database tests when asserting callbacks registered with `transaction.on_commit()`.
- Mock email and management-command boundaries; write report tests to `tmp_path`.

## Validation

Run checks in this order:

```bash
docker compose config --services
docker compose exec web python manage.py check
docker compose exec web python manage.py show_urls
docker compose exec web pytest -q
docker compose exec nginx nginx -t
docker compose ps
```

For runtime changes, also verify:

- Gunicorn, Celery, and Beat run as `appuser`.
- Worker logs show Redis broker DB 0, result DB 4, and all three tasks.
- A real `generate_books_report.delay()` job succeeds and creates a shared media CSV.
- NGINX returns HTTP 200 for `/en/` and `/static/css/bootstrap.css`; static responses include long-lived cache headers.
