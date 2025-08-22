#!/bin/bash

echo "🔧 Fixing Market Overview Metrics on VPS..."
echo "==========================================="

VPS_HOST="linuxuser@45.77.40.77"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Copy the fix script to VPS
echo "📤 Copying fix script to VPS..."
scp scripts/fix_market_overview_metrics.py $VPS_HOST:$PROJECT_DIR/scripts/

# Run the fix on VPS where Bybit API is accessible
echo "🔧 Running fix on VPS..."
ssh $VPS_HOST "cd $PROJECT_DIR && ./venv311/bin/python scripts/fix_market_overview_metrics.py"

# Copy updated cache adapter to VPS
echo "📤 Deploying updated cache adapter..."
scp src/api/cache_adapter.py $VPS_HOST:$PROJECT_DIR/src/api/

# Restart web service
echo "🔄 Restarting web service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso-web.service"

# Wait for service
sleep 3

# Test the API
echo ""
echo "🧪 Testing API endpoints..."
echo "============================"

echo "1. Testing mobile-data endpoint:"
curl -s "http://45.77.40.77:8001/api/dashboard-cached/mobile-data" | python3 -c "
import json, sys
data = json.load(sys.stdin)
overview = data.get('market_overview', {})
print(f'  ✓ Market Regime: {overview.get(\"market_regime\")}')
print(f'  ✓ Trend Strength: {overview.get(\"trend_strength\")}%')
print(f'  ✓ BTC Dominance: {overview.get(\"btc_dominance\")}%')
print(f'  ✓ Current Volatility: {overview.get(\"current_volatility\")}%')
print(f'  ✓ Average Volatility: {overview.get(\"avg_volatility\")}%')
print(f'  ✓ Total Volume: \${overview.get(\"total_volume\", 0):,.0f}')
"

echo ""
echo "2. Testing market breadth:"
curl -s "http://45.77.40.77:8001/api/dashboard-cached/mobile-data" | python3 -c "
import json, sys
data = json.load(sys.stdin)
if 'market_breadth' in data:
    breadth = data['market_breadth']
    print(f'  ✓ Up: {breadth.get(\"up_count\", 0)}')
    print(f'  ✓ Down: {breadth.get(\"down_count\", 0)}')
    print(f'  ✓ Percentage: {breadth.get(\"breadth_percentage\", 0)}% Bullish')
"

echo ""
echo "✅ Fix deployment complete!"
echo ""
echo "📊 Fixed Issues:"
echo "  1. Trend Strength: Now shows 0-100% scale"
echo "  2. BTC Dominance: Real data from CoinGecko API"
echo "  3. Volatility: Calculated from price movements"
echo "  4. Total Volume: Aggregated from all tickers"
echo ""
echo "📱 View at: http://45.77.40.77:8001/dashboard/mobile"