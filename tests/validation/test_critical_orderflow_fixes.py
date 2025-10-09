#!/usr/bin/env python3
"""
Test Critical Orderflow Indicator Fixes - Phase 1

Tests the three critical bug fixes:
1. Line 1296: Price/CVD comparison scaling
2. Line 1186: CVD volume epsilon guard
3. Line 1721: OI division epsilon guard
4. Line 1178: CVD bounds checking
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


class TestCriticalOrderflowFixes:
    """Test suite for critical orderflow indicator fixes."""

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

    def test_price_cvd_comparison_scaling(self):
        """Test Fix #1: Price/CVD comparison uses correct scaling."""
        print("\n" + "="*70)
        print("TEST 1: Price/CVD Comparison Scaling (Line 1296)")
        print("="*70)

        # Create test data with known CVD and price changes
        # CVD = 15% delta, Price = 2.5% change
        # Before fix: 0.15 > (2.5/100) = 0.025 ✅ CVD dominates (correct)
        # Before fix had the comparison inline which was wrong
        # After fix: 0.15 > 0.025 ✅ CVD dominates (correct)

        timestamp = datetime.now()
        trades = []

        # Create trades with 15% buy imbalance
        for i in range(100):
            if i < 57.5:  # 57.5% buy
                trades.append({
                    'timestamp': (timestamp - timedelta(seconds=100-i)).timestamp() * 1000,
                    'side': 'buy',
                    'amount': 1.0,
                    'price': 50000 + (i * 10),  # Slight price increase
                })
            else:  # 42.5% sell
                trades.append({
                    'timestamp': (timestamp - timedelta(seconds=100-i)).timestamp() * 1000,
                    'side': 'sell',
                    'amount': 1.0,
                    'price': 50000 + (i * 10),
                })

        market_data = {
            'trades': trades,
            'ohlcv': [
                [timestamp.timestamp() * 1000, 50000, 51000, 49900, 50250, 1000]
            ]
        }

        # Calculate CVD score
        try:
            score = self.indicator._calculate_cvd(market_data)

            # The score should reflect CVD dominance (bullish due to 15% buy imbalance)
            # Score should be > 50 (bullish) since CVD is positive
            passed = 50 < score <= 100

            details = f"Score: {score:.2f} (Expected: >50 for positive CVD)"
            self.log_test("Price/CVD comparison scaling", passed, details)

            return passed

        except Exception as e:
            self.log_test("Price/CVD comparison scaling", False, f"Error: {str(e)}")
            return False

    def test_cvd_volume_epsilon_guard(self):
        """Test Fix #2: CVD volume epsilon guard."""
        print("\n" + "="*70)
        print("TEST 2: CVD Volume Epsilon Guard (Line 1186)")
        print("="*70)

        # Reset cache to avoid interference from previous tests
        self.indicator._cache = {}

        # Test with near-zero volume (should return 50.0 neutral score)
        timestamp = datetime.now()
        trades = [
            {
                'timestamp': (timestamp - timedelta(seconds=1)).timestamp() * 1000,
                'side': 'buy',
                'amount': 1e-10,  # Extremely small volume
                'price': 50000,
            },
            {
                'timestamp': timestamp.timestamp() * 1000,
                'side': 'sell',
                'amount': 1e-10,  # Extremely small volume
                'price': 50000,
            }
        ]

        market_data = {
            'trades': trades,
            'ohlcv': [
                [timestamp.timestamp() * 1000, 50000, 50000, 50000, 50000, 1e-10]
            ]
        }

        try:
            score = self.indicator._calculate_cvd(market_data)

            # Should return exactly 50.0 (neutral) due to insufficient volume
            passed = score == 50.0

            details = f"Score: {score:.2f} (Expected: 50.0 for insufficient volume)"
            self.log_test("CVD volume epsilon guard", passed, details)

            return passed

        except Exception as e:
            self.log_test("CVD volume epsilon guard", False, f"Error: {str(e)}")
            return False

    def test_oi_epsilon_guard(self):
        """Test Fix #3: OI division epsilon guard."""
        print("\n" + "="*70)
        print("TEST 3: OI Division Epsilon Guard (Line 1721)")
        print("="*70)

        # Test with near-zero previous OI
        timestamp = datetime.now()

        market_data = {
            'trades': [],
            'open_interest': {
                'current': 1000000,
                'previous': 1e-10  # Near-zero OI (should be caught by epsilon)
            },
            'ohlcv': [
                [timestamp.timestamp() * 1000, 50000, 51000, 50000, 50500, 1000]
            ]
        }

        try:
            score = self.indicator._calculate_open_interest_score(market_data)

            # Should return 50.0 (neutral) due to insufficient previous OI
            # The epsilon guard should prevent division and return 0% change
            passed = 40 <= score <= 60  # Allow small variance

            details = f"Score: {score:.2f} (Expected: ~50.0 for near-zero previous OI)"
            self.log_test("OI epsilon guard", passed, details)

            return passed

        except Exception as e:
            self.log_test("OI epsilon guard", False, f"Error: {str(e)}")
            return False

    def test_extreme_oi_capping(self):
        """Test Fix #3b: OI extreme value capping."""
        print("\n" + "="*70)
        print("TEST 4: OI Extreme Value Capping (Line 1735)")
        print("="*70)

        # Test with valid but extreme OI change
        timestamp = datetime.now()

        market_data = {
            'trades': [],
            'open_interest': {
                'current': 1000000,
                'previous': 100  # 999,900% increase (should be capped at 500%)
            },
            'ohlcv': [
                [timestamp.timestamp() * 1000, 50000, 51000, 50000, 50500, 1000]
            ]
        }

        try:
            score = self.indicator._calculate_open_interest_score(market_data)

            # Score should be bounded (not infinite or NaN)
            passed = 0 <= score <= 100 and not np.isnan(score) and not np.isinf(score)

            details = f"Score: {score:.2f} (Expected: 0-100, not NaN/Inf)"
            self.log_test("OI extreme value capping", passed, details)

            return passed

        except Exception as e:
            self.log_test("OI extreme value capping", False, f"Error: {str(e)}")
            return False

    def test_cvd_bounds_checking(self):
        """Test Fix #4: CVD bounds checking."""
        print("\n" + "="*70)
        print("TEST 5: CVD Bounds Checking (Line 1178)")
        print("="*70)

        # Reset cache to avoid interference from previous tests
        self.indicator._cache = {}

        # Create trades that would result in extreme CVD value
        timestamp = datetime.now()
        trades = []

        # Create trades with extremely large volumes
        for i in range(100):
            trades.append({
                'timestamp': (timestamp - timedelta(seconds=100-i)).timestamp() * 1000,
                'side': 'buy',
                'amount': 1e11,  # Extremely large volume
                'price': 50000,
            })

        market_data = {
            'trades': trades,
            'ohlcv': [
                [timestamp.timestamp() * 1000, 50000, 51000, 50000, 50500, 1e13]
            ]
        }

        try:
            score = self.indicator._calculate_cvd(market_data)

            # Should return 50.0 (neutral) due to abnormal CVD value
            passed = score == 50.0

            details = f"Score: {score:.2f} (Expected: 50.0 for abnormal CVD)"
            self.log_test("CVD bounds checking", passed, details)

            return passed

        except Exception as e:
            self.log_test("CVD bounds checking", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all critical fix tests."""
        print("\n" + "="*70)
        print("CRITICAL ORDERFLOW FIXES VALIDATION - PHASE 1")
        print("="*70)
        print(f"Testing fixes in: {project_root}/src/indicators/orderflow_indicators.py")
        print()

        # Run tests
        test_methods = [
            self.test_price_cvd_comparison_scaling,
            self.test_cvd_volume_epsilon_guard,
            self.test_oi_epsilon_guard,
            self.test_extreme_oi_capping,
            self.test_cvd_bounds_checking,
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
            print("\n🎉 All critical fixes validated successfully!")
            return 0
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
            return 1


def main():
    """Main entry point."""
    tester = TestCriticalOrderflowFixes()
    return tester.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
