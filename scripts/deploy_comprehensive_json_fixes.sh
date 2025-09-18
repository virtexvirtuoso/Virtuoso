#!/bin/bash

# Deploy Comprehensive JSON Display Fixes
# This script fixes all JSON object display issues in the mobile dashboard

set -e

echo "🔧 Deploying Comprehensive JSON Display Fixes..."
echo "======================================================"

# Copy the fixed template
echo "📤 Updating mobile dashboard template with comprehensive fixes..."
scp src/dashboard/templates/dashboard_mobile_v1.html \
    linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/dashboard/templates/

# Restart the web server
echo "🔄 Restarting web service..."
ssh linuxuser@${VPS_HOST} "
    cd /home/linuxuser/trading/Virtuoso_ccxt
    sudo systemctl restart virtuoso.service
    sleep 3
    sudo systemctl status virtuoso.service --no-pager -l
"

# Test the endpoints
echo "🧪 Testing mobile dashboard endpoints..."
echo "Health check:"
curl -s http://${VPS_HOST}:8003/health | python3 -c "import sys,json; data=json.load(sys.stdin); print('✅ Service healthy' if data.get('status') == 'healthy' else '❌ Service unhealthy')" 2>/dev/null || echo "❌ Health check failed"

echo ""
echo "Market overview endpoint test:"
curl -s http://${VPS_HOST}:8003/api/dashboard-cached/market-overview | python3 -c "
import sys,json
try:
    data=json.load(sys.stdin)
    print('✅ Market overview endpoint responding')
    if 'market_regime' in data:
        regime = data['market_regime']
        if isinstance(regime, dict):
            print('⚠️  Market regime is still an object:', regime)
        else:
            print('✅ Market regime is properly formatted:', regime)
except:
    print('❌ Market overview endpoint failed')
" 2>/dev/null || echo "❌ Market overview test failed"

echo ""
echo "✅ Comprehensive JSON fixes deployed!"
echo ""
echo "🌐 Test the mobile dashboard at: http://${VPS_HOST}:8003/mobile"
echo "🔍 Check browser console for debug logs showing data structure"
echo ""
echo "📋 Fixed Issues:"
echo "  • Market Regime JSON object display → Proper string formatting"
echo "  • Beta Market Regime JSON handling → Safe data extraction" 
echo "  • Added safeExtractValue() helper for robust data parsing"
echo "  • Enhanced signal card data validation"
echo "  • Added comprehensive debug logging"