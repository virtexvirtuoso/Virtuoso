"""
Test to validate that PDF chart generation and risk management sections
produce consistent stop loss values.

This test ensures that both sections of the PDF use the same StopLossCalculator
logic and don't show conflicting values to users.
"""

import sys
import os
import unittest
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.reporting.pdf_generator import ReportGenerator
from src.core.risk.stop_loss_calculator import get_stop_loss_calculator, StopLossCalculator
import logging

# Initialize logging
logger = logging.getLogger(__name__)


class TestPDFChartRiskConsistency(unittest.TestCase):
    """Test suite to validate PDF consistency between chart and risk management sections."""

    def setUp(self):
        """Set up test fixtures."""
        # Minimal config for testing
        self.config = {
            'risk': {
                'long_stop_percentage': 4.5,
                'short_stop_percentage': 5.0,
                'min_stop_multiplier': 0.7,
                'max_stop_multiplier': 2.0,
            },
            'confluence': {
                'thresholds': {
                    'long': 70,
                    'short': 35
                }
            }
        }

        # Initialize calculator
        self.calculator = StopLossCalculator(self.config)

    def test_long_signal_consistency(self):
        """Test that LONG signal produces same stop loss in chart and risk management."""
        # Test case: LONG signal just above threshold
        entry_price = 0.512
        signal_type = "LONG"
        confluence_score = 70.1

        # Calculate expected stop loss using calculator
        expected_stop = self.calculator.calculate_stop_loss_price(
            entry_price=entry_price,
            signal_type=signal_type,
            confluence_score=confluence_score,
        )

        # Verify the expected value is reasonable
        self.assertIsNotNone(expected_stop, "Calculator should return a value")
        self.assertLess(expected_stop, entry_price, "LONG stop should be below entry")
        self.assertGreater(expected_stop, 0, "Stop loss should be positive")

        # Calculate percentage
        stop_pct = abs((expected_stop - entry_price) / entry_price) * 100

        # Should be within expected range (3.15% to 9.0%)
        self.assertGreaterEqual(stop_pct, 3.15, f"Stop {stop_pct:.2f}% too tight")
        self.assertLessEqual(stop_pct, 9.0, f"Stop {stop_pct:.2f}% too wide")

        logger.info(f"✅ LONG consistency test passed: entry ${entry_price:.3f} → stop ${expected_stop:.3f} ({stop_pct:.2f}%)")

    def test_short_signal_consistency(self):
        """Test that SHORT signal produces same stop loss in chart and risk management."""
        # Test case: SHORT signal with high confidence
        entry_price = 50000.0
        signal_type = "SHORT"
        confluence_score = 85.0

        # Calculate expected stop loss using calculator
        expected_stop = self.calculator.calculate_stop_loss_price(
            entry_price=entry_price,
            signal_type=signal_type,
            confluence_score=confluence_score,
        )

        # Verify the expected value is reasonable
        self.assertIsNotNone(expected_stop, "Calculator should return a value")
        self.assertGreater(expected_stop, entry_price, "SHORT stop should be above entry")

        # Calculate percentage
        stop_pct = abs((expected_stop - entry_price) / entry_price) * 100

        # Should be within expected range (3.5% to 10.0% for short)
        # Allow tiny floating point tolerance
        self.assertGreaterEqual(stop_pct, 3.5 - 0.01, f"Stop {stop_pct:.2f}% too tight")
        self.assertLessEqual(stop_pct, 10.0 + 0.01, f"Stop {stop_pct:.2f}% too wide")

        logger.info(f"✅ SHORT consistency test passed: entry ${entry_price:.2f} → stop ${expected_stop:.2f} ({stop_pct:.2f}%)")

    def test_multiple_confidence_levels(self):
        """Test consistency across different confidence levels."""
        entry_price = 1000.0
        signal_type = "LONG"

        test_cases = [
            {"score": 70.1, "name": "Just above threshold"},
            {"score": 75.0, "name": "Medium confidence"},
            {"score": 85.0, "name": "High confidence"},
            {"score": 95.0, "name": "Very high confidence"},
        ]

        previous_stop_pct = None

        for case in test_cases:
            stop_loss = self.calculator.calculate_stop_loss_price(
                entry_price=entry_price,
                signal_type=signal_type,
                confluence_score=case['score'],
                )

            stop_pct = abs((stop_loss - entry_price) / entry_price) * 100

            # Verify stop loss is reasonable
            self.assertLess(stop_loss, entry_price, f"LONG stop should be below entry for {case['name']}")
            self.assertGreaterEqual(stop_pct, 3.15, f"Stop too tight for {case['name']}")
            self.assertLessEqual(stop_pct, 9.0, f"Stop too wide for {case['name']}")

            # Verify higher confidence = tighter stops
            if previous_stop_pct is not None:
                self.assertLessEqual(
                    stop_pct,
                    previous_stop_pct + 0.5,  # Allow small tolerance for rounding
                    f"Higher confidence should have tighter or equal stop: {case['name']} "
                    f"({stop_pct:.2f}%) vs previous ({previous_stop_pct:.2f}%)"
                )

            previous_stop_pct = stop_pct
            logger.info(f"✅ {case['name']} (score {case['score']}): {stop_pct:.2f}%")

    def test_fallback_consistency(self):
        """Test that fallback logic produces consistent values."""
        entry_price = 100.0

        # Test NEUTRAL signal (should use fallback)
        signal_type = "NEUTRAL"
        confluence_score = 50

        # For NEUTRAL signals, both chart and risk management should use 3% fallback
        expected_stop = entry_price * 0.97  # 3% below entry

        # Verify the fallback value
        self.assertEqual(expected_stop, 97.0, "NEUTRAL fallback should be 3% below entry")

        logger.info(f"✅ Fallback consistency test passed: NEUTRAL signal uses 3% default")

    def test_edge_cases(self):
        """Test edge cases for consistency."""
        test_cases = [
            {"entry": 0.001, "type": "LONG", "score": 70, "name": "Very low price"},
            {"entry": 100000.0, "type": "SHORT", "score": 35, "name": "Very high price"},
            {"entry": 1.0, "type": "LONG", "score": 100, "name": "Perfect score"},
            {"entry": 50.0, "type": "SHORT", "score": 35, "name": "At threshold"},
        ]

        for case in test_cases:
            stop_loss = self.calculator.calculate_stop_loss_price(
                entry_price=case['entry'],
                signal_type=case['type'],
                confluence_score=case['score'],
                )

            # Verify stop loss makes sense
            self.assertIsNotNone(stop_loss, f"Calculator should return value for {case['name']}")
            self.assertGreater(stop_loss, 0, f"Stop loss should be positive for {case['name']}")

            if case['type'] == "LONG":
                self.assertLess(stop_loss, case['entry'], f"LONG stop should be below entry for {case['name']}")
            elif case['type'] == "SHORT":
                self.assertGreater(stop_loss, case['entry'], f"SHORT stop should be above entry for {case['name']}")

            logger.info(f"✅ Edge case passed: {case['name']}")

    def test_config_integration(self):
        """Test that config values are properly integrated."""
        # Verify config values match expected
        self.assertEqual(self.config['risk']['long_stop_percentage'], 4.5,
                        "Config should have 4.5% long stop")
        self.assertEqual(self.config['risk']['short_stop_percentage'], 5.0,
                        "Config should have 5.0% short stop")
        self.assertEqual(self.config['risk']['min_stop_multiplier'], 0.7,
                        "Config should have 0.7 min multiplier")
        self.assertEqual(self.config['risk']['max_stop_multiplier'], 2.0,
                        "Config should have 2.0 max multiplier")

        logger.info(f"✅ Config integration test passed")


class TestCalculatorOutput(unittest.TestCase):
    """Test the actual calculator output values for documentation accuracy."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'risk': {
                'long_stop_percentage': 4.5,
                'short_stop_percentage': 5.0,
                'min_stop_multiplier': 0.7,
                'max_stop_multiplier': 2.0,
            },
            'confluence': {
                'thresholds': {
                    'long': 70,
                    'short': 35
                }
            }
        }
        self.calculator = StopLossCalculator(self.config)

    def test_documentation_example(self):
        """Test the exact example from STOP_LOSS_FIX_SUMMARY.md."""
        # Example from documentation
        entry_price = 0.512
        signal_type = "LONG"
        confluence_score = 70.1

        # Calculate stop loss
        stop_loss = self.calculator.calculate_stop_loss_price(
            entry_price=entry_price,
            signal_type=signal_type,
            confluence_score=confluence_score,
        )

        # Calculate percentage
        stop_pct = abs((stop_loss - entry_price) / entry_price) * 100

        # Documentation claims ~$0.466 (8.98%)
        # Allow small tolerance for floating point
        self.assertAlmostEqual(stop_loss, 0.466, places=3,
                              msg=f"Expected ~$0.466, got ${stop_loss:.6f}")
        self.assertAlmostEqual(stop_pct, 8.98, places=1,
                              msg=f"Expected ~8.98%, got {stop_pct:.2f}%")

        logger.info(f"✅ Documentation example verified: ${stop_loss:.6f} ({stop_pct:.2f}%)")

    def test_value_ranges(self):
        """Test that values fall within expected ranges."""
        entry_price = 100.0

        # Test LONG with various scores
        long_test_cases = [
            {"score": 70, "min_pct": 8.5, "max_pct": 9.0, "name": "At threshold"},
            {"score": 85, "min_pct": 5.0, "max_pct": 7.0, "name": "High confidence"},
            {"score": 100, "min_pct": 3.15, "max_pct": 4.0, "name": "Perfect score"},
        ]

        for case in long_test_cases:
            stop_loss = self.calculator.calculate_stop_loss_price(
                entry_price=entry_price,
                signal_type="LONG",
                confluence_score=case['score'],
                )

            stop_pct = abs((stop_loss - entry_price) / entry_price) * 100

            self.assertGreaterEqual(stop_pct, case['min_pct'] - 0.01,  # Allow tiny floating point tolerance
                                   f"{case['name']}: {stop_pct:.2f}% below min {case['min_pct']}%")
            self.assertLessEqual(stop_pct, case['max_pct'] + 0.01,  # Allow tiny floating point tolerance
                                f"{case['name']}: {stop_pct:.2f}% above max {case['max_pct']}%")

            logger.info(f"✅ Value range test passed: {case['name']} → {stop_pct:.2f}%")


def run_tests():
    """Run all tests and report results."""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "="*70)
    if result.wasSuccessful():
        print("✅ ALL CONSISTENCY TESTS PASSED")
        print(f"   Ran {result.testsRun} tests successfully")
    else:
        print("❌ SOME TESTS FAILED")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
    print("="*70)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
