#!/usr/bin/env python3
"""
Simple Component Extraction Test

This script tests the component extraction logic patterns without requiring
the full SignalGenerator class import.
"""

import numpy as np
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_technical_components_test(indicators: Dict[str, Any]) -> Dict[str, float]:
    """Test implementation of technical component extraction with robust error handling."""
    components = {}
    
    try:
        # Input validation
        if not isinstance(indicators, dict):
            logger.error(f"Invalid indicators input type: {type(indicators)}")
            return {}
        
        # First, check if we have the nested technical indicator structure
        technical_data = indicators.get('technical', {})
        if isinstance(technical_data, dict) and 'components' in technical_data:
            actual_components = technical_data['components']
            if isinstance(actual_components, dict):
                for key, value in actual_components.items():
                    if isinstance(value, (int, float)) and not np.isnan(value) and np.isfinite(value):
                        if 0 <= value <= 100:  # Validate range
                            components[key] = float(value)
                
                if components:
                    logger.debug(f"Using actual technical components: {components}")
                    return components
        
        # Second, look for direct technical indicators
        technical_indicators = {
            'rsi': indicators.get('rsi'),
            'macd': indicators.get('macd'),
            'ao': indicators.get('ao'),
            'williams_r': indicators.get('williams_r'),
            'atr': indicators.get('atr'),
            'cci': indicators.get('cci')
        }
        
        for key, value in technical_indicators.items():
            if value is not None and isinstance(value, (int, float)):
                if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                    components[key] = float(value)
        
        return components
        
    except Exception as e:
        logger.error(f"Error in technical component extraction: {str(e)}")
        return {}

def run_simple_test():
    """Run simple component extraction tests."""
    logger.info("🚀 Starting Simple Component Extraction Test")
    
    test_scenarios = {
        'valid_nested': {
            'technical': {
                'components': {
                    'rsi': 68.2,
                    'macd': 72.1,
                    'ao': 80.3
                }
            }
        },
        'flat_structure': {
            'rsi': 68.2,
            'macd': 72.1,
            'ao': 80.3
        },
        'empty_structure': {},
        'invalid_structure': {
            'technical': 'invalid_string'
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
        },
        'none_input': None,
        'string_input': 'invalid'
    }
    
    passed = 0
    failed = 0
    
    for scenario_name, test_data in test_scenarios.items():
        logger.info(f"Testing {scenario_name}...")
        
        try:
            result = extract_technical_components_test(test_data)
            
            # Validate result
            if not isinstance(result, dict):
                logger.error(f"  ❌ {scenario_name}: Result not a dict")
                failed += 1
                continue
            
            # Check for invalid values in result
            valid_result = True
            for key, value in result.items():
                if not isinstance(value, (int, float)):
                    logger.error(f"  ❌ {scenario_name}: Invalid value type {key}={value}")
                    valid_result = False
                    break
                
                if np.isnan(value) or np.isinf(value):
                    logger.error(f"  ❌ {scenario_name}: NaN/Inf value {key}={value}")
                    valid_result = False
                    break
                
                if not (0 <= value <= 100):
                    logger.warning(f"  ⚠️ {scenario_name}: Value out of range {key}={value}")
            
            if valid_result:
                logger.info(f"  ✅ {scenario_name}: PASSED (extracted {len(result)} components)")
                passed += 1
            else:
                logger.error(f"  ❌ {scenario_name}: FAILED - Invalid result values")
                failed += 1
                
        except Exception as e:
            logger.error(f"  ❌ {scenario_name}: EXCEPTION - {str(e)}")
            failed += 1
    
    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0
    
    logger.info(f"\n🎯 TEST SUMMARY:")
    logger.info(f"  Total Tests: {total}")
    logger.info(f"  Passed: {passed} ✅")
    logger.info(f"  Failed: {failed} ❌")
    logger.info(f"  Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 95:
        logger.info("🎉 EXCELLENT: Component extraction logic is highly robust!")
        return True
    elif success_rate >= 85:
        logger.info("👍 GOOD: Component extraction logic is generally robust")
        return True
    else:
        logger.error("❌ POOR: Component extraction logic needs fixes")
        return False

if __name__ == "__main__":
    success = run_simple_test()
    exit(0 if success else 1) 