#!/bin/bash

# Stop any running Redis instances
pkill -f redis-server || true

# Start Redis server with configuration suitable for Replit
redis-server --daemonize yes --protected-mode no --maxmemory 100mb --maxmemory-policy allkeys-lru

# Wait for Redis to start up
for i in {1..10}; do
    if redis-cli ping > /dev/null 2>&1; then
        echo "Redis server started successfully"
        exit 0
    fi
    sleep 0.5
done

echo "Failed to start Redis server"
exit 1