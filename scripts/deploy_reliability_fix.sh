#!/bin/bash

echo "Deploying reliability fix to VPS..."

# Save local changes
echo "Saving local changes..."
git add -A

# Deploy signal_processor.py fix to VPS
echo "Copying signal_processor.py to VPS..."
scp src/monitoring/signal_processor.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/

# Restart the service on VPS
echo "Restarting trading service on VPS..."
ssh vps "sudo systemctl restart virtuoso-trading.service"

# Check service status
echo "Checking service status..."
ssh vps "sudo systemctl status virtuoso-trading.service | grep -A3 'Active:'"

echo "Deployment complete! Monitoring for alerts..."
