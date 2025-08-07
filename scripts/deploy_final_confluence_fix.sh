#!/bin/bash

echo "=========================================="
echo "🚀 DEPLOYING FINAL CONFLUENCE SCORE FIX"
echo "=========================================="
echo

# Copy the fixed dashboard.py to VPS
echo "📤 Copying fixed dashboard.py to VPS..."
scp src/api/routes/dashboard.py linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/

# Copy test script
echo "📤 Copying test script..."
scp scripts/test_final_dashboard_fix.py linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/scripts/

# SSH to VPS and test
ssh linuxuser@45.77.40.77 << 'EOF'
echo
echo "🔍 Testing on VPS..."
cd /home/linuxuser/trading/Virtuoso_ccxt

# First check if Memcached has data
echo "Checking Memcached for symbols data..."
echo "get virtuoso:symbols" | nc localhost 11211 | head -c 100

echo
echo "🔄 Restarting web server with fixed routes..."
sudo systemctl restart virtuoso-web

# Wait for service to start
sleep 3

echo
echo "✅ Testing dashboard endpoints..."
curl -s http://localhost:8001/api/dashboard/overview | python3 -m json.tool | head -20

echo
echo "🎯 Testing symbols endpoint for confluence scores..."
curl -s http://localhost:8001/api/dashboard/symbols | python3 -c "
import sys, json
data = json.load(sys.stdin)
symbols = data.get('symbols', [])
if symbols:
    print(f'✅ Found {len(symbols)} symbols')
    for sym in symbols[:3]:
        score = sym.get('confluence_score', 50)
        symbol = sym.get('symbol', 'N/A')
        if score != 50:
            print(f'  ✨ {symbol}: Real score = {score:.1f}')
        else:
            print(f'  ⚠️ {symbol}: Default score = {score}')
else:
    print('❌ No symbols returned')
"

echo
echo "=========================================="
echo "📊 DEPLOYMENT COMPLETE"
echo "=========================================="
EOF

echo
echo "✅ Fix deployed! Check the output above."
echo "The dashboard should now show real confluence scores!"