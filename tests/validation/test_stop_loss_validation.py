#!/usr/bin/env python3
"""
Comprehensive validation test for stop loss calculation consistency.
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

def test_stop_loss_calculator():
    """Test the unified stop loss calculator with real config values."""
    print("=== Testing Stop Loss Calculator ===")

    # Load real config
    config = load_config()
    print(f"Config loaded: {'✅' if config else '❌'}")

    # Get thresholds from config
    confluence_config = config.get('confluence', {})
    thresholds = confluence_config.get('thresholds', {})
    buy_threshold = thresholds.get('buy', 70)
    sell_threshold = thresholds.get('sell', 35)

    print(f"Real config thresholds: buy={buy_threshold}, sell={sell_threshold}")

    # Import and test stop loss calculator
    try:
        from src.core.risk.stop_loss_calculator import StopLossCalculator, StopLossMethod

        # Initialize calculator with real config
        calculator = StopLossCalculator(config)

        # Verify thresholds were loaded correctly
        print(f"Calculator buy threshold: {calculator.long_threshold}")
        print(f"Calculator sell threshold: {calculator.short_threshold}")

        # Test calculations
        test_cases = [
            {"signal_type": "LONG", "confluence_score": 75, "entry_price": 100.0},
            {"signal_type": "LONG", "confluence_score": 85, "entry_price": 100.0},
            {"signal_type": "SHORT", "confluence_score": 25, "entry_price": 100.0},
            {"signal_type": "SHORT", "confluence_score": 15, "entry_price": 100.0},
        ]

        for case in test_cases:
            stop_pct = calculator.calculate_stop_loss_percentage(
                case["signal_type"],
                case["confluence_score"]
            )
            stop_price = calculator.calculate_stop_loss_price(
                case["entry_price"],
                case["signal_type"],
                case["confluence_score"]
            )

            print(f"{case['signal_type']} @ score {case['confluence_score']}: "
                  f"{stop_pct*100:.2f}% → stop at ${stop_price:.2f}")

        # Test with signal data format
        signal_data = {
            "signal_type": "LONG",
            "confluence_score": 80,
            "price": 100.0
        }

        stop_info = calculator.get_stop_loss_info(signal_data)
        print(f"\nSignal data test: {stop_info}")

        return True

    except Exception as e:
        print(f"❌ Stop loss calculator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_alert_manager_integration():
    """Test that AlertManager uses the stop loss calculator correctly."""
    print("\n=== Testing AlertManager Integration ===")

    try:
        # We'll test the imports and basic initialization
        config = load_config()

        # Check if AlertManager can import the stop loss calculator
        from src.monitoring.alert_manager import AlertManager
        from src.core.risk.stop_loss_calculator import get_stop_loss_calculator

        print("✅ AlertManager can import stop loss calculator")

        # Initialize stop loss calculator with config
        stop_calc = get_stop_loss_calculator(config)
        print(f"✅ Stop loss calculator initialized with thresholds: buy={stop_calc.long_threshold}, sell={stop_calc.short_threshold}")

        return True

    except Exception as e:
        print(f"❌ AlertManager integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_config_consistency():
    """Validate that config loading is consistent."""
    print("\n=== Validating Config Consistency ===")

    config = load_config()

    # Check confluence thresholds
    confluence_config = config.get('confluence', {})
    thresholds = confluence_config.get('thresholds', {})

    expected_buy = 70
    expected_sell = 35

    actual_buy = thresholds.get('buy')
    actual_sell = thresholds.get('sell')

    print(f"Expected: buy={expected_buy}, sell={expected_sell}")
    print(f"Actual: buy={actual_buy}, sell={actual_sell}")

    buy_ok = actual_buy == expected_buy
    sell_ok = actual_sell == expected_sell

    print(f"Buy threshold correct: {'✅' if buy_ok else '❌'}")
    print(f"Sell threshold correct: {'✅' if sell_ok else '❌'}")

    return buy_ok and sell_ok

def main():
    """Run all validation tests."""
    print("Virtuoso Stop Loss Calculation Validation")
    print("=" * 50)

    results = []

    # Test 1: Config consistency
    results.append(validate_config_consistency())

    # Test 2: Stop loss calculator
    results.append(test_stop_loss_calculator())

    # Test 3: AlertManager integration
    results.append(test_alert_manager_integration())

    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)

    all_passed = all(results)

    if all_passed:
        print("🎉 ALL TESTS PASSED - Stop loss configuration is consistent!")
    else:
        print("❌ SOME TESTS FAILED - Issues found in stop loss configuration")

    test_names = [
        "Config Consistency",
        "Stop Loss Calculator",
        "AlertManager Integration"
    ]

    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {name}: {status}")

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)