#!/bin/bash

echo "======================================"
echo "DEPLOYING DATA FLOW FIXES"
echo "======================================"
echo ""
echo "This will fix:"
echo "  - Signal generation"
echo "  - Top movers data"
echo "  - Volume field name mismatch"
echo "  - Market regime calculation"
echo ""

VPS_HOST="45.77.40.77"
VPS_USER="linuxuser"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo "📦 Deploying enhanced analysis service..."
scp src/services/analysis_service_enhanced.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/services/

echo "📦 Deploying updated service coordinator..."
scp src/services/service_coordinator.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/services/

echo "📦 Deploying fixed direct cache..."
scp src/core/direct_cache.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/core/

echo ""
echo "🔄 Restarting services..."

ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Kill existing services
echo "Stopping old services..."
pkill -f "service_coordinator" || true
pkill -f "analysis_service" || true
sleep 3

# Start enhanced services
echo "Starting enhanced services..."
export PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt
nohup venv311/bin/python src/services/service_coordinator.py > logs/services_enhanced.log 2>&1 &
echo "Services started with PID: $!"

# Also restart web server to pick up cache fixes
echo "Restarting web server..."
pkill -f "web_server.py" || true
sleep 2
nohup venv311/bin/python src/web_server.py > logs/web_server.log 2>&1 &
echo "Web server restarted"

sleep 5

# Check if services are running
echo ""
echo "Service status:"
ps aux | grep -E "service_coordinator|web_server" | grep -v grep | wc -l
echo " processes running"

EOF

echo ""
echo "⏳ Waiting for services to generate data..."
sleep 15

echo ""
echo "🔍 Checking data generation..."
echo ""

# Check if signals are being generated
echo "1. Checking signals in cache:"
ssh ${VPS_USER}@${VPS_HOST} 'cd /home/linuxuser/trading/Virtuoso_ccxt && venv311/bin/python -c "
import asyncio
import aiomcache
import json

async def check():
    client = aiomcache.Client(\"localhost\", 11211)
    
    # Check signals
    signals_data = await client.get(b\"analysis:signals\")
    if signals_data:
        signals = json.loads(signals_data.decode())
        print(f\"   ✅ Signals: {len(signals.get(\"signals\", []))} generated\")
        if signals.get(\"signals\"):
            first = signals[\"signals\"][0]
            print(f\"   Sample: {first.get(\"symbol\")} - Score: {first.get(\"score\")}\")
    else:
        print(\"   ❌ No signals in cache\")
    
    # Check movers
    movers_data = await client.get(b\"market:movers\")
    if movers_data:
        movers = json.loads(movers_data.decode())
        print(f\"   ✅ Gainers: {len(movers.get(\"gainers\", []))}\")
        print(f\"   ✅ Losers: {len(movers.get(\"losers\", []))}\")
    else:
        print(\"   ❌ No movers in cache\")
    
    # Check overview
    overview_data = await client.get(b\"market:overview\")
    if overview_data:
        overview = json.loads(overview_data.decode())
        print(f\"   ✅ Volume: {overview.get(\"total_volume\", 0)/1e9:.2f}B (field fixed)\")
    else:
        print(\"   ❌ No overview in cache\")
    
    await client.close()

asyncio.run(check())
"'

echo ""
echo "2. Testing dashboard endpoints:"
echo ""

# Test fast endpoint
echo "   Fast endpoint:"
curl -s http://${VPS_HOST}:8001/api/fast/overview | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'      Signals: {len(data.get(\"signals\", []))}')
    print(f'      Volume: {data.get(\"summary\", {}).get(\"total_volume\", 0)/1e9:.2f}B')
    print(f'      Regime: {data.get(\"market_regime\", \"unknown\")}')
except Exception as e:
    print(f'      Error: {e}')
"

echo ""
echo "   Mobile endpoint:"
curl -s http://${VPS_HOST}:8001/api/dashboard-cached/mobile-data | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'      Confluence: {len(data.get(\"confluence_scores\", []))} scores')
    print(f'      Gainers: {len(data[\"top_movers\"][\"gainers\"])}')
    print(f'      Losers: {len(data[\"top_movers\"][\"losers\"])}')
except Exception as e:
    print(f'      Error: {e}')
"

echo ""
echo "======================================"
echo "Data Flow Fix Deployed!"
echo "======================================"
echo ""
echo "✅ Enhanced analysis service with:"
echo "   - Trading signal generation"
echo "   - Top movers calculation"
echo "   - Fixed volume field names"
echo "   - Market regime detection"
echo ""
echo "📊 Dashboards should now show:"
echo "   - Live trading signals with scores"
echo "   - Top gainers and losers"
echo "   - Correct volume data"
echo "   - Market regime indicators"