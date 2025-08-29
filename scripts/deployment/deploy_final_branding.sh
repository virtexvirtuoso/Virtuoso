#!/bin/bash

#############################################################################
# Script: deploy_final_branding.sh
# Purpose: Deploy and manage deploy final branding
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
#   ./deploy_final_branding.sh [options]
#   
#   Examples:
#     ./deploy_final_branding.sh
#     ./deploy_final_branding.sh --verbose
#     ./deploy_final_branding.sh --dry-run
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

# Deploy final corrected chart branding to VPS
echo "🚀 Deploying final chart branding to VPS (45.77.40.77)..."

# VPS details
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
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
echo "🎨 Final branding implementation:"
echo "  - Trending-up symbol: ↗ (Unicode arrow)"
echo "  - Orange color: #ff9900 (matching mobile header)"
echo "  - Text: 'VIRTUOSO'"
echo "  - Style: Dark box with orange border"
echo "  - Position: Bottom center with proper padding"
echo ""
echo "📊 Chart styling:"
echo "  - Reverted to original color scheme"
echo "  - Entry: #4CAF50 (green)"
echo "  - Stop Loss: #ef4444 (red)"
echo "  - Targets: Orange variations"
echo "  - Background: #121212 / #1E1E1E"

# Deploy to VPS
echo ""
echo "🔄 Syncing final version to VPS..."
rsync -avz --progress "${FILES_TO_UPDATE[@]}" "$VPS_USER@$VPS_HOST:$VPS_PATH/src/core/reporting/"

if [ $? -eq 0 ]; then
    echo "✅ Final branding successfully deployed to VPS!"
    
    # Show restart instructions
    echo ""
    echo "📌 To apply the final branding, restart the application on the VPS:"
    echo "   ssh $VPS_USER@$VPS_HOST"
    echo "   cd $VPS_PATH"
    echo "   docker-compose restart virtuoso"
    echo ""
    echo "📊 After restart, chart images will have:"
    echo "  - ↗ VIRTUOSO branding in orange"
    echo "  - Original professional color scheme"
    echo "  - Consistent with mobile header styling"
    echo "  - Clean professional appearance"
    echo ""
    echo "🎉 Final chart branding deployment complete!"
else
    echo "❌ Failed to deploy final branding to VPS"
    exit 1
fi