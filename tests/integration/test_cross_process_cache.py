#!/usr/bin/env python3
"""
Test script to validate cross-process cache sharing fix.

This simulates the monitoring service writing data and the web server reading it,
verifying that the cross-process cache isolation issue is resolved.
"""

import asyncio
import json
import time
import sys
import os

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api.cache_adapter_direct import DirectCacheAdapter


async def test_cross_process_cache():
    """Test that data written by one process is visible to another"""

    print("=" * 60)
    print("CROSS-PROCESS CACHE SHARING TEST")
    print("=" * 60)

    # Create two cache adapter instances (simulating different processes)
    print("\n1. Creating cache adapters (simulating monitoring and web server)...")
    monitoring_cache = DirectCacheAdapter()  # Monitoring service
    web_cache = DirectCacheAdapter()        # Web server

    # Test data representing signals from monitoring
    test_signals = {
        "signals": [
            {
                "symbol": "BTC/USDT",
                "confluence_score": 75.5,
                "sentiment": "BULLISH",
                "price": 45000,
                "volume_24h": 15000000000
            },
            {
                "symbol": "ETH/USDT",
                "confluence_score": 68.2,
                "sentiment": "NEUTRAL",
                "price": 3200,
                "volume_24h": 8000000000
            }
        ],
        "timestamp": int(time.time()),
        "count": 2
    }

    test_overview = {
        "total_symbols": 150,
        "total_volume_24h": 120000000000,
        "market_regime": "BULLISH",
        "trend_strength": 65,
        "btc_dominance": 58.5,
        "volatility": 3.2
    }

    # Key to test (cross-process key that should be shared)
    signals_key = "analysis:signals"
    overview_key = "market:overview"

    print("\n2. Monitoring service writing data to cache...")
    print(f"   - Writing {len(test_signals['signals'])} signals to '{signals_key}'")
    print(f"   - Writing market overview to '{overview_key}'")

    # Monitoring writes data
    await monitoring_cache.set(signals_key, test_signals, ttl=60)
    await monitoring_cache.set(overview_key, test_overview, ttl=60)

    print("\n3. Testing immediate read from web server cache...")

    # Web server reads immediately (within L1 TTL window)
    signals_from_web = await web_cache.get(signals_key)
    overview_from_web = await web_cache.get(overview_key)

    # Validate results
    print("\n4. Validation Results:")
    print("-" * 40)

    success = True

    # Check signals
    if signals_from_web and signals_from_web.get('count') == 2:
        print(f"✅ SIGNALS: Web server successfully read {signals_from_web['count']} signals")
        print(f"   - First signal: {signals_from_web['signals'][0]['symbol']} "
              f"(score: {signals_from_web['signals'][0]['confluence_score']})")
    else:
        print(f"❌ SIGNALS: Web server failed to read signals (got: {signals_from_web})")
        success = False

    # Check overview
    if overview_from_web and overview_from_web.get('total_symbols') == 150:
        print(f"✅ OVERVIEW: Web server successfully read market overview")
        print(f"   - Symbols: {overview_from_web['total_symbols']}, "
              f"Regime: {overview_from_web['market_regime']}, "
              f"BTC Dom: {overview_from_web['btc_dominance']}%")
    else:
        print(f"❌ OVERVIEW: Web server failed to read overview (got: {overview_from_web})")
        success = False

    # Test L1 TTL behavior
    print("\n5. Testing L1 cache TTL behavior (2-second TTL for cross-process keys)...")
    print("   Waiting 3 seconds for L1 to expire...")
    await asyncio.sleep(3)

    # Read again after L1 expiry (should hit L2)
    signals_after_expiry = await web_cache.get(signals_key)

    if signals_after_expiry and signals_after_expiry.get('count') == 2:
        print(f"✅ Data still available after L1 expiry (from L2/L3)")
    else:
        print(f"❌ Data lost after L1 expiry")
        success = False

    # Get cache metrics
    print("\n6. Cache Performance Metrics:")
    print("-" * 40)
    metrics = web_cache.multi_tier_cache.get_performance_metrics()

    print(f"Hit Rates:")
    print(f"  - Overall: {metrics['hit_rates']['overall']}%")
    print(f"  - L1: {metrics['hit_rates']['l1_percentage']}%")
    print(f"  - L2: {metrics['hit_rates']['l2_percentage']}%")
    print(f"  - L3: {metrics['hit_rates']['l3_percentage']}%")

    print(f"\nOperations:")
    print(f"  - Total Hits: {metrics['operations']['total_hits']}")
    print(f"  - Total Misses: {metrics['operations']['total_misses']}")
    print(f"  - Promotions: {metrics['operations']['promotions']}")

    # Test with non-cross-process key (should use normal L1 TTL)
    print("\n7. Testing process-local cache key (normal L1 behavior)...")
    local_key = "ohlcv:BTC/USDT:1h"
    local_data = {"candles": [[1234567890, 45000, 45100, 44900, 45050, 1000]]}

    await monitoring_cache.set(local_key, local_data, ttl=60)
    local_from_web = await web_cache.get(local_key)

    if local_from_web is None:
        print(f"✅ Process-local key correctly not shared immediately (as expected)")
    else:
        print(f"ℹ️  Process-local key was found (promoted from L2/L3)")

    # Final result
    print("\n" + "=" * 60)
    if success:
        print("✅ CROSS-PROCESS CACHE SHARING TEST PASSED")
        print("The fix successfully enables data sharing between processes!")
    else:
        print("❌ CROSS-PROCESS CACHE SHARING TEST FAILED")
        print("Issues detected with cross-process data sharing.")
    print("=" * 60)

    return success


async def main():
    """Main test runner"""
    try:
        success = await test_cross_process_cache()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())