#!/bin/bash

echo "🚀 Deploying Bybit timeout fix to VPS..."

# VPS connection details
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Copy the fixed bybit.py file
echo "📦 Copying fixed bybit.py to VPS..."
scp src/core/exchanges/bybit.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/core/exchanges/

# Restart the service
echo "🔄 Restarting virtuoso service..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl restart virtuoso.service"

# Wait a moment for service to start
sleep 5

# Check service status
echo "✅ Checking service status..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl status virtuoso.service --no-pager"

# Check recent logs
echo ""
echo "📋 Recent logs:"
ssh ${VPS_USER}@${VPS_HOST} "sudo journalctl -u virtuoso.service --since '1 minute ago' --no-pager | tail -30"

echo ""
echo "✅ Deployment complete!"