#!/bin/bash

echo "========================================="
echo "Deploying OHLCV Data Fix for Chart Generation"
echo "========================================="

# VPS connection details
VPS_USER="linuxuser"
VPS_IP="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo "📋 Fixing simulated data issue in chart generation..."
echo ""

# Copy the fixed monitor.py file
echo "📦 Copying fixed monitor.py to VPS..."
scp src/monitoring/monitor.py ${VPS_USER}@${VPS_IP}:${VPS_PATH}/src/monitoring/

echo ""
echo "🔄 Restarting services on VPS..."
ssh ${VPS_USER}@${VPS_IP} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Restart the service to apply changes
echo "Restarting virtuoso service..."
sudo systemctl restart virtuoso.service

# Check service status
echo ""
echo "Service status:"
sudo systemctl status virtuoso.service --no-pager | head -20

# Show recent logs to verify the fix is working
echo ""
echo "Recent logs (checking for OHLCV fetch messages):"
sudo journalctl -u virtuoso.service -n 50 --no-pager | grep -E "OHLCV|REPORT|simulated|fetching fresh" | tail -20

echo ""
echo "✅ Deployment complete!"
EOF

echo ""
echo "========================================="
echo "Deployment Summary:"
echo "- Fixed monitor.py to fetch OHLCV data when not cached"
echo "- This prevents falling back to simulated chart generation"
echo "- Service has been restarted"
echo ""
echo "Monitor the logs with:"
echo "ssh ${VPS_USER}@${VPS_IP} 'sudo journalctl -u virtuoso.service -f | grep -E \"OHLCV|REPORT|simulated\"'"
echo "========================================="