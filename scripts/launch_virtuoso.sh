#!/bin/bash

# Virtuoso Trading System Launcher
echo "🚀 Starting Virtuoso Trading System..."

# Navigate to project directory
cd /Users/ffv_macmini/Desktop/Virtuoso_ccxt

# Activate virtual environment
source venv311/bin/activate

# Check if port 8001 is in use and kill if necessary
if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 8001 is in use. Killing existing process..."
    lsof -ti:8001 | xargs kill -9
    sleep 2
fi

# Start the application
echo "✅ Environment activated. Starting main.py..."
python src/main.py 