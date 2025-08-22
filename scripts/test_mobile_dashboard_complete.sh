#!/bin/bash

echo "🧪 Complete Mobile Dashboard Test"
echo "================================="

echo ""
echo "📱 Testing Mobile Dashboard Endpoints..."
echo "----------------------------------------"

echo "1. Mobile Data Endpoint:"
curl -s "http://45.77.40.77:8001/api/dashboard-cached/mobile-data" | jq '.market_overview'

echo ""
echo "2. Market Regime:"
curl -s "http://45.77.40.77:8001/api/dashboard-cached/mobile-data" | jq -r '.market_overview.market_regime'

echo ""
echo "3. BTC Dominance:"
curl -s "http://45.77.40.77:8001/api/dashboard-cached/mobile-data" | jq -r '.market_overview.btc_dominance'

echo ""
echo "4. Total Volume:"
VOLUME=$(curl -s "http://45.77.40.77:8001/api/dashboard-cached/mobile-data" | jq -r '.market_overview.total_volume_24h')
echo "\$$(echo "scale=1; $VOLUME/1000000000" | bc)B"

echo ""
echo "5. Confluence Scores Count:"
curl -s "http://45.77.40.77:8001/api/dashboard-cached/mobile-data" | jq '.confluence_scores | length'

echo ""
echo "6. First Confluence Score:"
curl -s "http://45.77.40.77:8001/api/dashboard-cached/mobile-data" | jq '.confluence_scores[0] | {symbol, score, sentiment}'

echo ""
echo "🔍 Testing Analysis Button..."
echo "-----------------------------"

echo "7. Analysis Endpoint Test:"
curl -s "http://45.77.40.77:8001/api/dashboard/confluence-analysis/BTCUSDT" | jq -r '.analysis' | head -5

echo ""
echo "8. Analysis Page Test:"
curl -s -I "http://45.77.40.77:8001/api/dashboard/confluence-analysis-page?symbol=BTCUSDT" | head -1

echo ""
echo "📊 Testing Market Data..."
echo "-------------------------"

echo "9. Market Breadth:"
curl -s "http://45.77.40.77:8001/api/dashboard-cached/mobile-data" | jq '.market_breadth // "Not available"'

echo ""
echo "10. Top Movers:"
curl -s "http://45.77.40.77:8001/api/dashboard-cached/mobile-data" | jq '.top_movers.gainers | length'

echo ""
echo "✅ Mobile Dashboard Test Complete!"
echo "=================================="
echo ""
echo "🌐 Access mobile dashboard at:"
echo "   http://45.77.40.77:8001/dashboard/mobile"
echo ""
echo "🎯 Click 'Analyze' button on any symbol to see terminal breakdown"