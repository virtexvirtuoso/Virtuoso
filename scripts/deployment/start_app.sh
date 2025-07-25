#!/bin/bash
# Start the Virtuoso Trading System

cd /home/linuxuser/trading/Virtuoso_ccxt

# Kill any existing processes on port 8003
sudo lsof -ti:8003 | xargs -r sudo kill -9 2>/dev/null

# Activate virtual environment
source venv311/bin/activate

# Start the application
echo "Starting Virtuoso Trading System..."
python src/main.py