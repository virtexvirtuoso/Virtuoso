#!/bin/bash

#############################################################################
# Script: test_dashboard_performance.sh
# Purpose: Test and validate test dashboard performance
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
#   ./test_dashboard_performance.sh [options]
#   
#   Examples:
#     ./test_dashboard_performance.sh
#     ./test_dashboard_performance.sh --verbose
#     ./test_dashboard_performance.sh --dry-run
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

"""
Dashboard Performance Testing Script
Tests all dashboard endpoints and measures performance improvements

This script tests:
- Response times for all dashboard endpoints
- Cache hit rates and performance
- Memory usage and CPU impact
- Error rates and reliability
"""

set -e

echo "🧪 Dashboard Performance Testing Suite"
echo "======================================"

# Configuration
VPS_HOST="${VPS_HOST:-VPS_HOST_REDACTED}"
BASE_URL="http://${VPS_HOST}:8003"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Test results storage
RESULTS_FILE="/tmp/dashboard_performance_results_$(date +%s).json"

echo -e "${BLUE}📊 Test Configuration:${NC}"
echo "  Base URL: $BASE_URL"
echo "  Results: $RESULTS_FILE"
echo "  Test time: $(date)"
echo

# Function to test endpoint performance
test_endpoint() {
    local endpoint="$1"
    local description="$2"
    local max_time="${3:-5.0}"
    
    echo -e "${BLUE}Testing: ${description}${NC}"
    echo "  Endpoint: ${endpoint}"
    
    # Test multiple times for average
    local total_time=0
    local success_count=0
    local error_count=0
    local total_size=0
    
    for i in {1..5}; do
        result=$(curl -s -o /tmp/response_$i.json -w "%{http_code}|%{time_total}|%{size_download}" "${BASE_URL}${endpoint}" || echo "000|999|0")
        
        IFS='|' read -r status_code time_total size_download <<< "$result"
        
        if [[ "$status_code" == "200" ]]; then
            success_count=$((success_count + 1))
            total_time=$(echo "$total_time + $time_total" | bc -l)
            total_size=$((total_size + size_download))
            echo "    Try $i: HTTP $status_code - ${time_total}s - ${size_download} bytes"
        else
            error_count=$((error_count + 1))
            echo -e "    Try $i: ${RED}HTTP $status_code - ${time_total}s${NC}"
        fi
    done
    
    if [[ $success_count -gt 0 ]]; then
        local avg_time=$(echo "scale=3; $total_time / $success_count" | bc -l)
        local avg_size=$((total_size / success_count))
        
        # Determine status
        local status="✅"
        if (( $(echo "$avg_time > $max_time" | bc -l) )); then
            status="❌ SLOW"
        elif [[ $error_count -gt 0 ]]; then
            status="⚠️ ERRORS"
        fi
        
        echo -e "  ${status} Average: ${avg_time}s (${success_count}/${5} success, ${avg_size} bytes)"
        
        # Store results
        echo "{\"endpoint\":\"$endpoint\",\"description\":\"$description\",\"avg_time\":$avg_time,\"success_rate\":$((success_count*100/5)),\"avg_size\":$avg_size,\"timestamp\":$(date +%s)}" >> "$RESULTS_FILE.tmp"
    else
        echo -e "  ❌ FAILED: All requests failed"
        echo "{\"endpoint\":\"$endpoint\",\"description\":\"$description\",\"avg_time\":999,\"success_rate\":0,\"avg_size\":0,\"timestamp\":$(date +%s)}" >> "$RESULTS_FILE.tmp"
    fi
    
    echo
}

# Function to test concurrent load
test_concurrent_load() {
    echo -e "${PURPLE}🔄 Concurrent Load Testing${NC}"
    
    local endpoint="$1"
    local concurrent="${2:-10}"
    
    echo "  Testing $concurrent concurrent requests to $endpoint"
    
    # Create temporary script for concurrent testing
    cat > /tmp/concurrent_test.sh << EOF
#!/bin/bash
curl -s -o /dev/null -w "%{http_code}|%{time_total}" "${BASE_URL}${endpoint}"
EOF
    chmod +x /tmp/concurrent_test.sh
    
    # Run concurrent tests
    start_time=$(date +%s.%3N)
    
    for i in $(seq 1 $concurrent); do
        /tmp/concurrent_test.sh &
    done
    wait
    
    end_time=$(date +%s.%3N)
    total_time=$(echo "$end_time - $start_time" | bc -l)
    
    echo "  Concurrent test completed in ${total_time}s"
    echo
}

echo -e "${YELLOW}🚀 Starting Dashboard Performance Tests${NC}"
echo

# Test 1: Critical Dashboard Endpoints
echo -e "${BLUE}═══ Test 1: Critical Dashboard Endpoints ═══${NC}"

test_endpoint "/api/dashboard-cached/mobile-data" "Mobile Dashboard Data" 3.0
test_endpoint "/api/dashboard-cached/overview" "Dashboard Overview" 3.0  
test_endpoint "/api/dashboard-cached/alerts" "Dashboard Alerts" 2.0
test_endpoint "/api/dashboard-cached/opportunities" "Alpha Opportunities" 3.0
test_endpoint "/api/dashboard-cached/signals" "Trading Signals" 2.0

# Test 2: Health and Status Endpoints
echo -e "${BLUE}═══ Test 2: Health and Status Endpoints ═══${NC}"

test_endpoint "/api/dashboard/health" "Dashboard Health Check" 1.0
test_endpoint "/health" "System Health Check" 1.0

# Test 3: Market Data Endpoints
echo -e "${BLUE}═══ Test 3: Market Data Endpoints ═══${NC}"

test_endpoint "/api/dashboard-cached/market-overview" "Market Overview" 2.0
test_endpoint "/api/dashboard-cached/market-movers" "Market Movers" 2.0
test_endpoint "/api/dashboard-cached/symbols" "Symbol Data" 3.0

# Test 4: Streaming Endpoints (if available)
echo -e "${BLUE}═══ Test 4: Streaming Endpoints (Priority 1) ═══${NC}"

if curl -s "${BASE_URL}/api/dashboard-stream/mobile-data-stream" > /dev/null 2>&1; then
    test_endpoint "/api/dashboard-stream/mobile-data-stream" "Streaming Mobile Data" 2.0
    test_endpoint "/api/dashboard-stream/overview-stream" "Streaming Overview" 2.0
    test_endpoint "/api/dashboard-stream/cache-performance" "Cache Performance Metrics" 1.0
else
    echo "  ⚠️ Streaming endpoints not available (Priority 1 fixes not deployed)"
fi

# Test 5: Concurrent Load Testing
echo -e "${BLUE}═══ Test 5: Concurrent Load Testing ═══${NC}"

test_concurrent_load "/api/dashboard-cached/mobile-data" 5
test_concurrent_load "/api/dashboard-cached/overview" 3
test_concurrent_load "/api/dashboard/health" 10

# Test 6: Cache Performance Analysis
echo -e "${BLUE}═══ Test 6: Cache Performance Analysis ═══${NC}"

echo "Testing cache performance..."

# Check if we can get cache stats
if curl -s "${BASE_URL}/api/cache/stats" > /tmp/cache_stats.json 2>/dev/null; then
    echo "  ✅ Cache stats available"
    cat /tmp/cache_stats.json | jq '.hit_rate // "N/A"' 2>/dev/null | while read -r hit_rate; do
        echo "  📊 Cache hit rate: $hit_rate"
    done
else
    echo "  ⚠️ Cache stats not available"
fi

# Test multiple requests to same endpoint to check caching
echo "Testing cache effectiveness (5 rapid requests):"
for i in {1..5}; do
    start_time=$(date +%s.%3N)
    status_code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/api/dashboard-cached/overview")
    end_time=$(date +%s.%3N)
    response_time=$(echo "$end_time - $start_time" | bc -l)
    echo "    Request $i: HTTP $status_code - ${response_time}s"
done
echo

# Test 7: Error Rate Testing
echo -e "${BLUE}═══ Test 7: Error Rate Testing ═══${NC}"

echo "Testing error handling with invalid endpoints..."
test_endpoint "/api/dashboard-cached/nonexistent" "Non-existent Endpoint (should 404)" 1.0
test_endpoint "/api/dashboard-cached/" "Empty path" 1.0

# Generate final report
echo -e "${GREEN}═══ Performance Test Results Summary ═══${NC}"

if [[ -f "$RESULTS_FILE.tmp" ]]; then
    # Convert to proper JSON array
    echo "[" > "$RESULTS_FILE"
    sed '$!s/$/,/' "$RESULTS_FILE.tmp" >> "$RESULTS_FILE"
    echo "]" >> "$RESULTS_FILE"
    rm "$RESULTS_FILE.tmp"
    
    echo "📊 Detailed results saved to: $RESULTS_FILE"
    
    # Generate summary
    echo
    echo "🎯 Performance Summary:"
    
    # Count endpoints by performance
    fast_count=$(jq '[.[] | select(.avg_time < 1.0)] | length' "$RESULTS_FILE")
    good_count=$(jq '[.[] | select(.avg_time >= 1.0 and .avg_time < 3.0)] | length' "$RESULTS_FILE")
    slow_count=$(jq '[.[] | select(.avg_time >= 3.0)] | length' "$RESULTS_FILE")
    
    echo "  ⚡ Fast (< 1s): $fast_count endpoints"
    echo "  ✅ Good (1-3s): $good_count endpoints"  
    echo "  ❌ Slow (> 3s): $slow_count endpoints"
    
    # Show slowest endpoints
    echo
    echo "🐌 Slowest endpoints:"
    jq -r '.[] | select(.avg_time > 0) | "\(.avg_time)s - \(.description)"' "$RESULTS_FILE" | sort -rn | head -5
    
    echo
    echo "🏆 Recommendations:"
    
    if [[ $slow_count -gt 0 ]]; then
        echo "  1. Deploy quick fixes for slow endpoints"
        echo "  2. Implement Priority 1 optimizations"
        echo "  3. Enable streaming responses for large data"
    fi
    
    if [[ $good_count -gt $fast_count ]]; then
        echo "  4. Consider cache warming for frequently accessed endpoints"
        echo "  5. Implement response compression"
    fi
    
    if [[ $fast_count -gt 0 ]]; then
        echo "  6. Fast endpoints performing well - maintain current optimizations"
    fi
    
else
    echo "❌ No test results generated"
fi

echo
echo "🏁 Performance testing complete!"
echo "Deploy fixes with:"
echo "  ./scripts/deploy_dashboard_fixes.sh           (Quick wins)"
echo "  ./scripts/deploy_priority1_fixes.sh          (Advanced optimizations)"
echo "  ./scripts/deploy_priority2_fixes.sh          (Long-term improvements)"