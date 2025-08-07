#!/usr/bin/env python3
"""
Test Phase 2 Cache Integration End-to-End
"""

import sys
import time
import json
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')

print("=" * 60)
print("🧪 PHASE 2 CACHE INTEGRATION TEST")
print("=" * 60)
print()

# Test 1: Memcached Direct
print("Test 1: Direct Memcached Connection")
print("-" * 40)
try:
    from pymemcache.client.base import Client
    client = Client(('127.0.0.1', 11211))
    
    # Write test
    start = time.perf_counter()
    client.set(b'phase2_test', b'{"status": "active", "phase": 2}', expire=30)
    write_time = (time.perf_counter() - start) * 1000
    
    # Read test
    start = time.perf_counter()
    result = client.get(b'phase2_test')
    read_time = (time.perf_counter() - start) * 1000
    
    client.close()
    
    print(f"✅ Memcached Direct: Write={write_time:.2f}ms, Read={read_time:.2f}ms")
    if read_time < 1:
        print("   🎉 Sub-millisecond achieved!")
except Exception as e:
    print(f"❌ Memcached Direct failed: {e}")

print()

# Test 2: Cache Router
print("Test 2: Cache Router Integration")
print("-" * 40)
try:
    from src.core.cache.cache_router import cache_router
    
    test_data = {"test": "phase2", "timestamp": time.time()}
    
    # Set via router
    start = time.perf_counter()
    success = cache_router.set("router_test", test_data, use_memcached=True)
    set_time = (time.perf_counter() - start) * 1000
    
    # Get via router
    start = time.perf_counter()
    data = cache_router.get("router_test", use_memcached=True)
    get_time = (time.perf_counter() - start) * 1000
    
    if data:
        print(f"✅ Cache Router: Set={set_time:.2f}ms, Get={get_time:.2f}ms")
        
        # Get stats
        stats = cache_router.get_stats()
        print(f"   Memcached ops: {stats.get('memcached_ops', 0)}")
        print(f"   Memory ops: {stats.get('memory_ops', 0)}")
        print(f"   Performance improvement: {stats.get('performance_improvement', 'N/A')}")
    else:
        print("❌ Cache Router failed to retrieve data")
        
except Exception as e:
    print(f"❌ Cache Router failed: {e}")

print()

# Test 3: Dashboard Proxy Phase 2
print("Test 3: Dashboard Proxy Phase 2")
print("-" * 40)
try:
    from src.dashboard.dashboard_proxy_phase2 import get_dashboard_integration_phase2
    
    proxy = get_dashboard_integration_phase2()
    
    # Check if cache router is available
    if proxy._cache_router:
        print("✅ Phase 2 Proxy initialized with cache router")
        
        # Simulate caching dashboard data
        test_overview = {
            "status": "test",
            "signals": {"total": 10, "strong": 3},
            "timestamp": time.time()
        }
        
        # Cache it
        start = time.perf_counter()
        proxy._cache_router.set("dashboard:overview", test_overview, ttl=10)
        cache_time = (time.perf_counter() - start) * 1000
        
        # Retrieve it
        start = time.perf_counter()
        cached = proxy._cache_router.get("dashboard:overview")
        retrieve_time = (time.perf_counter() - start) * 1000
        
        if cached:
            print(f"✅ Dashboard caching working: Cache={cache_time:.2f}ms, Retrieve={retrieve_time:.2f}ms")
        else:
            print("❌ Failed to retrieve cached dashboard data")
    else:
        print("❌ Phase 2 Proxy cache router not available")
        
except Exception as e:
    print(f"❌ Dashboard Proxy Phase 2 failed: {e}")

print()
print("=" * 60)
print("📊 INTEGRATION TEST SUMMARY")
print("=" * 60)

# Final verdict
try:
    from src.core.cache.cache_router import cache_router
    stats = cache_router.get_stats()
    
    if stats.get('memcached_available', False):
        print("✅ Phase 2 Memcached Integration: OPERATIONAL")
        print(f"   Average latency: {stats.get('avg_memcached_latency_ms', 'N/A')}")
    else:
        print("⚠️ Phase 2 Memcached: NOT AVAILABLE")
        print("   Falling back to Phase 1 memory cache")
        
    if stats.get('memory_cache_available', False):
        print("✅ Phase 1 Memory Cache: AVAILABLE (fallback)")
    else:
        print("❌ Phase 1 Memory Cache: NOT AVAILABLE")
        
except:
    print("❌ Unable to get integration status")

print()
print("Deo Gratias - Thanks be to God")