#!/bin/bash

# Start the Flask application with Gunicorn
echo "Starting Flask application with Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app