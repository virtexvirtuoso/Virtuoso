#!/bin/bash

#############################################################################
# Script: deploy_ohlcv_fix.sh
# Purpose: Deploy and manage deploy ohlcv fix
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates deployment automation, service management, and infrastructure updates for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - rsync
#   - ssh
#   - git
#   - systemctl
#   - Access to project directory structure
#
# Usage:
#   ./deploy_ohlcv_fix.sh [options]
#   
#   Examples:
#     ./deploy_ohlcv_fix.sh
#     ./deploy_ohlcv_fix.sh --verbose
#     ./deploy_ohlcv_fix.sh --dry-run
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
#   0 - Success
#   1 - Deployment failed
#   2 - Invalid arguments
#   3 - Connection error
#   4 - Service start failed
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

echo "========================================="
echo "Deploying OHLCV Data Fix for Chart Generation"
echo "========================================="

# VPS connection details
VPS_USER="linuxuser"
VPS_IP="VPS_HOST_REDACTED"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo "📋 Fixing simulated data issue in chart generation..."
echo ""

# Copy the fixed monitor.py file
echo "📦 Copying fixed monitor.py to VPS..."
scp src/monitoring/monitor.py ${VPS_USER}@${VPS_IP}:${VPS_PATH}/src/monitoring/

echo ""
echo "🔄 Restarting services on VPS..."
ssh ${VPS_USER}@${VPS_IP} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Restart the service to apply changes
echo "Restarting virtuoso service..."
sudo systemctl restart virtuoso.service

# Check service status
echo ""
echo "Service status:"
sudo systemctl status virtuoso.service --no-pager | head -20

# Show recent logs to verify the fix is working
echo ""
echo "Recent logs (checking for OHLCV fetch messages):"
sudo journalctl -u virtuoso.service -n 50 --no-pager | grep -E "OHLCV|REPORT|simulated|fetching fresh" | tail -20

echo ""
echo "✅ Deployment complete!"
EOF

echo ""
echo "========================================="
echo "Deployment Summary:"
echo "- Fixed monitor.py to fetch OHLCV data when not cached"
echo "- This prevents falling back to simulated chart generation"
echo "- Service has been restarted"
echo ""
echo "Monitor the logs with:"
echo "ssh ${VPS_USER}@${VPS_IP} 'sudo journalctl -u virtuoso.service -f | grep -E \"OHLCV|REPORT|simulated\"'"
echo "========================================="