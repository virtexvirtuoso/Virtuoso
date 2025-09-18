#!/usr/bin/env python3
"""
Test aggressive memcached protocol error fixes
"""
import asyncio
import sys
import os
sys.path.append('/home/linuxuser/trading/Virtuoso_ccxt/src')

from src.api.cache_adapter_direct import DirectCacheAdapter

async def test_protocol_error_handling():
    """Test the aggressive protocol error handling"""
    
    print("🔬 Testing Aggressive Protocol Error Handling")
    print("=" * 60)
    
    cache = DirectCacheAdapter()
    
    # Test many concurrent operations to trigger protocol issues
    print("📝 Testing high-concurrency operations...")
    
    tasks = []
    for i in range(100):  # High number to stress test
        key = f"stress_test:{i}"
        value = {"test": i, "data": "x" * 100}  # Some data
        task = cache._set(key, value, ttl=30)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successes = sum(1 for r in results if r is True)
    errors = sum(1 for r in results if isinstance(r, Exception))
    failures = len(results) - successes - errors
    
    print(f"✅ Successful operations: {successes}")
    print(f"❌ Failed operations: {failures}")
    print(f"🚨 Exceptions: {errors}")
    
    # Check circuit breaker status
    print(f"\n⚡ Circuit breaker status:")
    print(f"   Open: {cache._memcached_circuit_breaker_open}")
    print(f"   Consecutive errors: {cache._memcached_consecutive_errors}")
    print(f"   Reset count: {cache._memcached_reset_count}")
    
    # Test health check
    print(f"\n🏥 Health check:")
    try:
        health = await cache._check_memcached_health()
        print(f"   Status: {'✅ Healthy' if health else '❌ Unhealthy'}")
    except Exception as e:
        print(f"   Status: ❌ Error - {e}")
    
    print(f"\n🎯 Stress test completed")

if __name__ == "__main__":
    asyncio.run(test_protocol_error_handling())
