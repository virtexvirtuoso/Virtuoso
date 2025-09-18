#!/bin/bash

echo "Deploying Bybit connector fix to VPS..."

# Save local changes
echo "Saving local changes..."
git add -A

# Deploy fixed bybit.py to VPS
echo "Copying fixed bybit.py to VPS..."
scp src/core/exchanges/bybit.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/core/exchanges/

# Restart the service on VPS
echo "Restarting trading service on VPS..."
ssh vps "sudo systemctl restart virtuoso-trading.service"

# Wait for service to stabilize
echo "Waiting for service to stabilize..."
sleep 10

# Check service status
echo "Checking service status..."
ssh vps "sudo systemctl status virtuoso-trading.service | grep -A3 'Active:'"

# Monitor for connector errors
echo "Monitoring for connector errors (should see retry messages if errors occur)..."
ssh vps "sudo journalctl -u virtuoso-trading.service -f | grep -E 'Connector.*closed|Retrying.*after session recreation|session.*recreat|Max retries' --line-buffered | head -20"

echo "Deployment complete! Bybit connector should now handle closed connections with retry logic."