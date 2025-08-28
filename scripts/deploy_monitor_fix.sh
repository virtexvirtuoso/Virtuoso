#!/bin/bash

# Deploy monitor.py fix to VPS
echo "🚀 Deploying monitor.py fix to VPS..."

# VPS connection details
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Local file path
LOCAL_FILE="/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/monitoring/monitor.py"

# Check if local file exists
if [ ! -f "$LOCAL_FILE" ]; then
    echo "❌ Error: Local monitor.py not found at $LOCAL_FILE"
    exit 1
fi

echo "📦 Creating backup on VPS..."
ssh ${VPS_USER}@${VPS_HOST} "cp ${VPS_PATH}/src/monitoring/monitor.py ${VPS_PATH}/src/monitoring/monitor.py.backup_$(date +%Y%m%d_%H%M%S)"

echo "📤 Uploading fixed monitor.py to VPS..."
scp "$LOCAL_FILE" ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/monitoring/monitor.py

if [ $? -eq 0 ]; then
    echo "✅ File uploaded successfully"
else
    echo "❌ Failed to upload file"
    exit 1
fi

echo "🔄 Restarting virtuoso service..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl restart virtuoso.service"

echo "⏳ Waiting for service to start..."
sleep 5

echo "📊 Checking service status..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl status virtuoso.service --no-pager | head -20"

echo ""
echo "📝 Recent logs (checking for AttributeError):"
ssh ${VPS_USER}@${VPS_HOST} "sudo journalctl -u virtuoso.service --since '1 minute ago' --no-pager | grep -E '(AttributeError|metrics_manager|start_operation|ERROR)' | tail -20"

echo ""
echo "✅ Deployment complete! Monitor the service with:"
echo "   ssh ${VPS_USER}@${VPS_HOST} 'sudo journalctl -u virtuoso.service -f'"