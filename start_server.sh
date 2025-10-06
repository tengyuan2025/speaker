#!/bin/bash
# Production startup script for 3D-Speaker Inference Server

set -e

# Configuration
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-"8000"}
DEVICE=${DEVICE:-"cpu"}
MODEL_ID=${SPEAKER_MODEL_ID:-"iic/speech_eres2net_sv_zh-cn_16k-common"}
WORKERS=${WORKERS:-"1"}

# Create necessary directories
mkdir -p uploads
mkdir -p models
mkdir -p logs

echo "========================================"
echo "3D-Speaker Inference Server"
echo "========================================"
echo "Host: $HOST"
echo "Port: $PORT"
echo "Device: $DEVICE"
echo "Model: $MODEL_ID"
echo "Workers: $WORKERS"
echo "========================================"

# Check if we're in conda environment
if [[ "$CONDA_DEFAULT_ENV" != "3D-Speaker" ]]; then
    echo "⚠️  Warning: Not in 3D-Speaker conda environment"
    echo "Please run: conda activate 3D-Speaker"
fi

# Check dependencies
echo "Checking dependencies..."
python -c "
import sys
try:
    from modelscope.pipelines import pipeline
    from flask import Flask
    print('✅ All dependencies available')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "Please install dependencies first:"
    echo "  pip install -r requirements-inference.txt"
    exit 1
fi

# Start server based on environment
if [ "$1" = "production" ]; then
    echo "Starting production server with gunicorn..."

    # Check if gunicorn is installed
    if ! command -v gunicorn &> /dev/null; then
        echo "Installing gunicorn..."
        pip install gunicorn
    fi

    exec gunicorn \
        --bind $HOST:$PORT \
        --workers $WORKERS \
        --worker-class sync \
        --timeout 120 \
        --keepalive 5 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --access-logfile logs/access.log \
        --error-logfile logs/error.log \
        --log-level info \
        server:app

elif [ "$1" = "development" ]; then
    echo "Starting development server..."
    export DEBUG=true
    exec python server.py

else
    echo "Starting server..."
    exec python server.py
fi