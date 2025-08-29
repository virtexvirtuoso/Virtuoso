#!/bin/bash

# Fix VPS environment variables issue
# This script updates the systemd service to load the .env file

set -e

echo "🔧 Fixing VPS Environment Variables"
echo "=================================="

# Create backup of current service file
echo "Creating backup of systemd service file..."
sudo cp /etc/systemd/system/virtuoso.service /etc/systemd/system/virtuoso.service.bak.$(date +%Y%m%d_%H%M%S)

# Create updated service file with EnvironmentFile
cat << 'EOF' | sudo tee /etc/systemd/system/virtuoso.service
[Unit]
Description=Virtuoso Trading System
After=network.target
Conflicts=virtuoso.service

[Service]
Type=simple
User=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
Environment="PATH=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/home/linuxuser/trading/Virtuoso_ccxt/.env

# Use a lock file to prevent multiple instances
ExecStartPre=/bin/bash -c 'if [ -f /tmp/virtuoso.lock ]; then PID=$(cat /tmp/virtuoso.lock); if ps -p $PID > /dev/null; then echo "Already running with PID $PID"; exit 1; fi; fi'
ExecStartPre=/bin/bash -c 'echo $$ > /tmp/virtuoso.lock'
ExecStartPre=/bin/bash -c 'sudo lsof -ti:8003 | xargs -r sudo kill -9 || true'
ExecStartPre=/bin/sleep 2

ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python -u src/main.py

ExecStopPost=/bin/rm -f /tmp/virtuoso.lock

# Restart configuration
Restart=on-failure
RestartSec=30
StartLimitBurst=3
StartLimitInterval=300

# Resource limits
MemoryMax=2G
CPUQuota=80%

# Logging
StandardOutput=journal+console
StandardError=journal+console
SyslogIdentifier=virtuoso

# Timeout for starting/stopping
TimeoutStartSec=300
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Updated systemd service file with EnvironmentFile directive"

# Reload systemd configuration
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "✅ Systemd daemon reloaded"

# Stop current service
echo "Stopping virtuoso service..."
sudo systemctl stop virtuoso.service || true

echo "Waiting for service to stop..."
sleep 5

# Start service with new configuration
echo "Starting virtuoso service with new configuration..."
sudo systemctl start virtuoso.service

echo "Checking service status..."
sudo systemctl is-active virtuoso.service && echo "✅ Service is active" || echo "❌ Service failed to start"

echo ""
echo "🔧 Environment Fix Complete!"
echo "============================="
echo "The service should now load API credentials from .env file"
echo "Monitor logs with: sudo journalctl -u virtuoso.service -f"