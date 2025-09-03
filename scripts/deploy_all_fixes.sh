#!/bin/bash

# Deploy all fixes to VPS
# This script deploys the OHLCV and metrics_tracker fixes to the VPS

set -e

echo "🚀 Deploying OHLCV and Metrics Tracker Fixes to VPS"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    echo "❌ ERROR: Must run from Virtuoso_ccxt root directory"
    exit 1
fi

echo "📦 Copying fixed files to VPS..."

# Copy the fixed bybit.py file
echo "  → Copying src/core/exchanges/bybit.py"
scp src/core/exchanges/bybit.py linuxuser@VPS_HOST_REDACTED:/home/linuxuser/trading/Virtuoso_ccxt/src/core/exchanges/

# Copy the fixed monitor_refactored.py file
echo "  → Copying src/monitoring/monitor_refactored.py"
scp src/monitoring/monitor_refactored.py linuxuser@VPS_HOST_REDACTED:/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/

echo "✅ Files deployed successfully"

echo "🔄 Restarting VPS service..."
ssh linuxuser@VPS_HOST_REDACTED "sudo systemctl restart virtuoso.service"

echo "⏱️  Waiting for service to start..."
sleep 10

echo "🩺 Checking service status..."
if ssh linuxuser@VPS_HOST_REDACTED "sudo systemctl is-active virtuoso.service" | grep -q "active"; then
    echo "✅ Service is running"
else
    echo "❌ Service failed to start"
    echo "📋 Service logs:"
    ssh linuxuser@VPS_HOST_REDACTED "sudo journalctl -u virtuoso.service --lines=20 --no-pager"
    exit 1
fi

echo ""
echo "🎉 Deployment Complete!"
echo "======================"
echo "✅ Fixed OHLCV 'unhashable type dict' error"
echo "✅ Fixed metrics_tracker NoneType error"
echo "✅ Service restarted successfully"
echo ""
echo "📊 Monitor the system with:"
echo "   ssh linuxuser@VPS_HOST_REDACTED 'sudo journalctl -u virtuoso.service -f'"
echo ""
echo "🧪 Test the fixes with:"
echo "   curl http://VPS_HOST_REDACTED:8003/api/dashboard/data"