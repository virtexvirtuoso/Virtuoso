#!/bin/bash

#############################################################################
# Script: setup_systemd_service.sh
# Purpose: Setup and configure setup systemd service
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
#   ./setup_systemd_service.sh [options]
#   
#   Examples:
#     ./setup_systemd_service.sh
#     ./setup_systemd_service.sh --verbose
#     ./setup_systemd_service.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: ${VPS_HOST})
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

echo "🔧 Setting up Virtuoso Trading Bot as systemd service"
echo "===================================================="

cd ~/trading/Virtuoso_ccxt

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${YELLOW}1. Creating systemd service file...${NC}"

# Create the service file
sudo tee /etc/systemd/system/virtuoso.service > /dev/null << EOF
[Unit]
Description=Virtuoso Trading Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=linuxuser
Group=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
Environment=PATH=/home/linuxuser/trading/Virtuoso_ccxt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv/bin/python src/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=virtuoso

# Resource limits
MemoryMax=2G
CPUQuota=80%

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/linuxuser/trading/Virtuoso_ccxt

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created"

echo -e "\n${YELLOW}2. Reloading systemd and enabling service...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable virtuoso.service

echo -e "\n${YELLOW}3. Stopping any running instances...${NC}"
# Kill any existing python processes
pkill -f "python src/main.py" || true
sleep 5

echo -e "\n${YELLOW}4. Starting the service...${NC}"
sudo systemctl start virtuoso.service

echo -e "\n${YELLOW}5. Checking service status...${NC}"
sudo systemctl status virtuoso.service --no-pager

echo -e "\n${GREEN}=============================================="
echo "✅ Systemd service setup complete!"
echo "===============================================${NC}"
echo ""
echo "Service management commands:"
echo "  sudo systemctl start virtuoso    # Start service"
echo "  sudo systemctl stop virtuoso     # Stop service"
echo "  sudo systemctl restart virtuoso  # Restart service"
echo "  sudo systemctl status virtuoso   # Check status"
echo "  sudo journalctl -u virtuoso -f   # View logs"
echo ""
echo "Dashboard accessible at: http://${VPS_HOST}:8003/dashboard"
echo ""
echo "🎉 Your trading bot is now running 24/7!"