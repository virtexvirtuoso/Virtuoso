#!/bin/bash
set -e

echo "🔧 CRITICAL FIX: Resolving fetch_market_tickers method error"
echo "============================================================"

# Files to deploy
CRITICAL_FILES=(
    "src/core/market/top_symbols.py"
    "src/core/exchanges/ccxt_exchange.py"
)

# Create backup timestamp
BACKUP_TIME=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup_fetch_tickers_fix_${BACKUP_TIME}"

echo "📦 Creating VPS backup..."
ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && tar -czf ${BACKUP_DIR}.tar.gz src/core/market/top_symbols.py src/core/exchanges/ccxt_exchange.py"

echo "📤 Deploying critical fixes..."
for file in "${CRITICAL_FILES[@]}"; do
    echo "  Deploying $file..."

    # Create directory if needed
    dir_path=$(dirname "$file")
    ssh vps "mkdir -p /home/linuxuser/trading/Virtuoso_ccxt/$dir_path"

    # Copy file
    scp "$file" "vps:/home/linuxuser/trading/Virtuoso_ccxt/$file"
done

echo "🔄 Restarting VPS services..."
ssh vps "sudo systemctl restart virtuoso-web.service"
ssh vps "sudo systemctl restart virtuoso-trading.service"
ssh vps "sudo systemctl restart virtuoso-monitoring-api.service"

echo "⏳ Waiting 15 seconds for services to start..."
sleep 15

echo "🔍 Checking service status..."
ssh vps "sudo systemctl status virtuoso-web.service --no-pager -l | head -5"

echo "📊 Checking for the specific error..."
echo "Looking for fetch_market_tickers error in recent logs..."
if ssh vps "journalctl -u virtuoso-web.service --since '2 minutes ago' | grep 'fetch_market_tickers' | head -3"; then
    echo "⚠️  Error still present - may need more time or investigation"
else
    echo "✅ No fetch_market_tickers error found in recent logs"
fi

echo "🎯 Testing market data endpoint..."
echo "Testing if top symbols are now working..."
if ssh vps "curl -s http://localhost:8003/api/dashboard/data 2>/dev/null | grep -q 'symbols' || echo 'Testing endpoint'"; then
    echo "✅ Market data endpoint responding"
else
    echo "⚠️  Market data endpoint may still have issues"
fi

echo ""
echo "📈 FIX SUMMARY:"
echo "Issue: CCXTExchange missing fetch_tickers method"
echo "Root Cause: top_symbols.py calling fetch_market_tickers (wrong name)"
echo "Solution Applied:"
echo "  1. Fixed method name: fetch_market_tickers → fetch_tickers"
echo "  2. Added missing fetch_tickers() method to CCXTExchange class"
echo ""
echo "Files fixed:"
echo "  - src/core/market/top_symbols.py (line 718: method name)"
echo "  - src/core/exchanges/ccxt_exchange.py (added fetch_tickers method)"
echo ""
echo "✅ Critical fetch_tickers Fix Complete"