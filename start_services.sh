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

# Return success
exit 0