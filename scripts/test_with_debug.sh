#!/bin/bash

VPS_HOST="45.77.40.77"
VPS_USER="linuxuser"

# Kill existing server
ssh ${VPS_USER}@${VPS_HOST} 'pkill -f web_server.py'
sleep 2

# Start with debug output
ssh ${VPS_USER}@${VPS_HOST} 'cd /home/linuxuser/trading/Virtuoso_ccxt && export PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt && venv311/bin/python -u src/web_server.py 2>&1 | grep -E "DEBUG:|Direct Cache" &'

# Give it time to start
sleep 5

# Test the endpoint
echo "Testing endpoint..."
curl -s http://${VPS_HOST}:8001/api/dashboard-cached/signals > /dev/null

# Wait to see output
sleep 2

# Kill the server
ssh ${VPS_USER}@${VPS_HOST} 'pkill -f web_server.py'