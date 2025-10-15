#!/usr/bin/env python3
"""
Simplified test for cross-process cache sharing fix.
Tests the MultiTierCacheAdapter directly without complex imports.
"""

import asyncio
import json
import time
import sys
import os

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import only the cache module directly
from src.core.cache.multi_tier_cache import MultiTierCacheAdapter


async def test_cross_process_cache():
    """Test that cross-process keys use short TTL in L1"""

    print("=" * 60)
    print("CROSS-PROCESS CACHE L1 TTL TEST")
    print("=" * 60)

    # Create cache adapter with cross-process mode enabled
    print("\n1. Creating MultiTierCacheAdapter with cross-process mode...")
    cache = MultiTierCacheAdapter(
        l1_max_size=1000,
        l1_default_ttl=30,
        cross_process_mode=True,
        cross_process_l1_ttl=2  # 2 second TTL for cross-process keys
    )

    # Test data
    test_signals = {
        "signals": [
            {"symbol": "BTC/USDT", "score": 75.5},
            {"symbol": "ETH/USDT", "score": 68.2}
        ],
        "timestamp": int(time.time())
    }

    # Test keys
    cross_process_key = "analysis:signals"  # Should use 2s TTL in L1
    local_key = "ohlcv:BTC/USDT:1h"        # Should use 30s TTL in L1

    print("\n2. Testing cross-process key behavior...")
    print(f"   Key: '{cross_process_key}' (should use 2s L1 TTL)")

    # Set the cross-process key
    await cache.set(cross_process_key, test_signals)

    # Immediate read should hit L1
    value1, layer1 = await cache.get(cross_process_key)
    print(f"   ✓ Immediate read: {layer1.value} (expected: l1_memory)")

    # Wait 2.5 seconds (L1 should expire for cross-process key)
    print("   Waiting 2.5 seconds for L1 expiry...")
    await asyncio.sleep(2.5)

    # Read again - should hit L2 since L1 expired
    value2, layer2 = await cache.get(cross_process_key)
    print(f"   ✓ After 2.5s: {layer2.value} (expected: l2_memcached)")

    # Verify data integrity
    if value2 and value2.get('signals'):
        print(f"   ✅ Data intact: {len(value2['signals'])} signals")
    else:
        print(f"   ❌ Data lost or corrupted")

    print("\n3. Testing process-local key behavior...")
    print(f"   Key: '{local_key}' (should use 30s L1 TTL)")

    # Set a local key
    local_data = {"candles": [[1234567890, 45000, 45100, 44900, 45050, 1000]]}
    await cache.set(local_key, local_data)

    # Immediate read should hit L1
    value3, layer3 = await cache.get(local_key)
    print(f"   ✓ Immediate read: {layer3.value} (expected: l1_memory)")

    # Wait 2.5 seconds (L1 should NOT expire for local key)
    print("   Waiting 2.5 seconds...")
    await asyncio.sleep(2.5)

    # Read again - should still hit L1 since it has 30s TTL
    value4, layer4 = await cache.get(local_key)
    print(f"   ✓ After 2.5s: {layer4.value} (expected: l1_memory - still cached)")

    # Get performance metrics
    print("\n4. Cache Performance Metrics:")
    print("-" * 40)
    metrics = cache.get_performance_metrics()

    print(f"Hit Rates:")
    print(f"  - Overall: {metrics['hit_rates']['overall']}%")
    print(f"  - L1: {metrics['hit_rates']['l1_percentage']}%")
    print(f"  - L2: {metrics['hit_rates']['l2_percentage']}%")

    print(f"\nOperations:")
    print(f"  - Total Hits: {metrics['operations']['total_hits']}")
    print(f"  - Total Misses: {metrics['operations']['total_misses']}")
    print(f"  - Promotions: {metrics['operations']['promotions']}")

    # Validate results
    print("\n" + "=" * 60)

    cross_process_works = (layer1.value == "l1_memory" and layer2.value == "l2_memcached")
    local_key_works = (layer3.value == "l1_memory" and layer4.value == "l1_memory")

    if cross_process_works and local_key_works:
        print("✅ TEST PASSED: Cross-process keys use short L1 TTL")
        print("   This ensures fresh data across process boundaries!")
        return True
    else:
        print("❌ TEST FAILED: Unexpected cache behavior")
        return False


async def main():
    """Main test runner"""
    try:
        success = await test_cross_process_cache()
        print("=" * 60)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())