#!/bin/bash

echo "Deploying full reliability fix to VPS..."

# Save local changes
echo "Saving local changes..."
git add -A

# Deploy both fixed files to VPS
echo "Copying fixed files to VPS..."
scp src/monitoring/signal_processor.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/
scp src/core/analysis/confluence.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/core/analysis/

# Restart the service on VPS
echo "Restarting trading service on VPS..."
ssh vps "sudo systemctl restart virtuoso-trading.service"

# Wait for service to stabilize
echo "Waiting for service to stabilize..."
sleep 5

# Check service status
echo "Checking service status..."
ssh vps "sudo systemctl status virtuoso-trading.service | grep -A3 'Active:'"

echo "Deployment complete! Monitoring for properly formatted alerts..."
