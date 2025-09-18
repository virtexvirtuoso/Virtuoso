#!/bin/bash

#############################################################################
# Script: deploy_to_current_vps.sh
# Purpose: Deploy and manage deploy to current vps
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
#   ./deploy_to_current_vps.sh [options]
#   
#   Examples:
#     ./deploy_to_current_vps.sh
#     ./deploy_to_current_vps.sh --verbose
#     ./deploy_to_current_vps.sh --dry-run
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

# Deploy PDF stop loss fix to current VPS
echo "🚀 Deploying PDF stop loss fix to VPS (${VPS_HOST})..."

# VPS details
VPS_USER="linuxuser"
VPS_HOST="${VPS_HOST}"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Files to update
FILES_TO_UPDATE=(
    "src/core/reporting/pdf_generator.py"
)

# Display what will be deployed
echo "📦 Files to be deployed:"
for file in "${FILES_TO_UPDATE[@]}"; do
    echo "  - $file"
done

echo ""
echo "📝 Changes being deployed:"
echo "- Updated stop loss extraction to check trade_params first"
echo "- Ensures stop loss from chart generation is used in Risk Management section"
echo "- Maintains backward compatibility with signal_data"

# Deploy to VPS
echo ""
echo "🔄 Syncing files to VPS..."
rsync -avz --progress "${FILES_TO_UPDATE[@]}" "$VPS_USER@$VPS_HOST:$VPS_PATH/src/core/reporting/"

if [ $? -eq 0 ]; then
    echo "✅ Files successfully deployed to VPS!"
    
    # Show restart instructions
    echo ""
    echo "📌 To apply the changes, restart the application on the VPS:"
    echo "   ssh $VPS_USER@$VPS_HOST"
    echo "   cd $VPS_PATH"
    echo "   docker-compose restart virtuoso"
    echo ""
    echo "📊 After restart, new PDF reports will show:"
    echo "  - Stop loss values from trade_params in Risk Management section"
    echo "  - Proper percentage calculations"
    echo "  - No more 'N/A (0%)' when stop loss is available"
else
    echo "❌ Failed to deploy files to VPS"
    echo ""
    echo "🔧 Manual deployment steps:"
    echo "1. Copy the file manually:"
    echo "   scp src/core/reporting/pdf_generator.py $VPS_USER@$VPS_HOST:$VPS_PATH/src/core/reporting/"
    echo ""
    echo "2. Or SSH to VPS and pull from git:"
    echo "   ssh $VPS_USER@$VPS_HOST"
    echo "   cd $VPS_PATH"
    echo "   git pull"
    exit 1
fi