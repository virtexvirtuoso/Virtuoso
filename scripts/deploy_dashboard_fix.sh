#!/bin/bash
set -e

echo "Deploying dashboard display fixes..."

# Backup current file
ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && cp src/static/js/dashboard-enhanced.js src/static/js/dashboard-enhanced.js.backup.$(date +%s)"

# Copy fixed JavaScript
scp src/static/js/dashboard-enhanced-fixed.js vps:/home/linuxuser/trading/Virtuoso_ccxt/src/static/js/dashboard-enhanced.js

# Clear browser cache by adding version parameter
ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && sed -i 's/dashboard-enhanced\.js/dashboard-enhanced.js?v='$(date +%s)'/g' src/static/index.html 2>/dev/null || true"

# Restart web service to ensure changes take effect
ssh vps "sudo systemctl restart virtuoso-web.service"

echo "Dashboard display fixes deployed!"
echo ""
echo "Testing dashboard data..."
curl -s http://VPS_HOST_REDACTED:8002/api/dashboard/data | python3 -c "
import json, sys
data = json.load(sys.stdin)
mo = data.get('market_overview', {})
print(f'API Response: Gainers={mo.get("gainers", 0)}, Losers={mo.get("losers", 0)}')
"

echo ""
echo "✅ Dashboard should now display market sentiment correctly!"
echo "🌐 View at: http://VPS_HOST_REDACTED:8002/"
