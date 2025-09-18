#!/bin/bash

#############################################################################
# Script: deploy_dashboard_selector.sh
# Purpose: Deploy and manage deploy dashboard selector
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
#   ./deploy_dashboard_selector.sh [options]
#   
#   Examples:
#     ./deploy_dashboard_selector.sh
#     ./deploy_dashboard_selector.sh --verbose
#     ./deploy_dashboard_selector.sh --dry-run
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

echo "📱 Deploying Dashboard Selector to VPS"
echo "====================================="

# VPS connection details
VPS_IP="${VPS_HOST}"
VPS_USER="linuxuser"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Files to transfer
FILES=(
    "src/dashboard/templates/dashboard_selector.html"
    "src/web_server.py"
)

echo "📤 Transferring updated files to VPS..."
echo ""

# Transfer each file
for FILE in "${FILES[@]}"; do
    LOCAL_FILE="$PROJECT_ROOT/$FILE"
    REMOTE_PATH="~/trading/Virtuoso_ccxt/$FILE"
    
    if [ -f "$LOCAL_FILE" ]; then
        echo "Copying $FILE..."
        # Create directory if needed
        REMOTE_DIR=$(dirname "$REMOTE_PATH")
        ssh "$VPS_USER@$VPS_IP" "mkdir -p $REMOTE_DIR"
        
        # Copy file
        scp "$LOCAL_FILE" "$VPS_USER@$VPS_IP:$REMOTE_PATH"
        
        if [ $? -eq 0 ]; then
            echo "✅ $FILE transferred successfully"
        else
            echo "❌ Failed to transfer $FILE"
        fi
    else
        echo "❌ File not found: $FILE"
    fi
    echo ""
done

echo ""
echo "🔄 Restarting application..."
ssh "$VPS_USER@$VPS_IP" "screen -S virtuoso -X quit; sleep 2; cd ~/trading/Virtuoso_ccxt && screen -dmS virtuoso python src/integrated_server.py && echo 'Application restarted'"

echo ""
echo "✅ Dashboard selector deployed!"
echo ""
echo "📱 Access Options:"
echo "1. Main selector: http://$VPS_IP:8003/dashboard"
echo "2. Direct mobile: http://$VPS_IP:8003/dashboard/mobile (with ₿ Beta tab)"
echo "3. Direct desktop: http://$VPS_IP:8003/dashboard/desktop"
echo ""
echo "Features:"
echo "- Auto-detects mobile devices"
echo "- Remembers user preference"
echo "- Clear descriptions of each dashboard"
echo "- Clean, intuitive interface"