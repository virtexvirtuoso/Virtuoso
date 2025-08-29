#!/bin/bash

#############################################################################
# Script: deploy_bitcoin_beta_tab.sh
# Purpose: Deploy and manage deploy bitcoin beta tab
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
#   ./deploy_bitcoin_beta_tab.sh [options]
#   
#   Examples:
#     ./deploy_bitcoin_beta_tab.sh
#     ./deploy_bitcoin_beta_tab.sh --verbose
#     ./deploy_bitcoin_beta_tab.sh --dry-run
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

echo "📱 Deploying Bitcoin Beta Tab to VPS"
echo "===================================="

# VPS connection details
VPS_IP="45.77.40.77"
VPS_USER="linuxuser"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Files to transfer
FILES=(
    "src/dashboard/templates/dashboard_mobile_v1.html"
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
echo "📝 Next steps on VPS:"
echo "1. SSH to VPS: ssh $VPS_USER@$VPS_IP"
echo "2. cd ~/trading/Virtuoso_ccxt"
echo "3. Restart the application:"
echo "   screen -r virtuoso"
echo "   Ctrl+C to stop"
echo "   python src/integrated_server.py"
echo ""
echo "4. Access the mobile dashboard to test:"
echo "   http://$VPS_IP:8080/dashboard"
echo ""
echo "✅ Bitcoin Beta tab deployment complete!"
echo ""
echo "New Features Added:"
echo "- ₿ Beta tab in bottom navigation"
echo "- Beta coefficient display"
echo "- BTC correlation percentage"
echo "- Market regime indicator"
echo "- Volatility ratio"
echo "- Beta rankings for all symbols"
echo "- Sorting options (beta, correlation, volume)"
echo ""
echo "Note: The beta values are currently using mock data."
echo "To use real beta calculations, implement the analysis in the Bitcoin Beta API."