#!/bin/bash

echo "=================================================="
echo "🎯 Deploying Increased Liquidity Zones Weight to VPS"
echo "=================================================="

# VPS connection details
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo -e "\n⚖️ Weight changes:"
echo "   Liquidity Zones: 0.05 (5%) → 0.20 (20%) ⬆️ 4x increase!"
echo "   CVD: 0.25 → 0.20 ⬇️"
echo "   Trade Flow: 0.20 → 0.15 ⬇️"
echo "   Imbalance: 0.15 → 0.12 ⬇️"
echo "   Pressure: 0.10 → 0.08 ⬇️"
echo ""
echo "   This gives much more importance to Smart Money liquidity zones!"

echo -e "\n📤 Deploying updated file to VPS..."
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
echo "🔍 To see the impact of increased liquidity_zones weight:"
echo "   ssh $VPS_USER@$VPS_HOST"
echo "   sudo journalctl -u virtuoso.service -f | grep -E 'liquidity_zones|Impact'"
echo ""
echo "💡 The liquidity_zones score will now have 4x more impact on final scores!"
echo "=================================================="