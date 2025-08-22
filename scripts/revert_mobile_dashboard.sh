#!/bin/bash

echo "🔄 Reverting Mobile Dashboard to Previous Version..."
echo "===================================================="

VPS_HOST="linuxuser@45.77.40.77"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# First, backup the enhanced version on VPS
echo "📦 Backing up enhanced version on VPS..."
ssh $VPS_HOST "cp $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1_enhanced_$(date +%Y%m%d_%H%M%S).html"

# Restore the previous version
echo "🔙 Restoring previous dashboard version..."
ssh $VPS_HOST "cp $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1_backup_20250821_100721.html $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html"

# Restart web service
echo "🔄 Restarting web service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso-web.service"

# Wait for service to start
sleep 3

# Verify the reversion
echo ""
echo "🧪 Verifying reversion..."
echo "=========================="

# Check for the old market overview structure
echo "1. Checking for original Market Overview structure:"
curl -s "http://45.77.40.77:8001/dashboard/mobile" | grep -q "MARKET REGIME" && echo "   ✅ Found original MARKET REGIME label" || echo "   ❌ Original structure not found"

echo ""
echo "2. Checking page loads correctly:"
TITLE=$(curl -s "http://45.77.40.77:8001/dashboard/mobile" | grep -o '<title>.*</title>')
echo "   Page title: $TITLE"

echo ""
echo "3. Testing data endpoint:"
curl -s "http://45.77.40.77:8001/api/dashboard-cached/mobile-data" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(f'   ✅ API working - Market regime: {data.get(\"market_overview\", {}).get(\"market_regime\", \"unknown\")}')
except:
    print('   ❌ API error')
"

echo ""
echo "✅ Reversion Complete!"
echo ""
echo "📱 The mobile dashboard has been reverted to the previous version"
echo "   URL: http://45.77.40.77:8001/dashboard/mobile"
echo ""
echo "💾 Backups created:"
echo "   • Enhanced version saved locally as: dashboard_mobile_v1_enhanced_backup.html"
echo "   • Enhanced version saved on VPS with timestamp"
echo ""
echo "📝 To restore the enhanced version later, use:"
echo "   scp src/dashboard/templates/dashboard_mobile_v1_enhanced_backup.html $VPS_HOST:$PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html"