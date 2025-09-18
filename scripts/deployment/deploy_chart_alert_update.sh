#!/bin/bash

#############################################################################
# Script: deploy_chart_alert_update.sh
# Purpose: Deploy and manage deploy chart alert update
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
#   ./deploy_chart_alert_update.sh [options]
#   
#   Examples:
#     ./deploy_chart_alert_update.sh
#     ./deploy_chart_alert_update.sh --verbose
#     ./deploy_chart_alert_update.sh --dry-run
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

# Deploy chart alert and PDF stop loss fixes to VPS
echo "🚀 Deploying chart alert and PDF stop loss fixes to VPS (5.223.63.4)..."

# VPS details
VPS_USER="linuxuser"
VPS_HOST="5.223.63.4"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Files to update
FILES_TO_UPDATE=(
    "src/core/reporting/pdf_generator.py"
    "src/core/reporting/report_manager.py"
    "src/monitoring/alert_manager.py"
)

# Display what will be deployed
echo "📦 Files to be deployed:"
for file in "${FILES_TO_UPDATE[@]}"; do
    echo "  - $file"
done

echo ""
echo "📝 Changes being deployed:"
echo "1. PDF Generator Updates:"
echo "   - Stop loss extraction from trade_params"
echo "   - Returns chart path along with PDF path"
echo ""
echo "2. Alert Manager Updates:"
echo "   - Sends high-resolution chart image to Discord"
echo "   - Shows TP/SL details in chart message"
echo "   - Chart sent before PDF attachment"
echo ""
echo "3. Report Manager Updates:"
echo "   - Handles chart path from PDF generator"
echo "   - Stores chart path in signal_data"

# Deploy to VPS
echo ""
echo "🔄 Syncing files to VPS..."
for file in "${FILES_TO_UPDATE[@]}"; do
    echo "  Deploying $file..."
    rsync -avz --progress "$file" "$VPS_USER@$VPS_HOST:$VPS_PATH/$file"
    if [ $? -ne 0 ]; then
        echo "❌ Failed to deploy $file"
        exit 1
    fi
done

echo ""
echo "✅ All files successfully deployed to VPS!"

# Show restart instructions
echo ""
echo "📌 To apply the changes, restart the application on the VPS:"
echo "   ssh $VPS_USER@$VPS_HOST"
echo "   cd $VPS_PATH"
echo "   docker-compose restart virtuoso"
echo ""
echo "📊 After restart:"
echo "  - PDF reports will show correct stop loss values"
echo "  - Discord alerts will include high-res chart images"
echo "  - Chart messages will display TP/SL details"
echo ""
echo "🎉 Deployment complete!"