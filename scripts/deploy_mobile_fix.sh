#!/bin/bash

echo "================================"
echo "DEPLOYING MOBILE DASHBOARD FIX"
echo "================================"
echo ""

# Deploy updated files
echo "📱 Deploying mobile dashboard fixes..."

# Deploy updated cached routes with mobile-data endpoint
echo "  - Deploying updated dashboard_cached.py..."
scp src/api/routes/dashboard_cached.py linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/

# Deploy updated mobile dashboard HTML
echo "  - Deploying updated dashboard_mobile_v1.html..."
scp src/dashboard/templates/dashboard_mobile_v1.html linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/dashboard/templates/

echo ""
echo "🔄 Restarting web server..."
ssh linuxuser@45.77.40.77 'pkill -f "web_server.py" && sleep 2 && cd /home/linuxuser/trading/Virtuoso_ccxt && PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt nohup venv311/bin/python src/web_server.py > logs/web_mobile_fix.log 2>&1 & echo "Web server restarted with PID: $!"'

sleep 5

echo ""
echo "✅ Testing mobile-data endpoint..."
echo ""

# Test the new cached mobile-data endpoint
echo "1. Testing /api/dashboard-cached/mobile-data:"
curl -s http://45.77.40.77:8001/api/dashboard-cached/mobile-data | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'  Status: {data.get(\"status\")}')
print(f'  Market Regime: {data[\"market_overview\"][\"market_regime\"]}')
print(f'  Confluence Scores: {len(data.get(\"confluence_scores\", []))} items')
print(f'  Top Gainers: {len(data[\"top_movers\"][\"gainers\"])} items')
print(f'  Top Losers: {len(data[\"top_movers\"][\"losers\"])} items')
print(f'  Source: {data.get(\"source\", \"unknown\")}')
"

echo ""
echo "2. Testing regular mobile-data (fallback):"
curl -s http://45.77.40.77:8001/api/dashboard/mobile-data | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'  Status: {data.get(\"status\")}')
print(f'  Confluence Scores: {len(data.get(\"confluence_scores\", []))} items')
" 2>/dev/null || echo "  Failed to parse"

echo ""
echo "================================"
echo "Mobile Dashboard Fix Deployed!"
echo "================================"
echo ""
echo "📱 Access mobile dashboard at:"
echo "   http://45.77.40.77:8001/dashboard/mobile"
echo ""
echo "✅ The mobile dashboard should now display:"
echo "   - Market overview data"
echo "   - Confluence scores"
echo "   - Top movers (gainers/losers)"