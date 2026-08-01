#!/bin/sh
set -e

if [ "${RUN_DJANGO_SETUP:-0}" = "1" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
fi

exec "$@"
