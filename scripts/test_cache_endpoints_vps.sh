#!/bin/bash

echo "Testing Cache Endpoints on VPS"
echo "=============================="
echo ""

# Test cache health endpoint first
echo "1. Testing cache health:"
curl -s http://45.77.40.77:8001/api/cache/health | python3 -m json.tool | head -n 10

echo ""
echo "2. Testing Phase 2 dashboard:"
curl -s http://45.77.40.77:8001/dashboard/phase2 | grep -o "<title>.*</title>" | head -n 1

echo ""
echo "3. Testing cache overview (Phase 2):"
curl -s http://45.77.40.77:8001/api/cache/cache/overview | python3 -m json.tool 2>/dev/null | head -n 10

echo ""
echo "4. Testing dashboard-cached endpoints (if available):"
for endpoint in overview market-overview signals; do
    echo "   - Testing /api/dashboard-cached/${endpoint}:"
    response=$(curl -s -w "\n[HTTP: %{http_code}, Time: %{time_total}s]" http://45.77.40.77:8001/api/dashboard-cached/${endpoint})
    echo "     ${response}" | tail -n 1
done

echo ""
echo "5. Testing regular dashboard endpoints (fallback):"
curl -s http://45.77.40.77:8001/api/dashboard/overview | python3 -m json.tool 2>/dev/null | head -n 5

echo ""
echo "=============================="
echo "Test Complete"