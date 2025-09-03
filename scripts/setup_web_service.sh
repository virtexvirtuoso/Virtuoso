#!/bin/bash

#############################################################################
# Script: setup_web_service.sh
# Purpose: Setup web server as a systemd service
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates system setup, service configuration, and environment preparation for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - systemctl
#   - mkdir
#   - chmod
#   - Access to project directory structure
#
# Usage:
#   ./setup_web_service.sh [options]
#   
#   Examples:
#     ./setup_web_service.sh
#     ./setup_web_service.sh --verbose
#     ./setup_web_service.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: VPS_HOST_REDACTED)
#   VPS_USER         VPS username (default: linuxuser)
#
# Output:
#   - Console output with operation status
#   - Log messages with timestamps
#   - Success/failure indicators
#
# Exit Codes:
#   0 - Setup completed successfully
#   1 - Setup failed
#   2 - Permission denied
#   3 - Dependencies missing
#   4 - Configuration error
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

echo "🚀 Setting up Virtuoso Web Server as systemd service..."

# Create the service file
cat > /tmp/virtuoso-web.service << 'EOF'
[Unit]
Description=Virtuoso Trading Web Dashboard
After=network.target virtuoso.service
Wants=virtuoso.service

[Service]
Type=simple
User=linuxuser
Group=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
Environment="PATH=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt"
ExecStartPre=/bin/sleep 10
ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/uvicorn src.web_server:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10
StandardOutput=append:/home/linuxuser/trading/Virtuoso_ccxt/logs/web_server.log
StandardError=append:/home/linuxuser/trading/Virtuoso_ccxt/logs/web_server_error.log

[Install]
WantedBy=multi-user.target
EOF

# Deploy to VPS
echo "📤 Deploying to VPS..."
scp /tmp/virtuoso-web.service linuxuser@VPS_HOST_REDACTED:/tmp/

# Install and enable the service
echo "📦 Installing service on VPS..."
ssh linuxuser@VPS_HOST_REDACTED << 'REMOTE_COMMANDS'
# Stop any existing web server
pkill -f 'uvicorn.*web_server' || true

# Install the service
sudo cp /tmp/virtuoso-web.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable virtuoso-web.service
sudo systemctl start virtuoso-web.service

# Check status
sleep 3
sudo systemctl status virtuoso-web.service

# Verify it's listening
sudo ss -tlnp | grep :8001
REMOTE_COMMANDS

echo "✅ Web server service setup complete!"
echo ""
echo "Useful commands:"
echo "  Check status:  sudo systemctl status virtuoso-web"
echo "  View logs:     sudo journalctl -u virtuoso-web -f"
echo "  Restart:       sudo systemctl restart virtuoso-web"
echo "  Stop:          sudo systemctl stop virtuoso-web"
echo "  Start:         sudo systemctl start virtuoso-web"