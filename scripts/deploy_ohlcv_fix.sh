#!/bin/bash

echo "Deploying OHLCV chart fix to VPS..."

# Save local changes
echo "Saving local changes..."
git add -A

# Deploy fixed files to VPS
echo "Copying fixed files to VPS..."
scp src/data_processing/data_processor.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/data_processing/
scp src/signal_generation/signal_generator.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/signal_generation/

# Restart the service on VPS
echo "Restarting trading service on VPS..."
ssh vps "sudo systemctl restart virtuoso-trading.service"

# Wait for service to stabilize
echo "Waiting for service to stabilize..."
sleep 10

# Check service status
echo "Checking service status..."
ssh vps "sudo systemctl status virtuoso-trading.service | grep -A3 'Active:'"

# Monitor for charts in alerts
echo "Monitoring for charts being included in alerts..."
ssh vps "sudo journalctl -u virtuoso-trading.service -f | grep -E 'chart_path|OHLCV|Generated report|PDF' --line-buffered | head -20"

echo "Deployment complete! OHLCV data should now flow from market_data_manager to charts."
