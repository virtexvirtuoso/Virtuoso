#!/bin/bash

echo "🔧 Deploying WebSocket timeout fix to VPS..."

# Copy the fix script to VPS
echo "📤 Copying fix script to VPS..."
scp scripts/fix_websocket_timeout.py linuxuser@45.77.40.77:/tmp/

# Run the fix on VPS
echo "🔨 Applying WebSocket timeout fix..."
ssh linuxuser@45.77.40.77 << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt
python3 /tmp/fix_websocket_timeout.py

# Restart the service to apply changes
echo "🔄 Restarting virtuoso service..."
sudo systemctl restart virtuoso.service

# Wait for service to start
sleep 5

# Check service status
echo "📊 Service status:"
sudo systemctl status virtuoso.service --no-pager | head -20

# Check for WebSocket errors in recent logs
echo ""
echo "📋 Recent WebSocket logs:"
sudo journalctl -u virtuoso.service --since "1 minute ago" | grep -i "websocket\|timeout" | tail -10

# Clean up
rm /tmp/fix_websocket_timeout.py
EOF

echo "✅ WebSocket timeout fix deployed successfully!"