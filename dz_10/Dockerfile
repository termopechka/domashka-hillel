FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
RUN apt-get update && apt-get install -y gettext libpq-dev gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/staticfiles /app/media /var/run/celery \
    && chown -R appuser:appuser /app /var/run/celery
COPY --chown=appuser:appuser . /app/
COPY --chown=appuser:appuser entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
USER appuser
ENTRYPOINT ["/entrypoint.sh"]
