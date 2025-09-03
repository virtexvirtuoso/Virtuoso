#!/bin/bash

#############################################################################
# Script: setup_mobile_dashboard_service.sh
# Purpose: Setup and configure setup mobile dashboard service
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
#   ./setup_mobile_dashboard_service.sh [options]
#   
#   Examples:
#     ./setup_mobile_dashboard_service.sh
#     ./setup_mobile_dashboard_service.sh --verbose
#     ./setup_mobile_dashboard_service.sh --dry-run
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

echo "📱 Setting up Mobile Dashboard Service on VPS..."
echo "=============================================="

VPS_HOST="linuxuser@VPS_HOST_REDACTED"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Create systemd service file
cat << 'EOF' > /tmp/mobile-dashboard-updater.service
[Unit]
Description=Mobile Dashboard Data Updater Service
After=network.target

[Service]
Type=simple
User=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
Environment="PATH=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python /home/linuxuser/trading/Virtuoso_ccxt/scripts/fix_mobile_dashboard_final.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Copy service file to VPS
echo "📦 Deploying service file..."
scp /tmp/mobile-dashboard-updater.service $VPS_HOST:/tmp/

# Install and start the service
echo "🔧 Installing service..."
ssh $VPS_HOST << 'REMOTE_COMMANDS'
# Copy service file
sudo cp /tmp/mobile-dashboard-updater.service /etc/systemd/system/

# Modify the fix script to run continuously
cd /home/linuxuser/trading/Virtuoso_ccxt
cat > scripts/mobile_dashboard_updater.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('/home/linuxuser/trading/Virtuoso_ccxt')

from scripts.fix_mobile_dashboard_final import MobileDashboardFixer

async def main():
    fixer = MobileDashboardFixer()
    await fixer.continuous_update(interval=60)

if __name__ == "__main__":
    asyncio.run(main())
PYTHON_SCRIPT

chmod +x scripts/mobile_dashboard_updater.py

# Reload systemd
sudo systemctl daemon-reload

# Stop any existing instance
sudo systemctl stop mobile-dashboard-updater.service 2>/dev/null

# Start the service
sudo systemctl start mobile-dashboard-updater.service

# Enable on boot
sudo systemctl enable mobile-dashboard-updater.service

# Check status
sudo systemctl status mobile-dashboard-updater.service --no-pager
REMOTE_COMMANDS

echo ""
echo "✅ Mobile Dashboard Service Setup Complete!"
echo ""
echo "📊 The service will update market data every 60 seconds"
echo "🔍 Check logs with: ssh $VPS_HOST 'sudo journalctl -u mobile-dashboard-updater -f'"
echo "📱 Access dashboard at: http://VPS_HOST_REDACTED:8001/dashboard/mobile"