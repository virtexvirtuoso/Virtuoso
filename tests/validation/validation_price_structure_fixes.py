#!/usr/bin/env python3
"""
Comprehensive validation script for price structure interpretation fixes.
Tests dict-to-narrative conversion functionality end-to-end.
"""

import logging
import sys
import json
from typing import Dict, Any
from src.core.formatting.formatter import AnalysisFormatter

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class PriceStructureValidationTest:
    """Test suite for validating price structure interpretation fixes"""

    def __init__(self):
        self.formatter = AnalysisFormatter()
        self.test_results = []

    def create_test_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Create various test scenarios with different dict structures"""
        return {
            "scenario_1_full_dict": {
                'score': 65.4,
                'confluence_score': 65.4,
                'reliability': 1.0,
                'components': {
                    'technical': 71.2,
                    'volume': 58.9,
                    'orderbook': 67.3,
                    'orderflow': 72.1,
                    'sentiment': 64.5,
                    'price_structure': 59.8
                },
                'results': {
                    'price_structure': {
                        'signals': {
                            'support_resistance': {
                                'signal': 'bullish_breakout',
                                'bias': 'bullish',
                                'strength': 'strong',
                                'interpretation': 'Price broke above key resistance level'
                            },
                            'trend_structure': {
                                'signal': 'uptrend',
                                'bias': 'bullish',
                                'strength': 'moderate',
                                'interpretation': 'Higher highs and higher lows pattern confirmed'
                            }
                        }
                    }
                }
            },
            "scenario_2_minimal_dict": {
                'score': 48.2,
                'confluence_score': 48.2,
                'reliability': 1.0,
                'components': {
                    'price_structure': 45.1
                },
                'results': {
                    'price_structure': {
                        'signals': {
                            'key_level': {
                                'signal': 'neutral',
                                'bias': 'neutral'
                            }
                        }
                    }
                }
            },
            "scenario_3_mixed_signals": {
                'score': 52.7,
                'confluence_score': 52.7,
                'reliability': 1.0,
                'components': {
                    'price_structure': 52.7
                },
                'results': {
                    'price_structure': {
                        'signals': {
                            'fibonacci_levels': {
                                'signal': 'retracement',
                                'strength': 0.618,
                                'interpretation': 'Price respecting 61.8% Fibonacci level'
                            },
                            'pivot_points': {
                                'trend': 'sideways',
                                'state': 'consolidation'
                            },
                            'simple_value': 'bullish'
                        }
                    }
                }
            },
            "scenario_4_interpretation_fallback": {
                'score': 43.8,
                'confluence_score': 43.8,
                'reliability': 1.0,
                'components': {
                    'price_structure': 43.8
                },
                'results': {
                    'price_structure': {
                        'interpretation': {
                            'summary': 'Price structure shows mixed signals with consolidation pattern'
                        }
                    }
                }
            },
            "scenario_5_no_interpretation": {
                'score': 38.5,
                'confluence_score': 38.5,
                'reliability': 1.0,
                'components': {
                    'price_structure': 38.5
                },
                'results': {
                    'price_structure': {
                        'raw_data': {
                            'levels': [1.2345, 1.2387, 1.2412],
                            'trends': ['up', 'down', 'sideways']
                        }
                    }
                }
            }
        }

    def run_test_scenario(self, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test scenario and capture results"""
        logger.info(f"\n{'='*60}")
        logger.info(f"TESTING SCENARIO: {name}")
        logger.info(f"{'='*60}")

        test_result = {
            'scenario': name,
            'input_data': data,
            'formatted_output': None,
            'price_structure_found': False,
            'narrative_conversion': False,
            'no_raw_dict': False,
            'errors': []
        }

        try:
            # Test the formatting
            formatted_output = self.formatter.format_analysis_result(data, "BTCUSDT")
            test_result['formatted_output'] = formatted_output

            logger.info("Formatted Output:")
            logger.info(formatted_output)

            # Check if Price Structure section exists
            if "Price Structure" in formatted_output:
                test_result['price_structure_found'] = True
                logger.info("✅ Price Structure section found in output")
            else:
                logger.warning("❌ Price Structure section NOT found in output")

            # Check for narrative text (not raw dict patterns)
            dict_patterns = ['{', '}', "'signal':", "'bias':", "'strength':"]
            has_dict_pattern = any(pattern in formatted_output for pattern in dict_patterns)

            if not has_dict_pattern:
                test_result['no_raw_dict'] = True
                logger.info("✅ No raw dictionary patterns found in output")
            else:
                logger.warning("❌ Raw dictionary patterns still present in output")

            # Check for narrative conversion
            narrative_indicators = [
                'bullish', 'bearish', 'neutral', 'strong', 'moderate', 'weak',
                'breakout', 'support', 'resistance', 'trend', 'consolidation'
            ]
            has_narrative = any(indicator in formatted_output.lower() for indicator in narrative_indicators)

            if has_narrative:
                test_result['narrative_conversion'] = True
                logger.info("✅ Narrative conversion appears successful")
            else:
                logger.warning("❌ Limited narrative indicators found")

        except Exception as e:
            error_msg = f"Error formatting scenario {name}: {str(e)}"
            logger.error(error_msg)
            test_result['errors'].append(error_msg)

        return test_result

    def validate_formatter_function_directly(self):
        """Test the _summarize_signals function directly"""
        logger.info(f"\n{'='*60}")
        logger.info("TESTING _summarize_signals FUNCTION DIRECTLY")
        logger.info(f"{'='*60}")

        # Access the function by creating a mock scenario
        test_signals = {
            'support_resistance': {
                'signal': 'bullish_breakout',
                'bias': 'bullish',
                'strength': 'strong',
                'interpretation': 'Price broke above key resistance level'
            },
            'trend_structure': {
                'signal': 'uptrend',
                'trend': 'bullish',
                'strength': 'moderate'
            },
            'simple_signal': 'bearish'
        }

        # The _summarize_signals function is defined inside _format_enhanced_interpretations
        # We'll test it indirectly through the formatter
        test_data = {
            'results': {
                'price_structure': {
                    'signals': test_signals
                }
            }
        }

        try:
            formatted = self.formatter.format_analysis_result(test_data, "TESTPAIR")
            logger.info("Direct function test output:")
            logger.info(formatted)

            # Check if signals were properly converted
            if "Support Resistance: bullish breakout" in formatted:
                logger.info("✅ Dict-to-narrative conversion working correctly")
                return True
            else:
                logger.warning("❌ Dict-to-narrative conversion may not be working")
                return False

        except Exception as e:
            logger.error(f"Error testing _summarize_signals function: {str(e)}")
            return False

    def run_regression_tests(self):
        """Test that other components still work correctly"""
        logger.info(f"\n{'='*60}")
        logger.info("RUNNING REGRESSION TESTS")
        logger.info(f"{'='*60}")

        regression_data = {
            'score': 67.8,
            'confluence_score': 67.8,
            'reliability': 1.0,
            'components': {
                'technical': 75.2,
                'volume': 62.4,
                'orderbook': 68.9,
                'orderflow': 73.1,
                'sentiment': 59.6,
                'price_structure': 65.3
            },
            'results': {
                'technical': {
                    'score': 75.2,
                    'interpretation': 'Technical indicators showing bullish momentum'
                },
                'volume': {
                    'interpretation': 'Volume confirms the price movement'
                },
                'sentiment': {
                    'interpretation': {
                        'summary': 'Market sentiment is cautiously optimistic'
                    }
                },
                'price_structure': {
                    'signals': {
                        'test_signal': {
                            'signal': 'bullish',
                            'strength': 'strong'
                        }
                    }
                }
            }
        }

        try:
            formatted = self.formatter.format_analysis_result(regression_data, "REGRESSTEST")
            logger.info("Regression test output:")
            logger.info(formatted)

            # Check that all components are present
            required_sections = ['Technical', 'Volume', 'Sentiment', 'Price Structure']
            missing_sections = []

            for section in required_sections:
                if section not in formatted:
                    missing_sections.append(section)

            if not missing_sections:
                logger.info("✅ All expected sections present in regression test")
                return True
            else:
                logger.warning(f"❌ Missing sections in regression test: {missing_sections}")
                return False

        except Exception as e:
            logger.error(f"Regression test failed: {str(e)}")
            return False

    def run_all_tests(self):
        """Run comprehensive validation suite"""
        logger.info("Starting comprehensive price structure validation...")

        # Test scenarios
        scenarios = self.create_test_scenarios()
        for name, data in scenarios.items():
            result = self.run_test_scenario(name, data)
            self.test_results.append(result)

        # Test function directly
        direct_test_passed = self.validate_formatter_function_directly()

        # Regression tests
        regression_passed = self.run_regression_tests()

        # Generate summary
        self.generate_summary_report(direct_test_passed, regression_passed)

    def generate_summary_report(self, direct_test_passed: bool, regression_passed: bool):
        """Generate comprehensive summary report"""
        logger.info(f"\n{'='*80}")
        logger.info("COMPREHENSIVE VALIDATION SUMMARY")
        logger.info(f"{'='*80}")

        total_scenarios = len(self.test_results)
        successful_scenarios = sum(1 for r in self.test_results if not r['errors'])
        narrative_conversions = sum(1 for r in self.test_results if r['narrative_conversion'])
        no_raw_dicts = sum(1 for r in self.test_results if r['no_raw_dict'])

        logger.info(f"Total test scenarios: {total_scenarios}")
        logger.info(f"Successful scenarios: {successful_scenarios}/{total_scenarios}")
        logger.info(f"Scenarios with narrative conversion: {narrative_conversions}/{total_scenarios}")
        logger.info(f"Scenarios without raw dict patterns: {no_raw_dicts}/{total_scenarios}")
        logger.info(f"Direct function test: {'PASSED' if direct_test_passed else 'FAILED'}")
        logger.info(f"Regression test: {'PASSED' if regression_passed else 'FAILED'}")

        # Individual scenario results
        logger.info("\nIndividual Scenario Results:")
        for result in self.test_results:
            status = "✅ PASS" if not result['errors'] and result['narrative_conversion'] else "❌ FAIL"
            logger.info(f"  {result['scenario']}: {status}")
            if result['errors']:
                for error in result['errors']:
                    logger.info(f"    Error: {error}")

        # Overall assessment
        overall_success = (
            successful_scenarios == total_scenarios and
            narrative_conversions > 0 and
            direct_test_passed and
            regression_passed
        )

        logger.info(f"\n{'='*80}")
        if overall_success:
            logger.info("🎉 OVERALL VALIDATION: PASSED")
            logger.info("Price structure interpretation fixes are working correctly!")
        else:
            logger.info("❌ OVERALL VALIDATION: FAILED")
            logger.info("Issues found that need attention.")
        logger.info(f"{'='*80}")

def main():
    """Main validation function"""
    validator = PriceStructureValidationTest()
    validator.run_all_tests()

if __name__ == "__main__":
    main()