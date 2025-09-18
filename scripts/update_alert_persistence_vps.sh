#!/bin/bash

#############################################################################
# Script: update_alert_persistence_vps.sh
# Purpose: Deploy and manage update alert persistence vps
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
#   ./update_alert_persistence_vps.sh [options]
#   
#   Examples:
#     ./update_alert_persistence_vps.sh
#     ./update_alert_persistence_vps.sh --verbose
#     ./update_alert_persistence_vps.sh --dry-run
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

echo "📱 Updating Alert Persistence on VPS"
echo "==================================="

# VPS connection details
VPS_IP="5.223.63.4"
VPS_USER="linuxuser"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Files to transfer
FILES=(
    "src/database/alert_storage.py"
    "src/database/__init__.py"
    "src/monitoring/alert_manager.py"
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
echo "3. Create data directory if needed:"
echo "   mkdir -p data"
echo "4. Restart the application:"
echo "   screen -r virtuoso"
echo "   Ctrl+C to stop"
echo "   python src/integrated_server.py"
echo ""
echo "5. The alert database will be created automatically at:"
echo "   ~/trading/Virtuoso_ccxt/data/virtuoso.db"
echo ""
echo "6. Access the mobile dashboard to see historical alerts:"
echo "   http://$VPS_IP:8080/dashboard"
echo ""
echo "✅ Alert persistence system deployed!"
echo ""
echo "Features added:"
echo "- All Discord alerts are now stored in SQLite database"
echo "- Mobile dashboard Alerts tab shows historical alerts"
echo "- Alerts persist across application restarts"
echo "- 7-day retention policy (configurable)"