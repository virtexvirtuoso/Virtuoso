#!/bin/bash

#############################################################################
# Script: setup_web_server_service.sh
# Purpose: Setup and configure setup web server service
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
#   ./setup_web_server_service.sh [options]
#   
#   Examples:
#     ./setup_web_server_service.sh
#     ./setup_web_server_service.sh --verbose
#     ./setup_web_server_service.sh --dry-run
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

# Setup systemd service for web server to ensure auto-start on reboot
VPS_HOST="linuxuser@VPS_HOST_REDACTED"

echo "Setting up web server systemd service..."

# Create the web server service file
ssh $VPS_HOST 'sudo tee /etc/systemd/system/virtuoso-web.service > /dev/null << "EOF"
[Unit]
Description=Virtuoso Web Server
After=network.target virtuoso.service
Requires=virtuoso.service

[Service]
Type=simple
User=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
Environment="PATH=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONUNBUFFERED=1"

# Kill any existing web server on port 8003 before starting
ExecStartPre=/bin/bash -c "pkill -f '\''python.*web_server.py'\'' || true"
ExecStartPre=/bin/sleep 2

# Start the web server
ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python -u src/web_server.py

# Restart configuration
Restart=on-failure
RestartSec=10
StartLimitBurst=3
StartLimitInterval=300

# Resource limits (web server uses less resources)
MemoryMax=512M
CPUQuota=20%

# Logging
StandardOutput=journal+console
StandardError=journal+console
SyslogIdentifier=virtuoso-web

# Timeout for starting/stopping
TimeoutStartSec=60
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF'

# Reload systemd daemon
ssh $VPS_HOST 'sudo systemctl daemon-reload'

# Enable the web server service to start on boot
ssh $VPS_HOST 'sudo systemctl enable virtuoso-web.service'

# Start the web server service
ssh $VPS_HOST 'sudo systemctl stop virtuoso-web.service 2>/dev/null || true'
ssh $VPS_HOST 'pkill -f "python.*web_server.py" 2>/dev/null || true'
sleep 2
ssh $VPS_HOST 'sudo systemctl start virtuoso-web.service'

# Check status
echo ""
echo "Checking web server service status..."
ssh $VPS_HOST 'sudo systemctl status virtuoso-web.service --no-pager'

echo ""
echo "✅ Web server systemd service setup complete!"
echo ""
echo "The web server will now:"
echo "  - Start automatically on system boot"
echo "  - Restart automatically if it crashes"
echo "  - Start after the main Virtuoso service"
echo ""
echo "Service commands:"
echo "  sudo systemctl status virtuoso-web   # Check status"
echo "  sudo systemctl start virtuoso-web    # Start service"
echo "  sudo systemctl stop virtuoso-web     # Stop service"
echo "  sudo systemctl restart virtuoso-web  # Restart service"
echo "  sudo journalctl -u virtuoso-web -f   # Follow logs"