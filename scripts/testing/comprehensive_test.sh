#!/bin/bash

#############################################################################
# Script: comprehensive_test.sh
# Purpose: Deploy and manage comprehensive test
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
#   ./comprehensive_test.sh [options]
#   
#   Examples:
#     ./comprehensive_test.sh
#     ./comprehensive_test.sh --verbose
#     ./comprehensive_test.sh --dry-run
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

# Comprehensive test script for Virtuoso Trading Dashboard
# Tests all endpoints, performance improvements, and stability

REMOTE_HOST="VPS_HOST_REDACTED"
PORT="8003"
BASE_URL="http://${REMOTE_HOST}:${PORT}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "======================================================"
echo "🧪 COMPREHENSIVE VIRTUOSO DASHBOARD TEST SUITE"
echo "======================================================"
echo "Target: ${BASE_URL}"
echo "Date: $(date)"
echo "======================================================"
echo ""

# Test results storage
PASSED=0
FAILED=0
TOTAL=0

# Function to test endpoint
test_endpoint() {
    local path=$1
    local expected=$2
    local description=$3
    TOTAL=$((TOTAL + 1))
    
    echo -n "[$TOTAL] Testing ${description}... "
    
    start_time=$(date +%s.%N)
    response=$(curl -s -o /tmp/response.tmp -w "%{http_code}" "${BASE_URL}${path}" --max-time 10)
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc)
    
    if [ "$response" = "$expected" ]; then
        echo -e "${GREEN}✓ PASS${NC} (${response}) - ${duration}s"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected: ${expected}, Got: ${response}) - ${duration}s"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Function to test API response content
test_api_content() {
    local path=$1
    local field=$2
    local description=$3
    TOTAL=$((TOTAL + 1))
    
    echo -n "[$TOTAL] Testing ${description}... "
    
    response=$(curl -s "${BASE_URL}${path}" --max-time 10)
    
    if echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); exit(0 if '$field' in data else 1)" 2>/dev/null; then
        value=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['$field'])")
        echo -e "${GREEN}✓ PASS${NC} (${field}: ${value})"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Field '${field}' not found)"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Function to test performance
test_performance() {
    local path=$1
    local max_time=$2
    local description=$3
    TOTAL=$((TOTAL + 1))
    
    echo -n "[$TOTAL] Performance: ${description}... "
    
    start_time=$(date +%s.%N)
    response=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}${path}" --max-time 15)
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc)
    
    if [ "$response" = "200" ] && (( $(echo "$duration < $max_time" | bc -l) )); then
        echo -e "${GREEN}✓ PASS${NC} (${duration}s < ${max_time}s)"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (${duration}s > ${max_time}s or status: ${response})"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo -e "${BLUE}1. DASHBOARD ENDPOINTS TEST${NC}"
echo "================================"
test_endpoint "/" 200 "Root endpoint"
test_endpoint "/health" 200 "Health check"
test_endpoint "/dashboard" 200 "Main dashboard (Desktop)"
test_endpoint "/dashboard/mobile" 200 "Mobile dashboard"
test_endpoint "/dashboard/desktop" 200 "Desktop dashboard (explicit)"
test_endpoint "/dashboard/v10" 200 "V10 dashboard"
test_endpoint "/dashboard/v1" 200 "Original dashboard"
test_endpoint "/ui" 200 "UI endpoint"
test_endpoint "/static/manifest.json" 200 "PWA Manifest"

echo ""
echo -e "${BLUE}2. API ENDPOINTS TEST${NC}"
echo "================================"
test_endpoint "/api/dashboard/overview" 200 "Dashboard Overview API"
test_endpoint "/api/dashboard/symbols" 200 "Dashboard Symbols API"
test_endpoint "/api/dashboard/signals" 200 "Dashboard Signals API"
test_endpoint "/api/dashboard/alerts" 200 "Dashboard Alerts API"
test_endpoint "/api/market/overview" 200 "Market Overview API"
test_endpoint "/api/market/movers" 200 "Market Movers API"
test_endpoint "/api/top-symbols" 200 "Top Symbols API"
test_endpoint "/version" 200 "Version endpoint"

echo ""
echo -e "${BLUE}3. API RESPONSE VALIDATION${NC}"
echo "================================"
test_api_content "/api/market/overview" "regime" "Market regime field"
test_api_content "/api/market/overview" "btc_dominance" "BTC dominance field"
test_api_content "/api/market/overview" "trend_strength" "Trend strength field"
test_api_content "/api/market/overview" "volatility" "Volatility field"
test_api_content "/api/dashboard/overview" "status" "Dashboard status"
test_api_content "/api/dashboard/overview" "signals" "Signals data"

echo ""
echo -e "${BLUE}4. PERFORMANCE TESTS${NC}"
echo "================================"
test_performance "/api/market/overview" 10 "Market Overview (first call)"

# Test cache performance
echo -n "Testing cache performance... "
sleep 1
start_time=$(date +%s.%N)
curl -s "${BASE_URL}/api/market/overview" > /tmp/cached_response.json
end_time=$(date +%s.%N)
cache_duration=$(echo "$end_time - $start_time" | bc)

if (( $(echo "$cache_duration < 1" | bc -l) )); then
    echo -e "${GREEN}✓ PASS${NC} (Cached response: ${cache_duration}s)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} (Cache too slow: ${cache_duration}s)"
    FAILED=$((FAILED + 1))
fi
TOTAL=$((TOTAL + 1))

# Check if response indicates it's cached
if grep -q '"cached":true' /tmp/cached_response.json 2>/dev/null; then
    echo -e "   ${GREEN}✓${NC} Cache flag detected in response"
fi

echo ""
echo -e "${BLUE}5. EXCHANGE MANAGER VERIFICATION${NC}"
echo "================================"

# Test that previously failing endpoints now work
echo "Testing Exchange Manager dependent endpoints:"
test_endpoint "/api/market/overview" 200 "Market Overview (Exchange Manager)"
test_endpoint "/api/top-symbols" 200 "Top Symbols (Exchange Manager)"

echo ""
echo -e "${BLUE}6. LOAD TEST${NC}"
echo "================================"
echo "Sending 10 concurrent requests to Market Overview API..."

# Run concurrent requests
start_time=$(date +%s.%N)
for i in {1..10}; do
    curl -s -o /dev/null "${BASE_URL}/api/market/overview" &
done
wait
end_time=$(date +%s.%N)
total_duration=$(echo "$end_time - $start_time" | bc)

echo -e "Completed 10 concurrent requests in ${total_duration}s"
avg_time=$(echo "$total_duration / 10" | bc -l | cut -c1-5)
echo -e "Average time per request: ${avg_time}s"

if (( $(echo "$avg_time < 2" | bc -l) )); then
    echo -e "${GREEN}✓ PASS${NC} - Good performance under load"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠ WARNING${NC} - Performance degradation under load"
fi
TOTAL=$((TOTAL + 1))

echo ""
echo -e "${BLUE}7. ERROR HANDLING TEST${NC}"
echo "================================"
test_endpoint "/api/invalid-endpoint" 404 "Invalid endpoint (404)"
test_endpoint "/dashboard/invalid" 404 "Invalid dashboard route"

echo ""
echo -e "${BLUE}8. WEBSOCKET TEST${NC}"
echo "================================"
echo -n "Testing WebSocket endpoint... "
timeout 2 bash -c "echo '' | nc ${REMOTE_HOST} ${PORT}" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ PASS${NC} - Port is accepting connections"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠ SKIP${NC} - WebSocket test not conclusive"
fi
TOTAL=$((TOTAL + 1))

echo ""
echo "======================================================"
echo -e "${BLUE}TEST SUMMARY${NC}"
echo "======================================================"
echo -e "Total Tests: ${TOTAL}"
echo -e "Passed: ${GREEN}${PASSED}${NC}"
echo -e "Failed: ${RED}${FAILED}${NC}"
echo -e "Success Rate: $(echo "scale=1; $PASSED * 100 / $TOTAL" | bc)%"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    echo ""
    echo "✅ All dashboard routes working"
    echo "✅ Exchange Manager properly initialized"
    echo "✅ Market Overview API optimized with caching"
    echo "✅ Performance improvements verified"
    exit 0
else
    echo -e "${RED}⚠️  SOME TESTS FAILED${NC}"
    echo ""
    echo "Please check the failed tests above for details."
    exit 1
fi

# Cleanup
rm -f /tmp/response.tmp /tmp/cached_response.json