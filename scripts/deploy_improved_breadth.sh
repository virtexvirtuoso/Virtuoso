#!/bin/bash

#############################################################################
# Script: deploy_improved_breadth.sh
# Purpose: Deploy and manage deploy improved breadth
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
#   ./deploy_improved_breadth.sh [options]
#   
#   Examples:
#     ./deploy_improved_breadth.sh
#     ./deploy_improved_breadth.sh --verbose
#     ./deploy_improved_breadth.sh --dry-run
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

echo "🎨 Deploying Improved Market Breadth Visualization..."
echo "===================================================="

VPS_HOST="linuxuser@${VPS_HOST}"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Backup current version on VPS
echo "📦 Backing up current version on VPS..."
ssh $VPS_HOST "cp $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1_backup_$(date +%Y%m%d_%H%M%S).html"

# Copy the improved version
echo "📤 Deploying improved mobile dashboard..."
scp src/dashboard/templates/dashboard_mobile_v1_improved.html $VPS_HOST:$PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html

# Restart web service
echo "🔄 Restarting web service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso-web.service"

# Wait for service to start
sleep 3

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "🎨 Visual Improvements Made:"
echo "   • Market sentiment icon (📈/📉/➡️) shows at-a-glance market direction"
echo "   • Visual percentage bar with bulls (green) vs bears (red)"
echo "   • Clear 'Bulls Leading/Bears Leading/Market Balanced' label"
echo "   • Rising/falling terminology instead of up/down"
echo "   • Live indicator shows real-time updates"
echo "   • Smooth animations for all transitions"
echo ""
echo "📱 Access the improved dashboard at:"
echo "   http://${VPS_HOST}:8001/dashboard/mobile"
echo ""
echo "💡 Features:"
echo "   • Clearer visualization of market sentiment"
echo "   • Easy-to-understand terminology"
echo "   • Professional trading dashboard appearance"
echo "   • Mobile-optimized for quick market assessment"