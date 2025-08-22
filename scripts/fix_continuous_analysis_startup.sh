#!/bin/bash

# Fix ContinuousAnalysisManager startup issue
# This ensures it properly initializes and starts pushing data to cache

echo "=== Fixing ContinuousAnalysisManager Startup ==="
echo ""

VPS_HOST="linuxuser@45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Step 1: Copy the fixed main.py
echo "1. Deploying fixed main.py..."
scp src/main.py $VPS_HOST:$VPS_PATH/src/

# Step 2: Restart the service
echo ""
echo "2. Restarting service to apply fix..."
ssh $VPS_HOST << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

echo "Stopping service..."
sudo systemctl stop virtuoso.service

echo "Waiting for clean shutdown..."
sleep 3

echo "Starting service with fix..."
sudo systemctl start virtuoso.service

echo ""
echo "Checking service status..."
sudo systemctl status virtuoso.service --no-pager | head -15

echo ""
echo "Waiting 15 seconds for initialization..."
sleep 15

echo ""
echo "=== Checking if ContinuousAnalysisManager started ==="
sudo journalctl -u virtuoso.service --since "1 minute ago" --no-pager | grep -i "ContinuousAnalysisManager\|continuous analysis" | tail -10

echo ""
echo "=== Checking cache push activity ==="
sudo journalctl -u virtuoso.service --since "1 minute ago" --no-pager | grep -i "pushed.*symbols\|unified cache" | tail -10

echo ""
echo "=== Testing cache data ==="
cd /home/linuxuser/trading/Virtuoso_ccxt
source venv311/bin/activate
python scripts/check_cache_simple.py 2>/dev/null || echo "Cache check script not available"
EOF

echo ""
echo "=== Fix Deployed ==="
echo ""
echo "The ContinuousAnalysisManager should now be:"
echo "1. Properly initialized with both required components"
echo "2. Running analysis every 2 seconds"  
echo "3. Pushing aggregated data to memcached"
echo ""
echo "Check dashboard at: http://45.77.40.77:8001/dashboard/mobile"