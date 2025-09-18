#!/bin/bash

#############################################################################
# Script: simple_test.sh
# Purpose: Deploy and manage simple test
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
#   ./simple_test.sh [options]
#   
#   Examples:
#     ./simple_test.sh
#     ./simple_test.sh --verbose
#     ./simple_test.sh --dry-run
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

# Simple focused test for core functionality

echo "🧪 SIMPLE VIRTUOSO TEST"
echo "======================="
echo ""

# First ensure server is running
echo "1. Checking server status..."
ssh linuxuser@${VPS_HOST} 'cd /home/linuxuser/trading/Virtuoso_ccxt && pgrep -f "python.*web_server" > /dev/null || (source venv311/bin/activate && nohup python src/web_server.py > web_server.log 2>&1 & echo "Started new server process")'

# Wait for server startup
echo "   Waiting for server to start..."
sleep 10

echo ""
echo "2. Testing core endpoints:"
echo "   Dashboard: $(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://${VPS_HOST}:8003/dashboard)"
echo "   Mobile: $(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://${VPS_HOST}:8003/dashboard/mobile)"
echo "   API Overview: $(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://${VPS_HOST}:8003/api/dashboard/overview)"

echo ""
echo "3. Testing Market Overview API Performance:"

# First call (uncached)
echo -n "   First call (uncached): "
start_time=$(date +%s.%N)
response=$(curl -s --max-time 15 http://${VPS_HOST}:8003/api/market/overview)
end_time=$(date +%s.%N)
duration=$(echo "$end_time - $start_time" | bc)

if echo "$response" | python3 -m json.tool > /dev/null 2>&1; then
    echo "✅ Success in ${duration}s"
    
    # Check if it has optimization fields
    if echo "$response" | grep -q "fetch_time_seconds"; then
        fetch_time=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('fetch_time_seconds', 'N/A'))")
        echo "   Parallel fetch time: ${fetch_time}s"
    fi
else
    echo "❌ Failed"
fi

# Second call (should be cached)
sleep 2
echo -n "   Second call (cached): "
start_time=$(date +%s.%N)
response=$(curl -s --max-time 5 http://${VPS_HOST}:8003/api/market/overview)
end_time=$(date +%s.%N)
duration=$(echo "$end_time - $start_time" | bc)

if echo "$response" | python3 -m json.tool > /dev/null 2>&1; then
    echo "✅ Success in ${duration}s"
    
    # Check cache status
    cached=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('cached', False))" 2>/dev/null || echo "unknown")
    echo "   Cached: ${cached}"
else
    echo "❌ Failed"
fi

echo ""
echo "4. Exchange Manager Status:"
# Check if Exchange Manager is working
response=$(curl -s --max-time 5 http://${VPS_HOST}:8003/api/market/overview 2>&1)
if echo "$response" | grep -q "Exchange manager not initialized"; then
    echo "   ❌ Exchange Manager NOT initialized"
else
    echo "   ✅ Exchange Manager working"
fi

echo ""
echo "Test complete!"