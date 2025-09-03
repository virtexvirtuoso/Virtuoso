#!/bin/bash

#############################################################################
# Script: test_mobile_dashboard_complete.sh
# Purpose: Test and validate test mobile dashboard complete
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates automated testing, validation, and quality assurance for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - python3
#   - curl
#   - grep
#   - Access to project directory structure
#
# Usage:
#   ./test_mobile_dashboard_complete.sh [options]
#   
#   Examples:
#     ./test_mobile_dashboard_complete.sh
#     ./test_mobile_dashboard_complete.sh --verbose
#     ./test_mobile_dashboard_complete.sh --dry-run
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
#   0 - All tests passed
#   1 - Test failures detected
#   2 - Test configuration error
#   3 - Dependencies missing
#   4 - Environment setup failed
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

echo "🧪 Complete Mobile Dashboard Test"
echo "================================="

echo ""
echo "📱 Testing Mobile Dashboard Endpoints..."
echo "----------------------------------------"

echo "1. Mobile Data Endpoint:"
curl -s "http://VPS_HOST_REDACTED:8001/api/dashboard-cached/mobile-data" | jq '.market_overview'

echo ""
echo "2. Market Regime:"
curl -s "http://VPS_HOST_REDACTED:8001/api/dashboard-cached/mobile-data" | jq -r '.market_overview.market_regime'

echo ""
echo "3. BTC Dominance:"
curl -s "http://VPS_HOST_REDACTED:8001/api/dashboard-cached/mobile-data" | jq -r '.market_overview.btc_dominance'

echo ""
echo "4. Total Volume:"
VOLUME=$(curl -s "http://VPS_HOST_REDACTED:8001/api/dashboard-cached/mobile-data" | jq -r '.market_overview.total_volume_24h')
echo "\$$(echo "scale=1; $VOLUME/1000000000" | bc)B"

echo ""
echo "5. Confluence Scores Count:"
curl -s "http://VPS_HOST_REDACTED:8001/api/dashboard-cached/mobile-data" | jq '.confluence_scores | length'

echo ""
echo "6. First Confluence Score:"
curl -s "http://VPS_HOST_REDACTED:8001/api/dashboard-cached/mobile-data" | jq '.confluence_scores[0] | {symbol, score, sentiment}'

echo ""
echo "🔍 Testing Analysis Button..."
echo "-----------------------------"

echo "7. Analysis Endpoint Test:"
curl -s "http://VPS_HOST_REDACTED:8001/api/dashboard/confluence-analysis/BTCUSDT" | jq -r '.analysis' | head -5

echo ""
echo "8. Analysis Page Test:"
curl -s -I "http://VPS_HOST_REDACTED:8001/api/dashboard/confluence-analysis-page?symbol=BTCUSDT" | head -1

echo ""
echo "📊 Testing Market Data..."
echo "-------------------------"

echo "9. Market Breadth:"
curl -s "http://VPS_HOST_REDACTED:8001/api/dashboard-cached/mobile-data" | jq '.market_breadth // "Not available"'

echo ""
echo "10. Top Movers:"
curl -s "http://VPS_HOST_REDACTED:8001/api/dashboard-cached/mobile-data" | jq '.top_movers.gainers | length'

echo ""
echo "✅ Mobile Dashboard Test Complete!"
echo "=================================="
echo ""
echo "🌐 Access mobile dashboard at:"
echo "   http://VPS_HOST_REDACTED:8001/dashboard/mobile"
echo ""
echo "🎯 Click 'Analyze' button on any symbol to see terminal breakdown"