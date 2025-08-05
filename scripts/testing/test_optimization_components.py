#!/usr/bin/env python3
"""
Test script for API optimization components:
1. API Request Queue
2. API Cache Manager  
3. Optimized Bybit Exchange Integration

This tests the actual optimization modules, not a web server.
"""

import asyncio
import sys
import time
from pathlib import Path
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.api_request_queue import APIRequestQueue, RequestPriority
from src.core.api_cache_manager import APICacheManager, CacheStrategy, CacheConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_request_queue():
    """Test the API Request Queue functionality."""
    logger.info("\n=== Testing API Request Queue ===")
    
    queue = APIRequestQueue(
        max_concurrent=3,
        rate_limit=5,
        cache_ttl=10,
        max_retries=2
    )
    
    await queue.start()
    
    # Track results
    results = []
    
    # Create test callback
    async def mock_api_call(endpoint, method, params):
        """Simulate API call with delay."""
        await asyncio.sleep(0.5)  # Simulate network delay
        result = {
            'endpoint': endpoint,
            'method': method,
            'params': params,
            'timestamp': time.time(),
            'data': f"Response for {endpoint}"
        }
        results.append(result)
        return result
    
    # Test 1: Basic queuing
    logger.info("\n1. Testing basic request queuing...")
    
    # Queue multiple requests
    request_ids = []
    for i in range(5):
        request_id = await queue.enqueue(
            endpoint=f"/test/endpoint{i}",
            method="GET",
            params={'index': i},
            callback=mock_api_call,
            priority=RequestPriority.NORMAL
        )
        request_ids.append(request_id)
        logger.info(f"  Queued request {i}: {request_id}")
    
    # Wait for processing
    await asyncio.sleep(3)
    
    # Check results
    logger.info(f"  Processed {len(results)} requests")
    assert len(results) >= 3, "Should have processed at least 3 requests"
    
    # Test 2: Priority handling
    logger.info("\n2. Testing priority handling...")
    results.clear()
    
    # Queue requests with different priorities
    await queue.enqueue(
        endpoint="/low/priority",
        method="GET",
        params={},
        callback=mock_api_call,
        priority=RequestPriority.LOW
    )
    
    await queue.enqueue(
        endpoint="/critical/priority",
        method="GET",
        params={},
        callback=mock_api_call,
        priority=RequestPriority.CRITICAL
    )
    
    await queue.enqueue(
        endpoint="/normal/priority",
        method="GET",
        params={},
        callback=mock_api_call,
        priority=RequestPriority.NORMAL
    )
    
    # Wait and check order
    await asyncio.sleep(2)
    
    # Critical should be processed first
    if len(results) > 0:
        logger.info(f"  First processed: {results[0]['endpoint']} (should be critical)")
        assert "/critical/priority" in results[0]['endpoint'], "Critical priority should be processed first"
    
    # Test 3: Rate limiting
    logger.info("\n3. Testing rate limiting...")
    results.clear()
    start_time = time.time()
    
    # Queue many requests at once
    for i in range(10):
        await queue.enqueue(
            endpoint=f"/rate/test{i}",
            method="GET",
            params={},
            callback=mock_api_call,
            priority=RequestPriority.NORMAL
        )
    
    # Wait for all to process
    await asyncio.sleep(3)
    
    elapsed = time.time() - start_time
    logger.info(f"  Processed {len(results)} requests in {elapsed:.1f}s")
    logger.info(f"  Rate: {len(results)/elapsed:.1f} req/s (limit: {queue.rate_limit})")
    
    # Test 4: Caching
    logger.info("\n4. Testing request caching...")
    results.clear()
    
    # Make same request twice
    endpoint = "/cached/endpoint"
    params = {'test': 'value'}
    
    # First request
    request_id1 = await queue.enqueue(
        endpoint=endpoint,
        method="GET",
        params=params,
        callback=mock_api_call,
        priority=RequestPriority.NORMAL,
        use_cache=True
    )
    
    await asyncio.sleep(1)
    
    # Second request (should be cached)
    request_id2 = await queue.enqueue(
        endpoint=endpoint,
        method="GET",
        params=params,
        callback=mock_api_call,
        priority=RequestPriority.NORMAL,
        use_cache=True
    )
    
    logger.info(f"  First request: {request_id1}")
    logger.info(f"  Second request: {request_id2} (should be cached)")
    assert request_id2.startswith("cached_"), "Second request should be served from cache"
    
    # Get stats
    stats = queue.get_stats()
    logger.info(f"\n  Queue Statistics:")
    logger.info(f"    Total requests: {stats['total_requests']}")
    logger.info(f"    Failed requests: {stats['failed_requests']}")
    logger.info(f"    Cache hits: {stats['cache_hits']}")
    logger.info(f"    Cache hit rate: {stats['cache_hit_rate']:.1%}")
    
    await queue.stop()
    
    logger.info("\n✅ Request Queue tests completed successfully!")
    return True


async def test_cache_manager():
    """Test the API Cache Manager functionality."""
    logger.info("\n=== Testing API Cache Manager ===")
    
    cache = APICacheManager()
    await cache.start()
    
    # Test 1: Basic caching
    logger.info("\n1. Testing basic caching...")
    
    # Store response
    test_response = {
        'retCode': 0,
        'data': {'price': 50000, 'volume': 100}
    }
    
    await cache.set(
        endpoint="/v5/market/tickers",
        method="GET",
        params={'symbol': 'BTCUSDT'},
        headers=None,
        response=test_response
    )
    
    # Retrieve from cache
    cached = await cache.get(
        endpoint="/v5/market/tickers",
        method="GET",
        params={'symbol': 'BTCUSDT'},
        headers=None
    )
    
    assert cached is not None, "Should retrieve cached response"
    assert cached['data']['price'] == 50000, "Cached data should match"
    logger.info("  ✅ Basic caching works")
    
    # Test 2: Cache strategies
    logger.info("\n2. Testing cache strategies...")
    
    # Test different endpoints
    endpoints = [
        ("/v5/market/instruments-info", CacheStrategy.AGGRESSIVE, 3600),
        ("/v5/market/tickers", CacheStrategy.MODERATE, 10),
        ("/v5/market/orderbook", CacheStrategy.CONSERVATIVE, 2),
        ("/v5/order/create", CacheStrategy.NO_CACHE, 0)
    ]
    
    for endpoint, expected_strategy, expected_ttl in endpoints:
        config = CacheConfig.get_config(endpoint)
        logger.info(f"  {endpoint}: {config.strategy.value} (TTL: {config.ttl}s)")
        assert config.strategy == expected_strategy, f"Wrong strategy for {endpoint}"
        assert config.ttl == expected_ttl, f"Wrong TTL for {endpoint}"
    
    # Test 3: TTL expiration
    logger.info("\n3. Testing TTL expiration...")
    
    # Store with short TTL
    await cache.set(
        endpoint="/v5/market/orderbook",  # Conservative cache (2s TTL)
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
    assert cached is not None, "Should be cached immediately"
    
    # Wait for expiration
    await asyncio.sleep(3)
    
    # Should be expired
    cached = await cache.get(
        endpoint="/v5/market/orderbook",
        method="GET",
        params={'symbol': 'ETHUSDT'},
        headers=None
    )
    assert cached is None, "Should be expired after TTL"
    logger.info("  ✅ TTL expiration works")
    
    # Test 4: No cache for critical operations
    logger.info("\n4. Testing no-cache for critical operations...")
    
    # Try to cache order creation (should not cache)
    await cache.set(
        endpoint="/v5/order/create",
        method="POST",
        params={'order': 'data'},
        headers=None,
        response={'retCode': 0, 'orderId': '12345'}
    )
    
    # Should not be cached
    cached = await cache.get(
        endpoint="/v5/order/create",
        method="POST",
        params={'order': 'data'},
        headers=None
    )
    assert cached is None, "Critical operations should not be cached"
    logger.info("  ✅ No-cache strategy works")
    
    # Get statistics
    stats = cache.get_statistics()
    logger.info(f"\n  Cache Statistics:")
    logger.info(f"    Total requests: {stats['total_requests']}")
    logger.info(f"    Cache bypasses: {stats['cache_bypasses']}")
    logger.info(f"    Overall hit rate: {stats['overall_hit_rate']:.1f}%")
    
    for strategy, strategy_stats in stats['strategy_stats'].items():
        logger.info(f"    {strategy}: Size={strategy_stats['size']}, Hit rate={strategy_stats['hit_rate']:.1f}%")
    
    await cache.stop()
    
    logger.info("\n✅ Cache Manager tests completed successfully!")
    return True


async def test_integration():
    """Test integration of optimization components."""
    logger.info("\n=== Testing Integration ===")
    
    try:
        # Import optimized exchange
        from src.core.exchanges.bybit_optimized import OptimizedBybitExchange, create_optimized_bybit_exchange
        
        logger.info("✅ Successfully imported OptimizedBybitExchange")
        
        # Check if all components are accessible
        exchange_config = {
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'testnet': True
        }
        
        # Create instance (but don't initialize - no real API calls)
        exchange = create_optimized_bybit_exchange(exchange_config)
        
        # Check attributes
        assert hasattr(exchange, 'request_queue'), "Should have request_queue"
        assert hasattr(exchange, 'cache_manager'), "Should have cache_manager"
        assert hasattr(exchange, 'optimization_stats'), "Should have optimization_stats"
        
        logger.info("✅ OptimizedBybitExchange has all required components")
        
        # Check methods
        assert hasattr(exchange, '_make_request_optimized'), "Should have optimized request method"
        assert hasattr(exchange, 'fetch_ticker'), "Should have fetch_ticker"
        assert hasattr(exchange, 'fetch_multiple_tickers'), "Should have batch operations"
        
        logger.info("✅ All optimization methods are present")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Integration test error: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("🚀 Starting API Optimization Component Tests")
    logger.info("=" * 50)
    
    results = {
        'request_queue': False,
        'cache_manager': False,
        'integration': False
    }
    
    # Test Request Queue
    try:
        results['request_queue'] = await test_request_queue()
    except Exception as e:
        logger.error(f"Request Queue test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Cache Manager
    try:
        results['cache_manager'] = await test_cache_manager()
    except Exception as e:
        logger.error(f"Cache Manager test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test Integration
    try:
        results['integration'] = await test_integration()
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📋 Test Summary")
    logger.info("=" * 50)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name.replace('_', ' ').title()}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        logger.info("\n🎉 All tests passed! The optimization components are working correctly.")
    else:
        logger.info("\n⚠️  Some tests failed. Please check the logs above.")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)