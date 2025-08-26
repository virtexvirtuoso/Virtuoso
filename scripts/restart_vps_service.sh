#!/bin/bash

# Restart Virtuoso Service on VPS
echo "🔄 Restarting Virtuoso Trading Service on VPS..."

ssh linuxuser@45.77.40.77 << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

echo "🛑 Stopping existing processes..."
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true
sleep 3

echo "🧹 Cleaning up logs..."
mkdir -p logs
> logs/virtuoso.log

echo "🚀 Starting Virtuoso service..."
nohup ./venv311/bin/python src/main.py > logs/virtuoso.log 2>&1 &
sleep 10

echo "🔍 Checking service status..."
if ps aux | grep -q "[p]ython.*main.py"; then
    echo "✅ Service started successfully"
    ps aux | grep "[p]ython.*main.py"
else
    echo "❌ Service failed to start"
    echo "Last 10 lines of log:"
    tail -10 logs/virtuoso.log
fi

echo "🌐 Testing web server..."
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ | grep -q "200" && echo "✅ Web server responding" || echo "⚠️ Web server not responding yet"

echo "🔗 Service URLs:"
echo "- Main Dashboard: http://45.77.40.77:8000/"
echo "- Performance Monitor: http://45.77.40.77:8000/performance" 
echo "- Performance API: http://45.77.40.77:8000/api/monitoring/performance/summary"
EOF

echo "✅ Service restart complete!"