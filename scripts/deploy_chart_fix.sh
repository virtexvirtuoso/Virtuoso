#!/bin/bash

echo "Deploying chart inclusion fix to VPS..."

# Save local changes
echo "Saving local changes..."
git add -A

# Deploy fixed files to VPS
echo "Copying fixed files to VPS..."
scp src/signal_generation/signal_generator.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/signal_generation/
scp src/monitoring/alert_manager.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/

# Restart the service on VPS
echo "Restarting trading service on VPS..."
ssh vps "sudo systemctl restart virtuoso-trading.service"

# Wait for service to stabilize
echo "Waiting for service to stabilize..."
sleep 10

# Check service status
echo "Checking service status..."
ssh vps "sudo systemctl status virtuoso-trading.service | grep -A3 'Active:'"

echo "Deployment complete! Charts should now be included in alerts."
