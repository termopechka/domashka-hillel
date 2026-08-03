# BookShop

BookShop is a Django-based bookstore project with user registration, a book
catalog, session cart, order checkout, Stripe payment redirect flow, and
administrative/order views.

## Tech Stack

- Python 3.12
- Django 6.0
- PostgreSQL 15 for Docker/runtime configuration
- Redis for Django cache/session storage in Docker/runtime configuration
- Celery and Celery Beat with Redis broker/result backend
- Gunicorn behind NGINX, with NGINX serving static and media files
- Optional Sentry error and performance monitoring
- pytest, pytest-django, pytest-cov, coverage.py
- factory_boy for test data

## Installation

1. Create and activate a virtual environment:

   ```bash
   python -m venv ../.venv
   source ../.venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root. The Docker setup expects:

   ```env
   SECRET_KEY=your-secret-key
   DB_NAME=django_db
   DB_USER=django_user
   DB_PASSWORD=your-password
   DB_HOST=db
   DB_PORT=5432
   DJANGO_REDIS_NAME=0
   REDIS_PASSWORD=your-redis-password
   REDIS_PORT=6379
   ALLOWED_HOSTS=localhost,127.0.0.1
   SENTRY_DSN=
   SENTRY_ENVIRONMENT=production
   SENTRY_TRACES_SAMPLE_RATE=0.1
   STRIPE_PUBLIC_KEY=your-stripe-public-key
   STRIPE_SECRET_KEY=your-stripe-secret-key
   ```

## Running

### Docker

Start PostgreSQL, Redis, Gunicorn, both Celery services, and NGINX:

```bash
docker compose up --build
```

NGINX exposes the app on:

```text
http://localhost/
```

Redis databases are separated by responsibility: broker `0`, application and
template cache `1`, sessions `2`, view cache `3`, and Celery results `4`.
Celery Beat generates a nightly CSV catalog report under `media/reports/` and
runs Django's expired-session cleanup daily.

### Render with GitHub Actions and GHCR

The repository-root `render.yaml` deploys the prebuilt
`ghcr.io/termopechka/domashka-hillel:main` image with the following production
services:

- Gunicorn web service with WhiteNoise static-file serving and `/health/`
  health checks.
- Celery worker with a persistent `/app/media` disk for generated CSV reports.
- Celery Beat scheduler.
- Render Postgres 15 and a private Render Key Value instance.

The Blueprint uses paid production plans: three Starter services, a Starter
Key Value instance, and a Basic Postgres instance. Adjust the `plan` fields in
`render.yaml` before applying the Blueprint if a different cost/reliability
tradeoff is required.

The existing `.github/workflows/django.yml` pipeline runs linting and tests for
pull requests. After a successful push to `main`, it builds one `linux/amd64`
image, publishes `main`, `latest`, and an immutable commit-SHA tag to GHCR, and
sends the exact image digest to the deploy hooks for all three Render services.

#### First deployment

1. Push the repository to GitHub. The first successful workflow run publishes
   the GHCR image; deployment remains disabled until the repository variable
   described below is set.
2. In Render, open **Workspace Settings > Container Registry Credentials** and
   add a GitHub credential named `github-container-registry`. Use GitHub user
   `termopechka` and a classic personal access token with `read:packages`.
   Alternatively, make the GHCR package public and remove each `creds` block
   from `render.yaml`.
3. In Render, create a Blueprint and select the repository-root `render.yaml`.
   Supply the prompted Stripe, SMTP, and optional Sentry values. Render
   generates `SECRET_KEY` and injects internal `DATABASE_URL` and `REDIS_URL`
   values automatically.
4. Copy the deploy hook from the **Settings** page of each Render service into
   these GitHub Actions secrets:

   - `RENDER_WEB_DEPLOY_HOOK_URL`
   - `RENDER_CELERY_DEPLOY_HOOK_URL`
   - `RENDER_BEAT_DEPLOY_HOOK_URL`

5. Create the GitHub Actions repository variable
   `RENDER_DEPLOY_ENABLED=true`. Optionally protect deployments by configuring
   required reviewers on the GitHub `production` environment used by the job.
6. Run **BookShop CI and deploy** manually from the Actions tab, or push another
   change to `main`. The workflow publishes the image and triggers Render.
   Database migrations run as the web service's pre-deploy command; static
   assets are already collected in the image.
7. Create an administrator from the Render web service shell:

```bash
python manage.py createsuperuser
```

For later deployments, merge or push to `main`. A pull request only runs the
test job and never publishes or deploys. Render image-backed services do not
watch GHCR for updated tags, so the deploy hooks are required. Keep old
commit-SHA images in GHCR if you want Render rollbacks to remain available.

If these Render services were already created with `runtime: docker`, recreate
them as image-backed services before applying this version of the Blueprint;
Render service runtimes cannot be changed in place.

Render filesystems are ephemeral unless a disk is attached. The report disk is
attached only to the Celery worker because Render does not support sharing one
disk between services. Use object storage if reports later need to be served
by the web application.

Keep real credentials only in the ignored local `.env`, GitHub Actions secrets,
and the Render Dashboard. Do not upload `.env` to GitHub Actions or bake it into
the image. Use `.env.example` as the local template, and rotate any credential
that has ever been pasted into chat, logs, source control, or another shared
location.

### Local Tests

Settings are split by environment:

- `BookShop.settings.base` contains shared application, database, cache, and
  Celery configuration.
- `BookShop.settings.development` is the default for `manage.py` and enables
  developer middleware and permissive local CORS.
- `BookShop.settings.production` is used by Docker, Gunicorn, ASGI, and Celery;
  it requires `SECRET_KEY` and `ALLOWED_HOSTS`.
- `BookShop.test_settings` uses SQLite and local-memory caches for tests.

For local tests without Docker, run:

```bash
pytest --ds=BookShop.test_settings -o addopts=''
```

Model coverage report for the documented model-test task:

```bash
coverage run -m pytest tests/test_models.py tests/test_generated_model_coverage.py --ds=BookShop.test_settings -o addopts=''
coverage report --include=accounts/models.py,books/models.py,orders/models.py -m --format=markdown
```

## Endpoints

DRF API endpoints live under `/api/` and are not wrapped in language prefixes.
Server-rendered Django pages are wrapped in `i18n_patterns`, so the active
language prefix is part of the path, for example `/en/book/`.

| Method | Endpoint | Name | Description | Access |
| --- | --- | --- | --- | --- |
| GET, POST | `/api/accounts/` | `api:accounts:user-list` | User API list/create | JWT authenticated |
| GET, PUT, PATCH, DELETE | `/api/accounts/<pk>/` | `api:accounts:user-detail` | User API detail/update/delete | JWT authenticated owner |
| GET, POST | `/api/books/` | `api:catalog:books-list` | Book API list/create; optional `search` query param | Public |
| GET, PUT, PATCH, DELETE | `/api/books/<pk>/` | `api:catalog:books-detail` | Book API detail/update/delete | Public |
| GET, POST | `/api/categories/` | `api:catalog:categories-list` | Category API list/create | Public |
| GET, PUT, PATCH, DELETE | `/api/categories/<pk>/` | `api:catalog:categories-detail` | Category API detail/update/delete | Public |
| POST | `/api/token/` | `api:token_obtain_pair` | Obtain JWT access/refresh token pair | Public |
| GET | `/en/` | `index` | Home page | Public |
| GET | `/en/book/` | `book:list` | Paginated book catalog; optional `search` query param | Public |
| GET | `/en/book/<pk>/` | `book:detail` | Book detail page | Public |
| GET, POST | `/en/book/add/` | `book:add` | Create a book | Authenticated user with `books.add_book` |
| GET | `/en/book/<pk>/to_cart` | `book:add_to_cart` | Add one book unit to the session cart | Public |
| POST | `/en/book/cart/<pk>/remove_from_cart` | `book:remove_from_cart` | Remove a book from the session cart | Public |
| GET | `/en/book/cart/clear` | `book:clear_cart` | Clear the session cart | Public |
| GET, POST | `/en/book/cart/` | `book:cart_view` | Show cart and submit checkout data | Authenticated |
| GET | `/en/book/payment/success` | `book:payment_success` | Stripe success redirect; accepts `order_id` and `session_id` query params | Public callback |
| GET | `/en/book/payment/cancel` | `book:payment_cancel` | Stripe cancel redirect | Public callback |
| GET, POST | `/en/auth/register/` | `auth:register` | Register a new user | Public |
| GET, POST | `/en/auth/login/` | `auth:login` | Login view | Public |
| POST | `/en/auth/logout/` | `auth:logout` | Logout view | Authenticated |
| GET | `/en/orders/` | `order:list` | Paginated order list; optional `search` query param | Authenticated user with `orders.view_order` |
| GET | `/en/admin/` | `admin:index` | Django admin | Staff/superuser |
| GET | `/__debug__/` | debug toolbar | Debug toolbar routes when `DEBUG=True` | Development only |
| GET | `/silk/` | silk | Silk profiling routes when `DEBUG=True` | Development only |

## Test Coverage

The model-focused coverage report is saved in `coverage_report.txt`.

Current selected model coverage:

| Name | Stmts | Miss | Cover |
| --- | ---: | ---: | ---: |
| `accounts/models.py` | 13 | 0 | 100% |
| `books/models.py` | 24 | 0 | 100% |
| `orders/models.py` | 40 | 0 | 100% |

## AI Usage

- Code review: prompt asked Codex to review the project code and write findings
  to `AI_REVIEW.md`. Tool: Codex. Manual review after AI output included
  checking the affected views and preserving unrelated user changes.
- Test generation and coverage: prompt asked Codex to identify weakly covered
  Django models, generate model unit tests, run tests, enforce at least 60%
  coverage for selected model modules, and save a coverage report. Tool: Codex.
  Manual changes after AI output included adjusting the expected localized book
  URL, adding `BookShop.test_settings` for local SQLite/cache tests, fixing
  factories to match the current `Order` model, and changing `add_to_cart` from
  async to sync because the existing sync view test hung against the async
  session save.
- Docstrings and README: prompt asked Codex to document every local Django view
  with Google/reStructuredText-style docstrings and update README sections for
  installation, running, endpoints, and AI usage. Tool: Codex. Manual review
  after AI output included checking URL patterns, permissions, form fields, and
  ensuring only docstrings were added to views for this documentation step.
