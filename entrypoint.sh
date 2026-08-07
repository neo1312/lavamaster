#!/bin/sh

set -e
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done
echo "PostgreSQL is ready."

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn lavamaster.wsgi:application \
    --bind 0.0.0.0:8006 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
