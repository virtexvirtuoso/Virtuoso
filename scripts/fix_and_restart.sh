#!/bin/bash

VPS_HOST="45.77.40.77"
VPS_USER="linuxuser"

echo "Fixing cache adapter import issue..."

# Clear all Python cache
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Clear ALL pycache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Kill web server
pkill -f web_server.py || true
sleep 2

# Start fresh
export PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt
export PYTHONDONTWRITEBYTECODE=1
nohup venv311/bin/python src/web_server.py > logs/web_fresh.log 2>&1 &

sleep 5

if pgrep -f web_server.py > /dev/null; then
    echo "✅ Web server restarted fresh"
else
    echo "❌ Failed to start"
    tail -20 logs/web_fresh.log
fi
EOF

echo "Testing endpoints..."
sleep 3

# Test
curl -s http://${VPS_HOST}:8001/api/dashboard-cached/signals | python3 -c "
import sys, json
data = json.load(sys.stdin)
signals = len(data.get('signals', []))
print(f'Cached signals: {signals}')
if signals > 0:
    print('  ✅ SIGNALS WORKING!')
else:
    print('  ❌ Still empty')
"

curl -s http://${VPS_HOST}:8001/api/dashboard-cached/mobile-data | python3 -c "
import sys, json
data = json.load(sys.stdin)
scores = len(data.get('confluence_scores', []))
print(f'Mobile confluence scores: {scores}')
if scores > 0:
    print('  ✅ MOBILE SCORES WORKING!')
"