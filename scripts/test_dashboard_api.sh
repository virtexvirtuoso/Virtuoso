#!/bin/bash

# Test script to simulate browser Promise.all fetch behavior
# This simulates the exact sequence from dashboard_mobile_v2.html loadDashboardData()

BASE_URL="${VPS_BASE_URL:-http://localhost:8002}"
ENDPOINTS=(
    "api/dashboard/overview"
    "api/dashboard/symbols"
    "api/dashboard/market-overview"
    "api/dashboard/mobile-data"
)

echo "================================================"
echo "Testing Dashboard API - Browser Simulation"
echo "================================================"
echo ""

# Test 1: Individual endpoint health
echo "[1/5] Testing individual endpoint health..."
for endpoint in "${ENDPOINTS[@]}"; do
    echo -n "  Testing /$endpoint... "
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/$endpoint")
    status_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [ "$status_code" = "200" ]; then
        # Validate JSON
        if echo "$body" | python3 -c "import sys, json; json.load(sys.stdin)" 2>/dev/null; then
            echo "✓ OK (HTTP $status_code, Valid JSON)"
        else
            echo "✗ FAIL (HTTP $status_code, Invalid JSON)"
            echo "     First 100 chars: ${body:0:100}"
        fi
    else
        echo "✗ FAIL (HTTP $status_code)"
    fi
done
echo ""

# Test 2: CORS headers
echo "[2/5] Testing CORS headers..."
for endpoint in "${ENDPOINTS[@]}"; do
    echo -n "  Testing /$endpoint... "
    cors_header=$(curl -s -I -H "Origin: ${VPS_BASE_URL:-http://localhost:8002}" "$BASE_URL/$endpoint" | grep -i "access-control-allow-origin")
    if [ -n "$cors_header" ]; then
        echo "✓ CORS OK: $cors_header"
    else
        echo "✗ CORS MISSING"
    fi
done
echo ""

# Test 3: Parallel requests (simulating Promise.all)
echo "[3/5] Testing parallel requests (Promise.all simulation)..."
start_time=$(date +%s)

# Make all requests in parallel
curl -s -w "\nStatus: %{http_code}\nTime: %{time_total}s\n" "$BASE_URL/${ENDPOINTS[0]}" > /tmp/test_overview.txt &
pid1=$!
curl -s -w "\nStatus: %{http_code}\nTime: %{time_total}s\n" "$BASE_URL/${ENDPOINTS[1]}" > /tmp/test_symbols.txt &
pid2=$!
curl -s -w "\nStatus: %{http_code}\nTime: %{time_total}s\n" "$BASE_URL/${ENDPOINTS[2]}" > /tmp/test_market.txt &
pid3=$!
curl -s -w "\nStatus: %{http_code}\nTime: %{time_total}s\n" "$BASE_URL/${ENDPOINTS[3]}" > /tmp/test_mobile.txt &
pid4=$!

# Wait for all to complete
wait $pid1 $pid2 $pid3 $pid4
end_time=$(date +%s)
total_time=$((end_time - start_time))

echo "  All requests completed in ${total_time}s"
echo ""

# Validate parallel request results
echo "[4/5] Validating parallel request results..."
for file in /tmp/test_{overview,symbols,market,mobile}.txt; do
    endpoint=$(basename "$file" | sed 's/test_//;s/.txt//')
    echo -n "  $endpoint: "

    # Extract status code
    status=$(grep "^Status:" "$file" | awk '{print $2}')
    time=$(grep "^Time:" "$file" | awk '{print $2}')

    # Get response body (everything except last 2 lines)
    body=$(head -n -2 "$file")

    if [ "$status" = "200" ]; then
        if echo "$body" | python3 -c "import sys, json; json.load(sys.stdin)" 2>/dev/null; then
            echo "✓ OK (HTTP $status, ${time}, Valid JSON)"
        else
            echo "✗ FAIL (HTTP $status, ${time}, Invalid JSON)"
        fi
    else
        echo "✗ FAIL (HTTP $status, ${time})"
    fi
done
echo ""

# Test 5: Browser simulation with timing
echo "[5/5] Simulating exact browser fetch sequence..."
python3 << 'PYTHON_SCRIPT'
import asyncio
import aiohttp
import time
import json

async def fetch_endpoint(session, url, name):
    """Simulate a single fetch call"""
    start = time.time()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            data = await response.json()
            elapsed = time.time() - start
            print(f"  {name}: ✓ OK (HTTP {response.status}, {elapsed:.3f}s, {len(str(data))} bytes)")
            return True
    except asyncio.TimeoutError:
        elapsed = time.time() - start
        print(f"  {name}: ✗ TIMEOUT after {elapsed:.3f}s")
        return False
    except json.JSONDecodeError as e:
        elapsed = time.time() - start
        print(f"  {name}: ✗ JSON ERROR ({e}) after {elapsed:.3f}s")
        return False
    except Exception as e:
        elapsed = time.time() - start
        print(f"  {name}: ✗ ERROR ({type(e).__name__}: {e}) after {elapsed:.3f}s")
        return False

async def simulate_promise_all():
    """Simulate JavaScript Promise.all([fetch1, fetch2, fetch3, fetch4])"""
    base_url = "${VPS_BASE_URL:-http://localhost:8002}"
    endpoints = [
        ("api/dashboard/overview", "overview"),
        ("api/dashboard/symbols", "symbols"),
        ("api/dashboard/market-overview", "market-overview"),
        ("api/dashboard/mobile-data", "mobile-data"),
    ]

    start = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_endpoint(session, f"{base_url}/{endpoint}", name)
            for endpoint, name in endpoints
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.time() - start
    success = all(r is True for r in results)

    print(f"\n  Total Promise.all time: {elapsed:.3f}s")
    if success:
        print("  ✓ All requests succeeded (Promise.all would resolve)")
    else:
        print("  ✗ At least one request failed (Promise.all would reject)")

    return success

# Run the simulation
asyncio.run(simulate_promise_all())
PYTHON_SCRIPT

echo ""
echo "================================================"
echo "Test Complete"
echo "================================================"

# Cleanup
rm -f /tmp/test_*.txt
