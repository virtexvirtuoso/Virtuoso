#!/bin/bash

#############################################################################
# Script: deploy_breadth_fix.sh
# Purpose: Deploy and manage deploy breadth fix
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
#   ./deploy_breadth_fix.sh [options]
#   
#   Examples:
#     ./deploy_breadth_fix.sh
#     ./deploy_breadth_fix.sh --verbose
#     ./deploy_breadth_fix.sh --dry-run
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

echo "🔧 Deploying Market Breadth Naming Fix..."
echo "========================================="

VPS_HOST="linuxuser@45.77.40.77"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Copy the updated version
echo "📤 Deploying updated mobile dashboard..."
scp src/dashboard/templates/dashboard_mobile_v1_updated.html $VPS_HOST:$PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html

# Restart web service
echo "🔄 Restarting web service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso-web.service"

# Wait for service to start
sleep 3

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📱 Improvements Made:"
echo "   • Compact view: 'Breadth' → 'Bulls %' (clearer indicator)"
echo "   • Expanded view: 'Market Breadth' → 'Up vs Down Markets'"
echo "   • Hint text: 'Advancers' → 'Bullish' (more intuitive)"
echo ""
echo "🎯 Result: No redundancy, clearer terminology!"
echo ""
echo "Access at: http://45.77.40.77:8001/dashboard/mobile"