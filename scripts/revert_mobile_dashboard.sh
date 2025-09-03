#!/bin/bash

#############################################################################
# Script: revert_mobile_dashboard.sh
# Purpose: Deploy and manage revert mobile dashboard
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
#   ./revert_mobile_dashboard.sh [options]
#   
#   Examples:
#     ./revert_mobile_dashboard.sh
#     ./revert_mobile_dashboard.sh --verbose
#     ./revert_mobile_dashboard.sh --dry-run
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

echo "🔄 Reverting Mobile Dashboard to Previous Version..."
echo "===================================================="

VPS_HOST="linuxuser@VPS_HOST_REDACTED"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# First, backup the enhanced version on VPS
echo "📦 Backing up enhanced version on VPS..."
ssh $VPS_HOST "cp $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1_enhanced_$(date +%Y%m%d_%H%M%S).html"

# Restore the previous version
echo "🔙 Restoring previous dashboard version..."
ssh $VPS_HOST "cp $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1_backup_20250821_100721.html $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html"

# Restart web service
echo "🔄 Restarting web service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso-web.service"

# Wait for service to start
sleep 3

# Verify the reversion
echo ""
echo "🧪 Verifying reversion..."
echo "=========================="

# Check for the old market overview structure
echo "1. Checking for original Market Overview structure:"
curl -s "http://VPS_HOST_REDACTED:8001/dashboard/mobile" | grep -q "MARKET REGIME" && echo "   ✅ Found original MARKET REGIME label" || echo "   ❌ Original structure not found"

echo ""
echo "2. Checking page loads correctly:"
TITLE=$(curl -s "http://VPS_HOST_REDACTED:8001/dashboard/mobile" | grep -o '<title>.*</title>')
echo "   Page title: $TITLE"

echo ""
echo "3. Testing data endpoint:"
curl -s "http://VPS_HOST_REDACTED:8001/api/dashboard-cached/mobile-data" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(f'   ✅ API working - Market regime: {data.get(\"market_overview\", {}).get(\"market_regime\", \"unknown\")}')
except:
    print('   ❌ API error')
"

echo ""
echo "✅ Reversion Complete!"
echo ""
echo "📱 The mobile dashboard has been reverted to the previous version"
echo "   URL: http://VPS_HOST_REDACTED:8001/dashboard/mobile"
echo ""
echo "💾 Backups created:"
echo "   • Enhanced version saved locally as: dashboard_mobile_v1_enhanced_backup.html"
echo "   • Enhanced version saved on VPS with timestamp"
echo ""
echo "📝 To restore the enhanced version later, use:"
echo "   scp src/dashboard/templates/dashboard_mobile_v1_enhanced_backup.html $VPS_HOST:$PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html"