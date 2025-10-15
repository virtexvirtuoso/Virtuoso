#!/bin/bash

echo "🔧 CRITICAL: Fix Persistent aiohttp Session Errors"
echo "================================================"
echo "Problem: CCXT aiohttp sessions are stuck in closed state"
echo "Solution: Hard restart with session cleanup"
echo ""

echo "📊 Current session errors in recent logs:"
journalctl -u virtuoso-trading.service --since '2 minutes ago' | grep -E "(Session is closed|RuntimeError)" | head -3

echo ""
echo "🛑 Stopping virtuoso-trading.service completely..."
sudo systemctl stop virtuoso-trading.service

echo "⏳ Waiting 15 seconds for complete cleanup..."
sleep 15

echo "💀 Ensuring all Python processes are terminated..."
# Kill any remaining Python trading processes
sudo pkill -f "python.*main.py" || true
sudo pkill -f "python.*web_server.py" || true

echo "⏳ Waiting 5 seconds for process cleanup..."
sleep 5

echo "🔄 Starting virtuoso-trading.service with fresh sessions..."
sudo systemctl start virtuoso-trading.service

echo "⏳ Waiting 20 seconds for full initialization..."
sleep 20

echo "🔍 Checking service status..."
sudo systemctl status virtuoso-trading.service --no-pager -l | head -10

echo ""
echo "📊 Monitoring new logs for session health (looking for successful operations)..."
sleep 10

echo "Looking for successful data fetches (should indicate session is working)..."
if journalctl -u virtuoso-trading.service --since '30 seconds ago' | grep -E "(Successfully|✅)" | head -3; then
    echo ""
    echo "✅ GOOD: Found successful operations in logs"
else
    echo ""
    echo "⚠️  No successful operations detected yet, checking for session errors..."
fi

echo ""
echo "🔍 Checking if session errors persist..."
if journalctl -u virtuoso-trading.service --since '30 seconds ago' | grep -q "Session is closed"; then
    echo "❌ FAILED: Session errors still present"
    echo "💡 This suggests a deeper issue with CCXT session initialization"
    echo ""
    echo "Manual intervention required:"
    echo "1. Check CCXT version compatibility"
    echo "2. Review aiohttp session configuration"
    echo "3. Consider temporary workaround with session retry logic"
else
    echo "✅ SUCCESS: No session errors detected in recent logs!"
    echo "🎉 Service restart with session cleanup was successful"
fi

echo ""
echo "📈 SESSION RESTART FIX SUMMARY:"
echo "Action Taken: Hard service restart with process cleanup"
echo "Expected Result: Fresh aiohttp sessions initialized"
echo "Service Status: $(sudo systemctl is-active virtuoso-trading.service)"
echo ""
echo "✅ Session Restart Fix Complete"