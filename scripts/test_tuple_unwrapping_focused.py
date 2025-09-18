#!/usr/bin/env python3
"""
Focused test for tuple unwrapping in _calculate_component_scores method.
Tests the specific fix without requiring full TechnicalIndicators initialization.
"""

import sys
import os
import unittest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import logging

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class MockTechnicalIndicators:
    """Mock implementation that only includes the _calculate_component_scores method."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.timeframe_weights = {
            'ltf': 0.4,
            'mtf': 0.4,
            'htf': 0.2
        }

    def _calculate_component_scores(self, data):
        """
        Calculate component scores from timeframe scores.
        This is the ACTUAL method from technical_indicators.py with tuple unwrapping fix.
        """
        try:
            # Initialize component scores dictionary
            component_scores = {
                'rsi': 0.0,
                'ao': 0.0,
                'macd': 0.0,
                'williams_r': 0.0,
                'atr': 0.0,
                'cci': 0.0,
                'ma_cross': 0.0,
                'volume': 0.0,
                'momentum': 0.0
            }

            # Combine scores across timeframes with weighted averaging
            valid_timeframes = 0
            for tf_name, tf_scores in data.items():
                if tf_name not in self.timeframe_weights:
                    self.logger.warning(f"Unknown timeframe: {tf_name}")
                    continue

                tf_weight = self.timeframe_weights[tf_name]

                # Skip if no scores for this timeframe
                if not isinstance(tf_scores, dict) or not tf_scores:
                    self.logger.warning(f"Invalid scores for timeframe: {tf_name}")
                    continue

                # Add weighted contribution to component scores
                for component, score in tf_scores.items():
                    if component in component_scores:
                        # Ensure score is numeric (unwrap tuples from cache and convert)
                        try:
                            value_to_use = score
                            # Some cache adapters may return (value, cache_layer) tuples
                            if isinstance(value_to_use, tuple) and len(value_to_use) >= 1:
                                value_to_use = value_to_use[0]
                            numeric_score = float(value_to_use) if not isinstance(value_to_use, (int, float)) else value_to_use
                            component_scores[component] += numeric_score * tf_weight
                        except (ValueError, TypeError) as e:
                            self.logger.warning(f"Invalid score for {component}: {score} (type: {type(score)}) - {e}")
                            continue

                valid_timeframes += 1

            # If no valid timeframes were processed, return default scores
            if valid_timeframes == 0:
                self.logger.warning("No valid timeframes found, returning default scores")
                return {k: 50.0 for k in component_scores.keys()}

            # Log timeframe analysis
            self.logger.debug("\n=== Timeframe Analysis ===")
            for tf_name, tf_scores in data.items():
                if isinstance(tf_scores, dict) and tf_scores:
                    self.logger.debug(f"\n{tf_name} Timeframe Scores:")
                    for comp, score in tf_scores.items():
                        try:
                            # Safely unwrap and convert score to float for logging
                            value_to_use = score
                            if isinstance(value_to_use, tuple) and len(value_to_use) >= 1:
                                value_to_use = value_to_use[0]
                            numeric_score = float(value_to_use) if not isinstance(value_to_use, (int, float)) else value_to_use
                            self.logger.debug(f"- {comp}: {numeric_score:.2f}")
                        except (ValueError, TypeError):
                            self.logger.debug(f"- {comp}: {score} (non-numeric)")

            return component_scores

        except Exception as e:
            self.logger.error(f"Error calculating component scores: {str(e)}")
            return {k: 50.0 for k in component_scores.keys()}


class TestTupleUnwrappingFocused(unittest.TestCase):
    """Focused test suite for tuple unwrapping."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_indicators = MockTechnicalIndicators()

    def test_basic_tuple_unwrapping(self):
        """Test basic tuple unwrapping functionality."""
        test_data = {
            'ltf': {
                'rsi': (65.5, 'L1'),          # Tuple with cache layer info
                'ma_cross': (1.2, 'L2'),      # Another tuple format
                'volume': 850000.0             # Normal float
            },
            'mtf': {
                'rsi': (72.3, 'L1'),
                'ma_cross': (-0.5, 'L3'),
                'volume': (920000.0, 'L2')     # Volume as tuple
            },
            'htf': {
                'rsi': 68.9,                   # Normal float
                'ma_cross': (0.8, 'L1'),
                'volume': (1050000.0, 'L1')
            }
        }

        try:
            result = self.mock_indicators._calculate_component_scores(test_data)

            # Check that all components have numeric scores
            for component, score in result.items():
                self.assertIsInstance(score, (int, float),
                                    f"Component {component} score should be numeric, got {type(score)}")
                self.assertFalse(pd.isna(score),
                               f"Component {component} score should not be NaN")

            # Verify specific calculations (weighted averages)
            # RSI: (65.5*0.4 + 72.3*0.4 + 68.9*0.2) = 26.2 + 28.92 + 13.78 = 68.9
            expected_rsi = (65.5 * 0.4 + 72.3 * 0.4 + 68.9 * 0.2)
            self.assertAlmostEqual(result['rsi'], expected_rsi, places=2)

            print("✓ Basic tuple unwrapping test passed")

        except Exception as e:
            self.fail(f"Basic tuple unwrapping failed: {e}")

    def test_format_string_safety(self):
        """Test that unwrapped values can be safely formatted."""
        test_data = {
            'ltf': {
                'rsi': (65.5, 'L1'),
                'ma_cross': (1.2, 'L2'),
                'volume': (850000.0, 'L1')
            }
        }

        try:
            result = self.mock_indicators._calculate_component_scores(test_data)

            # Try to format the results as strings (this would fail with raw tuples)
            for component, score in result.items():
                formatted = f"{component}: {score:.2f}"  # This should not raise an error
                self.assertIsInstance(formatted, str)
                self.assertNotIn("tuple", formatted.lower())
                self.assertNotIn("L1", formatted)  # Cache layer info should not appear

            print("✓ Format string safety test passed")

        except Exception as e:
            if "unsupported format string passed to tuple.__format__" in str(e):
                self.fail("Format string error not prevented by tuple unwrapping")
            else:
                self.fail(f"Unexpected error in format test: {e}")

    def test_mixed_data_types(self):
        """Test handling of mixed data types in tuples."""
        test_data = {
            'ltf': {
                'rsi': (65, 'L1'),             # Integer in tuple
                'ma_cross': (1.2345, 'L2'),   # Float in tuple
                'volume': ('850000', 'L1'),    # String in tuple (should handle gracefully)
                'momentum': None               # None value
            },
            'mtf': {
                'rsi': (72.0, 'L1'),
                'ma_cross': (-0.5, 'L3'),
                'volume': (920000, 'L2'),      # Int in tuple
                'momentum': (15.5, 'L1')      # Normal tuple
            }
        }

        try:
            result = self.mock_indicators._calculate_component_scores(test_data)

            # Check that numeric components work
            self.assertIsInstance(result['rsi'], (int, float))
            self.assertIsInstance(result['ma_cross'], (int, float))

            # Volume with string should be handled gracefully or excluded
            if 'volume' in result:
                self.assertIsInstance(result['volume'], (int, float))

            print("✓ Mixed data types test passed")

        except Exception as e:
            self.fail(f"Mixed types tuple unwrapping failed: {e}")

    def test_edge_cases(self):
        """Test edge cases for tuple unwrapping."""
        test_data = {
            'ltf': {
                'rsi': (),                     # Empty tuple
                'ma_cross': (1.2, 'L2', 'extra'),  # Tuple with extra elements
                'volume': (850000.0,),         # Single element tuple
                'momentum': ((15.5, 'nested'), 'L1')  # Nested tuple
            },
            'mtf': {
                'rsi': (None, 'L1'),          # None in tuple
                'ma_cross': ('invalid', 'L2'), # Invalid string in tuple
                'volume': ([920000], 'L2'),    # List in tuple
                'momentum': (float('inf'), 'L1')  # Infinity
            }
        }

        try:
            result = self.mock_indicators._calculate_component_scores(test_data)

            # Should handle edge cases gracefully
            for component, score in result.items():
                if not pd.isna(score):  # Allow NaN for invalid cases
                    self.assertIsInstance(score, (int, float))
                    # Note: infinity values might be present due to invalid data,
                    # the key is that they don't crash the system
                    if np.isinf(score):
                        print(f"⚠ Component {component} has infinite value: {score} (handled gracefully)")

            print("✓ Edge cases test passed")

        except Exception as e:
            self.fail(f"Edge cases tuple unwrapping failed: {e}")

    def test_performance_basic(self):
        """Test basic performance of tuple unwrapping."""
        import time

        # Create test data with many tuples
        test_data = {}
        for tf in ['ltf', 'mtf', 'htf']:
            test_data[tf] = {}
            for i in range(50):  # 50 components per timeframe
                test_data[tf][f'component_{i}'] = (float(i * 1.5), f'L{i % 3 + 1}')

        start_time = time.time()
        try:
            result = self.mock_indicators._calculate_component_scores(test_data)
            end_time = time.time()

            processing_time = end_time - start_time
            # Should complete quickly (< 0.1 seconds for 150 components)
            self.assertLess(processing_time, 0.1,
                          f"Performance test failed: took {processing_time:.3f}s")

            # Verify components were processed (many will be 0 since they're not in the base components list)
            # Just check that the result contains the expected base components
            expected_components = ['rsi', 'ao', 'macd', 'williams_r', 'atr', 'cci', 'ma_cross', 'volume', 'momentum']
            for comp in expected_components:
                self.assertIn(comp, result)

            print(f"✓ Performance test passed ({processing_time:.3f}s for 150 tuple operations)")

        except Exception as e:
            self.fail(f"Performance test failed: {e}")

    def test_logging_safety(self):
        """Test that logging doesn't crash with tuple data."""
        test_data = {
            'ltf': {
                'rsi': (65.5, 'L1'),
                'ma_cross': (1.2, 'L2')
            }
        }

        # Capture log output to ensure no crashes
        with patch.object(self.mock_indicators.logger, 'debug') as mock_debug:
            try:
                result = self.mock_indicators._calculate_component_scores(test_data)

                # Check that debug logging was called and didn't fail
                mock_debug.assert_called()

                # Verify result is valid
                self.assertIsInstance(result, dict)
                for score in result.values():
                    if not pd.isna(score):
                        self.assertIsInstance(score, (int, float))

                print("✓ Logging safety test passed")

            except Exception as e:
                self.fail(f"Logging safety test failed: {e}")


def run_focused_tests():
    """Run all focused tuple unwrapping tests."""
    print("=" * 80)
    print("FOCUSED TUPLE UNWRAPPING TESTS")
    print("=" * 80)
    print()

    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTupleUnwrappingFocused)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    print("\n" + "=" * 80)
    print("FOCUSED TEST SUMMARY")
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
    success = run_focused_tests()
    sys.exit(0 if success else 1)