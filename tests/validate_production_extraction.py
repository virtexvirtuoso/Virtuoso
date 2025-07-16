#!/usr/bin/env python3
"""
Production Component Extraction Validation

This script validates the actual production component extraction methods
in the SignalGenerator class to ensure they match our robust test patterns.
"""

import sys
import os
import logging
import traceback
from typing import Dict, Any

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from signal_generation.signal_generator import SignalGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionExtractionValidator:
    """Validates production component extraction methods."""
    
    def __init__(self):
        # Create a minimal SignalGenerator instance for testing
        self.signal_generator = SignalGenerator(
            config={'confluence': {'thresholds': {'buy': 68, 'sell': 35}}},
            alert_manager=None,
            interpretation_generator=None
        )
        
        # Test scenarios from our comprehensive test
        self.test_scenarios = {
            'valid_nested_structure': {
                'technical': {
                    'score': 75.5,
                    'components': {
                        'rsi': 68.2,
                        'macd': 72.1,
                        'ao': 80.3
                    }
                },
                'volume': {
                    'score': 82.3,
                    'components': {
                        'volume_delta': 85.2,
                        'adl': 78.9,
                        'cmf': 81.1
                    }
                },
                'sentiment': {
                    'score': 64.7,
                    'components': {
                        'funding_rate': 62.1,
                        'long_short_ratio': 68.3
                    }
                }
            },
            'flat_structure': {
                'rsi': 68.2,
                'macd': 72.1,
                'volume_delta': 85.2,
                'funding_rate': 62.1
            },
            'empty_structure': {},
            'invalid_structure': {
                'technical': 'invalid_string',
                'volume': ['invalid', 'array'],
                'sentiment': None
            },
            'invalid_values': {
                'technical': {
                    'components': {
                        'rsi': float('nan'),
                        'macd': float('inf'),
                        'ao': -50,  # Out of range
                        'williams_r': 150  # Out of range
                    }
                }
            }
        }
    
    def validate_all_methods(self) -> Dict[str, Any]:
        """Validate all production component extraction methods."""
        logger.info("🔍 Validating production component extraction methods...")
        
        results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'method_results': {}
        }
        
        extraction_methods = [
            ('technical', '_extract_technical_components'),
            ('volume', '_extract_volume_components'),
            ('sentiment', '_extract_sentiment_components'),
            ('orderbook', '_extract_orderbook_components'),
            ('orderflow', '_extract_orderflow_components'),
            ('price_structure', '_extract_price_structure_components')
        ]
        
        for method_name, method_attr in extraction_methods:
            logger.info(f"\n📊 Testing {method_name} extraction...")
            
            method_results = {
                'scenarios': {},
                'passed': 0,
                'failed': 0
            }
            
            method = getattr(self.signal_generator, method_attr)
            
            for scenario_name, test_data in self.test_scenarios.items():
                logger.info(f"  Testing {scenario_name}...")
                
                try:
                    # Execute the actual production method
                    result = method(test_data)
                    
                    # Validate the result
                    validation = self._validate_result(result, method_name, scenario_name)
                    
                    method_results['scenarios'][scenario_name] = {
                        'result': result,
                        'validation': validation,
                        'status': 'passed' if validation['valid'] else 'failed'
                    }
                    
                    if validation['valid']:
                        method_results['passed'] += 1
                        results['passed'] += 1
                        logger.info(f"    ✅ {scenario_name}: PASSED")
                    else:
                        method_results['failed'] += 1
                        results['failed'] += 1
                        logger.error(f"    ❌ {scenario_name}: FAILED - {validation['errors']}")
                        
                except Exception as e:
                    method_results['failed'] += 1
                    results['failed'] += 1
                    error_msg = f"Exception in {method_name}: {str(e)}"
                    logger.error(f"    ❌ {scenario_name}: ERROR - {error_msg}")
                    
                    method_results['scenarios'][scenario_name] = {
                        'result': None,
                        'validation': {'valid': False, 'errors': [error_msg]},
                        'status': 'error'
                    }
                
                results['total_tests'] += 1
            
            results['method_results'][method_name] = method_results
        
        return results
    
    def _validate_result(self, result: Any, method_name: str, scenario_name: str) -> Dict[str, Any]:
        """Validate extraction result."""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check if result is a dictionary
        if not isinstance(result, dict):
            validation['valid'] = False
            validation['errors'].append(f"Result is not a dictionary: {type(result)}")
            return validation
        
        # For invalid scenarios, expect empty result
        if scenario_name in ['empty_structure', 'invalid_structure']:
            if len(result) == 0:
                return validation  # Empty result is expected and valid
            else:
                validation['warnings'].append(f"Expected empty result for {scenario_name}, got: {result}")
        
        # Check component values
        for key, value in result.items():
            # Check if key is a string
            if not isinstance(key, str):
                validation['valid'] = False
                validation['errors'].append(f"Component key is not a string: {key}")
                continue
            
            # Check if value is a valid number
            if not isinstance(value, (int, float)):
                validation['valid'] = False
                validation['errors'].append(f"Component value is not numeric: {key}={value}")
                continue
            
            # Check for NaN or infinite values
            import numpy as np
            if np.isnan(value) or np.isinf(value):
                validation['valid'] = False
                validation['errors'].append(f"Component value is NaN or infinite: {key}={value}")
                continue
            
            # Check value range (0-100 expected for scores)
            if not (0 <= value <= 100):
                validation['warnings'].append(f"Component value outside expected range [0,100]: {key}={value}")
        
        return validation
    
    def run_validation(self) -> bool:
        """Run validation and return success status."""
        try:
            results = self.validate_all_methods()
            
            # Calculate success rate
            total_tests = results['total_tests']
            passed = results['passed']
            failed = results['failed']
            success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
            
            # Log summary
            logger.info(f"\n🎯 PRODUCTION VALIDATION SUMMARY:")
            logger.info(f"  Total Tests: {total_tests}")
            logger.info(f"  Passed: {passed} ✅")
            logger.info(f"  Failed: {failed} ❌")
            logger.info(f"  Success Rate: {success_rate:.1f}%")
            
            # Detailed method results
            for method_name, method_results in results['method_results'].items():
                method_passed = method_results['passed']
                method_failed = method_results['failed']
                method_total = method_passed + method_failed
                method_rate = (method_passed / method_total * 100) if method_total > 0 else 0
                
                logger.info(f"  {method_name}: {method_passed}/{method_total} ({method_rate:.1f}%)")
            
            if success_rate >= 95:
                logger.info("🎉 EXCELLENT: Production component extraction methods are highly robust!")
                return True
            elif success_rate >= 85:
                logger.info("👍 GOOD: Production component extraction methods are generally robust")
                return True
            elif success_rate >= 70:
                logger.warning("⚠️ MODERATE: Production component extraction methods need improvement")
                return False
            else:
                logger.error("❌ POOR: Production component extraction methods require significant fixes")
                return False
                
        except Exception as e:
            logger.error(f"💥 Validation failed: {str(e)}")
            logger.error(traceback.format_exc())
            return False

def main():
    """Main validation function."""
    logger.info("🚀 Starting Production Component Extraction Validation")
    
    validator = ProductionExtractionValidator()
    
    success = validator.run_validation()
    
    if success:
        logger.info("✅ Production component extraction validation PASSED")
        return 0
    else:
        logger.error("❌ Production component extraction validation FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 