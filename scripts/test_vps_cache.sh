#!/bin/bash

echo "Testing cache deployment on VPS..."
echo ""

ssh linuxuser@45.77.40.77 << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt
/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python << 'PYTHON'
import asyncio
import sys
import time
sys.path.insert(0, '.')

async def test_cache():
    print("1. Testing cache initialization...")
    try:
        from src.core.cache.unified_cache import UnifiedCache
        cache = UnifiedCache()
        print("   ✓ Cache initialized")
    except Exception as e:
        print(f"   ✗ Failed to initialize: {e}")
        return
    
    print("\n2. Testing cache operations...")
    try:
        # Test set and get
        await cache.set("test_key", {"data": "test_value", "timestamp": time.time()}, ttl=60)
        result = await cache.get("test_key")
        if result and result.get("data") == "test_value":
            print("   ✓ Cache read/write working")
        else:
            print(f"   ✗ Cache read/write failed: {result}")
    except Exception as e:
        print(f"   ✗ Cache operation failed: {e}")
    
    print("\n3. Testing performance...")
    try:
        # Test performance
        key = "perf_test"
        value = {"data": list(range(1000))}
        
        # Write performance
        start = time.time()
        await cache.set(key, value, ttl=60)
        write_time = time.time() - start
        
        # Read performance (cache hit)
        start = time.time()
        result = await cache.get(key)
        read_time = time.time() - start
        
        print(f"   Write time: {write_time*1000:.2f}ms")
        print(f"   Read time: {read_time*1000:.2f}ms")
        
        if read_time < write_time:
            print("   ✓ Cache is faster than computation")
    except Exception as e:
        print(f"   ✗ Performance test failed: {e}")
    
    print("\n4. Testing indicator cache...")
    try:
        from src.core.cache.indicator_cache import IndicatorCache
        ind_cache = IndicatorCache()
        
        # Test indicator caching
        async def compute_indicator():
            await asyncio.sleep(0.1)  # Simulate computation
            return 75.5
        
        start = time.time()
        result1 = await ind_cache.get_indicator(
            indicator_type='technical',
            symbol='BTCUSDT',
            component='rsi',
            params={'period': 14},
            compute_func=compute_indicator
        )
        first_time = time.time() - start
        
        start = time.time()
        result2 = await ind_cache.get_indicator(
            indicator_type='technical',
            symbol='BTCUSDT',
            component='rsi',
            params={'period': 14},
            compute_func=compute_indicator
        )
        second_time = time.time() - start
        
        print(f"   First call: {first_time*1000:.2f}ms (result: {result1})")
        print(f"   Second call: {second_time*1000:.2f}ms (result: {result2})")
        
        if second_time < first_time / 10:
            print("   ✓ Indicator caching working effectively")
        else:
            print("   ⚠ Indicator caching may not be working properly")
    except Exception as e:
        print(f"   ✗ Indicator cache test failed: {e}")
    
    print("\n5. Cache metrics...")
    try:
        metrics = cache.get_metrics()
        print(f"   Hits: {metrics.get('hits', 0)}")
        print(f"   Misses: {metrics.get('misses', 0)}")
        print(f"   Hit rate: {metrics.get('hit_rate', 0):.1f}%")
    except Exception as e:
        print(f"   ✗ Failed to get metrics: {e}")

asyncio.run(test_cache())
PYTHON
EOF

echo ""
echo "Test complete!"