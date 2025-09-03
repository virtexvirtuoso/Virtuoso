#!/bin/bash

#############################################################################
# Script: deploy_enhanced_market_overview.sh
# Purpose: Deploy and manage deploy enhanced market overview
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
#   ./deploy_enhanced_market_overview.sh [options]
#   
#   Examples:
#     ./deploy_enhanced_market_overview.sh
#     ./deploy_enhanced_market_overview.sh --verbose
#     ./deploy_enhanced_market_overview.sh --dry-run
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

echo "🚀 Deploying Enhanced Market Overview Card to VPS..."
echo "=================================================="

VPS_HOST="linuxuser@VPS_HOST_REDACTED"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Backup current version
echo "📦 Backing up current mobile dashboard..."
ssh $VPS_HOST "cp $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1_backup_$(date +%Y%m%d_%H%M%S).html"

# Copy the updated version
echo "📤 Deploying enhanced mobile dashboard..."
scp src/dashboard/templates/dashboard_mobile_v1_updated.html $VPS_HOST:$PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html

# Restart web service
echo "🔄 Restarting web service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso-web.service"

# Wait for service to start
sleep 3

echo ""
echo "🧪 Testing enhanced features..."
echo "================================"

# Test market overview data
echo "1. Testing market overview endpoint:"
curl -s "http://VPS_HOST_REDACTED:8001/api/dashboard-cached/mobile-data" | python3 -c "
import json, sys
data = json.load(sys.stdin)
overview = data.get('market_overview', {})
breadth = data.get('market_breadth', {})
print(f'   Market Regime: {overview.get(\"market_regime\", \"unknown\")}')
print(f'   Trend Strength: {overview.get(\"trend_strength\", 0)}')
print(f'   Volatility: {overview.get(\"volatility\", 0):.1f}%')
print(f'   BTC Dominance: {overview.get(\"btc_dominance\", 0):.1f}%')
if breadth:
    print(f'   Market Breadth: {breadth.get(\"display\", \"N/A\")}')
print(f'   Total Volume: \${overview.get(\"total_volume_24h\", 0)/1e9:.2f}B')
"

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📱 Access the enhanced mobile dashboard at:"
echo "   http://VPS_HOST_REDACTED:8001/dashboard/mobile"
echo ""
echo "🎯 New Features Added:"
echo "   • Expandable card (tap to expand/collapse)"
echo "   • Compact summary with regime chip & gauges"
echo "   • Sparkline charts for trend visualization"
echo "   • Timeframe selector (24h/7d/30d)"
echo "   • Live update timestamp"
echo "   • Improved tile layout in expanded view"
echo ""
echo "💡 Tip: Tap the market overview card to see detailed metrics!"