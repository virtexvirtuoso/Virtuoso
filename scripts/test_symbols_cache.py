#!/usr/bin/env python3
"""
Test symbols cache and API endpoints
"""

import sys
import time
import json
import requests
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')

print("=" * 60)
print("🧪 TESTING SYMBOLS CACHE AND API")
print("=" * 60)
print()

# Test 1: Direct cache access
print("Test 1: Direct Cache Access")
print("-" * 40)
from src.core.api_cache import api_cache

# Wait for a cache update
print("Waiting for cache update cycle...")
time.sleep(3)

# Try to get symbols
symbols_data = api_cache.get("symbols")
if symbols_data and "symbols" in symbols_data:
    symbols = symbols_data["symbols"]
    print(f"✅ Cache has {len(symbols)} symbols")
    for s in symbols[:3]:
        print(f"  {s.get('symbol')}: score={s.get('confluence_score')}, dir={s.get('direction')}")
else:
    print("❌ No symbols in cache")

print()

# Test 2: Main service API
print("Test 2: Main Service API (port 8003)")
print("-" * 40)
try:
    response = requests.get("http://localhost:8003/api/symbols", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API responded: {len(data.get('symbols', []))} symbols")
        print(f"  Status: {data.get('status', 'unknown')}")
    else:
        print(f"❌ API error: {response.status_code}")
except Exception as e:
    print(f"❌ API connection failed: {e}")

print()

# Test 3: Dashboard API
print("Test 3: Dashboard API (port 8001)")
print("-" * 40)
try:
    response = requests.get("http://localhost:8001/api/symbols", timeout=5)
    if response.status_code == 200:
        data = response.json()
        symbols = data.get("symbols", [])
        print(f"✅ Dashboard API: {len(symbols)} symbols")
        if symbols:
            s = symbols[0]
            print(f"  First: {s.get('symbol')} = {s.get('confluence_score')}")
    else:
        print(f"❌ Dashboard API error: {response.status_code}")
except Exception as e:
    print(f"❌ Dashboard API failed: {e}")

print()

# Test 4: Check cache persistence
print("Test 4: Cache Persistence Test")
print("-" * 40)

# Set a test value
test_data = {
    "symbols": [
        {"symbol": "TESTUSDT", "confluence_score": 75, "direction": "Bullish"}
    ],
    "timestamp": time.time()
}

api_cache.set("test_symbols", test_data, ttl_seconds=60)
print("Set test data in cache")

# Get it back
retrieved = api_cache.get("test_symbols")
if retrieved and retrieved.get("symbols"):
    print(f"✅ Cache persistence works: {retrieved['symbols'][0]['symbol']}")
else:
    print("❌ Cache persistence failed")

print()
print("=" * 60)
print("DIAGNOSIS")
print("=" * 60)

# Final diagnosis
if symbols_data:
    print("✅ Cache is populated with symbols")
else:
    print("❌ ISSUE: Cache is not retaining symbols data")
    print("   Possible causes:")
    print("   1. Multiple api_cache instances")
    print("   2. TTL too short (currently 30s)")
    print("   3. Cache being cleared elsewhere")
    print("   4. Dashboard updater using different cache instance")