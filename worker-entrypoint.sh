#!/bin/bash

# Cloud Run requires every service to listen to a web port (usually 8080).
# Since Celery is a background worker and doesn't have a web server, 
# Cloud Run thinks the deployment "failed" because it didn't detect a website.

# To fix this, we start a tiny, fake Python web server in the background 
# just to keep Google Cloud Run happy and pass the health check!
echo "Starting dummy web server on port $PORT to satisfy Cloud Run health checks..."
python -m http.server $PORT &

# Now we start the actual Celery worker in the foreground so it stays alive
echo "Starting Celery worker..."
celery -A core worker -l info
