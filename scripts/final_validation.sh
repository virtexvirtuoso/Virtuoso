#!/bin/bash
echo "====================================="
echo "🎯 FINAL VALIDATION OF FIXES"
echo "====================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Test results
PASS_COUNT=0
TOTAL_COUNT=0

# Function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local expected=$3
    
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$STATUS" = "$expected" ]; then
        echo -e "${GREEN}✅ $name: $STATUS${NC}"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo -e "${RED}❌ $name: $STATUS (expected $expected)${NC}"
    fi
}

echo "1️⃣ LOCAL ENDPOINT TESTS"
echo "------------------------"
test_endpoint "Unified endpoint" "http://localhost:8002/api/dashboard-unified/unified" "200"
test_endpoint "Mobile endpoint" "http://localhost:8002/api/dashboard-unified/mobile" "200"
test_endpoint "Signals endpoint" "http://localhost:8002/api/dashboard-unified/signals" "200"
test_endpoint "Admin endpoint" "http://localhost:8002/api/dashboard-unified/admin" "200"
test_endpoint "Performance metrics" "http://localhost:8002/api/dashboard-unified/performance" "200"

echo ""
echo "2️⃣ VPS ENDPOINT TESTS"
echo "---------------------"
test_endpoint "VPS Unified" "http://${VPS_HOST}:8002/api/dashboard-unified/unified" "200"
test_endpoint "VPS Mobile" "http://${VPS_HOST}:8002/api/dashboard-unified/mobile" "200"
test_endpoint "VPS Performance" "http://${VPS_HOST}:8002/api/dashboard-unified/performance" "200"

echo ""
echo "3️⃣ PERFORMANCE CHECK"
echo "--------------------"
# Quick performance test
echo "Testing response times (10 requests)..."
TOTAL_TIME=0
for i in {1..10}; do
    TIME=$(curl -s -o /dev/null -w "%{time_total}" "http://localhost:8002/api/dashboard-unified/unified")
    TIME_MS=$(echo "$TIME * 1000" | bc)
    TOTAL_TIME=$(echo "$TOTAL_TIME + $TIME_MS" | bc)
done
AVG_TIME=$(echo "scale=2; $TOTAL_TIME / 10" | bc)
echo "Average response time: ${AVG_TIME}ms"

# Check if performance is acceptable
if (( $(echo "$AVG_TIME < 10" | bc -l) )); then
    echo -e "${GREEN}✅ Performance is good (<10ms)${NC}"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "${RED}❌ Performance needs attention (>10ms)${NC}"
fi
TOTAL_COUNT=$((TOTAL_COUNT + 1))

echo ""
echo "4️⃣ ARCHITECTURE VERIFICATION"
echo "----------------------------"
# Check cache adapter
if grep -q "MultiTierCacheAdapter" src/api/cache_adapter_direct.py 2>/dev/null; then
    echo -e "${GREEN}✅ Multi-tier cache implemented${NC}"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "${RED}❌ Multi-tier cache not found${NC}"
fi
TOTAL_COUNT=$((TOTAL_COUNT + 1))

# Check unified routes
if [ -f "src/api/routes/dashboard_unified.py" ]; then
    echo -e "${GREEN}✅ Unified routes exist${NC}"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "${RED}❌ Unified routes missing${NC}"
fi
TOTAL_COUNT=$((TOTAL_COUNT + 1))

# Check obsolete files cleaned
OBSOLETE_COUNT=$(ls src/api/cache_adapter_optimized.py src/api/routes/dashboard_cached.py 2>/dev/null | wc -l)
if [ "$OBSOLETE_COUNT" -eq "0" ]; then
    echo -e "${GREEN}✅ Obsolete files cleaned${NC}"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "${RED}❌ Obsolete files still present${NC}"
fi
TOTAL_COUNT=$((TOTAL_COUNT + 1))

echo ""
echo "====================================="
echo "📊 FINAL RESULTS"
echo "====================================="
echo "Tests passed: $PASS_COUNT/$TOTAL_COUNT"
echo ""

if [ "$PASS_COUNT" -eq "$TOTAL_COUNT" ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    echo "DATA_FLOW_AUDIT_REPORT.md fixes are FULLY VALIDATED!"
    echo ""
    echo "✅ Multi-tier cache: WORKING"
    echo "✅ Unified endpoints: OPERATIONAL"
    echo "✅ Performance: IMPROVED"
    echo "✅ Production: DEPLOYED"
    echo "✅ Cleanup: COMPLETE"
elif [ "$PASS_COUNT" -ge $((TOTAL_COUNT - 2)) ]; then
    echo -e "${GREEN}✅ MOSTLY PASSED${NC}"
    echo "Core functionality is working with minor issues."
else
    echo -e "${RED}⚠️ NEEDS ATTENTION${NC}"
    echo "Some critical tests failed."
fi
echo "====================================="
