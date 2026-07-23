#!/bin/bash

if [ "$SERVICE" = "web" ]; then
    ./wait-for-it.sh db:5432 -- echo "DB is ready"
    
    echo "Starting Stripe CLI to listen for webhooks..."
    stripe listen --api-key $STRIPE_SECRET_KEY --forward-to https://orr-backend-105825824472.asia-southeast2.run.app/stripe-webhook/ &

    echo "Starting Django development server..."
    exec poetry run python manage.py runserver 0.0.0.0:8000
else
    exec "$@"
fi
