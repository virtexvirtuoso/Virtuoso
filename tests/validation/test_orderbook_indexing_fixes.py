#!/usr/bin/env python3
"""
Test orderbook indexing error fixes

Validates that the fixes for:
1. Price distance calculation errors
2. Absorption/exhaustion calculation errors
work correctly with edge case orderbook data
"""

import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.indicators.orderbook_indicators import OrderbookIndicators
from src.core.config.config_manager import ConfigManager


# Initialize config
config_manager = ConfigManager()
config_data = config_manager._config


def test_small_orderbook():
    """Test with very small orderbook (3 levels - minimum required)"""
    print("\n=== Test 1: Small Orderbook (3 levels) ===")

    indicator = OrderbookIndicators(config_data)

    # Create minimal orderbook with 3 levels
    bids = np.array([
        [100.0, 10.0],  # price, volume
        [99.9, 5.0],
        [99.8, 3.0]
    ])

    asks = np.array([
        [100.1, 8.0],
        [100.2, 6.0],
        [100.3, 4.0]
    ])

    try:
        # Test absorption/exhaustion (this is where we fixed the bid_gaps/ask_gaps indexing)
        absorption = indicator.calculate_absorption_exhaustion(bids, asks)
        assert 'absorption_score' in absorption, "Missing absorption_score"
        assert 'exhaustion_score' in absorption, "Missing exhaustion_score"
        assert 0 <= absorption['absorption_score'] <= 100, "Absorption score out of range"
        assert 0 <= absorption['exhaustion_score'] <= 100, "Exhaustion score out of range"
        print(f"✅ Absorption/Exhaustion calculation succeeded:")
        print(f"   - Absorption: {absorption['absorption_score']:.2f}")
        print(f"   - Exhaustion: {absorption['exhaustion_score']:.2f}")

        # Test spread calculation (also fixed similar issues)
        spread = indicator.calculate_spread_score(bids, asks)
        if spread:
            assert 'score' in spread, "Missing score in spread"
            assert 0 <= spread['score'] <= 100, "Spread score out of range"
            print(f"✅ Spread calculation succeeded: {spread['score']:.2f}")
        else:
            print(f"⚠️  Spread calculation returned None (expected for small orderbook)")

        # Test OBPS (contains the fixed price distances calculation)
        obps = indicator.calculate_obps(bids, asks)
        assert 'score' in obps, "Missing score in OBPS"
        assert 0 <= obps['score'] <= 100, "OBPS score out of range"
        print(f"✅ OBPS calculation succeeded: {obps['score']:.2f}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_single_element_orderbook():
    """Test with single-element orderbook (should handle gracefully)"""
    print("\n=== Test 2: Single Element Orderbook ===")

    indicator = OrderbookIndicators(config_data)

    # Create single-level orderbook
    bids = np.array([[100.0, 10.0]])
    asks = np.array([[100.1, 8.0]])

    try:
        # These should return defaults gracefully (not enough data)
        absorption = indicator.calculate_absorption_exhaustion(bids, asks)
        assert 'absorption_score' in absorption, "Missing absorption_score"
        assert absorption['absorption_score'] == 50.0, "Expected default neutral value for single-element"
        print(f"✅ Absorption with single level: {absorption['absorption_score']:.2f}")

        spread = indicator.calculate_spread_score(bids, asks)
        # Spread may return None for single element, which is expected
        print(f"✅ Spread with single level: {spread if spread else 'None (expected)'}")

        obps = indicator.calculate_obps(bids, asks)
        if obps:
            assert 'score' in obps, "Missing score in OBPS"
            print(f"✅ OBPS with single level: {obps['score']:.2f}")
        else:
            print(f"✅ OBPS with single level: None (expected)")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_normal_orderbook():
    """Test with normal-sized orderbook (20 levels)"""
    print("\n=== Test 3: Normal Orderbook (20 levels) ===")

    indicator = OrderbookIndicators(config_data)

    # Create realistic orderbook with 20 levels
    base_price = 50000.0
    bids = np.array([
        [base_price - i * 10, 100 - i * 3] for i in range(20)
    ])
    asks = np.array([
        [base_price + i * 10, 100 - i * 3] for i in range(20)
    ])

    try:
        absorption = indicator.calculate_absorption_exhaustion(bids, asks)
        assert 'absorption_score' in absorption, "Missing absorption_score"
        assert 'exhaustion_score' in absorption, "Missing exhaustion_score"
        assert 0 <= absorption['absorption_score'] <= 100, "Absorption score out of range"
        assert 0 <= absorption['exhaustion_score'] <= 100, "Exhaustion score out of range"
        print(f"✅ Absorption: {absorption['absorption_score']:.2f}, Exhaustion: {absorption['exhaustion_score']:.2f}")

        spread = indicator.calculate_spread_score(bids, asks)
        if spread:
            assert 'score' in spread, "Missing score in spread"
            assert 0 <= spread['score'] <= 100, "Spread score out of range"
            print(f"✅ Spread: {spread['score']:.2f}")
        else:
            print(f"⚠️  Spread returned None (may need more data)")

        obps = indicator.calculate_obps(bids, asks)
        assert 'score' in obps, "Missing score in OBPS"
        assert 0 <= obps['score'] <= 100, "OBPS score out of range"
        print(f"✅ OBPS: {obps['score']:.2f}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_edge_case_orderbook():
    """Test with edge case: very tight spread and concentrated volume"""
    print("\n=== Test 4: Edge Case - Tight Spread ===")

    indicator = OrderbookIndicators(config_data)

    # Create orderbook with very tight spread
    bids = np.array([
        [100.0, 1000.0],  # Concentrated volume at top
        [99.999, 10.0],
        [99.998, 5.0],
        [99.997, 2.0]
    ])

    asks = np.array([
        [100.001, 800.0],  # Concentrated volume at top
        [100.002, 10.0],
        [100.003, 5.0],
        [100.004, 2.0]
    ])

    try:
        absorption = indicator.calculate_absorption_exhaustion(bids, asks)
        assert 'absorption_score' in absorption, "Missing absorption_score"
        assert 0 <= absorption['absorption_score'] <= 100, "Absorption score out of range"
        print(f"✅ Absorption: {absorption['absorption_score']:.2f}")

        spread = indicator.calculate_spread_score(bids, asks)
        if spread:
            assert 'score' in spread, "Missing score in spread"
            assert 0 <= spread['score'] <= 100, "Spread score out of range"
            print(f"✅ Spread: {spread['score']:.2f}")
        else:
            print(f"⚠️  Spread returned None (may need more data)")

        obps = indicator.calculate_obps(bids, asks)
        assert 'score' in obps, "Missing score in OBPS"
        assert 0 <= obps['score'] <= 100, "OBPS score out of range"
        print(f"✅ OBPS: {obps['score']:.2f}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("ORDERBOOK INDEXING ERROR FIX VALIDATION")
    print("=" * 70)

    results = []

    # Run all tests
    results.append(("Small Orderbook", test_small_orderbook()))
    results.append(("Single Element", test_single_element_orderbook()))
    results.append(("Normal Orderbook", test_normal_orderbook()))
    results.append(("Edge Case", test_edge_case_orderbook()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Fixes are working correctly.")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review.")
        sys.exit(1)
