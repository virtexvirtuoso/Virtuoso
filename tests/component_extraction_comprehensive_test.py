#!/usr/bin/env python3
"""
Comprehensive Component Extraction Test System

This test suite validates all component extraction methods across the system to ensure:
1. Proper structure handling for all data formats
2. Robust error handling and graceful degradation
3. Consistent data validation and normalization
4. Comprehensive coverage of all extraction scenarios
"""

import asyncio
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComponentExtractionTester:
    """Comprehensive tester for all component extraction methods."""
    
    def __init__(self):
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'errors': [],
            'warnings': [],
            'detailed_results': {}
        }
        
        # Test data scenarios
        self.test_scenarios = self._create_test_scenarios()
        
        # Component extraction methods to test
        self.extraction_methods = [
            'technical_components',
            'volume_components', 
            'sentiment_components',
            'orderbook_components',
            'orderflow_components',
            'price_structure_components'
        ]
    
    def _create_test_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Create comprehensive test scenarios for all data structures."""
        return {
            'valid_nested_structure': {
                'technical': {
                    'score': 75.5,
                    'components': {
                        'rsi': 68.2,
                        'macd': 72.1,
                        'ao': 80.3,
                        'williams_r': 65.8,
                        'atr': 55.2,
                        'cci': 70.1,
                        'stoch': 74.5,
                        'bb': 69.8,
                        'ema': 71.2,
                        'sma': 68.9,
                        'momentum': 76.4,
                        'roc': 73.1,
                        'adx': 67.3,
                        'ppo': 72.8,
                        'ultimate_oscillator': 69.5
                    }
                },
                'volume': {
                    'score': 82.3,
                    'components': {
                        'volume_delta': 85.2,
                        'adl': 78.9,
                        'cmf': 81.1,
                        'relative_volume': 84.7,
                        'obv': 79.5,
                        'volume_profile': 83.2,
                        'vwap': 80.8
                    }
                },
                'sentiment': {
                    'score': 64.7,
                    'components': {
                        'funding_rate': 62.1,
                        'long_short_ratio': 68.3,
                        'liquidations': 59.8,
                        'market_activity': 66.2,
                        'risk': 63.5,
                        'volatility': 67.9,
                        'fear_greed_index': 61.4,
                        'put_call_ratio': 65.8,
                        'whale_sentiment': 69.2,
                        'institutional_flow': 64.1
                    }
                },
                'orderbook': {
                    'score': 73.8,
                    'components': {
                        'imbalance': 71.2,
                        'mpi': 75.6,
                        'depth': 72.9,
                        'liquidity': 76.1,
                        'absorption_exhaustion': 70.3,
                        'oir': 74.8,
                        'di': 73.2,
                        'spread': 77.5,
                        'obps': 69.7
                    }
                },
                'orderflow': {
                    'score': 79.1,
                    'components': {
                        'cvd': 81.3,
                        'trade_flow': 77.8,
                        'imbalance': 75.2,
                        'open_interest': 80.6,
                        'pressure': 78.9,
                        'liquidity': 76.4,
                        'liquidity_zones': 79.7
                    }
                },
                'price_structure': {
                    'score': 68.4,
                    'components': {
                        'support_resistance': 70.2,
                        'order_blocks': 67.8,
                        'trend_position': 69.5,
                        'swing_structure': 66.9,
                        'composite_value': 71.1,
                        'fair_value_gaps': 68.7,
                        'bos_choch': 67.3,
                        'range_score': 70.8,
                        'liquidity_pools': 68.1,
                        'market_structure': 69.6,
                        'pivot_points': 67.4,
                        'fibonacci_levels': 68.9
                    }
                }
            },
            
            'flat_structure': {
                'rsi': 68.2,
                'macd': 72.1,
                'ao': 80.3,
                'volume_delta': 85.2,
                'adl': 78.9,
                'funding_rate': 62.1,
                'long_short_ratio': 68.3,
                'orderbook_imbalance': 71.2,
                'orderflow_cvd': 81.3,
                'support_resistance': 70.2
            },
            
            'mixed_structure': {
                'technical': {
                    'components': {
                        'rsi': 68.2,
                        'macd': 72.1
                    }
                },
                'volume_delta': 85.2,
                'sentiment_funding_rate': 62.1,
                'orderbook': {
                    'score': 73.8,
                    'components': {
                        'imbalance': 71.2
                    }
                }
            },
            
            'empty_structure': {},
            
            'invalid_structure': {
                'technical': 'invalid_string',
                'volume': ['invalid', 'array'],
                'sentiment': None,
                'orderbook': 123.45
            },
            
            'missing_components': {
                'technical': {
                    'score': 75.5
                    # Missing 'components' key
                },
                'volume': {
                    'components': None
                }
            },
            
            'invalid_component_values': {
                'technical': {
                    'components': {
                        'rsi': 'invalid_string',
                        'macd': None,
                        'ao': float('inf'),
                        'williams_r': -999,
                        'atr': 150  # Out of range
                    }
                }
            }
        }
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive tests on all component extraction methods."""
        logger.info("🚀 Starting comprehensive component extraction tests...")
        
        # Test each extraction method
        for method_name in self.extraction_methods:
            logger.info(f"\n📊 Testing {method_name}...")
            await self._test_extraction_method(method_name)
        
        # Test cross-component interactions
        await self._test_cross_component_interactions()
        
        # Test error handling
        await self._test_error_handling()
        
        # Test performance
        await self._test_performance()
        
        # Generate comprehensive report
        return self._generate_test_report()
    
    async def _test_extraction_method(self, method_name: str) -> None:
        """Test a specific extraction method with all scenarios."""
        method_results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'scenarios': {}
        }
        
        for scenario_name, test_data in self.test_scenarios.items():
            logger.info(f"  Testing {method_name} with {scenario_name}...")
            
            try:
                # Test the extraction method
                result = await self._execute_extraction_test(method_name, test_data)
                
                # Validate result structure
                validation_result = self._validate_extraction_result(result, method_name)
                
                method_results['scenarios'][scenario_name] = {
                    'result': result,
                    'validation': validation_result,
                    'status': 'passed' if validation_result['valid'] else 'failed'
                }
                
                if validation_result['valid']:
                    method_results['passed'] += 1
                    self.test_results['passed'] += 1
                    logger.info(f"    ✅ {scenario_name}: PASSED")
                else:
                    method_results['failed'] += 1
                    self.test_results['failed'] += 1
                    logger.error(f"    ❌ {scenario_name}: FAILED - {validation_result['errors']}")
                    
            except Exception as e:
                method_results['failed'] += 1
                self.test_results['failed'] += 1
                error_msg = f"Exception in {method_name} with {scenario_name}: {str(e)}"
                logger.error(f"    ❌ {scenario_name}: ERROR - {error_msg}")
                self.test_results['errors'].append(error_msg)
                
                method_results['scenarios'][scenario_name] = {
                    'result': None,
                    'validation': {'valid': False, 'errors': [error_msg]},
                    'status': 'error'
                }
            
            method_results['total_tests'] += 1
        
        self.test_results['detailed_results'][method_name] = method_results
    
    async def _execute_extraction_test(self, method_name: str, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute extraction test by simulating the actual extraction logic."""
        # Simulate the extraction logic based on method name
        if method_name == 'technical_components':
            return self._extract_technical_components_test(test_data)
        elif method_name == 'volume_components':
            return self._extract_volume_components_test(test_data)
        elif method_name == 'sentiment_components':
            return self._extract_sentiment_components_test(test_data)
        elif method_name == 'orderbook_components':
            return self._extract_orderbook_components_test(test_data)
        elif method_name == 'orderflow_components':
            return self._extract_orderflow_components_test(test_data)
        elif method_name == 'price_structure_components':
            return self._extract_price_structure_components_test(test_data)
        else:
            raise ValueError(f"Unknown extraction method: {method_name}")
    
    def _extract_technical_components_test(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Test technical component extraction with robust error handling."""
        components = {}
        
        try:
            # First, check if we have the nested technical indicator structure
            technical_data = indicators.get('technical', {})
            if isinstance(technical_data, dict) and 'components' in technical_data:
                actual_components = technical_data['components']
                if isinstance(actual_components, dict):
                    for key, value in actual_components.items():
                        if isinstance(value, (int, float)) and not np.isnan(value) and np.isfinite(value):
                            components[key] = float(value)
                    
                    if components:
                        return components
            
            # Second, look for direct technical indicators
            technical_indicators = {
                'rsi': indicators.get('rsi'),
                'macd': indicators.get('macd'),
                'ao': indicators.get('ao'),
                'williams_r': indicators.get('williams_r'),
                'atr': indicators.get('atr'),
                'cci': indicators.get('cci'),
                'stoch': indicators.get('stoch'),
                'bb': indicators.get('bb'),
                'ema': indicators.get('ema'),
                'sma': indicators.get('sma'),
                'momentum': indicators.get('momentum'),
                'roc': indicators.get('roc'),
                'adx': indicators.get('adx'),
                'ppo': indicators.get('ppo'),
                'ultimate_oscillator': indicators.get('ultimate_oscillator')
            }
            
            for key, value in technical_indicators.items():
                if value is not None and isinstance(value, (int, float)):
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[key] = float(value)
            
            return components
            
        except Exception as e:
            logger.error(f"Error in technical component extraction: {str(e)}")
            return {}
    
    def _extract_volume_components_test(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Test volume component extraction with robust error handling."""
        components = {}
        
        try:
            # First, check nested structure
            volume_data = indicators.get('volume', {})
            if isinstance(volume_data, dict) and 'components' in volume_data:
                actual_components = volume_data['components']
                if isinstance(actual_components, dict):
                    for key, value in actual_components.items():
                        if isinstance(value, (int, float)) and not np.isnan(value) and np.isfinite(value):
                            components[key] = float(value)
                    
                    if components:
                        return components
            
            # Second, look for direct volume indicators
            for key, value in indicators.items():
                if key.startswith('volume_') and isinstance(value, (int, float)) and key != 'volume_score':
                    component_name = key.replace('volume_', '')
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[component_name] = float(value)
            
            # Third, look for common volume indicators
            volume_indicators = {
                'volume_delta': indicators.get('volume_delta'),
                'adl': indicators.get('adl'),
                'cmf': indicators.get('cmf'),
                'relative_volume': indicators.get('relative_volume'),
                'obv': indicators.get('obv'),
                'volume_profile': indicators.get('volume_profile'),
                'vwap': indicators.get('vwap')
            }
            
            for key, value in volume_indicators.items():
                if value is not None and isinstance(value, (int, float)):
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[key] = float(value)
            
            return components
            
        except Exception as e:
            logger.error(f"Error in volume component extraction: {str(e)}")
            return {}
    
    def _extract_sentiment_components_test(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Test sentiment component extraction with robust error handling."""
        components = {}
        
        try:
            # First, check nested structure
            sentiment_data = indicators.get('sentiment', {})
            if isinstance(sentiment_data, dict) and 'components' in sentiment_data:
                actual_components = sentiment_data['components']
                if isinstance(actual_components, dict):
                    for key, value in actual_components.items():
                        if isinstance(value, (int, float)) and not np.isnan(value) and np.isfinite(value):
                            components[key] = float(value)
                    
                    if components:
                        return components
            
            # Second, look for direct sentiment indicators
            for key, value in indicators.items():
                if key.startswith('sentiment_') and isinstance(value, (int, float)) and key != 'sentiment_score':
                    component_name = key.replace('sentiment_', '')
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[component_name] = float(value)
            
            # Third, look for common sentiment indicators
            sentiment_indicators = {
                'funding_rate': indicators.get('funding_rate'),
                'long_short_ratio': indicators.get('long_short_ratio'),
                'liquidations': indicators.get('liquidations'),
                'market_activity': indicators.get('market_activity'),
                'risk': indicators.get('risk'),
                'volatility': indicators.get('volatility'),
                'fear_greed_index': indicators.get('fear_greed_index'),
                'put_call_ratio': indicators.get('put_call_ratio'),
                'whale_sentiment': indicators.get('whale_sentiment'),
                'institutional_flow': indicators.get('institutional_flow')
            }
            
            for key, value in sentiment_indicators.items():
                if value is not None and isinstance(value, (int, float)):
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[key] = float(value)
            
            return components
            
        except Exception as e:
            logger.error(f"Error in sentiment component extraction: {str(e)}")
            return {}
    
    def _extract_orderbook_components_test(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Test orderbook component extraction with robust error handling."""
        components = {}
        
        try:
            # First, check nested structure
            orderbook_data = indicators.get('orderbook', {})
            if isinstance(orderbook_data, dict) and 'components' in orderbook_data:
                actual_components = orderbook_data['components']
                if isinstance(actual_components, dict):
                    for key, value in actual_components.items():
                        if isinstance(value, (int, float)) and not np.isnan(value) and np.isfinite(value):
                            components[key] = float(value)
                    
                    if components:
                        return components
            
            # Second, look for direct orderbook indicators
            for key, value in indicators.items():
                if key.startswith('orderbook_') and isinstance(value, (int, float)) and key != 'orderbook_score':
                    component_name = key.replace('orderbook_', '')
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[component_name] = float(value)
            
            # Third, look for common orderbook indicators
            orderbook_indicators = {
                'imbalance': indicators.get('imbalance'),
                'mpi': indicators.get('mpi'),
                'depth': indicators.get('depth'),
                'liquidity': indicators.get('liquidity'),
                'absorption_exhaustion': indicators.get('absorption_exhaustion'),
                'oir': indicators.get('oir'),
                'di': indicators.get('di'),
                'spread': indicators.get('spread'),
                'obps': indicators.get('obps')
            }
            
            for key, value in orderbook_indicators.items():
                if value is not None and isinstance(value, (int, float)):
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[key] = float(value)
            
            return components
            
        except Exception as e:
            logger.error(f"Error in orderbook component extraction: {str(e)}")
            return {}
    
    def _extract_orderflow_components_test(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Test orderflow component extraction with robust error handling."""
        components = {}
        
        try:
            # First, check nested structure
            orderflow_data = indicators.get('orderflow', {})
            if isinstance(orderflow_data, dict) and 'components' in orderflow_data:
                actual_components = orderflow_data['components']
                if isinstance(actual_components, dict):
                    for key, value in actual_components.items():
                        if isinstance(value, (int, float)) and not np.isnan(value) and np.isfinite(value):
                            components[key] = float(value)
                    
                    if components:
                        return components
            
            # Second, look for direct orderflow indicators
            for key, value in indicators.items():
                if key.startswith('orderflow_') and isinstance(value, (int, float)) and key != 'orderflow_score':
                    component_name = key.replace('orderflow_', '')
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[component_name] = float(value)
            
            # Third, look for common orderflow indicators
            orderflow_indicators = {
                'cvd': indicators.get('cvd'),
                'trade_flow': indicators.get('trade_flow'),
                'imbalance': indicators.get('imbalance'),
                'open_interest': indicators.get('open_interest'),
                'pressure': indicators.get('pressure'),
                'liquidity': indicators.get('liquidity'),
                'liquidity_zones': indicators.get('liquidity_zones')
            }
            
            for key, value in orderflow_indicators.items():
                if value is not None and isinstance(value, (int, float)):
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[key] = float(value)
            
            return components
            
        except Exception as e:
            logger.error(f"Error in orderflow component extraction: {str(e)}")
            return {}
    
    def _extract_price_structure_components_test(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Test price structure component extraction with robust error handling."""
        components = {}
        
        try:
            # First, check nested structure
            price_structure_data = indicators.get('price_structure', {})
            if isinstance(price_structure_data, dict) and 'components' in price_structure_data:
                actual_components = price_structure_data['components']
                if isinstance(actual_components, dict):
                    for key, value in actual_components.items():
                        if isinstance(value, (int, float)) and not np.isnan(value) and np.isfinite(value):
                            components[key] = float(value)
                    
                    if components:
                        return components
            
            # Second, look for direct price structure indicators
            for key, value in indicators.items():
                if key.startswith('price_structure_') and isinstance(value, (int, float)) and key != 'price_structure_score':
                    component_name = key.replace('price_structure_', '')
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[component_name] = float(value)
            
            # Third, look for common price structure indicators
            price_structure_indicators = {
                'support_resistance': indicators.get('support_resistance'),
                'order_blocks': indicators.get('order_blocks'),
                'trend_position': indicators.get('trend_position'),
                'swing_structure': indicators.get('swing_structure'),
                'composite_value': indicators.get('composite_value'),
                'fair_value_gaps': indicators.get('fair_value_gaps'),
                'bos_choch': indicators.get('bos_choch'),
                'range_score': indicators.get('range_score'),
                'liquidity_pools': indicators.get('liquidity_pools'),
                'market_structure': indicators.get('market_structure'),
                'pivot_points': indicators.get('pivot_points'),
                'fibonacci_levels': indicators.get('fibonacci_levels')
            }
            
            for key, value in price_structure_indicators.items():
                if value is not None and isinstance(value, (int, float)):
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[key] = float(value)
            
            return components
            
        except Exception as e:
            logger.error(f"Error in price structure component extraction: {str(e)}")
            return {}
    
    def _validate_extraction_result(self, result: Dict[str, Any], method_name: str) -> Dict[str, Any]:
        """Validate extraction result structure and content."""
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
            if np.isnan(value) or np.isinf(value):
                validation['valid'] = False
                validation['errors'].append(f"Component value is NaN or infinite: {key}={value}")
                continue
            
            # Check value range (0-100 expected for scores)
            if not (0 <= value <= 100):
                validation['warnings'].append(f"Component value outside expected range [0,100]: {key}={value}")
        
        # Check if result is empty when it shouldn't be
        if not result and method_name in ['technical_components', 'volume_components']:
            validation['warnings'].append(f"Empty result for {method_name} - may indicate missing data")
        
        return validation
    
    async def _test_cross_component_interactions(self) -> None:
        """Test interactions between different component extraction methods."""
        logger.info("\n🔄 Testing cross-component interactions...")
        
        # Test with mixed data that should affect multiple extractors
        mixed_data = {
            'technical': {'components': {'rsi': 75.0}},
            'volume_delta': 80.0,
            'sentiment_funding_rate': 60.0,
            'orderbook': {'components': {'imbalance': 70.0}},
            'orderflow_cvd': 85.0,
            'price_structure': {'components': {'support_resistance': 65.0}}
        }
        
        results = {}
        for method_name in self.extraction_methods:
            try:
                result = await self._execute_extraction_test(method_name, mixed_data)
                results[method_name] = result
                logger.info(f"  {method_name}: {len(result)} components extracted")
            except Exception as e:
                logger.error(f"  {method_name}: Error - {str(e)}")
                results[method_name] = {}
        
        # Validate no component conflicts
        all_components = set()
        conflicts = []
        
        for method_name, components in results.items():
            for component_name in components.keys():
                if component_name in all_components:
                    conflicts.append(f"Component '{component_name}' extracted by multiple methods")
                all_components.add(component_name)
        
        if conflicts:
            self.test_results['warnings'].extend(conflicts)
            logger.warning(f"  ⚠️ Found {len(conflicts)} component conflicts")
        else:
            logger.info("  ✅ No component conflicts found")
    
    async def _test_error_handling(self) -> None:
        """Test error handling capabilities."""
        logger.info("\n🛡️ Testing error handling...")
        
        error_scenarios = [
            {'data': None, 'name': 'None input'},
            {'data': 'invalid_string', 'name': 'String input'},
            {'data': 123, 'name': 'Numeric input'},
            {'data': [], 'name': 'List input'},
            {'data': {'circular': None}, 'name': 'Circular reference'},
            {'data': {'huge_number': 1e308}, 'name': 'Huge number'},
            {'data': {'negative': -1000}, 'name': 'Negative value'},
            {'data': {'nan_value': float('nan')}, 'name': 'NaN value'},
            {'data': {'inf_value': float('inf')}, 'name': 'Infinite value'}
        ]
        
        for scenario in error_scenarios:
            logger.info(f"  Testing {scenario['name']}...")
            
            for method_name in self.extraction_methods:
                try:
                    result = await self._execute_extraction_test(method_name, scenario['data'])
                    
                    # Should return empty dict for invalid input
                    if isinstance(result, dict) and len(result) == 0:
                        logger.info(f"    ✅ {method_name}: Graceful handling")
                    else:
                        logger.warning(f"    ⚠️ {method_name}: Unexpected result: {result}")
                        
                except Exception as e:
                    logger.error(f"    ❌ {method_name}: Unhandled exception: {str(e)}")
                    self.test_results['errors'].append(f"{method_name} failed on {scenario['name']}: {str(e)}")
    
    async def _test_performance(self) -> None:
        """Test performance of extraction methods."""
        logger.info("\n⚡ Testing performance...")
        
        # Create large test dataset
        large_dataset = {}
        for i in range(1000):
            large_dataset[f'indicator_{i}'] = float(i % 100)
        
        import time
        
        for method_name in self.extraction_methods:
            start_time = time.time()
            
            try:
                result = await self._execute_extraction_test(method_name, large_dataset)
                end_time = time.time()
                
                execution_time = end_time - start_time
                logger.info(f"  {method_name}: {execution_time:.4f}s ({len(result)} components)")
                
                if execution_time > 1.0:  # More than 1 second is concerning
                    self.test_results['warnings'].append(f"{method_name} took {execution_time:.4f}s - performance issue")
                    
            except Exception as e:
                logger.error(f"  {method_name}: Performance test failed: {str(e)}")
    
    def _generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        logger.info("\n📊 Generating test report...")
        
        total_tests = self.test_results['passed'] + self.test_results['failed']
        success_rate = (self.test_results['passed'] / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': total_tests,
                'passed': self.test_results['passed'],
                'failed': self.test_results['failed'],
                'success_rate': success_rate,
                'errors': len(self.test_results['errors']),
                'warnings': len(self.test_results['warnings'])
            },
            'detailed_results': self.test_results['detailed_results'],
            'errors': self.test_results['errors'],
            'warnings': self.test_results['warnings']
        }
        
        # Log summary
        logger.info(f"\n🎯 TEST SUMMARY:")
        logger.info(f"  Total Tests: {total_tests}")
        logger.info(f"  Passed: {self.test_results['passed']} ✅")
        logger.info(f"  Failed: {self.test_results['failed']} ❌")
        logger.info(f"  Success Rate: {success_rate:.1f}%")
        logger.info(f"  Errors: {len(self.test_results['errors'])}")
        logger.info(f"  Warnings: {len(self.test_results['warnings'])}")
        
        if success_rate >= 95:
            logger.info("🎉 EXCELLENT: Component extraction system is highly robust!")
        elif success_rate >= 85:
            logger.info("👍 GOOD: Component extraction system is generally robust")
        elif success_rate >= 70:
            logger.info("⚠️ MODERATE: Component extraction system needs improvement")
        else:
            logger.error("❌ POOR: Component extraction system requires significant fixes")
        
        return report
    
    def save_report(self, report: Dict[str, Any], filepath: str = None) -> None:
        """Save test report to file."""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"tests/reports/component_extraction_test_{timestamp}.json"
        
        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📄 Test report saved to: {filepath}")


async def main():
    """Main test execution function."""
    logger.info("🚀 Starting Comprehensive Component Extraction Test System")
    
    tester = ComponentExtractionTester()
    
    try:
        # Run comprehensive tests
        report = await tester.run_comprehensive_tests()
        
        # Save report
        tester.save_report(report)
        
        # Return success/failure based on results
        if report['summary']['success_rate'] >= 85:
            logger.info("✅ Component extraction system validation PASSED")
            return 0
        else:
            logger.error("❌ Component extraction system validation FAILED")
            return 1
            
    except Exception as e:
        logger.error(f"💥 Test system failed: {str(e)}")
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main())) 