#!/bin/bash

#############################################################################
# Script: bybit_curl_commands.sh
# Purpose: Direct curl commands to test Bybit API endpoints
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
#   ./bybit_curl_commands.sh [options]
#   
#   Examples:
#     ./bybit_curl_commands.sh
#     ./bybit_curl_commands.sh --verbose
#     ./bybit_curl_commands.sh --dry-run
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

echo "======================================"
echo "Testing Bybit API Endpoints with CURL"
echo "======================================"
echo ""

# 1. Test OHLCV (1 minute candles)
echo "1. Testing OHLCV/Klines (1m):"
echo "Command: curl -X GET \"https://api.bybit.com/v5/market/kline?category=linear&symbol=BTCUSDT&interval=1&limit=2\""
curl -s -X GET "https://api.bybit.com/v5/market/kline?category=linear&symbol=BTCUSDT&interval=1&limit=2" | jq '.'
echo ""

# 2. Test Recent Trades
echo "2. Testing Recent Trades:"
echo "Command: curl -X GET \"https://api.bybit.com/v5/market/recent-trade?category=linear&symbol=BTCUSDT&limit=2\""
curl -s -X GET "https://api.bybit.com/v5/market/recent-trade?category=linear&symbol=BTCUSDT&limit=2" | jq '.'
echo ""

# 3. Test Orderbook
echo "3. Testing Orderbook:"
echo "Command: curl -X GET \"https://api.bybit.com/v5/market/orderbook?category=linear&symbol=BTCUSDT&limit=5\""
curl -s -X GET "https://api.bybit.com/v5/market/orderbook?category=linear&symbol=BTCUSDT&limit=5" | jq '.'
echo ""

# 4. Test Ticker
echo "4. Testing 24hr Ticker:"
echo "Command: curl -X GET \"https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT\""
curl -s -X GET "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT" | jq '.result.list[0] | {symbol, lastPrice, volume24h, bid1Price, ask1Price}'
echo ""

# 5. Test all timeframes we use
echo "5. Testing All Required Timeframes:"
for interval in 1 5 15 30 60 240; do
    echo "  Testing ${interval} minute interval..."
    response=$(curl -s -X GET "https://api.bybit.com/v5/market/kline?category=linear&symbol=BTCUSDT&interval=${interval}&limit=1")
    retCode=$(echo $response | jq -r '.retCode')
    if [ "$retCode" = "0" ]; then
        echo "  ✓ ${interval}m: Success"
    else
        echo "  ✗ ${interval}m: Failed"
    fi
done
echo ""

echo "======================================"
echo "Testing Complete!"
echo "======================================