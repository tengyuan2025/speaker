#!/bin/bash
# Stop the production server

echo "Stopping 3D-Speaker server..."

# Kill processes on port 7001
if lsof -ti:7001 > /dev/null 2>&1; then
    lsof -ti:7001 | xargs kill -9
    echo "Server stopped successfully"
else
    echo "No server running on port 7001"
fi

# Kill gunicorn processes if any
pkill -f "gunicorn.*server:app" 2>/dev/null
pkill -f "waitress.*server:app" 2>/dev/null

echo "All server processes terminated"