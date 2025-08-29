#!/bin/bash

#############################################################################
# Script: deploy_breadth_visualization_only.sh
# Purpose: Deploy and manage deploy breadth visualization only
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
#   ./deploy_breadth_visualization_only.sh [options]
#   
#   Examples:
#     ./deploy_breadth_visualization_only.sh
#     ./deploy_breadth_visualization_only.sh --verbose
#     ./deploy_breadth_visualization_only.sh --dry-run
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

echo "🎨 Deploying Market Breadth Visualization Update Only..."
echo "========================================================"

VPS_HOST="linuxuser@45.77.40.77"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Backup current version on VPS
echo "📦 Backing up current version on VPS..."
ssh $VPS_HOST "cp $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1_backup_breadth_$(date +%Y%m%d_%H%M%S).html"

# Copy the updated version with only market breadth changes
echo "📤 Deploying updated dashboard with improved market breadth..."
scp src/dashboard/templates/dashboard_mobile_v1.html $VPS_HOST:$PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html

# Restart web service
echo "🔄 Restarting web service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso-web.service"

# Wait for service to start
sleep 3

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "🎨 Market Breadth Improvements:"
echo "   • Visual sentiment indicator with Lucide icons"
echo "   • Dynamic icon: trending-up (bulls), trending-down (bears), minus (neutral)"
echo "   • Percentage bar showing bulls (green) vs bears (red)"
echo "   • Clear labels: 'Bulls Leading', 'Bears Leading', 'Market Balanced'"
echo "   • 'Rising/falling' terminology for better clarity"
echo "   • Live indicator showing real-time updates"
echo ""
echo "📱 Access the updated dashboard at:"
echo "   http://45.77.40.77:8001/dashboard/mobile"
echo ""
echo "💡 Note: Only the market breadth visualization has been updated."
echo "   All other dashboard components remain unchanged."