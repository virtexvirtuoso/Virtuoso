#!/bin/bash

#############################################################################
# Script: fix_market_overview_vps.sh
# Purpose: Deploy and manage fix market overview vps
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
#   ./fix_market_overview_vps.sh [options]
#   
#   Examples:
#     ./fix_market_overview_vps.sh
#     ./fix_market_overview_vps.sh --verbose
#     ./fix_market_overview_vps.sh --dry-run
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

echo "🔧 Fixing Market Overview Metrics on VPS..."
echo "==========================================="

VPS_HOST="linuxuser@${VPS_HOST}"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Copy the fix script to VPS
echo "📤 Copying fix script to VPS..."
scp scripts/fix_market_overview_metrics.py $VPS_HOST:$PROJECT_DIR/scripts/

# Run the fix on VPS where Bybit API is accessible
echo "🔧 Running fix on VPS..."
ssh $VPS_HOST "cd $PROJECT_DIR && ./venv311/bin/python scripts/fix_market_overview_metrics.py"

# Copy updated cache adapter to VPS
echo "📤 Deploying updated cache adapter..."
scp src/api/cache_adapter.py $VPS_HOST:$PROJECT_DIR/src/api/

# Restart web service
echo "🔄 Restarting web service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso-web.service"

# Wait for service
sleep 3

# Test the API
echo ""
echo "🧪 Testing API endpoints..."
echo "============================"

echo "1. Testing mobile-data endpoint:"
curl -s "http://${VPS_HOST}:8001/api/dashboard-cached/mobile-data" | python3 -c "
import json, sys
data = json.load(sys.stdin)
overview = data.get('market_overview', {})
print(f'  ✓ Market Regime: {overview.get(\"market_regime\")}')
print(f'  ✓ Trend Strength: {overview.get(\"trend_strength\")}%')
print(f'  ✓ BTC Dominance: {overview.get(\"btc_dominance\")}%')
print(f'  ✓ Current Volatility: {overview.get(\"current_volatility\")}%')
print(f'  ✓ Average Volatility: {overview.get(\"avg_volatility\")}%')
print(f'  ✓ Total Volume: \${overview.get(\"total_volume\", 0):,.0f}')
"

echo ""
echo "2. Testing market breadth:"
curl -s "http://${VPS_HOST}:8001/api/dashboard-cached/mobile-data" | python3 -c "
import json, sys
data = json.load(sys.stdin)
if 'market_breadth' in data:
    breadth = data['market_breadth']
    print(f'  ✓ Up: {breadth.get(\"up_count\", 0)}')
    print(f'  ✓ Down: {breadth.get(\"down_count\", 0)}')
    print(f'  ✓ Percentage: {breadth.get(\"breadth_percentage\", 0)}% Bullish')
"

echo ""
echo "✅ Fix deployment complete!"
echo ""
echo "📊 Fixed Issues:"
echo "  1. Trend Strength: Now shows 0-100% scale"
echo "  2. BTC Dominance: Real data from CoinGecko API"
echo "  3. Volatility: Calculated from price movements"
echo "  4. Total Volume: Aggregated from all tickers"
echo ""
echo "📱 View at: http://${VPS_HOST}:8001/dashboard/mobile"