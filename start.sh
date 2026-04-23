#!/bin/bash
# RAG_for_AI startup script

cd /opt/RAG_for_AI
source .venv/bin/activate

# Collect static files
python manage.py collectstatic --noinput 2>/dev/null || true

# Start Gunicorn
echo "Starting Gunicorn on 0.0.0.0:8000..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile /var/log/tkos/access.log \
    --error-logfile /var/log/tkos/error.log
