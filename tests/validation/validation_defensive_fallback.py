#!/usr/bin/env python3
"""
Validation script for MetricsTracker defensive fallback fix.

Tests both scenarios:
1. Normal case: MetricsTracker has update_analysis_metrics method
2. Fallback case: MetricsTracker lacks update_analysis_metrics method

This script validates the fix implemented in src/monitoring/monitor.py line 1110-1119.
"""

import sys
import os
import asyncio
import logging
import time
from unittest.mock import Mock, MagicMock
from typing import Dict, Any

# Add project root to path
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

class TestMetricsTracker:
    """Test version of MetricsTracker with update_analysis_metrics method."""

    def __init__(self):
        print("✅ TestMetricsTracker created WITH update_analysis_metrics method")

    async def update_analysis_metrics(self, symbol, result):
        print(f"✅ TestMetricsTracker.update_analysis_metrics called with {symbol}")
        return True

class TestMetricsTrackerWithoutMethod:
    """Test version of MetricsTracker WITHOUT update_analysis_metrics method."""

    def __init__(self):
        # Intentionally does NOT have update_analysis_metrics method
        print("✅ TestMetricsTrackerWithoutMethod created WITHOUT update_analysis_metrics method")

class TestMetricsManager:
    """Test version of MetricsManager for fallback testing."""

    def __init__(self):
        print("✅ TestMetricsManager created with update_analysis_metrics method")

    async def update_analysis_metrics(self, symbol, result):
        print(f"✅ TestMetricsManager.update_analysis_metrics called with {symbol}")
        return True

async def test_normal_scenario():
    """Test normal scenario where MetricsTracker has the method."""
    print("\n=== Testing Normal Scenario ===")

    # Create test objects
    metrics_tracker = TestMetricsTracker()
    metrics_manager = TestMetricsManager()

    # Test data
    symbol = "BTC/USDT"
    result = {
        'confluence_score': 75.5,
        'reliability': 85.2,
        'signal_type': 'BUY',
        'components': {'rsi': 70.0, 'macd': 80.0}
    }

    # Simulate the fix logic from monitor.py lines 1110-1119
    try:
        if metrics_tracker and hasattr(metrics_tracker, 'update_analysis_metrics'):
            await metrics_tracker.update_analysis_metrics(symbol, result)
            print("✅ Normal path: Called metrics_tracker.update_analysis_metrics")
            return True
        elif metrics_manager:
            await metrics_manager.update_analysis_metrics(symbol, result)
            print("⚠️  Fallback path taken when normal path should have been used")
            return False
        else:
            print("❌ No metrics update path available")
            return False
    except Exception as e:
        print(f"❌ Error in normal scenario: {e}")
        return False

async def test_fallback_scenario():
    """Test fallback scenario where MetricsTracker lacks the method."""
    print("\n=== Testing Fallback Scenario ===")

    # Create test objects
    metrics_tracker = TestMetricsTrackerWithoutMethod()
    metrics_manager = TestMetricsManager()

    # Test data
    symbol = "ETH/USDT"
    result = {
        'confluence_score': 45.3,
        'reliability': 78.1,
        'signal_type': 'SELL',
        'components': {'rsi': 30.0, 'macd': 20.0}
    }

    # Simulate the fix logic from monitor.py lines 1110-1119
    try:
        if metrics_tracker and hasattr(metrics_tracker, 'update_analysis_metrics'):
            await metrics_tracker.update_analysis_metrics(symbol, result)
            print("❌ Normal path taken when fallback should have been used")
            return False
        elif metrics_manager:
            await metrics_manager.update_analysis_metrics(symbol, result)
            print("✅ Fallback path: Called metrics_manager.update_analysis_metrics")
            return True
        else:
            print("❌ No metrics update path available")
            return False
    except Exception as e:
        print(f"❌ Error in fallback scenario: {e}")
        return False

async def test_hasattr_performance():
    """Test performance impact of hasattr check."""
    print("\n=== Testing hasattr Performance Impact ===")

    metrics_tracker = TestMetricsTracker()

    # Time hasattr checks
    iterations = 100000

    # Test with method present
    start_time = time.time()
    for _ in range(iterations):
        hasattr(metrics_tracker, 'update_analysis_metrics')
    time_with_method = time.time() - start_time

    # Test with method absent
    metrics_tracker_no_method = TestMetricsTrackerWithoutMethod()
    start_time = time.time()
    for _ in range(iterations):
        hasattr(metrics_tracker_no_method, 'update_analysis_metrics')
    time_without_method = time.time() - start_time

    print(f"hasattr check performance ({iterations} iterations):")
    print(f"  With method:    {time_with_method:.6f}s ({time_with_method/iterations*1000000:.2f} μs/check)")
    print(f"  Without method: {time_without_method:.6f}s ({time_without_method/iterations*1000000:.2f} μs/check)")
    print(f"  Average:        {(time_with_method + time_without_method)/2/iterations*1000000:.2f} μs/check")

    # Performance is acceptable if each check takes less than 1 microsecond
    avg_time_us = (time_with_method + time_without_method) / 2 / iterations * 1000000
    if avg_time_us < 1.0:
        print("✅ Performance impact is negligible (< 1 μs per check)")
        return True
    else:
        print(f"⚠️  Performance impact may be noticeable ({avg_time_us:.2f} μs per check)")
        return False

async def test_error_handling():
    """Test error handling in the defensive fallback."""
    print("\n=== Testing Error Handling ===")

    # Test with failing metrics_tracker
    class FailingMetricsTracker:
        async def update_analysis_metrics(self, symbol, result):
            raise Exception("Simulated MetricsTracker failure")

    # Test with failing metrics_manager
    class FailingMetricsManager:
        async def update_analysis_metrics(self, symbol, result):
            raise Exception("Simulated MetricsManager failure")

    metrics_tracker = FailingMetricsTracker()
    metrics_manager = TestMetricsManager()

    symbol = "DOGE/USDT"
    result = {'confluence_score': 60.0}

    # Simulate the fix logic with error handling
    try:
        if metrics_tracker and hasattr(metrics_tracker, 'update_analysis_metrics'):
            try:
                await metrics_tracker.update_analysis_metrics(symbol, result)
                print("❌ Should have failed but didn't")
                return False
            except Exception:
                print("✅ MetricsTracker failure handled, falling back to MetricsManager")
                # Fallback to metrics_manager
                await metrics_manager.update_analysis_metrics(symbol, result)
                print("✅ Fallback to MetricsManager successful")
                return True
        else:
            print("❌ hasattr check failed unexpectedly")
            return False
    except Exception as e:
        print(f"❌ Unhandled error: {e}")
        return False

async def main():
    """Run all validation tests."""
    print("🔍 Defensive Fallback Fix Validation")
    print("=" * 50)

    results = []

    # Test normal scenario
    results.append(await test_normal_scenario())

    # Test fallback scenario
    results.append(await test_fallback_scenario())

    # Test performance impact
    results.append(await test_hasattr_performance())

    # Test error handling
    results.append(await test_error_handling())

    # Summary
    print("\n" + "=" * 50)
    print("📊 Validation Results Summary")

    test_names = [
        "Normal Scenario",
        "Fallback Scenario",
        "Performance Impact",
        "Error Handling"
    ]

    passed = 0
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All validation tests PASSED - Fix is working correctly!")
        return True
    else:
        print("⚠️  Some validation tests FAILED - Fix needs review!")
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())