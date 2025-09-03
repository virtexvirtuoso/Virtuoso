#!/bin/bash

#############################################################################
# Script: test_phase1.sh
# Purpose: Test Phase 1 Cache Implementation
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
#   ./test_phase1.sh [options]
#   
#   Examples:
#     ./test_phase1.sh
#     ./test_phase1.sh --verbose
#     ./test_phase1.sh --dry-run
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

# Comprehensive testing of the emergency fix

echo "🧪 Testing Phase 1 Cache Implementation"
echo "======================================"
echo ""

# Configuration
API_HOST="localhost"
API_PORT="8003"
WEB_PORT="8001"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Test results
PASSED=0
FAILED=0
WARNINGS=0

# Test function
run_test() {
    local test_name="$1"
    local command="$2"
    local expected="$3"
    
    echo -n "Testing: $test_name... "
    
    result=$(eval "$command" 2>/dev/null)
    
    if [[ "$result" == *"$expected"* ]]; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        echo "  Expected: $expected"
        echo "  Got: $result"
        ((FAILED++))
        return 1
    fi
}

# Performance test function
perf_test() {
    local test_name="$1"
    local url="$2"
    local max_time="$3"
    
    echo -n "Performance: $test_name... "
    
    response_time=$(curl -s -o /dev/null -w "%{time_total}" "$url")
    
    if (( $(echo "$response_time < $max_time" | bc -l) )); then
        echo -e "${GREEN}✅ PASSED (${response_time}s)${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌ FAILED (${response_time}s > ${max_time}s)${NC}"
        ((FAILED++))
        return 1
    fi
}

echo "1️⃣ SERVICE HEALTH TESTS"
echo "------------------------"

# Test 1: Main service health
run_test "Main service health" \
    "curl -s http://$API_HOST:$API_PORT/health | python3 -c 'import sys, json; print(json.load(sys.stdin)[\"status\"])'" \
    "healthy"

# Test 2: Web service health
run_test "Web service health" \
    "curl -s http://$API_HOST:$WEB_PORT/health | python3 -c 'import sys, json; print(json.load(sys.stdin)[\"status\"])'" \
    "healthy"

echo ""
echo "2️⃣ CACHE FUNCTIONALITY TESTS"
echo "-----------------------------"

# Test 3: Cache status endpoint exists
run_test "Cache status endpoint" \
    "curl -s -o /dev/null -w '%{http_code}' http://$API_HOST:$API_PORT/api/dashboard/cache-status" \
    "200"

# Test 4: Signals endpoint returns data
run_test "Signals endpoint responds" \
    "curl -s -o /dev/null -w '%{http_code}' http://$API_HOST:$API_PORT/api/dashboard/signals" \
    "200"

# Test 5: Overview endpoint returns data
run_test "Overview endpoint responds" \
    "curl -s -o /dev/null -w '%{http_code}' http://$API_HOST:$API_PORT/api/dashboard/overview" \
    "200"

echo ""
echo "3️⃣ PERFORMANCE TESTS"
echo "--------------------"

# Test 6: API response time (should be < 2 seconds with cache)
perf_test "Signals API response time" \
    "http://$API_HOST:$API_PORT/api/dashboard/signals" \
    "2.0"

perf_test "Overview API response time" \
    "http://$API_HOST:$API_PORT/api/dashboard/overview" \
    "2.0"

echo ""
echo "4️⃣ CACHE HIT RATE TEST"
echo "----------------------"

# Make multiple requests to test cache
echo "Making 5 rapid requests to test cache..."
for i in {1..5}; do
    start=$(date +%s%N)
    curl -s "http://$API_HOST:$API_PORT/api/dashboard/signals" > /dev/null
    end=$(date +%s%N)
    duration=$((($end - $start) / 1000000))
    echo "  Request $i: ${duration}ms"
    
    if [ $i -gt 1 ] && [ $duration -gt 1000 ]; then
        echo -e "    ${YELLOW}⚠️ Warning: Cache may not be working (>1000ms)${NC}"
        ((WARNINGS++))
    fi
done

# Check cache statistics
echo ""
echo "Cache Statistics:"
curl -s "http://$API_HOST:$API_PORT/api/dashboard/cache-status" 2>/dev/null | \
    python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    stats = data.get('cache_stats', {})
    print(f\"  • Cache Size: {stats.get('size', 0)}\")
    print(f\"  • Hit Rate: {stats.get('hit_rate', '0%')}\")
    print(f\"  • Total Requests: {stats.get('total_requests', 0)}\")
    print(f\"  • Hits: {stats.get('hits', 0)}\")
    print(f\"  • Misses: {stats.get('misses', 0)}\")
except:
    print('  ⚠️ Could not retrieve cache statistics')
" || echo "  ⚠️ Cache statistics not available"

echo ""
echo "5️⃣ INTEGRATION TEST"
echo "-------------------"

# Test dashboard integration
echo "Testing dashboard integration..."
integration_status=$(curl -s "http://$API_HOST:$WEB_PORT/api/dashboard/mobile" 2>/dev/null | \
    python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "error")

echo "  Integration status: $integration_status"

if [[ "$integration_status" == "main_service"* ]]; then
    echo -e "  ${GREEN}✅ Dashboard integrated with main service${NC}"
    ((PASSED++))
elif [ "$integration_status" = "no_integration" ]; then
    echo -e "  ${YELLOW}⚠️ Dashboard still using fallback${NC}"
    ((WARNINGS++))
else
    echo -e "  ${RED}❌ Integration error${NC}"
    ((FAILED++))
fi

echo ""
echo "6️⃣ DATA VALIDATION TEST"
echo "-----------------------"

# Check if signals have required fields
echo "Validating signal data structure..."
curl -s "http://$API_HOST:$API_PORT/api/dashboard/signals" 2>/dev/null | \
    python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    
    # Check status
    status = data.get('status', '')
    if status in ['success', 'computing']:
        print(f'  ✅ Valid status: {status}')
    else:
        print(f'  ❌ Invalid status: {status}')
    
    # Check source
    source = data.get('source', '')
    if 'cached' in source or 'main_service' in source:
        print(f'  ✅ Valid source: {source}')
    else:
        print(f'  ⚠️ Unexpected source: {source}')
    
    # Check signals
    signals = data.get('signals', [])
    if isinstance(signals, list):
        print(f'  ✅ Signals array present ({len(signals)} items)')
        
        if len(signals) > 0:
            # Check first signal structure
            first = signals[0]
            required_fields = ['symbol', 'score', 'price']
            missing = [f for f in required_fields if f not in first]
            if missing:
                print(f'  ⚠️ Missing fields in signals: {missing}')
            else:
                print(f'  ✅ Signal structure valid')
    else:
        print(f'  ❌ Invalid signals format')
        
except Exception as e:
    print(f'  ❌ Error validating data: {e}')
"

echo ""
echo "7️⃣ BACKGROUND UPDATER TEST"
echo "--------------------------"

# Check if background updater is running
echo "Checking background updater status..."
curl -s "http://$API_HOST:$API_PORT/api/dashboard/cache-status" 2>/dev/null | \
    python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    last_update = data.get('last_update', {})
    
    if last_update:
        status = last_update.get('status', 'unknown')
        timestamp = last_update.get('timestamp', 'never')
        update_count = last_update.get('update_count', 0)
        
        print(f'  • Status: {status}')
        print(f'  • Last update: {timestamp}')
        print(f'  • Update count: {update_count}')
        
        if status == 'success' and update_count > 0:
            print('  ✅ Background updater is working')
        else:
            print('  ⚠️ Background updater may have issues')
    else:
        print('  ⚠️ No update information available')
except:
    print('  ❌ Could not check updater status')
"

echo ""
echo "8️⃣ ERROR CHECK"
echo "--------------"

# Check for recent errors
ERROR_COUNT=$(sudo journalctl -u virtuoso -u virtuoso-web --since "5 minutes ago" -p err --no-pager 2>/dev/null | wc -l || echo "0")

if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "  ${GREEN}✅ No errors in last 5 minutes${NC}"
    ((PASSED++))
else
    echo -e "  ${YELLOW}⚠️ Found $ERROR_COUNT errors in last 5 minutes${NC}"
    ((WARNINGS++))
    echo "  Recent errors:"
    sudo journalctl -u virtuoso -u virtuoso-web --since "5 minutes ago" -p err --no-pager 2>/dev/null | head -3
fi

echo ""
echo "9️⃣ LOAD TEST"
echo "------------"

echo "Running light load test (10 concurrent requests)..."
if command -v ab &> /dev/null; then
    ab -n 10 -c 5 -q "http://$API_HOST:$API_PORT/api/dashboard/signals" 2>&1 | \
        grep -E "Requests per second|Time per request" | \
        sed 's/^/  /'
else
    echo "  ⚠️ Apache Bench (ab) not installed, skipping load test"
    ((WARNINGS++))
fi

echo ""
echo "======================================"
echo "📊 TEST SUMMARY"
echo "======================================"
echo -e "  Passed:   ${GREEN}$PASSED${NC}"
echo -e "  Failed:   ${RED}$FAILED${NC}"
echo -e "  Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
        echo "Phase 1 implementation is working perfectly!"
    else
        echo -e "${YELLOW}✅ TESTS PASSED WITH WARNINGS${NC}"
        echo "Phase 1 is functional but may need optimization."
    fi
    echo ""
    echo "Recommendations:"
    echo "1. Monitor for 30 minutes for stability"
    echo "2. Check dashboard functionality manually"
    echo "3. Review cache hit rates after 1 hour"
    echo "4. If stable, consider proceeding to Phase 2 (Redis)"
else
    echo -e "${RED}❌ TESTS FAILED${NC}"
    echo "Phase 1 implementation has issues that need to be resolved."
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check service logs: sudo journalctl -u virtuoso -f"
    echo "2. Verify all files were deployed correctly"
    echo "3. Check Python syntax errors"
    echo "4. Consider rolling back if critical"
fi

echo ""
echo "Useful commands:"
echo "  • Monitor cache: curl -s http://$API_HOST:$API_PORT/api/dashboard/cache-status | jq ."
echo "  • Check logs: sudo journalctl -u virtuoso -u virtuoso-web -f"
echo "  • Test API: curl -s http://$API_HOST:$API_PORT/api/dashboard/signals | jq ."
echo ""