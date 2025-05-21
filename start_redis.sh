#!/bin/bash
# Start Redis server and make sure it's properly configured
# for the A+ Trading application

# Kill any existing Redis server
pkill -f redis-server || true

# Start Redis server with proper binding
redis-server --daemonize yes --bind 0.0.0.0 --port 6379

# Wait for Redis to start
sleep 2

# Check if Redis is running
if redis-cli ping | grep -q PONG; then
  echo "Redis server started successfully"
  exit 0
else
  echo "Failed to start Redis server"
  exit 1
fi