#!/usr/bin/env python3
"""
Comprehensive edge case test suite for tuple unwrapping and reliability formatting fixes.
Tests extreme conditions, error scenarios, and boundary cases.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
import threading
import time
import concurrent.futures
from typing import Dict, Any, List, Tuple, Union
import traceback

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.core.formatting.formatter import PrettyTableFormatter, AnalysisFormatter
    from src.indicators.technical_indicators import TechnicalIndicators
    from src.core.exchanges.manager import ExchangeManager
    from src.core.market.market_data_manager import MarketDataManager
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root with venv311 activated")
    sys.exit(1)


class TestEdgeCases(unittest.TestCase):
    """Test suite for edge cases and extreme conditions."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_exchange_manager = Mock(spec=ExchangeManager)
        self.mock_market_data_manager = Mock(spec=MarketDataManager)

        self.tech_indicators = TechnicalIndicators(
            exchange_manager=self.mock_exchange_manager,
            market_data_manager=self.mock_market_data_manager
        )

    def test_extreme_reliability_values(self):
        """Test extreme reliability values that could cause overflow."""
        extreme_values = [
            -float('inf'),  # Negative infinity
            float('inf'),   # Positive infinity
            float('nan'),   # NaN
            1e308,          # Very large number
            -1e308,         # Very large negative number
            1e-308,         # Very small positive number
            -1e-308,        # Very small negative number
            999999999,      # Large integer
            -999999999,     # Large negative integer
        ]

        components = {'test': 50.0}
        results = {'test': {'interpretation': 'test'}}

        for reliability in extreme_values:
            with self.subTest(reliability=reliability):
                try:
                    output = PrettyTableFormatter.format_confluence_score_table(
                        symbol="TEST",
                        confluence_score=50.0,
                        components=components,
                        results=results,
                        reliability=reliability
                    )

                    # Should not contain extreme percentages
                    self.assertNotIn("inf%", output.lower())
                    self.assertNotIn("nan%", output.lower())
                    self.assertNotIn("999999", output)

                    # Should contain some valid percentage
                    reliability_match = False
                    for line in output.split('\n'):
                        if 'Reliability:' in line and '%' in line:
                            reliability_match = True
                            # Extract percentage
                            parts = line.split('%')[0]
                            if parts:
                                pct_part = parts.split()[-1]
                                try:
                                    pct_value = float(pct_part)
                                    self.assertGreaterEqual(pct_value, 0)
                                    self.assertLessEqual(pct_value, 100)
                                except ValueError:
                                    pass  # Color codes might interfere

                    self.assertTrue(reliability_match, "No valid reliability percentage found")

                except Exception as e:
                    self.fail(f"Extreme reliability {reliability} caused error: {e}")

    def test_malformed_tuple_data(self):
        """Test handling of malformed tuple data from cache."""
        malformed_data = {
            'ltf': {
                'rsi': (65.5,),              # Single element tuple
                'ma_cross': (),              # Empty tuple
                'volume': (None, None, None), # Multiple None values
                'momentum': (1, 2, 3, 4, 5), # Too many elements
            },
            'mtf': {
                'rsi': ('not_a_number', 'L1'),     # String instead of number
                'ma_cross': ([1, 2, 3], 'L2'),     # List instead of number
                'volume': ({'key': 'value'}, 'L1'), # Dict instead of number
                'momentum': (complex(1, 2), 'L3'),  # Complex number
            },
            'htf': {
                'rsi': (float('inf'), 'L1'),       # Infinity
                'ma_cross': (float('nan'), 'L2'),  # NaN
                'volume': (None, 'L3'),             # None value
                'momentum': (type, 'L1'),           # Type object
            }
        }

        try:
            result = self.tech_indicators._calculate_component_scores(malformed_data)

            # Should handle malformed data gracefully
            for component, score in result.items():
                if not np.isnan(score):  # Allow NaN for invalid cases
                    self.assertIsInstance(score, (int, float))
                    self.assertFalse(np.isinf(score))
                    self.assertGreaterEqual(score, 0)  # Assuming scores should be non-negative

        except Exception as e:
            self.fail(f"Malformed tuple data caused error: {e}\n{traceback.format_exc()}")

    def test_concurrent_cache_access(self):
        """Test concurrent access to cache with tuple unwrapping."""
        def create_test_data(thread_id):
            """Create test data with thread-specific values."""
            return {
                'ltf': {
                    'rsi': (50.0 + thread_id, f'L{thread_id % 3 + 1}'),
                    'ma_cross': (1.0 * thread_id, f'L{thread_id % 3 + 1}'),
                },
                'mtf': {
                    'rsi': (60.0 + thread_id, f'L{thread_id % 3 + 1}'),
                    'ma_cross': (2.0 * thread_id, f'L{thread_id % 3 + 1}'),
                }
            }

        def process_data(thread_id):
            """Process data in a separate thread."""
            try:
                test_data = create_test_data(thread_id)
                result = self.tech_indicators._calculate_component_scores(test_data)
                return thread_id, result, None
            except Exception as e:
                return thread_id, None, str(e)

        # Run multiple threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_data, i) for i in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Check results
        errors = [error for _, _, error in results if error is not None]
        successful_results = [(tid, result) for tid, result, error in results if error is None]

        if errors:
            self.fail(f"Concurrent access errors: {errors}")

        # Verify that different threads got different results (based on thread_id)
        if len(successful_results) >= 2:
            result1 = successful_results[0][1]
            result2 = successful_results[1][1]

            # Results should be different if thread IDs were different
            tid1, tid2 = successful_results[0][0], successful_results[1][0]
            if tid1 != tid2:
                self.assertNotEqual(result1['rsi'], result2['rsi'])

    def test_memory_stress(self):
        """Test memory usage with large datasets."""
        # Create large dataset
        large_data = {}
        for tf in ['ltf', 'mtf', 'htf']:
            large_data[tf] = {}
            for i in range(1000):  # Many components
                large_data[tf][f'component_{i}'] = (float(i), f'L{i % 3 + 1}')

        try:
            # Monitor memory usage (basic check)
            import psutil
            process = psutil.Process()
            initial_memory = process.memory_info().rss

            result = self.tech_indicators._calculate_component_scores(large_data)

            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory

            # Should not use excessive memory (less than 100MB increase)
            self.assertLess(memory_increase, 100 * 1024 * 1024,
                          f"Memory usage increased by {memory_increase / 1024 / 1024:.2f}MB")

            # Verify all components were processed
            self.assertEqual(len(result), 1000)

        except ImportError:
            # psutil not available, skip memory check but still test functionality
            result = self.tech_indicators._calculate_component_scores(large_data)
            self.assertEqual(len(result), 1000)

        except Exception as e:
            self.fail(f"Memory stress test failed: {e}")

    def test_nested_tuple_structures(self):
        """Test deeply nested tuple structures."""
        nested_data = {
            'ltf': {
                'rsi': ((65.5, 'nested'), 'L1'),           # Nested tuple
                'ma_cross': (((1.2, 'deep'), 'nested'), 'L2'), # Deeply nested
                'volume': ((850000.0,), 'L1'),             # Nested single element
            }
        }

        try:
            result = self.tech_indicators._calculate_component_scores(nested_data)

            # Should handle nested structures gracefully
            # Either extract the innermost value or handle as error
            for component, score in result.items():
                if not np.isnan(score):
                    self.assertIsInstance(score, (int, float))

        except Exception as e:
            self.fail(f"Nested tuple test failed: {e}")

    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters in tuple data."""
        unicode_data = {
            'ltf': {
                'rsi': (65.5, 'L1🚀'),              # Unicode in cache layer
                'ma_cross': (1.2, 'L2_测试'),        # Unicode characters
                'volume': (850000.0, 'L1\x00'),     # Null character
                'momentum': (15.5, 'L3\n\t'),       # Newlines and tabs
            }
        }

        try:
            result = self.tech_indicators._calculate_component_scores(unicode_data)

            # Should extract numeric values regardless of unicode in layer info
            for component, score in result.items():
                self.assertIsInstance(score, (int, float))
                self.assertFalse(np.isnan(score))

        except Exception as e:
            self.fail(f"Unicode test failed: {e}")

    def test_reliability_formatting_with_unicode(self):
        """Test reliability formatting with unicode in component names."""
        components = {
            'orderflow_测试': 75.0,
            'sentiment🚀': 60.0,
            'liquidity\n': 80.0,
        }
        results = {
            'orderflow_测试': {'interpretation': 'Test unicode'},
            'sentiment🚀': {'interpretation': 'Test emoji'},
            'liquidity\n': {'interpretation': 'Test newline'},
        }

        try:
            output = PrettyTableFormatter.format_confluence_score_table(
                symbol="BTCUSDT",
                confluence_score=65.0,
                components=components,
                results=results,
                reliability=0.85
            )

            # Should handle unicode components without errors
            self.assertIn("85%", output)
            self.assertNotIn("8500%", output)

        except Exception as e:
            self.fail(f"Unicode reliability test failed: {e}")

    def test_format_string_injection(self):
        """Test that tuple data cannot inject format strings."""
        malicious_data = {
            'ltf': {
                'rsi': (65.5, '{0.__class__.__name__}'),    # Format string injection attempt
                'ma_cross': (1.2, '{.__format__}'),         # Another injection attempt
                'volume': (850000.0, '%.2f'),               # Format specifier
            }
        }

        try:
            result = self.tech_indicators._calculate_component_scores(malicious_data)

            # Should safely extract numeric values
            for component, score in result.items():
                self.assertIsInstance(score, (int, float))

            # Try to format results (this should not execute injected code)
            for component, score in result.items():
                formatted = f"{component}: {score:.2f}"
                self.assertIsInstance(formatted, str)
                # Should not contain injection artifacts
                self.assertNotIn('__class__', formatted)
                self.assertNotIn('__format__', formatted)

        except Exception as e:
            self.fail(f"Format injection test failed: {e}")

    def test_recursive_tuple_unwrapping(self):
        """Test recursive tuple unwrapping scenarios."""
        def create_recursive_tuple(depth, value):
            """Create a recursively nested tuple."""
            if depth <= 0:
                return value
            return (create_recursive_tuple(depth - 1, value), f'L{depth}')

        recursive_data = {
            'ltf': {
                'rsi': create_recursive_tuple(5, 65.5),     # 5 levels deep
                'ma_cross': create_recursive_tuple(3, 1.2), # 3 levels deep
                'volume': (850000.0, 'L1'),                 # Normal case
            }
        }

        try:
            result = self.tech_indicators._calculate_component_scores(recursive_data)

            # Should handle recursive tuples (either extract or handle as error)
            for component, score in result.items():
                if not np.isnan(score):
                    self.assertIsInstance(score, (int, float))

        except Exception as e:
            # Recursive tuples might cause stack overflow, which is acceptable
            if "maximum recursion depth" in str(e):
                pass  # Expected for deeply nested structures
            else:
                self.fail(f"Recursive tuple test failed: {e}")


def run_edge_case_tests():
    """Run all edge case tests."""
    print("=" * 80)
    print("COMPREHENSIVE EDGE CASE TESTS")
    print("=" * 80)
    print()

    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEdgeCases)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    print("\n" + "=" * 80)
    print("EDGE CASE TEST SUMMARY")
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
    success = run_edge_case_tests()
    sys.exit(0 if success else 1)