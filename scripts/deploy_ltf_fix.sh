#!/bin/bash

echo "🚀 Deploying LTF data fetching fix to VPS..."

# VPS details
VPS_HOST="45.77.40.77"
VPS_USER="linuxuser"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Copy the fixed bybit.py file
echo "📤 Copying fixed bybit.py to VPS..."
scp src/core/exchanges/bybit.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/core/exchanges/

if [ $? -eq 0 ]; then
    echo "✅ File copied successfully"
else
    echo "❌ Failed to copy file"
    exit 1
fi

# Restart the service on VPS
echo "🔄 Restarting virtuoso service on VPS..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl restart virtuoso.service"

if [ $? -eq 0 ]; then
    echo "✅ Service restarted successfully"
else
    echo "❌ Failed to restart service"
    exit 1
fi

# Wait a moment for service to start
echo "⏳ Waiting for service to start..."
sleep 5

# Check service status
echo "📊 Checking service status..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl status virtuoso.service | grep 'Active:'"

# Check for LTF errors in recent logs
echo ""
echo "🔍 Checking for LTF errors in recent logs..."
ssh ${VPS_USER}@${VPS_HOST} "sudo journalctl -u virtuoso.service --since '1 minute ago' | grep -E 'ltf|LTF' | grep -E 'ERROR|Empty|Invalid' | head -5"

if [ $? -ne 0 ]; then
    echo "✅ No LTF errors found in recent logs!"
else
    echo "⚠️  Some LTF-related messages found (might be from startup)"
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Monitor logs with:"
echo "   ssh ${VPS_USER}@${VPS_HOST} 'sudo journalctl -u virtuoso.service -f | grep -E \"ltf|LTF\"'"