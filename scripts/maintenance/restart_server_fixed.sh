#!/bin/bash

echo "🔄 Restarting Virtuoso server with correct environment..."

ssh linuxuser@45.77.40.77 'bash -s' << 'ENDSSH'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Kill existing processes
echo "Stopping existing processes..."
pkill -9 -f "python.*web_server" || true
pkill -9 -f "uvicorn" || true
sleep 2

# Start with correct virtual environment
echo "Starting web server..."
if [ -f venv311/bin/activate ]; then
    source venv311/bin/activate
    nohup python src/web_server.py > web_server.log 2>&1 &
    echo "Server started with PID: $!"
    
    # Check logs after a few seconds
    sleep 5
    echo "Recent logs:"
    tail -20 web_server.log
else
    echo "Error: Virtual environment not found"
    exit 1
fi
ENDSSH