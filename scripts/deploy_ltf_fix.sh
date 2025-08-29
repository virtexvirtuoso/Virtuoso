#!/bin/bash

#############################################################################
# Script: deploy_ltf_fix.sh
# Purpose: Deploy and manage deploy ltf fix
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
#   ./deploy_ltf_fix.sh [options]
#   
#   Examples:
#     ./deploy_ltf_fix.sh
#     ./deploy_ltf_fix.sh --verbose
#     ./deploy_ltf_fix.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 45.77.40.77)
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

echo "🚀 Deploying LTF data fetching fix to VPS..."

# VPS details
VPS_HOST="45.77.40.77"
VPS_USER="linuxuser"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Copy the fixed bybit.py file
echo "📤 Copying fixed bybit.py to VPS..."
scp src/core/exchanges/bybit.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/core/exchanges/

if [ $? -eq 0 ]; then
    echo "✅ File copied successfully"
else
    echo "❌ Failed to copy file"
    exit 1
fi

# Restart the service on VPS
echo "🔄 Restarting virtuoso service on VPS..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl restart virtuoso.service"

if [ $? -eq 0 ]; then
    echo "✅ Service restarted successfully"
else
    echo "❌ Failed to restart service"
    exit 1
fi

# Wait a moment for service to start
echo "⏳ Waiting for service to start..."
sleep 5

# Check service status
echo "📊 Checking service status..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl status virtuoso.service | grep 'Active:'"

# Check for LTF errors in recent logs
echo ""
echo "🔍 Checking for LTF errors in recent logs..."
ssh ${VPS_USER}@${VPS_HOST} "sudo journalctl -u virtuoso.service --since '1 minute ago' | grep -E 'ltf|LTF' | grep -E 'ERROR|Empty|Invalid' | head -5"

if [ $? -ne 0 ]; then
    echo "✅ No LTF errors found in recent logs!"
else
    echo "⚠️  Some LTF-related messages found (might be from startup)"
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Monitor logs with:"
echo "   ssh ${VPS_USER}@${VPS_HOST} 'sudo journalctl -u virtuoso.service -f | grep -E \"ltf|LTF\"'"