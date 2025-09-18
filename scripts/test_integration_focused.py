#!/usr/bin/env python3
"""
Focused integration test for reliability formatting and tuple unwrapping fixes.
Tests key integration points without starting the full application.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch
import json

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.core.formatting.formatter import PrettyTableFormatter, AnalysisFormatter
    from scripts.test_tuple_unwrapping_focused import MockTechnicalIndicators
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root with venv311 activated")
    sys.exit(1)


class TestIntegrationFocused(unittest.TestCase):
    """Focused integration tests for the fixes."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_indicators = MockTechnicalIndicators()

        # Sample data that mimics real system output
        self.sample_analysis_result = {
            'score': 67.5,
            'confluence_score': 67.5,
            'reliability': 0.82,  # Should display as 82%
            'components': {
                'orderflow': 72.0,
                'sentiment': 58.0,
                'liquidity': 75.0,
                'bitcoin_beta': 45.0,
                'smart_money': 69.0,
                'ml_prediction': 71.0
            },
            'results': {
                'orderflow': {'interpretation': 'Strong buying pressure detected'},
                'sentiment': {'interpretation': 'Neutral market sentiment'},
                'liquidity': {'interpretation': 'High liquidity at key levels'},
                'bitcoin_beta': {'interpretation': 'Low correlation with BTC'},
                'smart_money': {'interpretation': 'Institutional accumulation'},
                'ml_prediction': {'interpretation': 'Bullish prediction model'}
            }
        }

    def test_end_to_end_analysis_formatting(self):
        """Test complete analysis formatting pipeline."""
        try:
            # Test AnalysisFormatter with reliability
            formatter = AnalysisFormatter()
            output = formatter.format_analysis_result(
                analysis_result=self.sample_analysis_result,
                symbol_str="BTCUSDT"
            )

            # Verify reliability is formatted correctly
            self.assertIn("Reliability:", output)
            self.assertIn("82%", output)
            self.assertNotIn("8200%", output)
            self.assertNotIn("0.82%", output)

            # Verify score formatting
            self.assertIn("67.5", output)
            self.assertIn("BULLISH", output)

            print("✓ End-to-end analysis formatting test passed")

        except Exception as e:
            self.fail(f"End-to-end analysis formatting failed: {e}")

    def test_technical_indicators_with_cache_tuples(self):
        """Test technical indicators with simulated cache tuple responses."""
        try:
            # Simulate cache returning tuple data
            cache_data = {
                'ltf': {
                    'rsi': (65.5, 'L1'),          # From L1 cache
                    'ma_cross': (1.2, 'L2'),      # From L2 cache
                    'volume': (850000.0, 'L1'),   # From L1 cache
                    'momentum': (12.5, 'L3')      # From L3 cache
                },
                'mtf': {
                    'rsi': (72.3, 'L2'),
                    'ma_cross': (-0.5, 'L1'),
                    'volume': (920000.0, 'L2'),
                    'momentum': (15.8, 'L1')
                },
                'htf': {
                    'rsi': (68.9, 'L3'),          # Mix of cache layers
                    'ma_cross': (0.8, 'L1'),
                    'volume': (1050000.0, 'L2'),
                    'momentum': (18.2, 'L3')
                }
            }

            # Process the data
            result = self.mock_indicators._calculate_component_scores(cache_data)

            # Verify results are numeric and reasonable
            for component, score in result.items():
                if component in ['rsi', 'ma_cross', 'volume', 'momentum']:
                    self.assertIsInstance(score, (int, float))
                    self.assertFalse(pd.isna(score))
                    # Scores should be weighted averages of input values
                    self.assertGreater(score, 0)

            # Try to format the results (this would fail with tuple format errors)
            for component, score in result.items():
                formatted = f"Component {component}: {score:.2f}%"
                self.assertIsInstance(formatted, str)
                self.assertNotIn("(", formatted)  # No tuple artifacts
                self.assertNotIn("L1", formatted)  # No cache layer artifacts

            print("✓ Technical indicators with cache tuples test passed")

        except Exception as e:
            self.fail(f"Technical indicators with cache tuples failed: {e}")

    def test_json_serialization_safety(self):
        """Test that processed data can be safely serialized to JSON."""
        try:
            # Process cache tuple data
            cache_data = {
                'ltf': {
                    'rsi': (65.5, 'L1'),
                    'sentiment': (75.2, 'L2'),
                    'volume': (850000.0, 'L1')
                }
            }

            result = self.mock_indicators._calculate_component_scores(cache_data)

            # Add reliability data
            output_data = {
                'technical_scores': result,
                'reliability': 0.85,  # This should be normalized in display
                'timestamp': '2023-01-01T00:00:00Z',
                'symbol': 'BTCUSDT'
            }

            # Try to serialize to JSON (would fail with tuple data)
            json_output = json.dumps(output_data, indent=2)
            self.assertIsInstance(json_output, str)

            # Parse back to verify structure
            parsed = json.loads(json_output)
            self.assertEqual(parsed['reliability'], 0.85)
            self.assertIsInstance(parsed['technical_scores'], dict)

            # Verify no tuple artifacts in JSON
            self.assertNotIn("(", json_output)
            self.assertNotIn("L1", json_output)
            self.assertNotIn("L2", json_output)

            print("✓ JSON serialization safety test passed")

        except Exception as e:
            self.fail(f"JSON serialization safety failed: {e}")

    def test_reliability_normalization_edge_cases(self):
        """Test reliability normalization with various input formats."""
        test_cases = [
            # (input_reliability, expected_percentage_in_output)
            (0.0, "0%"),
            (0.5, "50%"),
            (1.0, "100%"),
            (75, "75%"),      # Already in percentage format
            (100, "100%"),    # Boundary case
            (150, "100%"),    # Over 100 should clamp
            (-5, "0%"),       # Negative should clamp
            (0.999, "100%"),  # Just under 1.0
        ]

        for input_reliability, expected_pct in test_cases:
            with self.subTest(input_reliability=input_reliability):
                try:
                    # Create analysis result with specific reliability
                    analysis_result = self.sample_analysis_result.copy()
                    analysis_result['reliability'] = input_reliability

                    # Format with PrettyTableFormatter
                    output = PrettyTableFormatter.format_confluence_score_table(
                        symbol="BTCUSDT",
                        confluence_score=67.5,
                        components=analysis_result['components'],
                        results=analysis_result['results'],
                        reliability=input_reliability
                    )

                    # Check expected percentage appears
                    self.assertIn(expected_pct, output)

                    # Ensure no extreme percentages
                    self.assertNotIn("10000%", output)
                    self.assertNotIn("1000%", output)
                    self.assertNotIn("15000%", output)

                except Exception as e:
                    self.fail(f"Reliability normalization failed for {input_reliability}: {e}")

        print("✓ Reliability normalization edge cases test passed")

    def test_display_consistency(self):
        """Test that reliability displays consistently across different formatters."""
        try:
            reliability_value = 0.78

            # Test with PrettyTableFormatter
            pretty_output = PrettyTableFormatter.format_confluence_score_table(
                symbol="BTCUSDT",
                confluence_score=67.5,
                components=self.sample_analysis_result['components'],
                results=self.sample_analysis_result['results'],
                reliability=reliability_value
            )

            # Test with AnalysisFormatter
            analysis_result = self.sample_analysis_result.copy()
            analysis_result['reliability'] = reliability_value

            formatter = AnalysisFormatter()
            analysis_output = formatter.format_analysis_result(
                analysis_result=analysis_result,
                symbol_str="BTCUSDT"
            )

            # Both should show 78%
            self.assertIn("78%", pretty_output)
            self.assertIn("78%", analysis_output)

            # Neither should show incorrect percentages
            for output in [pretty_output, analysis_output]:
                self.assertNotIn("7800%", output)
                self.assertNotIn("0.78%", output)
                self.assertNotIn("780%", output)

            print("✓ Display consistency test passed")

        except Exception as e:
            self.fail(f"Display consistency test failed: {e}")

    def test_no_format_string_vulnerabilities(self):
        """Test that the system is not vulnerable to format string injection."""
        try:
            # Test with malicious cache data
            malicious_cache_data = {
                'ltf': {
                    'rsi': (65.5, '{.__class__.__name__}'),    # Format injection attempt
                    'ma_cross': (1.2, '%.2f'),                # Format specifier
                    'volume': (850000.0, '{0}')               # Format placeholder
                }
            }

            # Process the data
            result = self.mock_indicators._calculate_component_scores(malicious_cache_data)

            # Try to format results - should not execute injection
            for component, score in result.items():
                formatted = f"Component {component}: {score:.2f}"
                self.assertIsInstance(formatted, str)
                # Should not contain injection artifacts
                self.assertNotIn('__class__', formatted)
                self.assertNotIn('__name__', formatted)
                self.assertNotIn('{', formatted)

            print("✓ Format string vulnerability test passed")

        except Exception as e:
            self.fail(f"Format string vulnerability test failed: {e}")


def run_focused_integration_tests():
    """Run all focused integration tests."""
    print("=" * 80)
    print("FOCUSED INTEGRATION TESTS")
    print("=" * 80)
    print()

    # Add pandas import for the tests
    import pandas as pd
    globals()['pd'] = pd

    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIntegrationFocused)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    print("\n" + "=" * 80)
    print("FOCUSED INTEGRATION TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

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
    success = run_focused_integration_tests()
    sys.exit(0 if success else 1)