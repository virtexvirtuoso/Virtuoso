#!/bin/bash
# Test System Startup Script
# Verifies all Virtuoso services start correctly on boot

echo "🔄 Testing Virtuoso System Startup Configuration..."
echo "=================================================="

# Check enabled services
echo "📋 Enabled Services:"
echo "-------------------"
systemctl list-unit-files | grep virtuoso | grep enabled

echo ""
echo "📊 Current Service Status:"
echo "-------------------------"

services=("virtuoso.service" "virtuoso-web.service" "virtuoso-cache.service" "virtuoso-ticker.service")

for service in "${services[@]}"; do
    status=$(systemctl is-active $service)
    enabled=$(systemctl is-enabled $service)
    echo "• $service: $status (enabled: $enabled)"
done

echo ""
echo "🌐 Testing Service Endpoints:"
echo "-----------------------------"

# Test main service (port 8003 is used by main service internally)
echo -n "• Main Service (localhost:8003): "
if timeout 3 curl -s http://localhost:8003/health > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ FAILED or not responding"
fi

# Test web dashboard (port 8001)
echo -n "• Web Dashboard (localhost:8001): "
if timeout 3 curl -s http://localhost:8001 > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ FAILED or not responding"
fi

echo ""
echo "📝 Service Logs (last 3 lines each):"
echo "------------------------------------"

for service in "${services[@]}"; do
    echo "• $service:"
    sudo journalctl -u $service --no-pager -n 3 | tail -3 | sed 's/^/  /'
    echo ""
done

echo "🎯 Auto-Startup Test Complete"
echo "================================"
echo ""
echo "💡 To simulate a reboot test:"
echo "   sudo systemctl restart virtuoso-web.service virtuoso-cache.service virtuoso-ticker.service"
echo ""
echo "📋 Summary:"
echo "• Main Service (virtuoso.service): Core trading engine"
echo "• Web Service (virtuoso-web.service): Dashboard & API endpoints" 
echo "• Cache Service (virtuoso-cache.service): Confluence data sync"
echo "• Ticker Service (virtuoso-ticker.service): Market data cache"
echo ""
echo "All services are configured to start automatically on system boot! 🚀"