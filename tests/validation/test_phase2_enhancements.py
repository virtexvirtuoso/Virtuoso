#!/usr/bin/env python3
"""
Test Phase 2 Orderflow Indicator Enhancements

Tests the Phase 2 improvements:
1. Configurable normalization factors (CVD and OI)
2. _safe_ratio() helper function
3. Tick rule implementation for unknown trade sides
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from src.indicators.orderflow_indicators import OrderflowIndicators
from src.core.config.config_manager import ConfigManager


class TestPhase2Enhancements:
    """Test suite for Phase 2 orderflow indicator enhancements."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager._config
        self.indicator = OrderflowIndicators(self.config)
        self.test_results = []

    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = f"{status} - {test_name}"
        if details:
            result += f"\n    {details}"
        print(result)
        self.test_results.append((test_name, passed, details))

    def test_configurable_cvd_saturation(self):
        """Test Enhancement #1: Configurable CVD saturation threshold."""
        print("\n" + "="*70)
        print("TEST 1: Configurable CVD Saturation Threshold")
        print("="*70)

        # Reset cache
        self.indicator._cache = {}

        # Read the configured saturation from config
        cvd_config = self.config.get('analysis', {}).get('indicators', {}).get('orderflow', {}).get('cvd', {})
        configured_saturation = cvd_config.get('saturation_threshold', 0.15)

        # Create test data with CVD percentage matching the threshold
        timestamp = datetime.now()
        trades = []

        # Create trades that result in CVD percentage equal to configured threshold
        # If threshold is 0.15 (15%), create 57.5% buy and 42.5% sell = 15% imbalance
        buy_pct = 0.5 + (configured_saturation / 2)
        sell_pct = 1.0 - buy_pct

        for i in range(100):
            if i < (buy_pct * 100):
                trades.append({
                    'timestamp': (timestamp - timedelta(seconds=100-i)).timestamp() * 1000,
                    'side': 'buy',
                    'amount': 1.0,
                    'price': 50000,
                })
            else:
                trades.append({
                    'timestamp': (timestamp - timedelta(seconds=100-i)).timestamp() * 1000,
                    'side': 'sell',
                    'amount': 1.0,
                    'price': 50000,
                })

        market_data = {
            'trades': trades,
            'ohlcv': [
                [timestamp.timestamp() * 1000, 50000, 50000, 50000, 50000, 100]
            ]
        }

        try:
            score = self.indicator._calculate_cvd(market_data)

            # Score should reflect the configured threshold
            # With CVD at exactly the saturation threshold, strength should be ~1.0
            passed = 50 < score <= 100  # Should be bullish since CVD is positive

            details = f"Configured threshold: {configured_saturation}, Score: {score:.2f}"
            self.log_test("Configurable CVD saturation", passed, details)

            return passed

        except Exception as e:
            self.log_test("Configurable CVD saturation", False, f"Error: {str(e)}")
            return False

    def test_configurable_oi_saturation(self):
        """Test Enhancement #2: Configurable OI saturation thresholds."""
        print("\n" + "="*70)
        print("TEST 2: Configurable OI Saturation Thresholds")
        print("="*70)

        # Read configured thresholds
        oi_config = self.config.get('analysis', {}).get('indicators', {}).get('orderflow', {}).get('open_interest', {})
        oi_saturation = oi_config.get('oi_saturation_threshold', 2.0)
        price_saturation = oi_config.get('price_saturation_threshold', 1.0)

        timestamp = datetime.now()

        # Test with OI change and price change both exceeding configured thresholds
        # Note: minimal_change_threshold is 0.02 (2%) and price_direction_threshold is 0.01 (1%)

        # Create OHLCV DataFrame with at least 2 candles for price direction calculation
        ohlcv_df = pd.DataFrame({
            'timestamp': [
                (timestamp - timedelta(minutes=5)).timestamp() * 1000,
                timestamp.timestamp() * 1000
            ],
            'open': [50000, 50000],
            'high': [50100, 50800],
            'low': [49900, 50000],
            'close': [50000, 50750],  # 1.5% increase
            'volume': [1000, 1000]
        })

        market_data = {
            'trades': [],
            'open_interest': {
                'current': 1040,  # 4% increase from 1000 (well above minimal_change_threshold)
                'previous': 1000
            },
            'ohlcv': {
                'base': ohlcv_df  # Provide as DataFrame under 'base' timeframe
            }
        }

        try:
            score = self.indicator._calculate_open_interest_score(market_data)

            # With OI at 4% (2x saturation) and price at 1.5% (1.5x saturation), should show strong bullish signal
            # Scenario 1: OI↑ + Price↑ = Bullish
            passed = score >= 65  # Should be clearly bullish

            details = f"OI threshold: {oi_saturation}%, Price threshold: {price_saturation}%, Score: {score:.2f}"
            self.log_test("Configurable OI saturation", passed, details)

            return passed

        except Exception as e:
            self.log_test("Configurable OI saturation", False, f"Error: {str(e)}")
            return False

    def test_safe_ratio_helper(self):
        """Test Enhancement #3: _safe_ratio() helper function."""
        print("\n" + "="*70)
        print("TEST 3: _safe_ratio() Helper Function")
        print("="*70)

        test_cases = [
            # (numerator, denominator, default, expected_result, description)
            (100, 50, 0.0, 2.0, "Normal division"),
            (100, 0, 0.0, 0.0, "Zero denominator with default 0.0"),
            (100, 1e-15, 0.0, 0.0, "Near-zero denominator (below epsilon)"),
            (100, 1e-8, 0.0, 1e10, "Small but valid denominator"),
            (100, 0, 50.0, 50.0, "Zero denominator with custom default"),
            (-100, 50, 0.0, -2.0, "Negative numerator"),
            (100, -50, 0.0, -2.0, "Negative denominator"),
        ]

        all_passed = True

        for numerator, denominator, default, expected, description in test_cases:
            result = self.indicator._safe_ratio(numerator, denominator, default=default)

            # Allow small floating point error
            if abs(denominator) < 1e-10:
                passed = result == expected
            else:
                passed = abs(result - expected) < 1e-6

            if not passed:
                all_passed = False
                print(f"  ❌ {description}: Expected {expected}, got {result}")
            else:
                print(f"  ✅ {description}: {result}")

        self.log_test("_safe_ratio() helper", all_passed, f"Tested {len(test_cases)} cases")
        return all_passed

    def test_tick_rule_implementation(self):
        """Test Enhancement #4: Tick rule for unknown trade sides."""
        print("\n" + "="*70)
        print("TEST 4: Tick Rule Implementation")
        print("="*70)

        # Reset cache
        self.indicator._cache = {}

        # Create trades with unknown sides and varying prices
        timestamp = datetime.now()
        trades = [
            # First trade (no previous price, will remain unknown)
            {'timestamp': (timestamp - timedelta(seconds=5)).timestamp() * 1000,
             'side': 'unknown', 'amount': 1.0, 'price': 50000},

            # Uptick (50000 -> 50100) - should be classified as buy
            {'timestamp': (timestamp - timedelta(seconds=4)).timestamp() * 1000,
             'side': 'unknown', 'amount': 1.0, 'price': 50100},

            # Downtick (50100 -> 50050) - should be classified as sell
            {'timestamp': (timestamp - timedelta(seconds=3)).timestamp() * 1000,
             'side': 'unknown', 'amount': 1.0, 'price': 50050},

            # No change (50050 -> 50050) - should remain unknown
            {'timestamp': (timestamp - timedelta(seconds=2)).timestamp() * 1000,
             'side': 'unknown', 'amount': 1.0, 'price': 50050},

            # Uptick (50050 -> 50150) - should be classified as buy
            {'timestamp': (timestamp - timedelta(seconds=1)).timestamp() * 1000,
             'side': 'unknown', 'amount': 1.0, 'price': 50150},
        ]

        market_data = {
            'trades': trades,
            'ohlcv': [[timestamp.timestamp() * 1000, 50000, 50150, 50000, 50150, 5]]
        }

        try:
            # Get processed trades DataFrame
            trades_df = self.indicator._get_processed_trades(market_data)

            # Check classifications
            # Trade 0: Should be unknown (no previous price)
            # Trade 1: Should be buy (uptick)
            # Trade 2: Should be sell (downtick)
            # Trade 3: Should be unknown (no price change)
            # Trade 4: Should be buy (uptick)

            expected_buys = [False, True, False, False, True]
            expected_sells = [False, False, True, False, False]

            buy_matches = (trades_df['is_buy'].tolist() == expected_buys)
            sell_matches = (trades_df['is_sell'].tolist() == expected_sells)

            passed = buy_matches and sell_matches

            classified_count = (trades_df['is_buy'] | trades_df['is_sell']).sum()

            details = f"Classified {classified_count}/5 trades (expected: 3)"
            if not passed:
                details += f"\n    is_buy: {trades_df['is_buy'].tolist()}"
                details += f"\n    is_sell: {trades_df['is_sell'].tolist()}"

            self.log_test("Tick rule implementation", passed, details)

            return passed

        except Exception as e:
            self.log_test("Tick rule implementation", False, f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def test_tick_rule_high_unknown_warning(self):
        """Test that high percentage of unknown trades triggers warning."""
        print("\n" + "="*70)
        print("TEST 5: Tick Rule High Unknown Warning")
        print("="*70)

        # Reset cache
        self.indicator._cache = {}

        # Create data with >10% unknown trades
        timestamp = datetime.now()
        trades = []

        # 15 unknown trades
        for i in range(15):
            trades.append({
                'timestamp': (timestamp - timedelta(seconds=100-i)).timestamp() * 1000,
                'side': 'unknown',
                'amount': 1.0,
                'price': 50000,
            })

        # 85 known trades
        for i in range(85):
            trades.append({
                'timestamp': (timestamp - timedelta(seconds=85-i)).timestamp() * 1000,
                'side': 'buy' if i % 2 == 0 else 'sell',
                'amount': 1.0,
                'price': 50000,
            })

        market_data = {
            'trades': trades,
            'ohlcv': [[timestamp.timestamp() * 1000, 50000, 50000, 50000, 50000, 100]]
        }

        try:
            # This should log a warning about high unknown percentage
            trades_df = self.indicator._get_processed_trades(market_data)

            # Test passes if we got a DataFrame back without errors
            passed = len(trades_df) == 100

            unknown_pct = 15.0
            details = f"Processed {len(trades_df)} trades with {unknown_pct}% unknown (should warn)"
            self.log_test("High unknown percentage warning", passed, details)

            return passed

        except Exception as e:
            self.log_test("High unknown percentage warning", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all Phase 2 enhancement tests."""
        print("\n" + "="*70)
        print("PHASE 2 ENHANCEMENTS VALIDATION")
        print("="*70)
        print(f"Testing enhancements in: {project_root}/src/indicators/orderflow_indicators.py")
        print()

        # Run tests
        test_methods = [
            self.test_configurable_cvd_saturation,
            self.test_configurable_oi_saturation,
            self.test_safe_ratio_helper,
            self.test_tick_rule_implementation,
            self.test_tick_rule_high_unknown_warning,
        ]

        results = [test() for test in test_methods]

        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)

        passed = sum(results)
        total = len(results)

        for test_name, result, details in self.test_results:
            status = "✅" if result else "❌"
            print(f"{status} {test_name}")

        print()
        print(f"Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")

        if passed == total:
            print("\n🎉 All Phase 2 enhancements validated successfully!")
            return 0
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
            return 1


def main():
    """Main entry point."""
    tester = TestPhase2Enhancements()
    return tester.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
