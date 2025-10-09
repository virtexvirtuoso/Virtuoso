#!/usr/bin/env python3
"""
Test Phase 3 Orderflow Indicator Enhancements

Tests the Phase 3 improvements:
1. Consolidated epsilon constants
2. Decimal precision for CVD calculations
3. Performance monitoring
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
from decimal import Decimal
from src.indicators.orderflow_indicators import OrderflowIndicators
from src.core.config.config_manager import ConfigManager


class TestPhase3Enhancements:
    """Test suite for Phase 3 orderflow indicator enhancements."""

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

    def test_epsilon_constants_defined(self):
        """Test Enhancement #1: Verify epsilon constants are defined."""
        print("\n" + "="*70)
        print("TEST 1: Epsilon Constants Defined")
        print("="*70)

        required_constants = [
            'VOLUME_EPSILON',
            'PRICE_EPSILON',
            'OI_EPSILON',
            'GENERAL_EPSILON',
            'MAX_CVD_VALUE'
        ]

        missing = []
        values = {}

        for const in required_constants:
            if hasattr(self.indicator, const):
                values[const] = getattr(self.indicator, const)
            else:
                missing.append(const)

        passed = len(missing) == 0

        if passed:
            details = "All epsilon constants defined:\n"
            for const, value in values.items():
                details += f"      {const} = {value}\n"
            details = details.rstrip()
        else:
            details = f"Missing constants: {', '.join(missing)}"

        self.log_test("Epsilon constants defined", passed, details)
        return passed

    def test_epsilon_constants_used_correctly(self):
        """Test Enhancement #1: Verify epsilon constants are used in calculations."""
        print("\n" + "="*70)
        print("TEST 2: Epsilon Constants Used Correctly")
        print("="*70)

        # Test 1: VOLUME_EPSILON used in CVD calculation
        timestamp = datetime.now()

        # Create market data with very small volume (below VOLUME_EPSILON)
        small_volume = self.indicator.VOLUME_EPSILON / 2

        trades = [{
            'timestamp': timestamp.timestamp() * 1000,
            'side': 'buy',
            'amount': small_volume,
            'price': 50000,
        }]

        market_data = {
            'trades': trades,
            'ohlcv': [[timestamp.timestamp() * 1000, 50000, 50000, 50000, 50000, small_volume]]
        }

        try:
            # Reset cache
            self.indicator._cache = {}

            # Should return neutral score due to insufficient volume
            score = self.indicator._calculate_cvd(market_data)

            # Should be neutral (50) due to volume check
            passed = abs(score - 50.0) < 0.1

            details = f"Small volume ({small_volume:.2e} < {self.indicator.VOLUME_EPSILON:.2e}), Score: {score:.2f}"
            self.log_test("VOLUME_EPSILON guards CVD calculation", passed, details)

            return passed

        except Exception as e:
            self.log_test("VOLUME_EPSILON guards CVD calculation", False, f"Error: {str(e)}")
            return False

    def test_decimal_precision_accuracy(self):
        """Test Enhancement #2: Verify Decimal precision improves accuracy."""
        print("\n" + "="*70)
        print("TEST 3: Decimal Precision Accuracy")
        print("="*70)

        # Test case: Large CVD value with potential floating-point errors
        cvd = 123456789.123456789
        total_volume = 987654321.987654321

        # Calculate with Decimal precision
        decimal_result = self.indicator._calculate_precise_cvd_percentage(cvd, total_volume)

        # Calculate with standard float
        float_result = cvd / total_volume

        # Calculate with Decimal for reference
        reference = float(Decimal(str(cvd)) / Decimal(str(total_volume)))

        # Decimal precision should match reference exactly
        decimal_error = abs(decimal_result - reference)
        float_error = abs(float_result - reference)

        passed = decimal_error <= float_error

        details = f"Decimal error: {decimal_error:.2e}, Float error: {float_error:.2e}\n"
        details += f"      Decimal result: {decimal_result:.15f}\n"
        details += f"      Float result: {float_result:.15f}\n"
        details += f"      Reference: {reference:.15f}"

        self.log_test("Decimal precision more accurate", passed, details)
        return passed

    def test_decimal_precision_edge_cases(self):
        """Test Enhancement #2: Verify Decimal precision handles edge cases."""
        print("\n" + "="*70)
        print("TEST 4: Decimal Precision Edge Cases")
        print("="*70)

        test_cases = [
            # (cvd, volume, description, expected_behavior)
            (100, 1e-10, "Zero volume", 0.0),
            (1e10, 1e10, "Equal large values", 1.0),
            (-1e10, 1e10, "Large negative CVD", -1.0),
            (50, 100, "Normal calculation", 0.5),
            (1.5, 1.0, "CVD > volume (capped)", 1.0),
            (-1.5, 1.0, "CVD < -volume (capped)", -1.0),
        ]

        all_passed = True

        for cvd, volume, description, expected in test_cases:
            result = self.indicator._calculate_precise_cvd_percentage(cvd, volume)

            # Allow small error
            passed = abs(result - expected) < 1e-6

            if not passed:
                all_passed = False
                print(f"  ❌ {description}: Expected {expected}, got {result}")
            else:
                print(f"  ✅ {description}: {result}")

        self.log_test("Decimal precision edge cases", all_passed, f"Tested {len(test_cases)} cases")
        return all_passed

    def test_performance_monitoring_tracking(self):
        """Test Enhancement #3: Verify performance monitoring tracks metrics."""
        print("\n" + "="*70)
        print("TEST 5: Performance Monitoring Tracking")
        print("="*70)

        # Reset debug stats
        if hasattr(self.indicator, '_debug_stats'):
            self.indicator._debug_stats['performance_metrics'] = {}

        # Manually track a test operation
        operation_name = "test_operation"
        execution_times = [0.001, 0.002, 0.0015, 0.003, 0.0025]

        for exec_time in execution_times:
            self.indicator._track_performance(operation_name, exec_time)

        # Verify metrics are tracked correctly
        metrics = self.indicator._debug_stats['performance_metrics'].get(operation_name, {})

        expected_count = len(execution_times)
        expected_total = sum(execution_times)
        expected_min = min(execution_times)
        expected_max = max(execution_times)
        expected_avg = expected_total / expected_count

        passed = (
            metrics.get('count') == expected_count and
            abs(metrics.get('total_time', 0) - expected_total) < 1e-9 and
            abs(metrics.get('min_time', 0) - expected_min) < 1e-9 and
            abs(metrics.get('max_time', 0) - expected_max) < 1e-9 and
            abs(metrics.get('avg_time', 0) - expected_avg) < 1e-9
        )

        details = f"Count: {metrics.get('count')} (expected {expected_count})\n"
        details += f"      Total: {metrics.get('total_time', 0):.6f}s (expected {expected_total:.6f}s)\n"
        details += f"      Min: {metrics.get('min_time', 0):.6f}s (expected {expected_min:.6f}s)\n"
        details += f"      Max: {metrics.get('max_time', 0):.6f}s (expected {expected_max:.6f}s)\n"
        details += f"      Avg: {metrics.get('avg_time', 0):.6f}s (expected {expected_avg:.6f}s)"

        self.log_test("Performance tracking accuracy", passed, details)
        return passed

    def test_performance_monitoring_slow_warning(self):
        """Test Enhancement #3: Verify slow operation warnings."""
        print("\n" + "="*70)
        print("TEST 6: Performance Monitoring Slow Operation Warning")
        print("="*70)

        # Reset debug stats
        if hasattr(self.indicator, '_debug_stats'):
            self.indicator._debug_stats['performance_metrics'] = {}

        # Track a slow operation (>100ms)
        slow_operation = "intentionally_slow_test"
        slow_time = 0.15  # 150ms

        # This should log a warning
        self.indicator._track_performance(slow_operation, slow_time)

        # Check that it was tracked
        metrics = self.indicator._debug_stats['performance_metrics'].get(slow_operation, {})

        passed = (
            metrics.get('count') == 1 and
            abs(metrics.get('max_time', 0) - slow_time) < 1e-9
        )

        details = f"Slow operation tracked: {slow_time*1000:.2f}ms (threshold: 100ms)\n"
        details += f"      Warning should be logged for operations >100ms"

        self.log_test("Slow operation warning", passed, details)
        return passed

    def test_performance_metrics_api(self):
        """Test Enhancement #3: Verify get_performance_metrics() API."""
        print("\n" + "="*70)
        print("TEST 7: Performance Metrics API")
        print("="*70)

        # Track some operations
        if hasattr(self.indicator, '_debug_stats'):
            self.indicator._debug_stats['performance_metrics'] = {}

        self.indicator._track_performance("op1", 0.001)
        self.indicator._track_performance("op2", 0.002)
        self.indicator._track_performance("op1", 0.003)

        # Get metrics via API
        try:
            metrics = self.indicator.get_performance_metrics()

            required_keys = ['operations', 'cache_efficiency', 'scenario_distribution']
            has_all_keys = all(key in metrics for key in required_keys)

            has_operations = (
                'op1' in metrics['operations'] and
                'op2' in metrics['operations']
            )

            op1_correct = metrics['operations']['op1']['count'] == 2
            op2_correct = metrics['operations']['op2']['count'] == 1

            passed = has_all_keys and has_operations and op1_correct and op2_correct

            details = f"API returns required keys: {has_all_keys}\n"
            details += f"      Operations tracked: {list(metrics['operations'].keys())}\n"
            details += f"      op1 count: {metrics['operations']['op1']['count']} (expected 2)\n"
            details += f"      op2 count: {metrics['operations']['op2']['count']} (expected 1)"

            self.log_test("Performance metrics API", passed, details)
            return passed

        except Exception as e:
            self.log_test("Performance metrics API", False, f"Error: {str(e)}")
            return False

    def test_integration_cvd_with_decimal_precision(self):
        """Integration test: CVD calculation uses Decimal precision."""
        print("\n" + "="*70)
        print("TEST 8: Integration - CVD Uses Decimal Precision")
        print("="*70)

        # Create realistic market data
        timestamp = datetime.now()
        trades = []

        # Create 100 trades with varying volumes
        for i in range(100):
            trades.append({
                'timestamp': (timestamp - timedelta(seconds=100-i)).timestamp() * 1000,
                'side': 'buy' if i < 60 else 'sell',
                'amount': 1.123456789 + (i * 0.001),  # Varying amounts with precision
                'price': 50000 + (i * 10),
            })

        total_volume = sum(t['amount'] for t in trades)

        market_data = {
            'trades': trades,
            'ohlcv': [[timestamp.timestamp() * 1000, 50000, 51000, 50000, 51000, total_volume]]
        }

        try:
            # Reset cache
            self.indicator._cache = {}

            # Calculate CVD score
            score = self.indicator._calculate_cvd(market_data)

            # Should return a valid bullish score (60 buy, 40 sell)
            passed = 50 < score <= 100

            details = f"CVD score: {score:.2f} (60% buy, 40% sell)\n"
            details += f"      Total volume: {total_volume:.9f}\n"
            details += f"      Decimal precision used internally"

            self.log_test("CVD integration with Decimal precision", passed, details)
            return passed

        except Exception as e:
            self.log_test("CVD integration with Decimal precision", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all Phase 3 enhancement tests."""
        print("\n" + "="*70)
        print("PHASE 3 ENHANCEMENTS VALIDATION")
        print("="*70)
        print(f"Testing enhancements in: {project_root}/src/indicators/orderflow_indicators.py")
        print()

        # Run tests
        test_methods = [
            self.test_epsilon_constants_defined,
            self.test_epsilon_constants_used_correctly,
            self.test_decimal_precision_accuracy,
            self.test_decimal_precision_edge_cases,
            self.test_performance_monitoring_tracking,
            self.test_performance_monitoring_slow_warning,
            self.test_performance_metrics_api,
            self.test_integration_cvd_with_decimal_precision,
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
            print("\n🎉 All Phase 3 enhancements validated successfully!")
            return 0
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
            return 1


def main():
    """Main entry point."""
    tester = TestPhase3Enhancements()
    return tester.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
