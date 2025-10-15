#!/usr/bin/env python3
"""
Comprehensive Regression Test for Price Structure Interpretation Fixes
Tests all related components to ensure no breaking changes
"""

import logging
import sys
import traceback
from typing import Dict, Any, List
from src.core.formatting.formatter import AnalysisFormatter

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class ComprehensiveRegressionTest:
    """Test suite for regression testing of price structure fixes"""

    def __init__(self):
        self.formatter = AnalysisFormatter()
        self.test_results = []

    def test_basic_formatting(self) -> bool:
        """Test basic analysis result formatting still works"""
        logger.info("Testing basic formatting functionality...")

        test_data = {
            'score': 75.6,
            'confluence_score': 75.6,
            'reliability': 1.0,
            'components': {
                'technical': 78.2,
                'volume': 72.8,
                'orderbook': 76.4
            }
        }

        try:
            result = self.formatter.format_analysis_result(test_data, "BTCUSDT")

            # Check basic structure
            if "BTCUSDT CONFLUENCE ANALYSIS" in result:
                logger.info("✅ Basic formatting test passed")
                return True
            else:
                logger.error("❌ Basic formatting test failed")
                return False

        except Exception as e:
            logger.error(f"❌ Basic formatting test error: {e}")
            return False

    def test_component_breakdown(self) -> bool:
        """Test component breakdown formatting"""
        logger.info("Testing component breakdown functionality...")

        components = {
            'technical': 81.5,
            'volume': 76.3,
            'orderbook': 78.9,
            'sentiment': 73.2,
            'price_structure': 74.1,
            'orderflow': 79.8
        }

        try:
            result = self.formatter.format_component_breakdown(components, {})

            # Check that all components are present
            expected_components = ['Technical', 'Volume', 'Orderbook', 'Sentiment', 'Price Structure', 'Orderflow']
            missing_components = []

            for component in expected_components:
                if component not in result:
                    missing_components.append(component)

            if not missing_components:
                logger.info("✅ Component breakdown test passed")
                return True
            else:
                logger.error(f"❌ Component breakdown test failed - missing: {missing_components}")
                return False

        except Exception as e:
            logger.error(f"❌ Component breakdown test error: {e}")
            return False

    def test_mixed_interpretation_formats(self) -> bool:
        """Test handling of mixed interpretation formats"""
        logger.info("Testing mixed interpretation formats...")

        test_data = {
            'score': 68.4,
            'confluence_score': 68.4,
            'reliability': 1.0,
            'components': {
                'technical': 72.1,
                'volume': 65.8,
                'sentiment': 67.3,
                'price_structure': 69.2
            },
            'results': {
                'technical': {
                    'interpretation': 'Technical indicators show bullish momentum building'
                },
                'volume': {
                    'interpretation': {
                        'summary': 'Volume patterns confirm price action'
                    }
                },
                'sentiment': {
                    'signals': {
                        'market_mood': 'optimistic',
                        'fear_greed': 62
                    }
                },
                'price_structure': {
                    'signals': {
                        'support_level': {
                            'signal': 'strong_support',
                            'bias': 'bullish',
                            'strength': 'high'
                        }
                    }
                }
            }
        }

        try:
            result = self.formatter.format_analysis_result(test_data, "ETHUSDT")

            # Check that all interpretation formats are handled
            checks = [
                'Technical indicators show bullish momentum building' in result,
                'Volume patterns confirm price action' in result,
                'Strong Support: strong support' in result or 'Support Level: strong support' in result
            ]

            if all(checks):
                logger.info("✅ Mixed interpretation formats test passed")
                return True
            else:
                logger.error("❌ Mixed interpretation formats test failed")
                return False

        except Exception as e:
            logger.error(f"❌ Mixed interpretation formats test error: {e}")
            return False

    def test_error_handling(self) -> bool:
        """Test error handling with malformed data"""
        logger.info("Testing error handling...")

        test_cases = [
            {'score': None, 'confluence_score': None},  # None values
            {'results': {'price_structure': None}},  # None component
            {'results': {'price_structure': {'signals': None}}},  # None signals
            {'results': {'price_structure': {'signals': {'test': 'invalid'}}}},  # Invalid signal structure
            {}  # Empty data
        ]

        failed_tests = 0

        for i, test_case in enumerate(test_cases):
            try:
                result = self.formatter.format_analysis_result(test_case, f"TEST{i}")

                # Should not crash and should return some output
                if result and len(result.strip()) > 0:
                    logger.info(f"✅ Error handling test {i+1} passed")
                else:
                    logger.warning(f"⚠️ Error handling test {i+1} returned empty result")
                    failed_tests += 1

            except Exception as e:
                logger.error(f"❌ Error handling test {i+1} failed: {e}")
                failed_tests += 1

        if failed_tests == 0:
            logger.info("✅ All error handling tests passed")
            return True
        else:
            logger.error(f"❌ {failed_tests}/{len(test_cases)} error handling tests failed")
            return False

    def test_edge_cases(self) -> bool:
        """Test edge cases with various data structures"""
        logger.info("Testing edge cases...")

        test_cases = [
            {
                'score': 0.0,
                'confluence_score': 0.0,
                'results': {
                    'price_structure': {
                        'signals': {
                            'empty_signal': {}
                        }
                    }
                }
            },
            {
                'score': 100.0,
                'confluence_score': 100.0,
                'results': {
                    'price_structure': {
                        'signals': {
                            'nested_signal': {
                                'signal': 'test',
                                'nested_data': {
                                    'deep': {
                                        'value': 'should_be_ignored'
                                    }
                                }
                            }
                        }
                    }
                }
            }
        ]

        passed_tests = 0

        for i, test_case in enumerate(test_cases):
            try:
                result = self.formatter.format_analysis_result(test_case, f"EDGE{i}")

                # Check that result is valid and contains expected structure
                if "CONFLUENCE ANALYSIS" in result and len(result.strip()) > 100:
                    logger.info(f"✅ Edge case test {i+1} passed")
                    passed_tests += 1
                else:
                    logger.warning(f"⚠️ Edge case test {i+1} produced minimal output")

            except Exception as e:
                logger.error(f"❌ Edge case test {i+1} failed: {e}")

        if passed_tests == len(test_cases):
            logger.info("✅ All edge case tests passed")
            return True
        else:
            logger.error(f"❌ {len(test_cases)-passed_tests}/{len(test_cases)} edge case tests failed")
            return False

    def test_performance_impact(self) -> bool:
        """Test that changes don't significantly impact performance"""
        logger.info("Testing performance impact...")

        import time

        # Create a large test dataset
        large_test_data = {
            'score': 67.3,
            'confluence_score': 67.3,
            'reliability': 1.0,
            'components': {f'component_{i}': float(50 + i % 40) for i in range(20)},
            'results': {
                f'component_{i}': {
                    'signals': {
                        f'signal_{j}': {
                            'signal': f'test_signal_{j}',
                            'bias': 'neutral',
                            'strength': 'moderate'
                        } for j in range(10)
                    }
                } for i in range(10)
            }
        }

        try:
            # Run multiple iterations and measure time
            iterations = 50
            start_time = time.time()

            for i in range(iterations):
                result = self.formatter.format_analysis_result(large_test_data, f"PERF{i}")

            end_time = time.time()
            avg_time = (end_time - start_time) / iterations

            # Performance threshold: should complete in reasonable time
            if avg_time < 0.1:  # 100ms per formatting operation
                logger.info(f"✅ Performance test passed - avg time: {avg_time:.4f}s")
                return True
            else:
                logger.warning(f"⚠️ Performance test concerning - avg time: {avg_time:.4f}s")
                return False

        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all regression tests"""
        logger.info("Starting comprehensive regression testing...")

        tests = [
            ("Basic Formatting", self.test_basic_formatting),
            ("Component Breakdown", self.test_component_breakdown),
            ("Mixed Interpretation Formats", self.test_mixed_interpretation_formats),
            ("Error Handling", self.test_error_handling),
            ("Edge Cases", self.test_edge_cases),
            ("Performance Impact", self.test_performance_impact)
        ]

        results = {}
        passed_count = 0

        for test_name, test_func in tests:
            logger.info(f"\n{'='*60}")
            logger.info(f"RUNNING: {test_name}")
            logger.info(f"{'='*60}")

            try:
                result = test_func()
                results[test_name] = result
                if result:
                    passed_count += 1
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    logger.error(f"❌ {test_name}: FAILED")
            except Exception as e:
                logger.error(f"❌ {test_name}: ERROR - {e}")
                logger.error(traceback.format_exc())
                results[test_name] = False

        # Generate summary
        total_tests = len(tests)
        success_rate = (passed_count / total_tests) * 100

        logger.info(f"\n{'='*80}")
        logger.info("COMPREHENSIVE REGRESSION TEST SUMMARY")
        logger.info(f"{'='*80}")
        logger.info(f"Total tests: {total_tests}")
        logger.info(f"Passed: {passed_count}")
        logger.info(f"Failed: {total_tests - passed_count}")
        logger.info(f"Success rate: {success_rate:.1f}%")

        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"  {test_name}: {status}")

        logger.info(f"\n{'='*80}")
        if success_rate >= 100:
            logger.info("🎉 ALL REGRESSION TESTS PASSED!")
            logger.info("Price structure interpretation fixes are stable and backward compatible!")
        elif success_rate >= 80:
            logger.info("⚠️  MOST REGRESSION TESTS PASSED")
            logger.info("Minor issues detected but core functionality is stable")
        else:
            logger.info("❌ REGRESSION TESTS FAILED")
            logger.info("Significant issues detected that need attention")
        logger.info(f"{'='*80}")

        return {
            'total_tests': total_tests,
            'passed': passed_count,
            'failed': total_tests - passed_count,
            'success_rate': success_rate,
            'results': results
        }

def main():
    """Main regression test function"""
    test_suite = ComprehensiveRegressionTest()
    return test_suite.run_all_tests()

if __name__ == "__main__":
    main()