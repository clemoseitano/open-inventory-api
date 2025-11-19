#!/bin/sh

if [ "$SERVICE_TYPE" = "web" ]; then
   # Run Django migrations
    python manage.py migrate

    # Collect static files
    python manage.py collectstatic --noinput

    exec daphne service.asgi:application --port 8000 --bind 0.0.0.0 -v 1
elif [ "$SERVICE_TYPE" = "celery-worker" ]; then
    exec celery -A service worker -l INFO
elif [ "$SERVICE_TYPE" = "celery-beat" ]; then
    exec celery -A service beat -l INFO  --scheduler django_celery_beat.schedulers:DatabaseScheduler --max-interval=5
else
    echo "No service specified"
    exit 1
fi
