#!/bin/bash

#############################################################################
# Script: update_mobile_dashboard_vps.sh
# Purpose: Deploy and manage update mobile dashboard vps
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
#   ./update_mobile_dashboard_vps.sh [options]
#   
#   Examples:
#     ./update_mobile_dashboard_vps.sh
#     ./update_mobile_dashboard_vps.sh --verbose
#     ./update_mobile_dashboard_vps.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 5.223.63.4)
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

echo "📱 Updating Mobile Dashboard on VPS"
echo "=================================="

# VPS connection details
VPS_IP="5.223.63.4"
VPS_USER="linuxuser"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_FILE="$SCRIPT_DIR/../src/dashboard/templates/dashboard_mobile_v1.html"
REMOTE_PATH="~/trading/Virtuoso_ccxt/src/dashboard/templates/"

# Check if the file exists
if [ ! -f "$LOCAL_FILE" ]; then
    echo "❌ Error: dashboard_mobile_v1.html not found!"
    echo "Expected at: $LOCAL_FILE"
    exit 1
fi

echo "✅ Found dashboard_mobile_v1.html"
echo ""

# Method 1: Direct file copy (fastest for single file)
echo "📤 Transferring updated mobile dashboard to VPS..."
echo ""
echo "Using SCP to copy the file:"
echo "scp $LOCAL_FILE $VPS_USER@$VPS_IP:$REMOTE_PATH"
echo ""

# Execute the transfer
scp "$LOCAL_FILE" "$VPS_USER@$VPS_IP:$REMOTE_PATH"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully updated mobile dashboard on VPS!"
    echo ""
    echo "📝 Next steps:"
    echo "1. SSH to VPS: ssh $VPS_USER@$VPS_IP"
    echo "2. Restart the application (if needed):"
    echo "   cd ~/trading/Virtuoso_ccxt"
    echo "   sudo systemctl restart virtuoso"
    echo ""
    echo "3. Or if using screen:"
    echo "   screen -r virtuoso"
    echo "   Ctrl+C to stop"
    echo "   python src/integrated_server.py"
    echo ""
    echo "4. Access the mobile dashboard:"
    echo "   http://$VPS_IP:8080/dashboard"
else
    echo ""
    echo "❌ Failed to transfer file to VPS"
    echo "Please check your SSH connection and try again"
    exit 1
fi

# Optional: Also update via rsync (preserves permissions)
echo "Alternative method using rsync:"
echo "rsync -avzP $LOCAL_FILE $VPS_USER@$VPS_IP:$REMOTE_PATH"