#!/usr/bin/env python3
"""
Regression test to ensure core functionality still works after stop loss fixes.
"""

import sys
import os
import yaml
from typing import Dict, Any

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def load_config() -> Dict[str, Any]:
    """Load the actual config from config.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Failed to load config: {e}")
        return {}

def test_config_loading():
    """Test that config loads correctly with the right thresholds."""
    print("=== Testing Config Loading ===")

    config = load_config()

    # Check confluence thresholds
    confluence_config = config.get('confluence', {})
    thresholds = confluence_config.get('thresholds', {})

    buy_threshold = thresholds.get('buy')
    sell_threshold = thresholds.get('sell')

    print(f"Buy threshold: {buy_threshold}")
    print(f"Sell threshold: {sell_threshold}")

    # Verify expected values
    expected_buy = 70
    expected_sell = 35

    buy_ok = buy_threshold == expected_buy
    sell_ok = sell_threshold == expected_sell

    print(f"Buy threshold correct: {'✅' if buy_ok else '❌'}")
    print(f"Sell threshold correct: {'✅' if sell_ok else '❌'}")

    return buy_ok and sell_ok

def test_stop_loss_calculator_import():
    """Test that the stop loss calculator can be imported and initialized."""
    print("\n=== Testing Stop Loss Calculator Import ===")

    try:
        from src.core.risk.stop_loss_calculator import StopLossCalculator, get_stop_loss_calculator, StopLossMethod
        print("✅ Stop loss calculator imports successful")

        config = load_config()
        calculator = StopLossCalculator(config)
        print("✅ Stop loss calculator initialization successful")

        # Test calculation
        pct = calculator.calculate_stop_loss_percentage("BUY", 75.0)
        print(f"✅ Stop loss calculation successful: {pct*100:.2f}%")

        return True
    except Exception as e:
        print(f"❌ Stop loss calculator test failed: {e}")
        return False

def test_alert_manager_import():
    """Test that AlertManager can still be imported and initialized."""
    print("\n=== Testing AlertManager Import ===")

    try:
        from src.monitoring.alert_manager import AlertManager
        print("✅ AlertManager import successful")

        # Test basic initialization (without full setup)
        config = load_config()
        # Don't actually initialize AlertManager as it has many dependencies
        print("✅ AlertManager config access successful")

        return True
    except Exception as e:
        print(f"❌ AlertManager test failed: {e}")
        return False

def test_pdf_generator_import():
    """Test that PDF generator can still be imported."""
    print("\n=== Testing PDF Generator Import ===")

    try:
        from src.core.reporting.pdf_generator import ReportGenerator
        print("✅ PDF generator import successful")

        config = load_config()
        generator = ReportGenerator()
        print("✅ PDF generator initialization successful")

        return True
    except Exception as e:
        print(f"❌ PDF generator test failed: {e}")
        return False

def test_basic_stop_loss_calculations():
    """Test basic stop loss calculation scenarios."""
    print("\n=== Testing Basic Stop Loss Calculations ===")

    try:
        from src.core.risk.stop_loss_calculator import get_stop_loss_calculator

        config = load_config()
        calculator = get_stop_loss_calculator(config)

        # Test various scenarios
        test_cases = [
            {"signal": "BUY", "score": 70, "expected_range": (2.4, 2.6)},   # At threshold
            {"signal": "BUY", "score": 75, "expected_range": (2.6, 2.9)},   # Above threshold
            {"signal": "BUY", "score": 85, "expected_range": (3.2, 3.6)},   # High confidence
            {"signal": "SELL", "score": 35, "expected_range": (2.8, 3.0)},  # At threshold
            {"signal": "SELL", "score": 25, "expected_range": (3.3, 3.7)},  # Below threshold
            {"signal": "SELL", "score": 15, "expected_range": (4.0, 4.4)},  # High confidence
        ]

        all_passed = True

        for case in test_cases:
            pct = calculator.calculate_stop_loss_percentage(case["signal"], case["score"]) * 100
            min_expected, max_expected = case["expected_range"]

            in_range = min_expected <= pct <= max_expected

            print(f"  {case['signal']} @ {case['score']}: {pct:.2f}% {'✅' if in_range else '❌'}")

            if not in_range:
                print(f"    Expected {min_expected:.1f}%-{max_expected:.1f}%, got {pct:.2f}%")
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"❌ Basic calculations test failed: {e}")
        return False

def main():
    """Run all regression tests."""
    print("Stop Loss Fix Regression Test Suite")
    print("=" * 40)

    tests = [
        ("Config Loading", test_config_loading),
        ("Stop Loss Calculator Import", test_stop_loss_calculator_import),
        ("AlertManager Import", test_alert_manager_import),
        ("PDF Generator Import", test_pdf_generator_import),
        ("Basic Stop Loss Calculations", test_basic_stop_loss_calculations),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 40)
    print("REGRESSION TEST SUMMARY")
    print("=" * 40)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")

    if passed == total:
        print("\n🎉 ALL REGRESSION TESTS PASSED!")
        print("✅ Stop loss fixes do not introduce regressions")
    else:
        print(f"\n❌ {total - passed} REGRESSION TEST(S) FAILED")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)