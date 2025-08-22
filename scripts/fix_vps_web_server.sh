#!/bin/bash

echo "Fixing VPS Web Server"
echo "===================="

ssh linuxuser@45.77.40.77 'bash -s' << 'ENDSSH'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Kill any existing web servers
echo "Stopping existing web servers..."
pkill -f "uvicorn" || true
pkill -f "web_server.py" || true
sleep 2

# Start the web server properly
echo "Starting web server..."
export PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt
nohup venv311/bin/python src/web_server.py > logs/web_server_fixed.log 2>&1 &

sleep 5

# Check if running
if pgrep -f "web_server.py" > /dev/null; then
    echo "✅ Web server started"
    
    # Test endpoints
    echo ""
    echo "Testing endpoints:"
    curl -s -o /dev/null -w "Regular dashboard: %{http_code}\n" http://localhost:8000/api/dashboard/overview
    curl -s -o /dev/null -w "Cache health: %{http_code}\n" http://localhost:8000/api/cache/health
    curl -s -o /dev/null -w "Phase 2 dashboard: %{http_code}\n" http://localhost:8000/dashboard/phase2
else
    echo "❌ Web server failed to start"
    tail -n 30 logs/web_server_fixed.log
fi
ENDSSH