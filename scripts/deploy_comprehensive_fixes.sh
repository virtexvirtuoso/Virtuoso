#!/bin/bash

# Deploy comprehensive fixes to VPS
# This script deploys all the recent fixes to resolve system issues

set -e

echo "🚀 Deploying Comprehensive System Fixes to VPS"
echo "=============================================="

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    echo "❌ ERROR: Must run from Virtuoso_ccxt root directory"
    exit 1
fi

echo "📦 Copying fixed files to VPS..."

# Copy the AlertManagerRefactored fixes
echo "  → Copying src/monitoring/components/alerts/alert_manager_refactored.py"
scp src/monitoring/components/alerts/alert_manager_refactored.py linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/components/alerts/

# Copy the dependency injection fixes
echo "  → Copying src/core/di/registration.py"
scp src/core/di/registration.py linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/core/di/

echo "  → Copying src/monitoring/monitor_refactored.py"
scp src/monitoring/monitor_refactored.py linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/

echo "  → Copying src/main.py"
scp src/main.py linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/

echo "✅ All fixed files deployed successfully"

echo "🔄 Restarting VPS service..."
ssh linuxuser@${VPS_HOST} "sudo systemctl restart virtuoso.service"

echo "⏱️  Waiting for service to start..."
sleep 15

echo "🩺 Checking service status..."
if ssh linuxuser@${VPS_HOST} "sudo systemctl is-active virtuoso.service" | grep -q "active"; then
    echo "✅ Service is running"
else
    echo "❌ Service failed to start"
    echo "📋 Service logs:"
    ssh linuxuser@${VPS_HOST} "sudo journalctl -u virtuoso.service --lines=30 --no-pager"
    exit 1
fi

echo ""
echo "🎉 Comprehensive Deployment Complete!"
echo "===================================="
echo "✅ Fixed AlertManagerRefactored interface compatibility"
echo "✅ Fixed dependency injection initialization warnings"
echo "✅ Fixed health check system integration"
echo "✅ Fixed OHLCV 'unhashable type dict' error"
echo "✅ Fixed metrics_tracker NoneType error"
echo "✅ Service restarted successfully"
echo ""
echo "📊 Monitor the system with:"
echo "   ssh linuxuser@${VPS_HOST} 'sudo journalctl -u virtuoso.service -f'"
echo ""
echo "🧪 Test the system with:"
echo "   curl http://${VPS_HOST}:8003/api/dashboard/data"
echo "   curl http://${VPS_HOST}:8003/health"
echo ""
echo "🔍 Check for error resolution:"
echo "   ssh linuxuser@${VPS_HOST} 'sudo journalctl -u virtuoso.service --since=\"1 minute ago\" | grep -E \"(ERROR|WARNING|✅|SUCCESS)\"'"