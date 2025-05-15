#!/bin/bash

# Start Redis server in the background
echo "Starting Redis server..."
redis-server --daemonize yes --protected-mode no

# Wait for Redis to start
sleep 1

# Check if Redis is running
if redis-cli ping > /dev/null 2>&1; then
  echo "Redis server started successfully"
else
  echo "Failed to start Redis server"
fi

# Start the Flask application with Gunicorn
echo "Starting Flask application with Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app