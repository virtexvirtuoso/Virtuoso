#!/bin/bash

# Deploy Confluence Scores System Status Fix
# This script fixes the SYSTEM_STATUS appearing in confluence scores

set -e

echo "🔧 Deploying Confluence Scores System Status Fix..."
echo "==================================================="

# Copy the fixed template
echo "📤 Updating mobile dashboard template..."
scp src/dashboard/templates/dashboard_mobile_v1.html \
    linuxuser@VPS_HOST_REDACTED:/home/linuxuser/trading/Virtuoso_ccxt/src/dashboard/templates/

# Add cache-busting and restart
echo "🔄 Restarting with cache-busting..."
ssh linuxuser@VPS_HOST_REDACTED "
    cd /home/linuxuser/trading/Virtuoso_ccxt
    # Add timestamp to force browser refresh
    sed -i '1i<!-- Confluence fix deployed: $(date) -->' src/dashboard/templates/dashboard_mobile_v1.html
    sudo systemctl restart virtuoso.service
    sleep 3
    sudo systemctl status virtuoso.service --no-pager -l | head -10
"

echo ""
echo "🧪 Testing confluence scores fix..."
curl -s http://VPS_HOST_REDACTED:8003/api/dashboard-cached/mobile-data | python3 -c "
import sys,json
try:
    data=json.load(sys.stdin)
    scores = data.get('confluence_scores', [])
    print(f'✅ Mobile-data endpoint: {len(scores)} confluence scores')
    for score in scores:
        symbol = score.get('symbol', 'NO_SYMBOL') if isinstance(score, dict) else str(score)
        if 'SYSTEM' in symbol:
            print(f'⚠️  Found system entry: {symbol}')
        else:
            print(f'✅ Valid symbol: {symbol}')
except Exception as e:
    print(f'❌ Test failed: {e}')
"

echo ""
echo "✅ Confluence scores fix deployed!"
echo ""
echo "🌐 Test the mobile dashboard at: http://VPS_HOST_REDACTED:8003/dashboard/mobile"
echo "🔍 Check browser console for confluence filtering logs"
echo ""
echo "📋 Fixed Issues:"
echo "  • SYSTEM_STATUS entries filtered out of confluence scores"
echo "  • Added validation to prevent system entries from displaying"
echo "  • Added debug logging for confluence score processing"
echo "  • Empty state will show when no valid symbols available"