#!/usr/bin/env python3
"""
Test script for memcached protocol confusion fixes
"""
import asyncio
import sys
import os
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

from src.api.cache_adapter_direct import DirectCacheAdapter

async def test_memcached_safety():
    """Test memcached operations with the new safety measures"""
    
    print("🧪 Testing Memcached Protocol Safety")
    print("=" * 50)
    
    # Initialize cache adapter
    cache = DirectCacheAdapter()
    
    # Test multiple concurrent operations
    test_keys = [
        f"test:safety:{i}" for i in range(20)
    ]
    
    test_values = [
        {"value": i * 10, "timestamp": 1234567890 + i}
        for i in range(20)
    ]
    
    print("📝 Testing concurrent SET operations...")
    
    # Test concurrent sets
    tasks = []
    for i, (key, value) in enumerate(zip(test_keys, test_values)):
        task = cache._set(key, value, ttl=60)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in results if r is True)
    error_count = sum(1 for r in results if isinstance(r, Exception))
    
    print(f"✅ Successful operations: {success_count}")
    print(f"❌ Failed operations: {len(results) - success_count}")
    print(f"🚨 Exceptions: {error_count}")
    
    # Test health check
    print("\n🏥 Testing connection health...")
    health = await cache._check_memcached_health()
    print(f"Health status: {'✅ Healthy' if health else '❌ Unhealthy'}")
    
    # Test retrieval
    print("\n📖 Testing GET operations...")
    get_tasks = [cache._get_with_fallback(key) for key in test_keys[:5]]
    get_results = await asyncio.gather(*get_tasks, return_exceptions=True)
    
    successful_gets = sum(1 for r in get_results if not isinstance(r, Exception) and len(r) == 2 and r[1].name in ['HIT', 'FALLBACK'])
    print(f"✅ Successful retrievals: {successful_gets}/5")
    
    print("\n🎯 Test completed")

if __name__ == "__main__":
    asyncio.run(test_memcached_safety())
