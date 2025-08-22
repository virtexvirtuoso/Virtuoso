#!/bin/bash

echo "=================================================="
echo "🚀 Deploying Liquidity Zones Performance Fix to VPS"
echo "=================================================="

# VPS connection details
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo -e "\n📊 Performance optimizations applied:"
echo "   ✓ Reduced swing_length from 50 to 25"
echo "   ✓ Limited analysis to last 500 candles"
echo "   ✓ Expected improvement: 2100ms → ~500-700ms"

echo -e "\n📤 Deploying optimized file to VPS..."
scp src/indicators/orderflow_indicators.py "$VPS_USER@$VPS_HOST:$VPS_PATH/src/indicators/"

if [ $? -eq 0 ]; then
    echo "   ✅ File deployed successfully"
else
    echo "   ❌ Deployment failed"
    exit 1
fi

echo -e "\n🔄 Restarting Virtuoso service..."
ssh "$VPS_USER@$VPS_HOST" "sudo systemctl restart virtuoso.service"

echo -e "\n📊 Service status:"
ssh "$VPS_USER@$VPS_HOST" "sudo systemctl status virtuoso.service --no-pager | head -10"

echo -e "\n=================================================="
echo "✅ Deployment complete!"
echo ""
echo "🔍 To monitor performance improvements:"
echo "   ssh $VPS_USER@$VPS_HOST"
echo "   sudo journalctl -u virtuoso.service -f | grep 'liquidity_zones'"
echo "=================================================="