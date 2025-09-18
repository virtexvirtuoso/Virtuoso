#!/usr/bin/env python3
"""
Comprehensive test suite for tuple unwrapping fixes in technical indicators.
Tests the cache tuple handling that prevents format string errors.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Union
import traceback

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.indicators.technical_indicators import TechnicalIndicators
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root with venv311 activated")
    sys.exit(1)


class TestTupleUnwrapping(unittest.TestCase):
    """Test suite for tuple unwrapping in cache responses."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock config for TechnicalIndicators
        mock_config = {
            'indicators': {
                'rsi_period': 14,
                'ma_short': 10,
                'ma_long': 20
            },
            'timeframes': {
                'base': {
                    'interval': 1,
                    'weight': 0.4,
                    'validation': {
                        'min_candles': 100,
                        'max_gap': 60
                    }
                },
                'ltf': {
                    'interval': 5,
                    'weight': 0.3,
                    'validation': {
                        'min_candles': 50,
                        'max_gap': 300
                    }
                },
                'mtf': {
                    'interval': 15,
                    'weight': 0.2,
                    'validation': {
                        'min_candles': 50,
                        'max_gap': 900
                    }
                },
                'htf': {
                    'interval': 60,
                    'weight': 0.1,
                    'validation': {
                        'min_candles': 50,
                        'max_gap': 3600
                    }
                }
            }
        }

        # Create TechnicalIndicators instance
        self.tech_indicators = TechnicalIndicators(config=mock_config)

        # Sample OHLCV data for testing
        self.sample_ohlcv = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=100, freq='1H'),
            'open': np.random.random(100) * 1000 + 40000,
            'high': np.random.random(100) * 1000 + 40500,
            'low': np.random.random(100) * 1000 + 39500,
            'close': np.random.random(100) * 1000 + 40000,
            'volume': np.random.random(100) * 1000000
        })

        # Ensure high >= max(open, close) and low <= min(open, close)
        self.sample_ohlcv['high'] = np.maximum(self.sample_ohlcv['high'],
                                               np.maximum(self.sample_ohlcv['open'], self.sample_ohlcv['close']))
        self.sample_ohlcv['low'] = np.minimum(self.sample_ohlcv['low'],
                                              np.minimum(self.sample_ohlcv['open'], self.sample_ohlcv['close']))

    def test_tuple_unwrapping_basic(self):
        """Test basic tuple unwrapping functionality."""
        # Test data with various tuple formats that cache might return
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
            result = self.tech_indicators._calculate_component_scores(test_data)

            # Check that all components have numeric scores
            for component, score in result.items():
                self.assertIsInstance(score, (int, float),
                                    f"Component {component} score should be numeric, got {type(score)}")
                self.assertFalse(np.isnan(score),
                               f"Component {component} score should not be NaN")

            # Verify specific calculations (weighted averages)
            # RSI: (65.5*0.4 + 72.3*0.4 + 68.9*0.2) = 26.2 + 28.92 + 13.78 = 68.9
            expected_rsi = (65.5 * 0.4 + 72.3 * 0.4 + 68.9 * 0.2)
            self.assertAlmostEqual(result['rsi'], expected_rsi, places=2)

        except Exception as e:
            self.fail(f"Basic tuple unwrapping failed: {e}\n{traceback.format_exc()}")

    def test_tuple_unwrapping_mixed_types(self):
        """Test tuple unwrapping with mixed data types."""
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
            result = self.tech_indicators._calculate_component_scores(test_data)

            # Check that numeric components work
            self.assertIsInstance(result['rsi'], (int, float))
            self.assertIsInstance(result['ma_cross'], (int, float))

            # Volume with string should be handled gracefully or excluded
            if 'volume' in result:
                self.assertIsInstance(result['volume'], (int, float))

        except Exception as e:
            self.fail(f"Mixed types tuple unwrapping failed: {e}\n{traceback.format_exc()}")

    def test_tuple_unwrapping_edge_cases(self):
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
            result = self.tech_indicators._calculate_component_scores(test_data)

            # Should handle edge cases gracefully
            for component, score in result.items():
                if not np.isnan(score):  # Allow NaN for invalid cases
                    self.assertIsInstance(score, (int, float))
                    self.assertFalse(np.isinf(score), f"Component {component} should not be infinite")

        except Exception as e:
            self.fail(f"Edge cases tuple unwrapping failed: {e}\n{traceback.format_exc()}")

    def test_no_format_string_errors(self):
        """Test that tuple unwrapping prevents format string errors."""
        # Simulate cache returning tuples that would cause format errors
        test_data = {
            'ltf': {
                'rsi': (65.5, 'L1'),
                'ma_cross': (1.2, 'L2'),
                'volume': (850000.0, 'L1')
            }
        }

        try:
            result = self.tech_indicators._calculate_component_scores(test_data)

            # Try to format the results as strings (this would fail with raw tuples)
            for component, score in result.items():
                formatted = f"{component}: {score:.2f}"  # This should not raise an error
                self.assertIsInstance(formatted, str)
                self.assertNotIn("tuple", formatted.lower())

        except Exception as e:
            if "unsupported format string passed to tuple.__format__" in str(e):
                self.fail("Format string error not prevented by tuple unwrapping")
            else:
                self.fail(f"Unexpected error in format test: {e}")

    def test_tuple_logging_safety(self):
        """Test that tuple unwrapping makes logging safe."""
        test_data = {
            'ltf': {
                'rsi': (65.5, 'L1'),
                'ma_cross': (1.2, 'L2')
            }
        }

        # Capture log output
        with patch.object(self.tech_indicators.logger, 'debug') as mock_debug:
            try:
                result = self.tech_indicators._calculate_component_scores(test_data)

                # Check that debug logging was called and didn't fail
                mock_debug.assert_called()

                # Verify logged values are numeric strings, not tuple representations
                for call in mock_debug.call_args_list:
                    if len(call[0]) > 0:
                        log_message = call[0][0]
                        if ': ' in log_message and any(comp in log_message for comp in ['rsi', 'ma_cross']):
                            # Extract the numeric part after the colon
                            parts = log_message.split(': ')
                            if len(parts) > 1:
                                numeric_part = parts[1].strip()
                                # Should be a clean number, not a tuple representation
                                self.assertNotIn('(', numeric_part)
                                self.assertNotIn(')', numeric_part)
                                self.assertNotIn("'", numeric_part)

            except Exception as e:
                self.fail(f"Logging safety test failed: {e}")

    def test_cache_layer_preservation(self):
        """Test that cache layer information is logged but not used in calculations."""
        test_data = {
            'ltf': {
                'rsi': (65.5, 'L1'),    # Layer 1 cache
                'ma_cross': (1.2, 'L2')  # Layer 2 cache
            },
            'mtf': {
                'rsi': (72.3, 'L3'),    # Layer 3 cache
                'ma_cross': (-0.5, 'L1') # Layer 1 cache
            }
        }

        with patch.object(self.tech_indicators.logger, 'debug') as mock_debug:
            try:
                result = self.tech_indicators._calculate_component_scores(test_data)

                # Verify calculations use only the numeric values
                expected_rsi = (65.5 * 0.4 + 72.3 * 0.4)  # Only ltf and mtf weights
                self.assertAlmostEqual(result['rsi'], expected_rsi, places=2)

                # Note: Cache layer info should be logged but not affect calculations
                # The actual layer information is discarded after unwrapping

            except Exception as e:
                self.fail(f"Cache layer preservation test failed: {e}")

    def test_performance_impact(self):
        """Test that tuple unwrapping doesn't significantly impact performance."""
        import time

        # Large dataset to test performance
        large_test_data = {}
        for tf in ['ltf', 'mtf', 'htf']:
            large_test_data[tf] = {}
            for i in range(100):  # Many components
                large_test_data[tf][f'component_{i}'] = (float(i * 1.5), f'L{i % 3 + 1}')

        start_time = time.time()
        try:
            result = self.tech_indicators._calculate_component_scores(large_test_data)
            end_time = time.time()

            processing_time = end_time - start_time
            # Should complete within reasonable time (< 1 second for 300 components)
            self.assertLess(processing_time, 1.0,
                          f"Performance test failed: took {processing_time:.3f}s")

            # Verify all components were processed
            self.assertEqual(len(result), 100)

        except Exception as e:
            self.fail(f"Performance test failed: {e}")

    def test_concurrent_access_safety(self):
        """Test that tuple unwrapping is thread-safe."""
        import threading
        import concurrent.futures

        test_data = {
            'ltf': {
                'rsi': (65.5, 'L1'),
                'ma_cross': (1.2, 'L2'),
                'volume': (850000.0, 'L1')
            },
            'mtf': {
                'rsi': (72.3, 'L1'),
                'ma_cross': (-0.5, 'L3'),
                'volume': (920000.0, 'L2')
            }
        }

        def process_scores(data):
            """Helper function to process scores in a thread."""
            return self.tech_indicators._calculate_component_scores(data)

        try:
            # Run multiple threads concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(process_scores, test_data) for _ in range(10)]

                results = []
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    results.append(result)

                # All results should be identical
                for result in results[1:]:
                    for component in results[0]:
                        self.assertAlmostEqual(results[0][component], result[component], places=2)

        except Exception as e:
            self.fail(f"Concurrent access test failed: {e}")


def run_tuple_unwrapping_tests():
    """Run all tuple unwrapping tests."""
    print("=" * 80)
    print("COMPREHENSIVE TUPLE UNWRAPPING TESTS")
    print("=" * 80)
    print()

    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTupleUnwrapping)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    print("\n" + "=" * 80)
    print("TUPLE UNWRAPPING TEST SUMMARY")
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
    success = run_tuple_unwrapping_tests()
    sys.exit(0 if success else 1)