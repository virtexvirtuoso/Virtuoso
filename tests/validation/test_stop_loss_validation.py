#!/usr/bin/env python3
"""
Critical Stop Loss Validation Test

Tests that stop loss calculations produce values in the 1.4-2.3% range
(aggressive day trading), NOT 10% (old bug).

Test Case: BTCUSDT @ $107,981.50
Expected Results:
- SHORT stop loss: ~$110,378 (+2.22%) ✅ NOT $118,779 (+10%) ❌
- LONG stop loss: ~$106,470 (-1.40%) ✅ NOT $97,183 (-10%) ❌
"""

import sys
import os
sys.path.insert(0, '/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

import yaml
from src.core.risk.stop_loss_calculator import StopLossCalculator, StopLossMethod

def load_config():
    """Load configuration from config.yaml"""
    config_path = '/Users/ffv_macmini/Desktop/Virtuoso_ccxt/config/config.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def test_stop_loss_calculations():
    """Test stop loss calculations match aggressive day trading parameters"""

    print("=" * 80)
    print("CRITICAL STOP LOSS VALIDATION TEST")
    print("=" * 80)
    print()

    # Load config
    config = load_config()

    # Check config values
    risk_config = config.get('risk', {})
    long_stop_pct = risk_config.get('long_stop_percentage', 0)
    short_stop_pct = risk_config.get('short_stop_percentage', 0)

    print(f"📋 Configuration Values:")
    print(f"   Long Stop Percentage:  {long_stop_pct}%")
    print(f"   Short Stop Percentage: {short_stop_pct}%")
    print()

    # Validate config values match aggressive day trading
    assert long_stop_pct == 1.4, f"FAIL: long_stop_percentage should be 1.4%, got {long_stop_pct}%"
    assert short_stop_pct == 1.75, f"FAIL: short_stop_percentage should be 1.75%, got {short_stop_pct}%"
    print("✅ Config values correct!")
    print()

    # Initialize calculator
    calculator = StopLossCalculator(config)

    # Test case parameters
    entry_price = 107981.50
    test_cases = [
        {
            'name': 'SHORT Signal (High Confidence)',
            'signal_type': 'SHORT',
            'confluence_score': 25.0,  # Strong short signal (low score)
            'expected_stop_pct_min': 1.40,  # Min: 1.75% * 0.8 = 1.40%
            'expected_stop_pct_max': 2.28,  # Max: 1.75% * 1.3 = 2.28%
        },
        {
            'name': 'SHORT Signal (Medium Confidence)',
            'signal_type': 'SHORT',
            'confluence_score': 30.0,
            'expected_stop_pct_min': 1.40,
            'expected_stop_pct_max': 2.28,
        },
        {
            'name': 'LONG Signal (High Confidence)',
            'signal_type': 'LONG',
            'confluence_score': 75.0,  # Strong long signal (high score)
            'expected_stop_pct_min': 1.12,  # Min: 1.4% * 0.8 = 1.12%
            'expected_stop_pct_max': 1.82,  # Max: 1.4% * 1.3 = 1.82%
        },
        {
            'name': 'LONG Signal (Medium Confidence)',
            'signal_type': 'LONG',
            'confluence_score': 72.0,
            'expected_stop_pct_min': 1.12,
            'expected_stop_pct_max': 1.82,
        }
    ]

    print(f"🧪 Test Case: BTCUSDT @ ${entry_price:,.2f}")
    print()

    all_passed = True

    for test_case in test_cases:
        print(f"Testing: {test_case['name']}")
        print(f"  Signal Type: {test_case['signal_type']}")
        print(f"  Confluence Score: {test_case['confluence_score']}")

        # Calculate stop loss
        try:
            stop_loss_pct = calculator.calculate_stop_loss_percentage(
                signal_type=test_case['signal_type'],
                confluence_score=test_case['confluence_score'],
                method=StopLossMethod.CONFIDENCE_BASED
            )

            stop_loss_price = calculator.calculate_stop_loss_price(
                entry_price=entry_price,
                signal_type=test_case['signal_type'],
                confluence_score=test_case['confluence_score'],
                method=StopLossMethod.CONFIDENCE_BASED
            )

            # Calculate actual percentage change
            if test_case['signal_type'] == 'LONG':
                actual_pct_change = ((entry_price - stop_loss_price) / entry_price) * 100
            else:  # SHORT
                actual_pct_change = ((stop_loss_price - entry_price) / entry_price) * 100

            print(f"  📊 Result:")
            print(f"     Stop Loss Price: ${stop_loss_price:,.2f}")
            print(f"     Stop Loss %: {stop_loss_pct * 100:.2f}%")
            print(f"     Actual Distance: {actual_pct_change:.2f}%")

            # Validate: NOT 10%!
            if stop_loss_pct >= 0.09:  # 9% or higher = OLD BUG
                print(f"  ❌ CRITICAL FAILURE: Stop loss is {stop_loss_pct*100:.2f}% (≥9%)")
                print(f"     This indicates the OLD 10% BUG is still present!")
                all_passed = False
            elif stop_loss_pct < 0.01:  # Less than 1%
                print(f"  ⚠️  WARNING: Stop loss is {stop_loss_pct*100:.2f}% (too tight)")
                all_passed = False
            elif test_case['expected_stop_pct_min'] / 100 <= stop_loss_pct <= test_case['expected_stop_pct_max'] / 100:
                print(f"  ✅ PASS: Stop loss within expected range ({test_case['expected_stop_pct_min']:.2f}% - {test_case['expected_stop_pct_max']:.2f}%)")
            else:
                print(f"  ⚠️  WARNING: Stop loss outside expected range")
                print(f"     Expected: {test_case['expected_stop_pct_min']:.2f}% - {test_case['expected_stop_pct_max']:.2f}%")
                print(f"     Got: {stop_loss_pct * 100:.2f}%")
                all_passed = False

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            all_passed = False

        print()

    print("=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED - Stop loss calculations are correct!")
        print("   The 10% bug is FIXED and aggressive day trading parameters are active.")
    else:
        print("❌ TESTS FAILED - Stop loss calculations have issues!")
        print("   Review the failures above for details.")
    print("=" * 80)

    return all_passed

if __name__ == '__main__':
    success = test_stop_loss_calculations()
    sys.exit(0 if success else 1)
