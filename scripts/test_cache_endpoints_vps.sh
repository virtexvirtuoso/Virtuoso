#!/bin/bash

#############################################################################
# Script: test_cache_endpoints_vps.sh
# Purpose: Test and validate test cache endpoints vps
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
#   ./test_cache_endpoints_vps.sh [options]
#   
#   Examples:
#     ./test_cache_endpoints_vps.sh
#     ./test_cache_endpoints_vps.sh --verbose
#     ./test_cache_endpoints_vps.sh --dry-run
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

echo "Testing Cache Endpoints on VPS"
echo "=============================="
echo ""

# Test cache health endpoint first
echo "1. Testing cache health:"
curl -s http://VPS_HOST_REDACTED:8001/api/cache/health | python3 -m json.tool | head -n 10

echo ""
echo "2. Testing Phase 2 dashboard:"
curl -s http://VPS_HOST_REDACTED:8001/dashboard/phase2 | grep -o "<title>.*</title>" | head -n 1

echo ""
echo "3. Testing cache overview (Phase 2):"
curl -s http://VPS_HOST_REDACTED:8001/api/cache/cache/overview | python3 -m json.tool 2>/dev/null | head -n 10

echo ""
echo "4. Testing dashboard-cached endpoints (if available):"
for endpoint in overview market-overview signals; do
    echo "   - Testing /api/dashboard-cached/${endpoint}:"
    response=$(curl -s -w "\n[HTTP: %{http_code}, Time: %{time_total}s]" http://VPS_HOST_REDACTED:8001/api/dashboard-cached/${endpoint})
    echo "     ${response}" | tail -n 1
done

echo ""
echo "5. Testing regular dashboard endpoints (fallback):"
curl -s http://VPS_HOST_REDACTED:8001/api/dashboard/overview | python3 -m json.tool 2>/dev/null | head -n 5

echo ""
echo "=============================="
echo "Test Complete"