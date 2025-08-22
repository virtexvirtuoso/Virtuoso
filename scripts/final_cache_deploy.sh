#!/bin/bash

echo "Final Cache Dashboard Deployment"
echo "================================"

# Deploy all cache files
echo "Deploying cache files..."
scp src/api/routes/dashboard_cached.py linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/
scp src/api/cache_adapter.py linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/api/
scp src/api/__init__.py linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/api/

# Restart web server
echo ""
echo "Restarting web server..."
ssh linuxuser@45.77.40.77 'bash -s' << 'EOF'
pkill -f "python.*web_server" || true
pkill -f "uvicorn" || true
sleep 3

cd /home/linuxuser/trading/Virtuoso_ccxt
export PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt

# Start fresh
nohup venv311/bin/python src/web_server.py > logs/web_cache_final.log 2>&1 &

sleep 5

# Check if running
if pgrep -f "web_server.py" > /dev/null; then
    echo "✅ Web server started"
else
    echo "❌ Failed to start"
    tail -n 30 logs/web_cache_final.log
    exit 1
fi
EOF

echo ""
echo "Testing endpoints..."
sleep 2

# Test endpoints
echo "1. Cache Health:"
curl -s http://45.77.40.77:8000/api/cache/health | python3 -m json.tool 2>/dev/null | head -n 5

echo ""
echo "2. Cached Overview (new):"
curl -s -w "\nTime: %{time_total}s\n" http://45.77.40.77:8000/api/dashboard-cached/overview 2>/dev/null | tail -n 1

echo ""
echo "3. Regular Dashboard:"
curl -s -w "\nTime: %{time_total}s\n" http://45.77.40.77:8000/api/dashboard/overview 2>/dev/null | tail -n 1

echo ""
echo "================================"
echo "Deployment Complete!"