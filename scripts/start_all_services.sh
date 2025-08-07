#!/bin/bash
# Start both main service and web server

# Kill any existing processes
pkill -f "python.*main.py" || true
pkill -f "uvicorn.*web_server" || true

# Wait for ports to be released
sleep 2

# Set up environment
cd /home/linuxuser/trading/Virtuoso_ccxt
source venv311/bin/activate

# Create logs directory if not exists
mkdir -p logs

# Start web server in background
echo "Starting web server on port 8001..."
nohup uvicorn src.web_server:app --host 0.0.0.0 --port 8001 > logs/web_server.log 2>&1 &
WEB_PID=$!
echo "Web server PID: $WEB_PID"

# Wait for web server to start
sleep 5

# Start main service (this will run in foreground)
echo "Starting main trading service..."
python -u src/main.py