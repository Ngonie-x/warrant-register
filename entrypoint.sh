#!/bin/sh
set -e

# Wait-for DB is optional if you rely on compose healthchecks; still useful outside compose
python manage.py migrate --noinput
python manage.py collectstatic --noinput || true

exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60
