#!/usr/bin/env python3
"""Validate that the cache tuple unpacking fix is working correctly across all components"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.cache.multi_tier_cache import MultiTierCacheAdapter, CacheLayer
from src.core.cache.indicator_cache import IndicatorCache
from src.api.cache_adapter_direct import DirectCacheAdapter

async def test_multi_tier_cache():
    """Test MultiTierCacheAdapter returns tuple correctly"""
    print("\n=== Testing MultiTierCacheAdapter ===")

    adapter = MultiTierCacheAdapter()

    # Test set and get
    test_key = "test:multi_tier"
    test_value = {"data": "test_value", "number": 123}

    await adapter.set(test_key, test_value, 60)

    # Get should return tuple (value, CacheLayer)
    result = await adapter.get(test_key)

    if isinstance(result, tuple) and len(result) == 2:
        value, layer = result
        print(f"✅ MultiTierCacheAdapter.get() returns tuple: (value, {layer})")

        if value == test_value:
            print(f"✅ Value matches: {value}")
        else:
            print(f"❌ Value mismatch: expected {test_value}, got {value}")

        if layer in [CacheLayer.L1_MEMORY, CacheLayer.L2_MEMCACHED, CacheLayer.L3_REDIS]:
            print(f"✅ Cache layer is valid: {layer}")
        else:
            print(f"❌ Invalid cache layer: {layer}")
    else:
        print(f"❌ MultiTierCacheAdapter.get() should return tuple, got: {type(result)}")

    # Clean up
    await adapter.delete(test_key)

    return True

async def test_indicator_cache():
    """Test IndicatorCache handles tuple unpacking correctly"""
    print("\n=== Testing IndicatorCache ===")

    cache = IndicatorCache()
    await cache.initialize()

    # Test set and get
    symbol = "BTCUSDT"
    indicator_type = "technical"
    timeframe = "base"
    test_value = 75.5

    await cache.set(symbol, indicator_type, timeframe, test_value, "rsi")

    # Get should return just the value (not a tuple)
    result = await cache.get(symbol, indicator_type, timeframe, "rsi")

    if isinstance(result, tuple):
        print(f"❌ IndicatorCache.get() should not return tuple, got: {result}")
        return False
    else:
        print(f"✅ IndicatorCache.get() returns single value: {result}")

        if result == test_value:
            print(f"✅ Value matches: {result}")
        else:
            print(f"❌ Value mismatch: expected {test_value}, got {result}")

    # Test get_indicator method
    async def compute_func():
        return 55.5

    result2 = await cache.get_indicator(
        indicator_type="technical",
        symbol="ETHUSDT",
        component="macd",
        params={"fast": 12, "slow": 26},
        compute_func=compute_func
    )

    if isinstance(result2, tuple):
        print(f"❌ IndicatorCache.get_indicator() should not return tuple, got: {result2}")
    else:
        print(f"✅ IndicatorCache.get_indicator() returns single value: {result2}")

    # Clean up
    await cache.delete(symbol, indicator_type, timeframe, "rsi")

    return True

async def test_direct_cache_adapter():
    """Test DirectCacheAdapter handles internal tuple correctly"""
    print("\n=== Testing DirectCacheAdapter ===")

    adapter = DirectCacheAdapter()

    # Test set and get
    test_key = "test:direct"
    test_value = {"data": "test_direct", "number": 456}

    await adapter.set(test_key, test_value, 60)

    # Get should return just the value (not a tuple)
    result = await adapter.get(test_key)

    if isinstance(result, tuple):
        print(f"❌ DirectCacheAdapter.get() should not return tuple, got: {result}")
        return False
    else:
        print(f"✅ DirectCacheAdapter.get() returns single value")

        if result == test_value:
            print(f"✅ Value matches: {result}")
        else:
            print(f"❌ Value mismatch: expected {test_value}, got {result}")

    # Clean up
    await adapter.delete(test_key)

    return True

async def main():
    """Run all validation tests"""
    print("=" * 60)
    print("CACHE TUPLE FIX VALIDATION")
    print("=" * 60)

    results = []

    # Run tests
    try:
        results.append(("MultiTierCacheAdapter", await test_multi_tier_cache()))
    except Exception as e:
        print(f"❌ MultiTierCacheAdapter test failed: {e}")
        results.append(("MultiTierCacheAdapter", False))

    try:
        results.append(("IndicatorCache", await test_indicator_cache()))
    except Exception as e:
        print(f"❌ IndicatorCache test failed: {e}")
        results.append(("IndicatorCache", False))

    try:
        results.append(("DirectCacheAdapter", await test_direct_cache_adapter()))
    except Exception as e:
        print(f"❌ DirectCacheAdapter test failed: {e}")
        results.append(("DirectCacheAdapter", False))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:25s}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("✅ All cache components are handling tuples correctly!")
    else:
        print("❌ Some components need fixing")

    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)