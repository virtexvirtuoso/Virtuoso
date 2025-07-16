#!/bin/bash

# Virtuoso Trading System Startup Script
# This script ensures the correct Python environment is used

echo "🚀 Starting Virtuoso Trading System..."

# Check if we're in the correct directory
if [ ! -f "src/main.py" ]; then
    echo "❌ Error: Please run this script from the Virtuoso_ccxt directory"
    exit 1
fi

# Check if Python 3.11 virtual environment exists
if [ ! -d "venv311" ]; then
    echo "❌ Error: Python 3.11 virtual environment not found (venv311)"
    echo "Please create the virtual environment first:"
    echo "python3.11 -m venv venv311"
    echo "source venv311/bin/activate"
    echo "pip install -r requirements.txt"
    exit 1
fi

echo "📦 Activating Python 3.11 virtual environment..."
source venv311/bin/activate

echo "🔍 Python version: $(python --version)"
echo "📍 Python path: $(which python)"

# Check if required packages are installed
echo "🔧 Checking dependencies..."
if ! python -c "import pybit" 2>/dev/null; then
    echo "❌ Error: pybit not installed in virtual environment"
    echo "Please install dependencies: pip install -r requirements.txt"
    exit 1
fi

echo "✅ Dependencies OK"

# Kill any existing processes on port 8000
if lsof -ti:8000 >/dev/null 2>&1; then
    echo "🔄 Stopping existing processes on port 8000..."
    kill $(lsof -ti:8000) 2>/dev/null || true
    sleep 2
fi

echo "🎯 Starting Virtuoso Trading System..."
echo "📊 Access dashboard at: http://localhost:8000"
echo "🔴 Press Ctrl+C to stop"
echo ""

# Start the application
python src/main.py 