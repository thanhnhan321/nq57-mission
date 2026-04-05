#!/bin/bash

set -e
# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || true

# Run the application with uvicorn
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 300 --graceful-timeout 300 & python manage.py run_huey
wait

