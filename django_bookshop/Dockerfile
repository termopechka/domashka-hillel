FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

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

RUN SECRET_KEY=static-build-only \
    ALLOWED_HOSTS=localhost \
    SECURE_SSL_REDIRECT=False \
    python manage.py collectstatic --noinput \
    --settings=BookShop.settings.production

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--config", "gunicorn.conf.py", "BookShop.wsgi:application"]
