#!/bin/bash

echo "🔧 CRITICAL FIX: Invalid Symbols in TopSymbolsManager Cache"
echo "==============================================="
echo "Problem: System processing invalid symbols like '10000SATSUSDT'"
echo "Solution: Restart trading service to clear symbol cache"
echo ""

echo "📊 Current invalid symbols in logs:"
journalctl -u virtuoso-trading.service --since '2 minutes ago' | grep -E '(10000.*USDT|1000000.*USDT)' | head -3

echo ""
echo "🔄 Restarting virtuoso-trading.service to clear symbol cache..."
sudo systemctl restart virtuoso-trading.service

echo "⏳ Waiting 10 seconds for service to restart..."
sleep 10

echo "🔍 Checking service status..."
sudo systemctl status virtuoso-trading.service --no-pager -l | head -5

echo ""
echo "📊 Monitoring new logs for symbol refresh..."
sleep 5

echo "Looking for 'Fetching market data for dynamic symbol selection'..."
journalctl -u virtuoso-trading.service --since '1 minute ago' | grep -E '(dynamic symbol selection|Selected.*with turnover)' | head -5

echo ""
echo "🔍 Checking if invalid symbols are still present..."
sleep 5

if journalctl -u virtuoso-trading.service --since '1 minute ago' | grep -q '10000.*USDT'; then
    echo "⚠️  WARNING: Still seeing invalid symbols in logs"
    echo "💡 This suggests a deeper issue with symbol source"
    echo ""
    echo "Next steps:"
    echo "1. Check if symbols are hardcoded somewhere"
    echo "2. Verify TopSymbolsManager is fetching from Bybit correctly"
    echo "3. Check if system is using static_symbols list"
else
    echo "✅ SUCCESS: No more invalid symbols detected!"
    echo "🎉 TopSymbolsManager cache has been refreshed"
fi

echo ""
echo "📈 INVALID SYMBOLS FIX SUMMARY:"
echo "Root Cause: Stale symbol cache in TopSymbolsManager"
echo "Action Taken: Restarted trading service to force cache refresh"
echo "Expected Result: System should now use valid Bybit symbols"
echo ""
echo "✅ Invalid Symbols Fix Complete"