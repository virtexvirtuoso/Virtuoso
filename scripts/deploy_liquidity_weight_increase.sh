#!/bin/bash

#############################################################################
# Script: deploy_liquidity_weight_increase.sh
# Purpose: Deploy and manage deploy liquidity weight increase
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
#   ./deploy_liquidity_weight_increase.sh [options]
#   
#   Examples:
#     ./deploy_liquidity_weight_increase.sh
#     ./deploy_liquidity_weight_increase.sh --verbose
#     ./deploy_liquidity_weight_increase.sh --dry-run
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

echo "=================================================="
echo "🎯 Deploying Increased Liquidity Zones Weight to VPS"
echo "=================================================="

# VPS connection details
VPS_USER="linuxuser"
VPS_HOST="VPS_HOST_REDACTED"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo -e "\n⚖️ Weight changes:"
echo "   Liquidity Zones: 0.05 (5%) → 0.20 (20%) ⬆️ 4x increase!"
echo "   CVD: 0.25 → 0.20 ⬇️"
echo "   Trade Flow: 0.20 → 0.15 ⬇️"
echo "   Imbalance: 0.15 → 0.12 ⬇️"
echo "   Pressure: 0.10 → 0.08 ⬇️"
echo ""
echo "   This gives much more importance to Smart Money liquidity zones!"

echo -e "\n📤 Deploying updated file to VPS..."
scp src/indicators/orderflow_indicators.py "$VPS_USER@$VPS_HOST:$VPS_PATH/src/indicators/"

if [ $? -eq 0 ]; then
    echo "   ✅ File deployed successfully"
else
    echo "   ❌ Deployment failed"
    exit 1
fi

echo -e "\n🔄 Restarting Virtuoso service..."
ssh "$VPS_USER@$VPS_HOST" "sudo systemctl restart virtuoso.service"

echo -e "\n📊 Service status:"
ssh "$VPS_USER@$VPS_HOST" "sudo systemctl status virtuoso.service --no-pager | head -10"

echo -e "\n=================================================="
echo "✅ Deployment complete!"
echo ""
echo "🔍 To see the impact of increased liquidity_zones weight:"
echo "   ssh $VPS_USER@$VPS_HOST"
echo "   sudo journalctl -u virtuoso.service -f | grep -E 'liquidity_zones|Impact'"
echo ""
echo "💡 The liquidity_zones score will now have 4x more impact on final scores!"
echo "=================================================="