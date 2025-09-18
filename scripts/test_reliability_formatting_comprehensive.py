#!/usr/bin/env python3
"""
Comprehensive test suite for reliability formatting fixes.
Tests the normalization logic that prevents 10000% displays.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch
import traceback
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.core.formatting.formatter import PrettyTableFormatter, AnalysisFormatter, EnhancedFormatter
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root with venv311 activated")
    sys.exit(1)


class TestReliabilityFormatting(unittest.TestCase):
    """Test suite for reliability percentage formatting."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_components = {
            'orderflow': 75.0,
            'sentiment': 60.0,
            'liquidity': 80.0,
            'bitcoin_beta': 45.0,
            'smart_money': 70.0,
            'ml_prediction': 65.0
        }
        self.sample_results = {
            'orderflow': {'interpretation': 'Strong buying pressure'},
            'sentiment': {'interpretation': 'Neutral market mood'},
            'liquidity': {'interpretation': 'High liquidity zones'},
            'bitcoin_beta': {'interpretation': 'Low correlation'},
            'smart_money': {'interpretation': 'Institutional accumulation'},
            'ml_prediction': {'interpretation': 'Bullish prediction'}
        }

    def test_reliability_0_to_1_range(self):
        """Test reliability values in 0.0-1.0 range (normal case)."""
        test_cases = [
            (0.0, "0%"),
            (0.5, "50%"),
            (0.75, "75%"),
            (1.0, "100%"),
            (0.12345, "12%"),  # Should round to nearest integer
            (0.987, "99%")
        ]

        for reliability, expected_pct in test_cases:
            with self.subTest(reliability=reliability):
                try:
                    output = PrettyTableFormatter.format_confluence_score_table(
                        symbol="BTCUSDT",
                        confluence_score=65.0,
                        components=self.sample_components,
                        results=self.sample_results,
                        reliability=reliability
                    )

                    # Check that the expected percentage appears in output
                    self.assertIn(f"Reliability: ", output)
                    self.assertIn(f"{expected_pct}", output)
                    # Ensure no 10000% appears
                    self.assertNotIn("10000%", output)
                    self.assertNotIn("1000%", output)

                except Exception as e:
                    self.fail(f"Failed for reliability {reliability}: {e}")

    def test_reliability_percentage_range(self):
        """Test reliability values in percentage range (needs normalization)."""
        test_cases = [
            (0, "0%"),
            (50, "50%"),
            (75, "75%"),
            (100, "100%"),
            (92.5, "92%"),  # Should round down
            (87.123, "87%")
        ]

        for reliability, expected_pct in test_cases:
            with self.subTest(reliability=reliability):
                try:
                    output = PrettyTableFormatter.format_confluence_score_table(
                        symbol="BTCUSDT",
                        confluence_score=65.0,
                        components=self.sample_components,
                        results=self.sample_results,
                        reliability=reliability
                    )

                    # Check that the expected percentage appears in output
                    self.assertIn(f"Reliability: ", output)
                    self.assertIn(f"{expected_pct}", output)
                    # Ensure no 10000% appears
                    self.assertNotIn("10000%", output)
                    self.assertNotIn("1000%", output)

                except Exception as e:
                    self.fail(f"Failed for reliability {reliability}: {e}")

    def test_reliability_edge_cases(self):
        """Test edge cases and invalid inputs."""
        test_cases = [
            (-5, "0%"),      # Negative should clamp to 0%
            (150, "100%"),   # Over 100 should clamp to 100%
            (500, "100%"),   # Way over 100 should clamp to 100%
            (-0.5, "0%"),    # Negative decimal should clamp to 0%
            (1.5, "2%"),     # Over 1.0 gets normalized as percentage -> 1.5/100 = 0.015 -> 2% (rounded)
        ]

        for reliability, expected_pct in test_cases:
            with self.subTest(reliability=reliability):
                try:
                    output = PrettyTableFormatter.format_confluence_score_table(
                        symbol="BTCUSDT",
                        confluence_score=65.0,
                        components=self.sample_components,
                        results=self.sample_results,
                        reliability=reliability
                    )

                    # Check that the expected percentage appears in output
                    self.assertIn(f"Reliability: ", output)
                    self.assertIn(f"{expected_pct}", output)
                    # Ensure no crazy percentages appear
                    self.assertNotIn("10000%", output)
                    self.assertNotIn("1000%", output)
                    self.assertNotIn("-", output.split("Reliability: ")[1].split("%")[0])  # No negative signs

                except Exception as e:
                    self.fail(f"Failed for reliability {reliability}: {e}")

    def test_reliability_invalid_types(self):
        """Test invalid data types for reliability."""
        test_cases = [
            ("invalid", "0%"),
            (None, "0%"),
            ([], "0%"),
            ({}, "0%"),
            ("75", "75%"),  # String numbers might be converted
        ]

        for reliability, expected_pct in test_cases:
            with self.subTest(reliability=reliability):
                try:
                    output = PrettyTableFormatter.format_confluence_score_table(
                        symbol="BTCUSDT",
                        confluence_score=65.0,
                        components=self.sample_components,
                        results=self.sample_results,
                        reliability=reliability
                    )

                    # Check that it defaults to 0% and doesn't crash
                    self.assertIn(f"Reliability: ", output)
                    self.assertIn(f"{expected_pct}", output)
                    # Ensure no crazy percentages appear
                    self.assertNotIn("10000%", output)
                    self.assertNotIn("1000%", output)

                except Exception as e:
                    self.fail(f"Failed for reliability {reliability}: {e}")

    def test_reliability_colors_and_status(self):
        """Test reliability color coding and status."""
        test_cases = [
            (0.9, "HIGH"),    # >= 0.8 should be HIGH
            (0.8, "HIGH"),    # Boundary case
            (0.7, "MEDIUM"),  # >= 0.5 but < 0.8 should be MEDIUM
            (0.5, "MEDIUM"),  # Boundary case
            (0.4, "LOW"),     # < 0.5 should be LOW
            (0.0, "LOW"),     # Bottom case
            (95, "HIGH"),     # 95% -> 0.95 -> HIGH
            (60, "MEDIUM"),   # 60% -> 0.6 -> MEDIUM
            (30, "LOW"),      # 30% -> 0.3 -> LOW
        ]

        for reliability, expected_status in test_cases:
            with self.subTest(reliability=reliability, expected_status=expected_status):
                try:
                    output = PrettyTableFormatter.format_confluence_score_table(
                        symbol="BTCUSDT",
                        confluence_score=65.0,
                        components=self.sample_components,
                        results=self.sample_results,
                        reliability=reliability
                    )

                    # Check that the expected status appears in output
                    self.assertIn(f"({expected_status})", output)

                except Exception as e:
                    self.fail(f"Failed for reliability {reliability}: {e}")

    def test_enhanced_formatter_reliability(self):
        """Test EnhancedFormatter handles reliability correctly."""
        try:
            output = PrettyTableFormatter.format_enhanced_confluence_score_table(
                symbol="BTCUSDT",
                confluence_score=65.0,
                components=self.sample_components,
                results=self.sample_results,
                reliability=85  # Should normalize to 85%
            )

            # Check for reliability display
            self.assertIn("Reliability:", output)
            self.assertIn("85%", output)
            self.assertNotIn("8500%", output)

        except Exception as e:
            self.fail(f"Enhanced formatter failed: {e}")

    def test_analysis_formatter_reliability(self):
        """Test AnalysisFormatter handles reliability correctly."""
        try:
            # Create a mock analysis result
            analysis_result = {
                'score': 65.0,
                'confluence_score': 65.0,
                'reliability': 0.75,  # Should display as 75%
                'components': self.sample_components,
                'results': self.sample_results
            }

            formatter = AnalysisFormatter()
            output = formatter.format_analysis_result(
                analysis_result=analysis_result,
                symbol_str="BTCUSDT"
            )

            # Check for proper reliability formatting
            self.assertIn("Reliability:", output)
            self.assertIn("75%", output)
            self.assertNotIn("7500%", output)

        except Exception as e:
            self.fail(f"Analysis formatter failed: {e}")

    def test_reliability_boundary_conditions(self):
        """Test boundary conditions for reliability normalization."""
        boundary_cases = [
            (0.999999, "100%"),  # Just under 1.0
            (1.000001, "1%"),    # Just over 1.0 -> should be normalized as percentage
            (99.999, "100%"),    # Just under 100
            (100.001, "100%"),   # Just over 100
            (0.000001, "0%"),    # Just above 0
            (-0.000001, "0%"),   # Just below 0
        ]

        for reliability, expected_pct in boundary_cases:
            with self.subTest(reliability=reliability):
                try:
                    output = PrettyTableFormatter.format_confluence_score_table(
                        symbol="BTCUSDT",
                        confluence_score=65.0,
                        components=self.sample_components,
                        results=self.sample_results,
                        reliability=reliability
                    )

                    self.assertIn(f"{expected_pct}", output)
                    self.assertNotIn("10000%", output)

                except Exception as e:
                    self.fail(f"Failed for boundary case {reliability}: {e}")


def run_reliability_tests():
    """Run all reliability formatting tests."""
    print("=" * 80)
    print("COMPREHENSIVE RELIABILITY FORMATTING TESTS")
    print("=" * 80)
    print()

    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestReliabilityFormatting)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    print("\n" + "=" * 80)
    print("RELIABILITY TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")

    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")

    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nOverall Result: {'PASS' if success else 'FAIL'}")

    return success


if __name__ == "__main__":
    success = run_reliability_tests()
    sys.exit(0 if success else 1)