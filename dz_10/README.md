# BookShop

BookShop is a Django-based bookstore project with user registration, a book
catalog, session cart, order checkout, Stripe payment redirect flow, and
administrative/order views.

## Tech Stack

- Python 3.12
- Django 6.0
- PostgreSQL 15 for Docker/runtime configuration
- Redis for Django cache/session storage in Docker/runtime configuration
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
   STRIPE_PUBLIC_KEY=your-stripe-public-key
   STRIPE_SECRET_KEY=your-stripe-secret-key
   ```

## Running

### Docker

Start PostgreSQL, Redis, and the Django ASGI app:

```bash
docker compose up --build
```

The app is exposed on:

```text
http://localhost:8000/
```

### Local Tests

The default settings module reads PostgreSQL and Redis values from environment
variables. For local tests without Docker, use the test settings module:

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
