FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=core.settings_production

RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R appuser:appuser /app

COPY --chown=appuser:appuser . /app/
COPY --chown=appuser:appuser entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER appuser

RUN DJANGO_SECRET_KEY=static-build-only-not-used-at-runtime \
    DJANGO_ALLOWED_HOSTS=localhost \
    WAREHOUSE_SERVICE_API_KEY=static-build-only \
    DATABASE_URL=sqlite:////tmp/warehouse-static-build.sqlite3 \
    REDIS_URL=redis://127.0.0.1:6379 \
    SECURE_SSL_REDIRECT=False \
    python manage.py collectstatic --noinput \
    --settings=core.settings_production

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--config", "gunicorn.conf.py", "core.wsgi:application"]
