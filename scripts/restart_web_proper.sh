#!/bin/bash

VPS_HOST="45.77.40.77"
VPS_USER="linuxuser"

echo "Restarting web server with direct cache adapter..."

ssh ${VPS_USER}@${VPS_HOST} 'bash -s' << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Kill and restart web server
pkill -f "web_server.py" || true
sleep 2

export PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt
nohup venv311/bin/python src/web_server.py > logs/web_server_restart.log 2>&1 &

sleep 5

# Check the log for which adapter is being used
echo "Checking adapter usage:"
grep -i "adapter" logs/web_server_restart.log | head -10

# Check if server is running
if pgrep -f "web_server.py" > /dev/null; then
    echo "✅ Web server restarted"
else
    echo "❌ Web server failed to start"
    tail -20 logs/web_server_restart.log
fi
EOF