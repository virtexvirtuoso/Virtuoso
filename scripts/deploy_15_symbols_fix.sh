#!/bin/bash

echo "🚀 Deploying configuration update to increase top symbols from 5 to 15..."

# Deploy the config file
echo "📤 Deploying updated config.yaml to VPS..."
scp config/config.yaml vps:/home/linuxuser/trading/Virtuoso_ccxt/config/

# Verify the change was applied
echo "✅ Verifying the change..."
ssh vps "grep 'max_symbols:' /home/linuxuser/trading/Virtuoso_ccxt/config/config.yaml"

# Restart the service
echo "🔄 Restarting trading service..."
ssh vps "sudo systemctl restart virtuoso-trading.service"

echo "⏳ Waiting for service to stabilize..."
sleep 5

# Check service status
echo "📊 Checking service status..."
ssh vps "systemctl status virtuoso-trading.service | head -10"

echo "📈 Monitoring symbol loading..."
ssh vps "journalctl -u virtuoso-trading.service --since '10 seconds ago' | grep -E 'symbols|Selected.*symbols|Monitoring.*symbols|max_symbols' | head -20"

echo "✅ Deployment complete! System now configured to monitor up to 15 symbols."