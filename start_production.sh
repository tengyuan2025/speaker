#!/bin/bash
# Production deployment script for 3D-Speaker server

# Set working directory to script location
cd "$(dirname "$0")"

# Environment variables for production
export FLASK_ENV=production
export FLASK_DEBUG=0
export DEBUG=false
export HOST=0.0.0.0
export PORT=7001
export DEVICE=cpu

# Stop any existing processes first
echo "=== Stopping existing processes on port 7001 ==="
if lsof -ti:7001 > /dev/null 2>&1; then
    lsof -ti:7001 | xargs kill -9 2>/dev/null
    echo "Stopped existing processes"
    sleep 2
fi

# Kill any existing gunicorn/waitress processes
pkill -f "gunicorn.*server:app" 2>/dev/null
pkill -f "waitress.*server:app" 2>/dev/null
pkill -f "python.*server.py" 2>/dev/null

# Check Python environment
echo "=== Checking Python environment ==="
if [ -d "/root/miniconda3/envs/3D-Speaker" ]; then
    echo "Activating conda environment..."
    source /root/miniconda3/bin/activate 3D-Speaker
elif [ -d "~/miniconda3/envs/3D-Speaker" ]; then
    echo "Activating conda environment..."
    source ~/miniconda3/bin/activate 3D-Speaker
elif command -v python3 &> /dev/null; then
    echo "Using system Python 3"
    alias python=python3
else
    echo "Error: Python environment not found"
    exit 1
fi

echo "Python: $(which python)"
echo "Python version: $(python --version)"

# Create logs directory
mkdir -p logs

# Install production dependencies if needed
echo "=== Checking dependencies ==="
if ! python -c "import gunicorn" 2>/dev/null; then
    echo "Installing gunicorn..."
    pip install gunicorn==21.2.0
fi

if ! python -c "import waitress" 2>/dev/null; then
    echo "Installing waitress..."
    pip install waitress==2.1.2
fi

if ! python -c "import flask" 2>/dev/null; then
    echo "Installing Flask..."
    pip install Flask==2.3.2 Werkzeug==2.3.6
fi

if ! python -c "import modelscope" 2>/dev/null; then
    echo "Installing modelscope..."
    pip install modelscope
fi

# Start the server
echo "=== Starting 3D-Speaker production server ==="

# Try gunicorn first (best for production)
if command -v gunicorn &> /dev/null; then
    echo "Starting with Gunicorn..."
    gunicorn --bind 0.0.0.0:7001 \
             --workers 2 \
             --worker-class sync \
             --timeout 120 \
             --keep-alive 5 \
             --log-level info \
             --access-logfile logs/access.log \
             --error-logfile logs/error.log \
             --daemon \
             server:app

    sleep 3
    if lsof -ti:7001 > /dev/null 2>&1; then
        echo "✅ Server started successfully on port 7001 (Gunicorn)"
        echo "📝 Access logs: logs/access.log"
        echo "📝 Error logs: logs/error.log"
        echo "🔗 Test URL: http://localhost:7001/health"
        echo ""
        echo "To stop: lsof -ti:7001 | xargs kill -9"
    else
        echo "⚠️ Gunicorn failed to start, trying waitress..."
        # Fallback to waitress
        nohup python -m waitress --host=0.0.0.0 --port=7001 --threads=4 server:app > logs/server.log 2>&1 &
        sleep 3
        if lsof -ti:7001 > /dev/null 2>&1; then
            echo "✅ Server started successfully on port 7001 (Waitress)"
            echo "📝 Server logs: logs/server.log"
        else
            echo "❌ Failed to start server"
            exit 1
        fi
    fi
else
    # No gunicorn, try waitress
    echo "Gunicorn not found, starting with Waitress..."
    if python -c "import waitress" 2>/dev/null; then
        nohup python -m waitress --host=0.0.0.0 --port=7001 --threads=4 server:app > logs/server.log 2>&1 &
        sleep 3
        if lsof -ti:7001 > /dev/null 2>&1; then
            echo "✅ Server started successfully on port 7001 (Waitress)"
            echo "📝 Server logs: logs/server.log"
            echo "🔗 Test URL: http://localhost:7001/health"
        else
            echo "❌ Failed to start server"
            exit 1
        fi
    else
        # Last resort - use Flask development server with warning
        echo "⚠️ WARNING: No production server found, using Flask development server"
        echo "This is NOT recommended for production!"
        nohup python server.py > logs/server.log 2>&1 &
        sleep 3
        if lsof -ti:7001 > /dev/null 2>&1; then
            echo "✅ Server started on port 7001 (Development mode)"
            echo "📝 Server logs: logs/server.log"
            echo "⚠️ Please install gunicorn or waitress for production use"
        else
            echo "❌ Failed to start server"
            exit 1
        fi
    fi
fi

# Test the server
echo ""
echo "=== Testing server ==="
sleep 2
if curl -s -o /dev/null -w "%{http_code}" http://localhost:7001/health | grep -q "200\|503"; then
    echo "✅ Server is responding"
else
    echo "⚠️ Server may not be ready yet. Check logs for details."
fi

echo ""
echo "=== Server Status ==="
ps aux | grep -E "(gunicorn|waitress|server.py)" | grep -v grep || echo "No server processes found"