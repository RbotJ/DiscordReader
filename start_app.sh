#!/bin/bash

# Kill any existing Redis server processes
pkill -f redis-server || true

# Start Redis server in the foreground in a background process
echo "Starting Redis server..."
redis-server --protected-mode no > /tmp/redis.log 2>&1 &
REDIS_PID=$!

# Wait for Redis to start
echo "Waiting for Redis to start..."
for i in {1..10}; do
  if redis-cli ping > /dev/null 2>&1; then
    echo "Redis server started successfully (PID: $REDIS_PID)"
    break
  fi
  if [ $i -eq 10 ]; then
    echo "Failed to start Redis server after 10 attempts"
    cat /tmp/redis.log
  fi
  sleep 1
done

# Start the Flask application with Gunicorn
echo "Starting Flask application with Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app