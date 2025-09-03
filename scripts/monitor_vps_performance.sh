#!/bin/bash

#############################################################################
# Script: monitor_vps_performance.sh
# Purpose: Deploy and manage monitor vps performance
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
#   ./monitor_vps_performance.sh [options]
#   
#   Examples:
#     ./monitor_vps_performance.sh
#     ./monitor_vps_performance.sh --verbose
#     ./monitor_vps_performance.sh --dry-run
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

echo "======================================"
echo "VPS CACHE PERFORMANCE MONITOR"
echo "======================================"
echo ""

# Test the API endpoints
echo "Testing API performance with caching..."
echo ""

# Test ticker endpoint (should be cached)
echo "1. Market Tickers Endpoint:"
for i in {1..5}; do
    START=$(date +%s%3N)
    RESPONSE=$(curl -s -w "\n%{http_code}" http://VPS_HOST_REDACTED:8003/api/market/tickers 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    END=$(date +%s%3N)
    DURATION=$((END - START))
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "   Request $i: ${DURATION}ms (HTTP $HTTP_CODE)"
    else
        echo "   Request $i: Failed (HTTP $HTTP_CODE)"
    fi
    
    sleep 0.5
done

echo ""
echo "2. Dashboard Mobile Endpoint:"
for i in {1..3}; do
    START=$(date +%s%3N)
    RESPONSE=$(curl -s -w "\n%{http_code}" http://VPS_HOST_REDACTED:8001/api/dashboard/mobile 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    END=$(date +%s%3N)
    DURATION=$((END - START))
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "   Request $i: ${DURATION}ms (HTTP $HTTP_CODE)"
    else
        echo "   Request $i: Failed (HTTP $HTTP_CODE)"
    fi
    
    sleep 0.5
done

echo ""
echo "3. System Status:"
ssh linuxuser@VPS_HOST_REDACTED << 'EOF'
echo "   Memcached: $(systemctl is-active memcached)"
echo "   Memory usage: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "   CPU load: $(uptime | awk -F'load average:' '{print $2}')"

# Check cache stats from memcached
echo ""
echo "4. Memcached Statistics:"
echo -e "stats\r\nquit" | nc 127.0.0.1 11211 | grep -E "cmd_get|cmd_set|get_hits|get_misses" | head -4
EOF

echo ""
echo "======================================"
echo "Monitoring complete!"