#!/bin/bash

# Script to restart the web server on remote host

echo "🔄 Restarting Virtuoso web server on 45.77.40.77..."

ssh linuxuser@45.77.40.77 'bash -s' << 'ENDSSH'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Kill any existing web server processes
echo "Stopping existing processes..."
pkill -f "python src/web_server.py" || true
pkill -f "python.*web_server" || true
sleep 2

# Activate virtual environment and start server
echo "Starting web server..."
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
    nohup python src/web_server.py > web_server.log 2>&1 &
    SERVER_PID=$!
    echo "Web server started with PID: $SERVER_PID"
    
    # Wait and check if it's running
    sleep 3
    if ps -p $SERVER_PID > /dev/null; then
        echo "✅ Server is running"
        echo "Recent log output:"
        tail -n 20 web_server.log
    else
        echo "❌ Server failed to start. Check web_server.log for errors"
        tail -n 50 web_server.log
    fi
else
    echo "❌ Virtual environment not found at venv/"
    echo "Please create it first with: python -m venv venv"
fi
ENDSSH

echo ""
echo "🌐 Dashboard URLs:"
echo "   Desktop: http://45.77.40.77:8003/dashboard"
echo "   Mobile:  http://45.77.40.77:8003/dashboard/mobile"
echo "   Legacy:  http://45.77.40.77:8003/dashboard/v10"