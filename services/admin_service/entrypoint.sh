#!/usr/bin/env sh
set -eu

echo "Applying admin-service migrations..."

python manage.py migrate \
    --database=default \
    --noinput

echo "Collecting admin-service static files..."

python manage.py collectstatic \
    --noinput

echo "Starting admin-service..."

exec gunicorn admin_panel.wsgi:application \
    --bind "${ADMIN_SERVICE_HOST:-0.0.0.0}:${ADMIN_SERVICE_PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-1}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile -