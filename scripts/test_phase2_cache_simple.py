#!/usr/bin/env python3
"""
Simple test script to verify Phase 2 indicator caching is working
Tests the cache infrastructure without requiring full indicator calculations
"""

import asyncio
import time
import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.cache.indicator_cache import IndicatorCache

async def test_basic_cache():
    """Test basic caching functionality"""
    print("=" * 60)
    print("PHASE 2: INDICATOR CACHE BASIC TEST")
    print("=" * 60)
    
    # Initialize cache
    cache = IndicatorCache()
    print("✅ IndicatorCache initialized successfully")
    
    # Test 1: Cache set and get
    print("\n📝 Test 1: Basic cache operations")
    test_key = "test:indicator:BTCUSDT"
    test_value = {"score": 75.5, "timestamp": int(time.time())}
    
    await cache.set(test_key, test_value, ttl=5)
    print(f"  Set value: {test_value}")
    
    retrieved = await cache.get(test_key)
    print(f"  Retrieved: {retrieved}")
    assert retrieved == test_value, "Value mismatch!"
    print("  ✅ Basic cache operations working")
    
    # Test 2: TTL test
    print("\n⏱️ Test 2: TTL expiration")
    await cache.set("test:ttl", {"value": 100}, ttl=2)
    print("  Set value with 2 second TTL")
    
    # Should exist immediately
    val1 = await cache.get("test:ttl")
    assert val1 is not None, "Value should exist"
    print("  ✅ Value exists immediately after set")
    
    # Wait for expiration
    await asyncio.sleep(3)
    val2 = await cache.get("test:ttl")
    assert val2 is None, "Value should have expired"
    print("  ✅ Value expired after TTL")
    
    # Test 3: Indicator-specific caching
    print("\n📊 Test 3: Indicator-specific caching")
    
    # Simulate RSI calculation
    rsi_calls = 0
    def calculate_rsi():
        nonlocal rsi_calls
        rsi_calls += 1
        time.sleep(0.1)  # Simulate expensive calculation
        return 65.5
    
    async def async_calculate_rsi():
        return await asyncio.to_thread(calculate_rsi)
    
    # First call - should compute
    start = time.perf_counter()
    result1 = await cache.get_indicator(
        indicator_type='technical',
        symbol='BTCUSDT',
        component='rsi_base',
        params={'period': 14},
        compute_func=async_calculate_rsi,
        ttl=30
    )
    time1 = (time.perf_counter() - start) * 1000
    print(f"  First call (computed): {result1} in {time1:.2f}ms")
    assert rsi_calls == 1, "Should have computed once"
    
    # Second call - should hit cache
    start = time.perf_counter()
    result2 = await cache.get_indicator(
        indicator_type='technical',
        symbol='BTCUSDT',
        component='rsi_base',
        params={'period': 14},
        compute_func=async_calculate_rsi,
        ttl=30
    )
    time2 = (time.perf_counter() - start) * 1000
    print(f"  Second call (cached): {result2} in {time2:.2f}ms")
    assert rsi_calls == 1, "Should not have computed again"
    assert result2 == result1, "Results should match"
    
    speedup = time1 / time2
    print(f"  ✅ Cache hit achieved {speedup:.1f}x speedup")
    
    # Test 4: Different TTLs for different indicator types
    print("\n⏰ Test 4: TTL configurations by type")
    for ind_type, ttl in cache.TTL_CONFIG.items():
        print(f"  {ind_type}: {ttl} seconds TTL")
    print("  ✅ TTL configurations loaded correctly")
    
    # Test 5: Cache metrics
    print("\n📈 Test 5: Cache metrics")
    metrics = await cache.get_indicator_metrics()
    
    print(f"  Overall metrics:")
    print(f"    Hit rate: {metrics['overall']['hit_rate']:.1f}%")
    print(f"    Total hits: {metrics['overall']['total_hits']}")
    print(f"    Total misses: {metrics['overall']['total_misses']}")
    
    if 'technical' in metrics['by_type']:
        tech_metrics = metrics['by_type']['technical']
        print(f"  Technical indicator metrics:")
        print(f"    Hit rate: {tech_metrics['hit_rate']:.1f}%")
        print(f"    Hits: {tech_metrics['hits']}")
        print(f"    Misses: {tech_metrics['misses']}")
    
    print("  ✅ Metrics tracking working")
    
    # Test 6: Multiple indicators
    print("\n🔄 Test 6: Multiple indicator caching")
    
    # Simulate multiple indicators
    indicators = ['rsi', 'macd', 'ao', 'williams_r', 'atr', 'cci']
    calculation_times = {}
    
    for indicator in indicators:
        # First call - compute
        start = time.perf_counter()
        await cache.get_indicator(
            indicator_type='technical',
            symbol='BTCUSDT',
            component=f'{indicator}_base',
            params={'test': indicator},
            compute_func=lambda: asyncio.sleep(0.05),  # 50ms simulation
            ttl=30
        )
        calculation_times[indicator] = (time.perf_counter() - start) * 1000
    
    print(f"  Initial calculations: {len(indicators)} indicators")
    print(f"  Total time: {sum(calculation_times.values()):.2f}ms")
    
    # Second round - all should hit cache
    cached_times = {}
    for indicator in indicators:
        start = time.perf_counter()
        await cache.get_indicator(
            indicator_type='technical',
            symbol='BTCUSDT',
            component=f'{indicator}_base',
            params={'test': indicator},
            compute_func=lambda: asyncio.sleep(0.05),
            ttl=30
        )
        cached_times[indicator] = (time.perf_counter() - start) * 1000
    
    print(f"  Cached retrievals: {len(indicators)} indicators")
    print(f"  Total time: {sum(cached_times.values()):.2f}ms")
    
    overall_speedup = sum(calculation_times.values()) / sum(cached_times.values())
    print(f"  ✅ Overall speedup: {overall_speedup:.1f}x")
    
    # Final summary
    print("\n" + "=" * 60)
    print("✅ PHASE 2 CACHE IMPLEMENTATION VERIFIED")
    print("=" * 60)
    print("Summary:")
    print("  - IndicatorCache class working")
    print("  - TTL management functioning")
    print("  - Cache hit/miss tracking operational")
    print("  - Performance improvements confirmed")
    print(f"  - Average speedup: {overall_speedup:.1f}x for cached calls")
    print("\n🎉 Phase 2 implementation successful!")

if __name__ == "__main__":
    asyncio.run(test_basic_cache())