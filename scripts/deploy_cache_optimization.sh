#!/bin/bash

echo "=== Deploying Indicator Cache Optimizations to VPS ==="
echo "Time: $(date)"

VPS_HOST="linuxuser@45.77.40.77"
PROJECT_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Step 1: Copy the optimized indicator cache file
echo "→ Copying optimized indicator_cache.py..."
scp src/core/cache/indicator_cache.py $VPS_HOST:$PROJECT_PATH/src/core/cache/

# Step 2: SSH to VPS and restart the service
echo "→ Restarting service on VPS..."
ssh $VPS_HOST << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Restart the service
echo "Restarting virtuoso service..."
sudo systemctl restart virtuoso.service

# Wait for service to start
sleep 5

# Check service status
echo "Service status:"
sudo systemctl status virtuoso.service --no-pager | head -20

# Check recent logs for cache performance
echo ""
echo "Recent cache logs (last 50 lines):"
sudo journalctl -u virtuoso.service --no-pager -n 50 | grep -E "(cache|indicator)" | tail -20

echo ""
echo "Deployment complete!"
EOF

echo "=== Cache Optimization Deployment Finished ==="