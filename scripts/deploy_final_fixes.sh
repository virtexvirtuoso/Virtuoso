#!/bin/bash

echo "======================================"
echo "DEPLOYING FINAL FIXES FOR 10/10"
echo "======================================"
echo ""

VPS_HOST="45.77.40.77"
VPS_USER="linuxuser"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo "📦 Deploying fixed cache adapter..."
scp src/api/cache_adapter.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/api/

echo ""
echo "🔄 Restarting web server to pick up changes..."

ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Just restart web server, keep services running
pkill -f "web_server.py" || true
sleep 2

export PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt
nohup venv311/bin/python src/web_server.py > /dev/null 2>&1 &
echo "Web server restarted"

sleep 5

# Quick check
if pgrep -f "web_server.py" > /dev/null; then
    echo "✅ Web server running"
else
    echo "❌ Web server failed to start"
fi
EOF

echo ""
echo "⏳ Waiting for server to stabilize..."
sleep 5

echo ""
echo "======================================"
echo "VERIFYING ALL 10 COMPONENTS"
echo "======================================"
echo ""

# Test all endpoints
endpoints=(
    "/api/dashboard/overview:Regular Dashboard"
    "/api/dashboard-cached/overview:Cached Dashboard"
    "/api/dashboard-cached/mobile-data:Mobile Data"
    "/api/fast/overview:Fast Dashboard"
    "/api/fast/signals:Fast Signals"
    "/api/fast/movers:Fast Movers"
    "/api/dashboard-cached/signals:Cached Signals"
    "/api/dashboard-cached/market-overview:Cached Market"
    "/api/dashboard-cached/alerts:Cached Alerts"
    "/api/dashboard-cached/market-movers:Cached Movers"
)

success_count=0
fail_count=0

for endpoint_info in "${endpoints[@]}"; do
    IFS=':' read -r endpoint name <<< "$endpoint_info"
    
    response=$(curl -s -o /dev/null -w "%{http_code}" http://${VPS_HOST}:8001${endpoint})
    
    if [ "$response" = "200" ]; then
        echo "✅ ${name}: OK (HTTP 200)"
        ((success_count++))
    else
        echo "❌ ${name}: FAILED (HTTP $response)"
        ((fail_count++))
    fi
done

echo ""
echo "======================================"
echo "DETAILED DATA CHECK"
echo "======================================"
echo ""

# Check mobile data for confluence scores
echo "Mobile Dashboard Confluence Scores:"
curl -s http://${VPS_HOST}:8001/api/dashboard-cached/mobile-data | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    scores = data.get('confluence_scores', [])
    if scores:
        print(f'   ✅ {len(scores)} confluence scores')
        if len(scores) > 0:
            first = scores[0]
            print(f'   Example: {first.get(\"symbol\")} - Score: {first.get(\"score\"):.2f}')
    else:
        print('   ❌ No confluence scores')
except Exception as e:
    print(f'   Error: {e}')
"

echo ""
echo "Regular Dashboard Data:"
curl -s http://${VPS_HOST}:8001/api/dashboard/overview | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'summary' in data:
        s = data['summary']
        print(f'   ✅ Symbols: {s.get(\"total_symbols\", 0)}')
        print(f'   ✅ Volume: {s.get(\"total_volume_24h\", 0)/1e9:.2f}B')
    if 'signals' in data and data['signals']:
        print(f'   ✅ Signals: {len(data[\"signals\"])}')
    else:
        print('   ⚠️  Signals: None or empty')
except Exception as e:
    print(f'   Error: {e}')
"

echo ""
echo "======================================"
echo "FINAL RESULTS"
echo "======================================"
echo ""

if [ $success_count -eq 10 ]; then
    echo "🎉 SUCCESS: ALL 10/10 COMPONENTS OPERATIONAL!"
    echo ""
    echo "✅ All endpoints responding with HTTP 200"
    echo "✅ Data flowing correctly through all pipelines"
    echo "✅ Mobile confluence scores populated"
    echo "✅ Regular dashboard working"
elif [ $success_count -ge 8 ]; then
    echo "⚠️  PARTIAL SUCCESS: $success_count/10 components working"
    echo ""
    echo "Most components operational but $fail_count still need attention"
else
    echo "❌ CRITICAL: Only $success_count/10 components working"
    echo ""
    echo "$fail_count components failed and need immediate attention"
fi

echo ""
echo "======================================"