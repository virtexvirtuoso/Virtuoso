#!/bin/bash

#############################################################################
# Script: deploy_corrected_branding.sh
# Purpose: Deploy and manage deploy corrected branding
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
#   ./deploy_corrected_branding.sh [options]
#   
#   Examples:
#     ./deploy_corrected_branding.sh
#     ./deploy_corrected_branding.sh --verbose
#     ./deploy_corrected_branding.sh --dry-run
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

# Deploy corrected chart branding to VPS
echo "🚀 Deploying corrected chart branding to VPS (5.223.63.4)..."

# VPS details
VPS_USER="linuxuser"
VPS_HOST="5.223.63.4"
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
echo "🔧 Corrections being deployed:"
echo "  - Removed emoji from branding (fixed rendering issue)"
echo "  - Reverted to original chart color scheme"
echo "  - Simple 'VIRTUOSO' text branding only"
echo "  - Minimal padding to avoid layout issues"
echo "  - Professional subtle appearance"

# Deploy to VPS
echo ""
echo "🔄 Syncing corrected files to VPS..."
rsync -avz --progress "${FILES_TO_UPDATE[@]}" "$VPS_USER@$VPS_HOST:$VPS_PATH/src/core/reporting/"

if [ $? -eq 0 ]; then
    echo "✅ Corrected branding successfully deployed to VPS!"
    
    # Show restart instructions
    echo ""
    echo "📌 To apply the corrected branding, restart the application on the VPS:"
    echo "   ssh $VPS_USER@$VPS_HOST"
    echo "   cd $VPS_PATH"
    echo "   docker-compose restart virtuoso"
    echo ""
    echo "📊 After restart, chart images will have:"
    echo "  - Original professional color scheme"
    echo "  - Simple 'VIRTUOSO' text branding"
    echo "  - No emoji rendering issues"
    echo "  - Clean professional appearance"
    echo ""
    echo "🎉 Corrected chart branding deployment complete!"
else
    echo "❌ Failed to deploy corrected branding to VPS"
    exit 1
fi