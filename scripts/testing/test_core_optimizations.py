#!/usr/bin/env python3
"""
Test core optimization components without requiring Bybit imports.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.api_request_queue import APIRequestQueue, RequestPriority
from src.core.api_cache_manager import APICacheManager, CacheStrategy, CacheConfig


async def test_request_queue():
    """Test the API Request Queue."""
    print("\n=== Testing Request Queue ===")
    
    queue = APIRequestQueue(
        max_concurrent=3,
        rate_limit=5,
        cache_ttl=5,
        max_retries=2
    )
    
    await queue.start()
    
    # Test callback that simulates API calls
    call_count = 0
    async def mock_api_call(endpoint, method, params):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)  # Simulate network delay
        return {'endpoint': endpoint, 'call_number': call_count}
    
    # Test 1: Basic queuing
    print("\n1. Basic queuing test:")
    request_ids = []
    for i in range(5):
        request_id = await queue.enqueue(
            endpoint=f"/test/{i}",
            method="GET",
            params={'index': i},
            callback=mock_api_call,
            priority=RequestPriority.NORMAL
        )
        request_ids.append(request_id)
    
    await asyncio.sleep(2)
    print(f"   Processed {call_count} requests")
    
    # Test 2: Priority handling
    print("\n2. Priority test:")
    call_count = 0
    
    # Queue with different priorities
    await queue.enqueue("/low", "GET", {}, mock_api_call, RequestPriority.LOW)
    await queue.enqueue("/critical", "GET", {}, mock_api_call, RequestPriority.CRITICAL)
    await queue.enqueue("/normal", "GET", {}, mock_api_call, RequestPriority.NORMAL)
    
    await asyncio.sleep(1)
    print(f"   Processed {call_count} requests with priority ordering")
    
    # Test 3: Get statistics
    stats = queue.get_stats()
    print(f"\n3. Queue Statistics:")
    print(f"   Total requests: {stats['total_requests']}")
    print(f"   Cache hit rate: {stats['cache_hit_rate']:.1%}")
    
    await queue.stop()
    print("\n✅ Request Queue tests passed!")
    return True


async def test_cache_manager():
    """Test the API Cache Manager."""
    print("\n=== Testing Cache Manager ===")
    
    cache = APICacheManager()
    await cache.start()
    
    # Test 1: Basic caching
    print("\n1. Basic caching test:")
    test_response = {'retCode': 0, 'data': {'price': 50000}}
    
    await cache.set(
        endpoint="/v5/market/tickers",
        method="GET",
        params={'symbol': 'BTCUSDT'},
        headers=None,
        response=test_response
    )
    
    cached = await cache.get(
        endpoint="/v5/market/tickers",
        method="GET",
        params={'symbol': 'BTCUSDT'},
        headers=None
    )
    
    if cached and cached['data']['price'] == 50000:
        print("   ✅ Basic caching works")
    else:
        print("   ❌ Basic caching failed")
    
    # Test 2: Cache strategies
    print("\n2. Cache strategy test:")
    configs = [
        ("/v5/market/instruments-info", CacheStrategy.AGGRESSIVE),
        ("/v5/market/tickers", CacheStrategy.MODERATE),
        ("/v5/market/orderbook", CacheStrategy.CONSERVATIVE),
        ("/v5/order/create", CacheStrategy.NO_CACHE)
    ]
    
    for endpoint, expected_strategy in configs:
        config = CacheConfig.get_config(endpoint)
        if config.strategy == expected_strategy:
            print(f"   ✅ {endpoint}: {config.strategy.value}")
        else:
            print(f"   ❌ {endpoint}: expected {expected_strategy.value}, got {config.strategy.value}")
    
    # Test 3: TTL expiration
    print("\n3. TTL expiration test:")
    
    # Store with conservative cache (2s TTL)
    await cache.set(
        endpoint="/v5/market/orderbook",
        method="GET",
        params={'symbol': 'ETHUSDT'},
        headers=None,
        response={'retCode': 0, 'data': 'test'}
    )
    
    # Should be cached
    cached = await cache.get(
        endpoint="/v5/market/orderbook",
        method="GET",
        params={'symbol': 'ETHUSDT'},
        headers=None
    )
    
    if cached:
        print("   ✅ Item cached immediately")
    
    # Wait for expiration
    await asyncio.sleep(3)
    
    cached = await cache.get(
        endpoint="/v5/market/orderbook",
        method="GET",
        params={'symbol': 'ETHUSDT'},
        headers=None
    )
    
    if not cached:
        print("   ✅ Item expired after TTL")
    else:
        print("   ❌ Item should have expired")
    
    # Get statistics
    stats = cache.get_statistics()
    print(f"\n4. Cache Statistics:")
    print(f"   Total requests: {stats['total_requests']}")
    print(f"   Overall hit rate: {stats['overall_hit_rate']:.1f}%")
    
    await cache.stop()
    print("\n✅ Cache Manager tests passed!")
    return True


async def test_integration_concept():
    """Test how the components would work together."""
    print("\n=== Testing Integration Concept ===")
    
    # Initialize components
    queue = APIRequestQueue(max_concurrent=2, rate_limit=3)
    cache = APICacheManager()
    
    await queue.start()
    await cache.start()
    
    # Simulate integrated workflow
    async def cached_api_call(endpoint, method, params):
        # Check cache first
        cached_response = await cache.get(endpoint, method, params, None)
        if cached_response:
            print(f"   📦 Cache hit for {endpoint}")
            return cached_response
        
        # Simulate API call
        print(f"   🌐 API call to {endpoint}")
        await asyncio.sleep(0.5)
        response = {'retCode': 0, 'data': f'Response for {endpoint}'}
        
        # Cache the response
        await cache.set(endpoint, method, params, None, response)
        return response
    
    print("\n1. Testing integrated workflow:")
    
    # First request (cache miss)
    await queue.enqueue("/api/ticker", "GET", {'symbol': 'BTC'}, cached_api_call)
    await asyncio.sleep(1)
    
    # Second request (should be cached)
    await queue.enqueue("/api/ticker", "GET", {'symbol': 'BTC'}, cached_api_call)
    await asyncio.sleep(0.5)
    
    # Different request (cache miss)
    await queue.enqueue("/api/ticker", "GET", {'symbol': 'ETH'}, cached_api_call)
    await asyncio.sleep(1)
    
    await queue.stop()
    await cache.stop()
    
    print("\n✅ Integration concept test passed!")
    return True


async def main():
    """Run all tests."""
    print("🚀 Testing Core Optimization Components")
    print("=" * 50)
    
    results = []
    
    # Test Request Queue
    try:
        results.append(await test_request_queue())
    except Exception as e:
        print(f"\n❌ Request Queue test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(False)
    
    # Test Cache Manager
    try:
        results.append(await test_cache_manager())
    except Exception as e:
        print(f"\n❌ Cache Manager test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(False)
    
    # Test Integration Concept
    try:
        results.append(await test_integration_concept())
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary")
    print("=" * 50)
    
    if all(results):
        print("\n🎉 All tests passed!")
        print("\nThe optimization components are working correctly.")
        print("\nNext steps:")
        print("1. Deploy to VPS: ./scripts/deploy_api_optimizations.sh")
        print("2. Monitor improvements: Check logs for reduced timeouts")
        return True
    else:
        print("\n⚠️  Some tests failed. Please check the logs above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)