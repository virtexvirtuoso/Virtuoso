#!/bin/bash

echo "🚀 Deploying Enhanced Market Overview Card to VPS..."
echo "=================================================="

VPS_HOST="linuxuser@45.77.40.77"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Backup current version
echo "📦 Backing up current mobile dashboard..."
ssh $VPS_HOST "cp $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1_backup_$(date +%Y%m%d_%H%M%S).html"

# Copy the updated version
echo "📤 Deploying enhanced mobile dashboard..."
scp src/dashboard/templates/dashboard_mobile_v1_updated.html $VPS_HOST:$PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html

# Restart web service
echo "🔄 Restarting web service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso-web.service"

# Wait for service to start
sleep 3

echo ""
echo "🧪 Testing enhanced features..."
echo "================================"

# Test market overview data
echo "1. Testing market overview endpoint:"
curl -s "http://45.77.40.77:8001/api/dashboard-cached/mobile-data" | python3 -c "
import json, sys
data = json.load(sys.stdin)
overview = data.get('market_overview', {})
breadth = data.get('market_breadth', {})
print(f'   Market Regime: {overview.get(\"market_regime\", \"unknown\")}')
print(f'   Trend Strength: {overview.get(\"trend_strength\", 0)}')
print(f'   Volatility: {overview.get(\"volatility\", 0):.1f}%')
print(f'   BTC Dominance: {overview.get(\"btc_dominance\", 0):.1f}%')
if breadth:
    print(f'   Market Breadth: {breadth.get(\"display\", \"N/A\")}')
print(f'   Total Volume: \${overview.get(\"total_volume_24h\", 0)/1e9:.2f}B')
"

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📱 Access the enhanced mobile dashboard at:"
echo "   http://45.77.40.77:8001/dashboard/mobile"
echo ""
echo "🎯 New Features Added:"
echo "   • Expandable card (tap to expand/collapse)"
echo "   • Compact summary with regime chip & gauges"
echo "   • Sparkline charts for trend visualization"
echo "   • Timeframe selector (24h/7d/30d)"
echo "   • Live update timestamp"
echo "   • Improved tile layout in expanded view"
echo ""
echo "💡 Tip: Tap the market overview card to see detailed metrics!"