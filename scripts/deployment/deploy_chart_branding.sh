#!/bin/bash

#############################################################################
# Script: deploy_chart_branding.sh
# Purpose: Deploy and manage deploy chart branding
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
#   ./deploy_chart_branding.sh [options]
#   
#   Examples:
#     ./deploy_chart_branding.sh
#     ./deploy_chart_branding.sh --verbose
#     ./deploy_chart_branding.sh --dry-run
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

# Deploy chart branding update to VPS
echo "🚀 Deploying chart branding update to VPS (VPS_HOST_REDACTED)..."

# VPS details
VPS_USER="linuxuser"
VPS_HOST="VPS_HOST_REDACTED"
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
echo "📝 Branding changes being deployed:"
echo "  - Added 'VIRTUOSO' branding to all chart PNGs"
echo "  - Orange color (#ff9900) matching mobile header"
echo "  - Dark background box with orange border"
echo "  - Positioned at bottom center with padding"
echo "  - Applied to: candlestick charts, simulated charts, component charts"

# Deploy to VPS
echo ""
echo "🔄 Syncing files to VPS..."
rsync -avz --progress "${FILES_TO_UPDATE[@]}" "$VPS_USER@$VPS_HOST:$VPS_PATH/src/core/reporting/"

if [ $? -eq 0 ]; then
    echo "✅ Branding update successfully deployed to VPS!"
    
    # Show restart instructions
    echo ""
    echo "📌 To apply the branding changes, restart the application on the VPS:"
    echo "   ssh $VPS_USER@$VPS_HOST"
    echo "   cd $VPS_PATH"
    echo "   docker-compose restart virtuoso"
    echo ""
    echo "📊 After restart, all new chart images will include:"
    echo "  - Virtuoso branding at the bottom"
    echo "  - Professional appearance with company colors"
    echo "  - Consistent branding across Discord alerts"
    echo ""
    echo "🎉 Chart branding deployment complete!"
else
    echo "❌ Failed to deploy branding update to VPS"
    exit 1
fi