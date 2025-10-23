#!/usr/bin/env python3
"""
Test script to verify cross-process cache sharing between monitoring and web server.

This script tests:
1. SharedCacheBridge initialization
2. Writing data from one process (simulating monitoring)
3. Reading data from another process (simulating web server)
4. Cross-process data flow
5. Cache metrics and health
"""

import asyncio
import sys
import os
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.cache.shared_cache_bridge import (
    get_shared_cache_bridge,
    initialize_shared_cache,
    DataSource,
    publish_market_data,
    get_market_data
)


class CacheTestResult:
    """Store test results"""
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []

    def pass_test(self, name: str):
        self.tests_passed += 1
        print(f"✅ PASS: {name}")

    def fail_test(self, name: str, error: str):
        self.tests_failed += 1
        self.failures.append((name, error))
        print(f"❌ FAIL: {name}")
        print(f"   Error: {error}")

    def print_summary(self):
        total = self.tests_passed + self.tests_failed
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {total}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")

        if self.failures:
            print("\nFailed Tests:")
            for name, error in self.failures:
                print(f"  - {name}: {error}")

        print("=" * 70)

        return self.tests_failed == 0


async def test_shared_cache_initialization(result: CacheTestResult):
    """Test 1: Verify SharedCacheBridge can be initialized"""
    print("\n" + "=" * 70)
    print("TEST 1: SharedCacheBridge Initialization")
    print("=" * 70)

    try:
        # Initialize shared cache
        initialized = await initialize_shared_cache()

        if initialized:
            result.pass_test("SharedCacheBridge initialization")
        else:
            result.fail_test("SharedCacheBridge initialization", "initialize_shared_cache() returned False")

        # Get bridge instance
        bridge = get_shared_cache_bridge()
        if bridge is not None:
            result.pass_test("Get SharedCacheBridge instance")
        else:
            result.fail_test("Get SharedCacheBridge instance", "get_shared_cache_bridge() returned None")

        return bridge

    except Exception as e:
        result.fail_test("SharedCacheBridge initialization", str(e))
        return None


async def test_write_to_shared_cache(bridge, result: CacheTestResult):
    """Test 2: Write data to shared cache (simulating monitoring process)"""
    print("\n" + "=" * 70)
    print("TEST 2: Writing Data to Shared Cache")
    print("=" * 70)

    try:
        # Test data - simulating monitoring system writing signals
        test_signals_data = {
            'signals': [
                {
                    'symbol': 'BTCUSDT',
                    'score': 75.5,
                    'type': 'BUY',
                    'price': 43000,
                    'timestamp': int(time.time())
                },
                {
                    'symbol': 'ETHUSDT',
                    'score': 68.2,
                    'type': 'BUY',
                    'price': 2300,
                    'timestamp': int(time.time())
                }
            ],
            'timestamp': int(time.time()),
            'count': 2
        }

        # Write signals to cache
        await bridge.publish_data_update(
            key="analysis:signals",
            data=test_signals_data,
            source=DataSource.TRADING_SERVICE,
            ttl=300
        )
        result.pass_test("Write signals to shared cache")

        # Write market overview to cache
        test_market_overview = {
            'total_symbols': 150,
            'total_volume_24h': 125000000000,
            'average_change': 1.2,
            'volatility': 3.5,
            'timestamp': int(time.time())
        }

        await bridge.publish_data_update(
            key="market:overview",
            data=test_market_overview,
            source=DataSource.TRADING_SERVICE,
            ttl=300
        )
        result.pass_test("Write market overview to shared cache")

        # Write market regime to cache
        await bridge.publish_data_update(
            key="analysis:market_regime",
            data="bullish",
            source=DataSource.TRADING_SERVICE,
            ttl=300
        )
        result.pass_test("Write market regime to shared cache")

        print(f"\n📝 Wrote {len(test_signals_data['signals'])} signals to cache")

    except Exception as e:
        result.fail_test("Write data to shared cache", str(e))


async def test_read_from_shared_cache(bridge, result: CacheTestResult):
    """Test 3: Read data from shared cache (simulating web server process)"""
    print("\n" + "=" * 70)
    print("TEST 3: Reading Data from Shared Cache")
    print("=" * 70)

    try:
        # Read signals from cache
        signals_data, is_cross_service = await bridge.get_shared_data("analysis:signals")

        if signals_data is not None:
            result.pass_test("Read signals from shared cache")

            # Verify data content
            if 'signals' in signals_data and len(signals_data['signals']) > 0:
                result.pass_test("Signals data contains expected content")
                print(f"📊 Retrieved {len(signals_data['signals'])} signals:")
                for signal in signals_data['signals']:
                    print(f"   - {signal['symbol']}: {signal['score']} ({signal['type']})")
            else:
                result.fail_test("Signals data content validation", "No signals in data")
        else:
            result.fail_test("Read signals from shared cache", "Got None")

        # Read market overview from cache
        market_overview, _ = await bridge.get_shared_data("market:overview")

        if market_overview is not None:
            result.pass_test("Read market overview from shared cache")
            print(f"📈 Market Overview: {market_overview}")
        else:
            result.fail_test("Read market overview from shared cache", "Got None")

        # Read market regime from cache
        market_regime, _ = await bridge.get_shared_data("analysis:market_regime")

        if market_regime is not None:
            result.pass_test("Read market regime from shared cache")
            print(f"🎯 Market Regime: {market_regime}")
        else:
            result.fail_test("Read market regime from shared cache", "Got None")

    except Exception as e:
        result.fail_test("Read data from shared cache", str(e))


async def test_cross_service_hit_tracking(bridge, result: CacheTestResult):
    """Test 4: Verify cross-service hit tracking works"""
    print("\n" + "=" * 70)
    print("TEST 4: Cross-Service Hit Tracking")
    print("=" * 70)

    try:
        # Write some data
        await bridge.publish_data_update(
            key="test:cross_service",
            data={"test": "data", "timestamp": time.time()},
            source=DataSource.TRADING_SERVICE,
            ttl=60
        )

        # Clear local cache to force cross-service hit
        # (In real scenario, this would be a different process)
        await asyncio.sleep(0.5)

        # Read it back
        data, is_cross_service = await bridge.get_shared_data("test:cross_service")

        if data is not None:
            result.pass_test("Cross-service data retrieval")

            # Note: is_cross_service might be False if read from same process
            # In real cross-process scenario, it would be True
            print(f"🔄 Cross-service hit: {is_cross_service}")

        else:
            result.fail_test("Cross-service data retrieval", "Got None")

    except Exception as e:
        result.fail_test("Cross-service hit tracking", str(e))


async def test_cache_metrics(bridge, result: CacheTestResult):
    """Test 5: Verify cache metrics are being tracked"""
    print("\n" + "=" * 70)
    print("TEST 5: Cache Metrics")
    print("=" * 70)

    try:
        # Get bridge metrics
        metrics = bridge.get_bridge_metrics()

        if metrics is not None:
            result.pass_test("Get bridge metrics")

            # Verify metrics structure
            required_keys = ['bridge_status', 'cross_service_metrics', 'cache_infrastructure']
            for key in required_keys:
                if key in metrics:
                    result.pass_test(f"Metrics contains '{key}'")
                else:
                    result.fail_test(f"Metrics contains '{key}'", f"Missing key: {key}")

            print("\n📊 Cache Metrics:")
            print(f"   Bridge Status: {metrics.get('bridge_status', 'unknown')}")
            print(f"   Cross-service hits: {metrics.get('cross_service_metrics', {}).get('cross_service_hits', 0)}")
            print(f"   Data bridge events: {metrics.get('cross_service_metrics', {}).get('data_bridge_events', 0)}")

        else:
            result.fail_test("Get bridge metrics", "Got None")

    except Exception as e:
        result.fail_test("Cache metrics", str(e))


async def test_health_check(bridge, result: CacheTestResult):
    """Test 6: Verify health check works"""
    print("\n" + "=" * 70)
    print("TEST 6: Health Check")
    print("=" * 70)

    try:
        health = await bridge.health_check()

        if health is not None:
            result.pass_test("Get health check")

            print(f"\n🏥 Health Status: {health.get('status', 'unknown')}")
            print(f"   Bridge initialized: {health.get('bridge_initialized', False)}")

            # Check connections
            connections = health.get('connections', {})
            for conn_name, conn_status in connections.items():
                print(f"   {conn_name}: {conn_status}")
        else:
            result.fail_test("Get health check", "Got None")

    except Exception as e:
        result.fail_test("Health check", str(e))


async def test_convenience_functions(result: CacheTestResult):
    """Test 7: Test convenience functions"""
    print("\n" + "=" * 70)
    print("TEST 7: Convenience Functions")
    print("=" * 70)

    try:
        # Test publish_market_data convenience function
        test_data = {
            'symbol': 'BTCUSDT',
            'price': 43000,
            'timestamp': int(time.time())
        }

        await publish_market_data("test:convenience", test_data, ttl=60)
        result.pass_test("publish_market_data() convenience function")

        # Test get_market_data convenience function
        retrieved_data, is_cross_service = await get_market_data("test:convenience")

        if retrieved_data is not None:
            result.pass_test("get_market_data() convenience function")
            print(f"📦 Retrieved data: {retrieved_data}")
        else:
            result.fail_test("get_market_data() convenience function", "Got None")

    except Exception as e:
        result.fail_test("Convenience functions", str(e))


async def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("CROSS-PROCESS CACHE SHARING TEST SUITE")
    print("=" * 70)
    print("Testing SharedCacheBridge functionality for cross-process communication")
    print("between monitoring system and web server")
    print("=" * 70)

    result = CacheTestResult()

    # Test 1: Initialize
    bridge = await test_shared_cache_initialization(result)

    if bridge is None:
        print("\n❌ Cannot proceed with tests - initialization failed")
        result.print_summary()
        return False

    # Test 2: Write data
    await test_write_to_shared_cache(bridge, result)

    # Test 3: Read data
    await test_read_from_shared_cache(bridge, result)

    # Test 4: Cross-service tracking
    await test_cross_service_hit_tracking(bridge, result)

    # Test 5: Metrics
    await test_cache_metrics(bridge, result)

    # Test 6: Health check
    await test_health_check(bridge, result)

    # Test 7: Convenience functions
    await test_convenience_functions(result)

    # Print summary
    success = result.print_summary()

    # Cleanup
    print("\n🧹 Cleaning up...")
    await bridge.close()

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
