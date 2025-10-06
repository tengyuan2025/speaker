#!/bin/bash
# Production deployment script for 3D-Speaker server

# Environment variables for production
export FLASK_ENV=production
export FLASK_DEBUG=0
export DEBUG=false
export HOST=0.0.0.0
export PORT=7001
export DEVICE=cpu

# Check if virtual environment exists
if [ ! -d "3D-Speaker" ]; then
    echo "Error: Virtual environment not found. Please run setup first."
    exit 1
fi

# Activate environment
source ~/miniconda3/bin/activate 3D-Speaker

echo "Starting 3D-Speaker production server..."

# Kill existing processes on port 7001
echo "Checking for existing processes on port 7001..."
lsof -ti:7001 | xargs -r kill -9 2>/dev/null

# Use gunicorn for production (WSGI server)
if command -v gunicorn &> /dev/null; then
    echo "Starting with Gunicorn (recommended)..."
    gunicorn --bind 0.0.0.0:7001 \
             --workers 4 \
             --worker-class sync \
             --timeout 120 \
             --keep-alive 5 \
             --log-level info \
             --access-logfile logs/access.log \
             --error-logfile logs/error.log \
             --daemon \
             server:app
    echo "Server started on port 7001 (background)"
    echo "Logs: logs/access.log and logs/error.log"
else
    # Fallback to waitress if gunicorn not installed
    echo "Gunicorn not found, using waitress..."
    nohup python -m waitress --host=0.0.0.0 --port=7001 server:app > logs/server.log 2>&1 &
    echo "Server started on port 7001 (background)"
    echo "Logs: logs/server.log"
fi

echo "To stop the server, run: ./stop_server.sh"