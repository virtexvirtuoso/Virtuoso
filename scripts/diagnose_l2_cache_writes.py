"""
L2 Cache Write Diagnostic Script
==================================

This script tests the complete L2 (memcached) write path to identify
why monitoring's cache writes are not persisting to memcached.

Tests:
1. Direct memcached write/read (baseline)
2. MultiTierCache write/read
3. DirectCacheAdapter write/read
4. MonitoringCacheWriter write path
5. Cross-process key detection
6. TTL verification

Run on VPS:
    cd /home/linuxuser/trading/Virtuoso_ccxt
    PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt python3 scripts/diagnose_l2_cache_writes.py
"""

import asyncio
import json
import logging
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')

import aiomcache
from src.core.cache.multi_tier_cache import MultiTierCacheAdapter
from src.api.cache_adapter_direct import DirectCacheAdapter
from src.monitoring.cache_writer import MonitoringCacheWriter


async def test_1_direct_memcached():
    """Test 1: Direct memcached write/read (baseline)"""
    print("\n" + "="*70)
    print("TEST 1: Direct Memcached Write/Read")
    print("="*70)

    try:
        client = aiomcache.Client('localhost', 11211)

        # Write test data
        test_key = b'test:direct_memcached'
        test_data = {"test": "direct_memcached", "value": 123}
        json_data = json.dumps(test_data).encode()

        logger.info(f"Writing to memcached: {test_key.decode()}")
        await client.set(test_key, json_data, exptime=60)
        logger.info("✅ Write successful")

        # Read it back
        logger.info(f"Reading from memcached: {test_key.decode()}")
        read_data = await client.get(test_key)

        if read_data:
            decoded = json.loads(read_data.decode())
            logger.info(f"✅ Read successful: {decoded}")

            if decoded == test_data:
                logger.info("✅ TEST 1 PASSED: Data matches")
                return True
            else:
                logger.error("❌ TEST 1 FAILED: Data mismatch")
                return False
        else:
            logger.error("❌ TEST 1 FAILED: No data read back")
            return False

    except Exception as e:
        logger.error(f"❌ TEST 1 FAILED: {e}")
        return False


async def test_2_multi_tier_cache():
    """Test 2: MultiTierCache write/read"""
    print("\n" + "="*70)
    print("TEST 2: MultiTierCache Write/Read")
    print("="*70)

    try:
        # Initialize multi-tier cache
        cache = MultiTierCacheAdapter(
            memcached_host='localhost',
            memcached_port=11211,
            redis_host='localhost',
            redis_port=6379,
            l1_max_size=1000,
            l1_default_ttl=30,
            cross_process_mode=True,
            cross_process_l1_ttl=2
        )
        logger.info("✅ MultiTierCache initialized")

        # Write test data
        test_key = 'test:multi_tier'
        test_data = {"test": "multi_tier", "value": 456}

        logger.info(f"Writing via MultiTierCache.set(): {test_key}")
        await cache.set(test_key, test_data, ttl_override=60)
        logger.info("✅ Write completed (no exception)")

        # Wait a moment for async writes
        await asyncio.sleep(0.5)

        # Check L1 directly
        if test_key in cache.multi_tier_cache.l1_cache:
            logger.info(f"✅ Data found in L1: {cache.multi_tier_cache.l1_cache[test_key]}")
        else:
            logger.warning("⚠️  Data NOT in L1")

        # Check L2 directly
        logger.info("Checking L2 (memcached) directly...")
        memcached_client = aiomcache.Client('localhost', 11211)
        l2_data = await memcached_client.get(test_key.encode())

        if l2_data:
            decoded = json.loads(l2_data.decode())
            logger.info(f"✅ Data found in L2: {decoded}")
        else:
            logger.error("❌ Data NOT found in L2 (memcached)")

        # Read via MultiTierCache
        logger.info(f"Reading via MultiTierCache.get(): {test_key}")
        read_data, layer = await cache.get(test_key)

        if read_data:
            logger.info(f"✅ Read successful from layer {layer}: {read_data}")

            if read_data == test_data:
                logger.info("✅ TEST 2 PASSED: Data matches")
                return True
            else:
                logger.error(f"❌ TEST 2 FAILED: Data mismatch - expected {test_data}, got {read_data}")
                return False
        else:
            logger.error("❌ TEST 2 FAILED: No data read back")
            return False

    except Exception as e:
        logger.error(f"❌ TEST 2 FAILED: {e}", exc_info=True)
        return False


async def test_3_direct_cache_adapter():
    """Test 3: DirectCacheAdapter write/read"""
    print("\n" + "="*70)
    print("TEST 3: DirectCacheAdapter Write/Read")
    print("="*70)

    try:
        # Initialize DirectCacheAdapter
        adapter = DirectCacheAdapter()
        logger.info("✅ DirectCacheAdapter initialized")

        # Write test data
        test_key = 'test:direct_adapter'
        test_data = {"test": "direct_adapter", "value": 789}

        logger.info(f"Writing via DirectCacheAdapter.set(): {test_key}")
        result = await adapter.set(test_key, test_data, ttl=60)
        logger.info(f"✅ Write result: {result}")

        # Wait a moment for async writes
        await asyncio.sleep(0.5)

        # Check L2 directly
        logger.info("Checking L2 (memcached) directly...")
        memcached_client = aiomcache.Client('localhost', 11211)
        l2_data = await memcached_client.get(test_key.encode())

        if l2_data:
            decoded = json.loads(l2_data.decode())
            logger.info(f"✅ Data found in L2: {decoded}")
        else:
            logger.error("❌ Data NOT found in L2 (memcached)")

        # Read via DirectCacheAdapter
        logger.info(f"Reading via DirectCacheAdapter.get(): {test_key}")
        read_data = await adapter.get(test_key)

        if read_data:
            logger.info(f"✅ Read successful: {read_data}")

            if read_data == test_data:
                logger.info("✅ TEST 3 PASSED: Data matches")
                return True
            else:
                logger.error(f"❌ TEST 3 FAILED: Data mismatch")
                return False
        else:
            logger.error("❌ TEST 3 FAILED: No data read back")
            return False

    except Exception as e:
        logger.error(f"❌ TEST 3 FAILED: {e}", exc_info=True)
        return False


async def test_4_cross_process_key_detection():
    """Test 4: Cross-process key detection"""
    print("\n" + "="*70)
    print("TEST 4: Cross-Process Key Detection")
    print("="*70)

    try:
        cache = MultiTierCacheAdapter(
            memcached_host='localhost',
            memcached_port=11211,
            cross_process_mode=True,
            cross_process_l1_ttl=2
        )

        test_keys = [
            ('analysis:signals', True),
            ('market:overview', True),
            ('market:movers', True),
            ('market:tickers', False),
            ('ohlcv:BTCUSDT:1h', False),
        ]

        for key, expected_cross_process in test_keys:
            is_cross = cache.multi_tier_cache._is_cross_process_key(key)
            status = "✅" if is_cross == expected_cross_process else "❌"
            logger.info(f"{status} {key}: cross_process={is_cross} (expected={expected_cross_process})")

        logger.info("✅ TEST 4 PASSED: Cross-process key detection working")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 4 FAILED: {e}", exc_info=True)
        return False


async def test_5_monitoring_cache_writer():
    """Test 5: MonitoringCacheWriter write path"""
    print("\n" + "="*70)
    print("TEST 5: MonitoringCacheWriter Write Path")
    print("="*70)

    try:
        # Initialize cache adapter and writer
        adapter = DirectCacheAdapter()
        writer = MonitoringCacheWriter(adapter)
        logger.info("✅ MonitoringCacheWriter initialized")

        # Create test signal data
        test_signals = [
            {
                'symbol': 'BTCUSDT',
                'confluence_score': 65.5,
                'price': 45000.0,
                'volume': 1000000,
                'sentiment': 'BULLISH',
                'timestamp': 1234567890
            },
            {
                'symbol': 'ETHUSDT',
                'confluence_score': 58.3,
                'price': 3000.0,
                'volume': 500000,
                'sentiment': 'NEUTRAL',
                'timestamp': 1234567890
            }
        ]

        logger.info(f"Writing {len(test_signals)} signals via MonitoringCacheWriter.write_signals()")
        await writer.write_signals(test_signals, ttl=120)
        logger.info("✅ Write completed (no exception)")

        # Wait for async writes
        await asyncio.sleep(0.5)

        # Check L2 directly
        logger.info("Checking L2 (memcached) for 'analysis:signals'...")
        memcached_client = aiomcache.Client('localhost', 11211)
        l2_data = await memcached_client.get(b'analysis:signals')

        if l2_data:
            decoded = json.loads(l2_data.decode())
            signal_count = len(decoded.get('signals', decoded.get('recent_signals', [])))
            logger.info(f"✅ Data found in L2: {signal_count} signals")
            logger.info(f"   Schema: {list(decoded.keys())}")

            if signal_count == 2:
                logger.info("✅ TEST 5 PASSED: Signals written correctly")
                return True
            else:
                logger.error(f"❌ TEST 5 FAILED: Expected 2 signals, got {signal_count}")
                return False
        else:
            logger.error("❌ TEST 5 FAILED: No data found in L2 (memcached)")
            return False

    except Exception as e:
        logger.error(f"❌ TEST 5 FAILED: {e}", exc_info=True)
        return False


async def test_6_ttl_verification():
    """Test 6: TTL verification"""
    print("\n" + "="*70)
    print("TEST 6: TTL Verification")
    print("="*70)

    try:
        cache = MultiTierCacheAdapter(
            memcached_host='localhost',
            memcached_port=11211,
            cross_process_mode=True,
            cross_process_l1_ttl=2
        )

        # Test cross-process key L1 TTL
        logger.info("Testing analysis:signals L1 TTL...")
        test_data = {"test": "ttl_check"}
        await cache.set('analysis:signals', test_data, ttl_override=120)

        # Check L1 TTL
        if 'analysis:signals' in cache.multi_tier_cache.l1_cache:
            ttl_info = cache.multi_tier_cache.l1_cache_ttl.get('analysis:signals', 0)
            logger.info(f"✅ L1 TTL for analysis:signals: {ttl_info}")
        else:
            logger.warning("⚠️  analysis:signals not in L1 cache")

        # Test non-cross-process key L1 TTL
        logger.info("Testing market:tickers L1 TTL...")
        await cache.set('market:tickers', test_data, ttl_override=120)

        if 'market:tickers' in cache.multi_tier_cache.l1_cache:
            ttl_info = cache.multi_tier_cache.l1_cache_ttl.get('market:tickers', 0)
            logger.info(f"✅ L1 TTL for market:tickers: {ttl_info}")
        else:
            logger.warning("⚠️  market:tickers not in L1 cache")

        logger.info("✅ TEST 6 PASSED: TTL verification complete")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 6 FAILED: {e}", exc_info=True)
        return False


async def main():
    """Run all diagnostic tests"""
    print("\n" + "="*70)
    print("L2 CACHE WRITE DIAGNOSTIC SUITE")
    print("="*70)
    print("Purpose: Identify why monitoring L2 writes are not persisting")
    print("="*70)

    results = []

    # Run all tests
    results.append(("Direct Memcached", await test_1_direct_memcached()))
    results.append(("MultiTierCache", await test_2_multi_tier_cache()))
    results.append(("DirectCacheAdapter", await test_3_direct_cache_adapter()))
    results.append(("Cross-Process Detection", await test_4_cross_process_key_detection()))
    results.append(("MonitoringCacheWriter", await test_5_monitoring_cache_writer()))
    results.append(("TTL Verification", await test_6_ttl_verification()))

    # Summary
    print("\n" + "="*70)
    print("DIAGNOSTIC RESULTS SUMMARY")
    print("="*70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print("="*70)
    print(f"TOTAL: {passed_count}/{total_count} tests passed")
    print("="*70)

    if passed_count == total_count:
        print("\n✅ ALL TESTS PASSED - L2 write path is functional!")
    else:
        print("\n❌ SOME TESTS FAILED - Check logs above for details")
        print("\nNext steps:")
        print("1. Check which test failed")
        print("2. Review error messages and stack traces")
        print("3. Verify memcached is running: systemctl status memcached")
        print("4. Check memcached logs: journalctl -u memcached -n 50")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDiagnostic interrupted by user")
    except Exception as e:
        logger.error(f"Diagnostic script failed: {e}", exc_info=True)
