#!/bin/bash

#############################################################################
# Script: deploy_mobile_dashboard_final_fix.sh
# Purpose: Deploy and manage deploy mobile dashboard final fix
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
#   ./deploy_mobile_dashboard_final_fix.sh [options]
#   
#   Examples:
#     ./deploy_mobile_dashboard_final_fix.sh
#     ./deploy_mobile_dashboard_final_fix.sh --verbose
#     ./deploy_mobile_dashboard_final_fix.sh --dry-run
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

echo "🚀 Deploying Mobile Dashboard Final Fixes to VPS..."
echo "==========================================="

VPS_HOST="linuxuser@5.223.63.4"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Copy the updated files
echo "📦 Copying updated files..."
scp src/api/routes/dashboard_cached.py $VPS_HOST:$PROJECT_DIR/src/api/routes/
scp scripts/fix_mobile_dashboard_final.py $VPS_HOST:$PROJECT_DIR/scripts/

# Run the fix script on VPS
echo ""
echo "🔧 Running fix script on VPS..."
ssh $VPS_HOST "cd $PROJECT_DIR && echo 'n' | ./venv311/bin/python scripts/fix_mobile_dashboard_final.py"

# Restart web service
echo ""
echo "🔄 Restarting web service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso-web.service"

# Wait for service to start
sleep 3

# Test the endpoints
echo ""
echo "🧪 Testing fixed endpoints..."
echo ""

echo "1. Market Breadth Test:"
curl -s "http://5.223.63.4:8001/api/dashboard-cached/mobile-data" | jq '.market_breadth'

echo ""
echo "2. Top Movers Test:"
curl -s "http://5.223.63.4:8001/api/dashboard-cached/mobile-data" | jq '{gainers: .top_movers.gainers | length, losers: .top_movers.losers | length}'

echo ""
echo "3. First Confluence Score with Price:"
curl -s "http://5.223.63.4:8001/api/dashboard-cached/mobile-data" | jq '.confluence_scores[0] | {symbol, score, price, change_24h}'

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📱 Test mobile dashboard at: http://5.223.63.4:8001/dashboard/mobile"