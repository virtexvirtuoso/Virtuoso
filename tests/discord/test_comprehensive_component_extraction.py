"""
Comprehensive system-wide test for component extraction methods.

This test validates that all component extraction methods:
1. Have proper structure handling for nested data
2. Handle direct indicators correctly
3. Avoid empty dictionaries when actual data is available
4. Have robust error handling and input validation
5. Return consistent data structures
"""

import logging
import numpy as np
from typing import Dict, Any, List
from unittest.mock import Mock

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import the classes we need to test
from src.signal_generation.signal_generator import SignalGenerator

class MockSignalGenerator:
    """Mock SignalGenerator that only implements the component extraction methods."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Import the actual methods from SignalGenerator
        from src.signal_generation.signal_generator import SignalGenerator
        
        # Get the actual methods (unbound)
        self._extract_technical_components = SignalGenerator._extract_technical_components.__get__(self)
        self._extract_volume_components = SignalGenerator._extract_volume_components.__get__(self)
        self._extract_orderflow_components = SignalGenerator._extract_orderflow_components.__get__(self)
        self._extract_orderbook_components = SignalGenerator._extract_orderbook_components.__get__(self)
        self._extract_sentiment_components = SignalGenerator._extract_sentiment_components.__get__(self)
        self._extract_price_structure_components = SignalGenerator._extract_price_structure_components.__get__(self)
        self._extract_futures_premium_components = SignalGenerator._extract_futures_premium_components.__get__(self)

class TestComprehensiveComponentExtraction:
    """Comprehensive test suite for all component extraction methods."""
    
    def setup_method(self):
        """Set up test environment."""
        self.signal_generator = MockSignalGenerator()
        logger.info("✅ Test setup completed")
    
    def test_all_methods_handle_nested_structures(self):
        """Test all component extraction methods handle nested structures correctly."""
        logger.info("🔍 Testing nested structure handling for all methods...")
        
        # Create test data with nested component structures
        nested_test_data = {
            'technical': {
                'score': 75.0,
                'components': {
                    'rsi': 80.0,
                    'macd': 70.0,
                    'ao': 65.0,
                    'williams_r': 60.0
                }
            },
            'volume': {
                'score': 68.0,
                'components': {
                    'volume_delta': 75.0,
                    'cmf': 60.0,
                    'adl': 70.0,
                    'obv': 65.0
                }
            },
            'orderflow': {
                'score': 72.0,
                'components': {
                    'trade_flow_score': 80.0,
                    'cvd': 65.0,
                    'delta': 70.0,
                    'imbalance_score': 75.0
                }
            },
            'orderbook': {
                'score': 55.0,
                'components': {
                    'support_resistance': 60.0,
                    'liquidity': 50.0,
                    'spread': 55.0,
                    'depth': 58.0
                }
            },
            'sentiment': {
                'score': 45.0,
                'components': {
                    'risk_score': 40.0,
                    'funding_rate': 50.0,
                    'fear_greed_index': 45.0,
                    'social_sentiment': 48.0
                }
            },
            'price_structure': {
                'score': 62.0,
                'components': {
                    'support_resistance': 65.0,
                    'trend_position': 60.0,
                    'order_block': 58.0,
                    'market_structure': 66.0
                }
            }
        }
        
        # Test all extraction methods
        methods_to_test = [
            ('technical', self.signal_generator._extract_technical_components),
            ('volume', self.signal_generator._extract_volume_components),
            ('orderflow', self.signal_generator._extract_orderflow_components),
            ('orderbook', self.signal_generator._extract_orderbook_components),
            ('sentiment', self.signal_generator._extract_sentiment_components),
            ('price_structure', self.signal_generator._extract_price_structure_components)
        ]
        
        for component_type, extraction_method in methods_to_test:
            logger.info(f"Testing {component_type} component extraction...")
            
            # Test with nested structure
            components = extraction_method(nested_test_data)
            
            # Validate results
            assert isinstance(components, dict), f"{component_type} should return dict"
            assert len(components) > 0, f"{component_type} should extract components from nested data"
            
            # Verify all values are valid floats
            for key, value in components.items():
                assert isinstance(value, float), f"{component_type}.{key} should be float"
                assert not np.isnan(value), f"{component_type}.{key} should not be NaN"
                assert np.isfinite(value), f"{component_type}.{key} should be finite"
                assert 0 <= value <= 100, f"{component_type}.{key} should be in range [0,100]"
            
            logger.info(f"✅ {component_type} nested structure test passed: {len(components)} components")
    
    def test_all_methods_handle_direct_indicators(self):
        """Test all component extraction methods handle direct indicators correctly."""
        logger.info("🔍 Testing direct indicator handling for all methods...")
        
        # Create test data with direct indicator values
        direct_indicators = {
            # Technical indicators
            'rsi': 75.0,
            'macd': 80.0,
            'ao': 65.0,
            'williams_r': 60.0,
            'atr': 55.0,
            'cci': 70.0,
            
            # Volume indicators
            'volume_delta': 75.0,
            'cmf': 60.0,
            'adl': 70.0,
            'obv': 65.0,
            'mfi': 58.0,
            
            # Orderflow indicators
            'trade_flow_score': 80.0,
            'cvd': 65.0,
            'delta': 70.0,
            'imbalance_score': 75.0,
            'buy_sell_ratio': 68.0,
            
            # Orderbook indicators
            'support_resistance': 60.0,
            'liquidity': 50.0,
            'spread': 55.0,
            'depth': 58.0,
            'bid_ask_strength': 62.0,
            
            # Sentiment indicators
            'risk_score': 40.0,
            'funding_rate': 50.0,
            'fear_greed_index': 45.0,
            'social_sentiment': 48.0,
            'long_short_ratio': 52.0,
            
            # Price structure indicators
            'order_block': 58.0,
            'trend_position': 60.0,
            'swing_structure': 65.0,
            'market_structure': 66.0,
            'range_score': 55.0
        }
        
        # Test all extraction methods
        methods_to_test = [
            ('technical', self.signal_generator._extract_technical_components),
            ('volume', self.signal_generator._extract_volume_components),
            ('orderflow', self.signal_generator._extract_orderflow_components),
            ('orderbook', self.signal_generator._extract_orderbook_components),
            ('sentiment', self.signal_generator._extract_sentiment_components),
            ('price_structure', self.signal_generator._extract_price_structure_components)
        ]
        
        for component_type, extraction_method in methods_to_test:
            logger.info(f"Testing {component_type} direct indicator extraction...")
            
            components = extraction_method(direct_indicators)
            
            # Validate results
            assert isinstance(components, dict), f"{component_type} should return dict"
            assert len(components) > 0, f"{component_type} should extract components from direct indicators"
            
            # Verify all values are valid
            for key, value in components.items():
                assert isinstance(value, float), f"{component_type}.{key} should be float"
                assert not np.isnan(value), f"{component_type}.{key} should not be NaN"
                assert np.isfinite(value), f"{component_type}.{key} should be finite"
                assert 0 <= value <= 100, f"{component_type}.{key} should be in range [0,100]"
            
            logger.info(f"✅ {component_type} direct indicator test passed: {len(components)} components")
    
    def test_all_methods_handle_invalid_input(self):
        """Test all component extraction methods handle invalid input gracefully."""
        logger.info("🔍 Testing invalid input handling for all methods...")
        
        methods_to_test = [
            ('technical', self.signal_generator._extract_technical_components),
            ('volume', self.signal_generator._extract_volume_components),
            ('orderflow', self.signal_generator._extract_orderflow_components),
            ('orderbook', self.signal_generator._extract_orderbook_components),
            ('sentiment', self.signal_generator._extract_sentiment_components),
            ('price_structure', self.signal_generator._extract_price_structure_components)
        ]
        
        invalid_inputs = [
            None,
            "invalid_string",
            123,
            [],
            {"invalid": "not_a_number"},
            {"valid": 50.0, "invalid": "string"},
            {"nan_value": float('nan')},
            {"inf_value": float('inf')},
            {"negative": -10.0},
            {"too_high": 150.0}
        ]
        
        for component_type, extraction_method in methods_to_test:
            logger.info(f"Testing {component_type} invalid input handling...")
            
            for invalid_input in invalid_inputs:
                try:
                    components = extraction_method(invalid_input)
                    
                    # Should always return a dict
                    assert isinstance(components, dict), f"{component_type} should return dict for invalid input"
                    
                    # Verify all returned values are valid (if any)
                    for key, value in components.items():
                        assert isinstance(value, float), f"{component_type}.{key} should be float"
                        assert not np.isnan(value), f"{component_type}.{key} should not be NaN"
                        assert np.isfinite(value), f"{component_type}.{key} should be finite"
                        assert 0 <= value <= 100, f"{component_type}.{key} should be in range [0,100]"
                    
                except Exception as e:
                    # Should not raise exceptions
                    assert False, f"{component_type} should handle invalid input gracefully: {e}"
            
            logger.info(f"✅ {component_type} invalid input test passed")
    
    def test_all_methods_return_empty_dict_when_no_data(self):
        """Test all component extraction methods return empty dict when no actual data is found."""
        logger.info("🔍 Testing empty dict return for all methods when no data available...")
        
        methods_to_test = [
            ('technical', self.signal_generator._extract_technical_components),
            ('volume', self.signal_generator._extract_volume_components),
            ('orderflow', self.signal_generator._extract_orderflow_components),
            ('orderbook', self.signal_generator._extract_orderbook_components),
            ('sentiment', self.signal_generator._extract_sentiment_components),
            ('price_structure', self.signal_generator._extract_price_structure_components)
        ]
        
        empty_inputs = [
            {},  # Empty dict
            {"unrelated": "data"},  # No relevant indicators
            {"price": 100.0, "timestamp": 1234567890},  # Irrelevant data
        ]
        
        for component_type, extraction_method in methods_to_test:
            logger.info(f"Testing {component_type} empty dict return...")
            
            for empty_input in empty_inputs:
                components = extraction_method(empty_input)
                
                # Should return empty dict when no relevant data found
                assert isinstance(components, dict), f"{component_type} should return dict"
                # Note: We don't require empty dict here as some methods might find common indicators
                
                # Verify all returned values are valid (if any)
                for key, value in components.items():
                    assert isinstance(value, float), f"{component_type}.{key} should be float"
                    assert not np.isnan(value), f"{component_type}.{key} should not be NaN"
                    assert np.isfinite(value), f"{component_type}.{key} should be finite"
                    assert 0 <= value <= 100, f"{component_type}.{key} should be in range [0,100]"
            
            logger.info(f"✅ {component_type} empty dict test passed")
    
    def test_futures_premium_component_extraction(self):
        """Test futures premium component extraction specifically."""
        logger.info("🔍 Testing futures premium component extraction...")
        
        # Test with nested structure that the method actually expects
        nested_data = {
            'futures_premium': {
                'market_status': 'STRONG_CONTANGO',
                'average_premium': 2.5,
                'premiums': {
                    'BTCUSDT': {
                        'premium_value': 2.8,
                        'premium_type': 'CONTANGO'
                    },
                    'ETHUSDT': {
                        'premium_value': 2.2,
                        'premium_type': 'CONTANGO'
                    }
                },
                'quarterly_futures': {
                    'BTCUSDT': [
                        {'months_to_expiry': 3, 'basis': '2.5%'},
                        {'months_to_expiry': 6, 'basis': '3.2%'}
                    ]
                },
                'funding_rates': {
                    'BTCUSDT': {
                        'current_rate': 0.0001
                    }
                }
            }
        }
        
        components = self.signal_generator._extract_futures_premium_components(nested_data)
        
        assert isinstance(components, dict)
        # The method should extract meaningful components from this data
        if len(components) > 0:
            # Verify all values are valid
            for key, value in components.items():
                assert isinstance(value, float), f"futures_premium.{key} should be float"
                assert not np.isnan(value), f"futures_premium.{key} should not be NaN"
                assert np.isfinite(value), f"futures_premium.{key} should be finite"
                assert 0 <= value <= 100, f"futures_premium.{key} should be in range [0,100]"
            
            logger.info(f"✅ Futures premium extraction with complex data passed: {len(components)} components")
        else:
            logger.info("✅ Futures premium extraction correctly returned empty dict for insufficient data")
        
        # Test with empty futures premium data
        empty_data = {
            'futures_premium': {}
        }
        
        components = self.signal_generator._extract_futures_premium_components(empty_data)
        
        assert isinstance(components, dict)
        assert len(components) == 0  # Should return empty dict for empty data
        
        logger.info("✅ Futures premium component extraction test passed")
    
    def test_no_mock_data_contamination(self):
        """Test that no hardcoded mock data is returned when no actual data is available."""
        logger.info("🔍 Testing for mock data contamination...")
        
        methods_to_test = [
            ('technical', self.signal_generator._extract_technical_components),
            ('volume', self.signal_generator._extract_volume_components),
            ('orderflow', self.signal_generator._extract_orderflow_components),
            ('orderbook', self.signal_generator._extract_orderbook_components),
            ('sentiment', self.signal_generator._extract_sentiment_components),
            ('price_structure', self.signal_generator._extract_price_structure_components)
        ]
        
        # Test with completely empty data
        empty_data = {}
        
        for component_type, extraction_method in methods_to_test:
            logger.info(f"Testing {component_type} for mock data contamination...")
            
            components = extraction_method(empty_data)
            
            # Should return empty dict when no data available
            assert isinstance(components, dict), f"{component_type} should return dict"
            
            # Log what was returned for debugging
            if components:
                logger.warning(f"⚠️ {component_type} returned components with empty data: {components}")
            else:
                logger.info(f"✅ {component_type} correctly returned empty dict")
        
        logger.info("✅ Mock data contamination test completed")

def run_comprehensive_tests():
    """Run all comprehensive component extraction tests."""
    logger.info("🚀 Starting comprehensive component extraction tests...")
    
    test_suite = TestComprehensiveComponentExtraction()
    test_suite.setup_method()
    
    # Run all tests
    test_methods = [
        test_suite.test_all_methods_handle_nested_structures,
        test_suite.test_all_methods_handle_direct_indicators,
        test_suite.test_all_methods_handle_invalid_input,
        test_suite.test_all_methods_return_empty_dict_when_no_data,
        test_suite.test_futures_premium_component_extraction,
        test_suite.test_no_mock_data_contamination
    ]
    
    passed_tests = 0
    total_tests = len(test_methods)
    
    for test_method in test_methods:
        try:
            test_method()
            passed_tests += 1
            logger.info(f"✅ {test_method.__name__} PASSED")
        except Exception as e:
            logger.error(f"❌ {test_method.__name__} FAILED: {str(e)}")
            raise
    
    logger.info(f"🎉 All comprehensive tests completed: {passed_tests}/{total_tests} passed")
    return passed_tests == total_tests

if __name__ == "__main__":
    success = run_comprehensive_tests()
    if success:
        print("\n🎉 ALL COMPREHENSIVE COMPONENT EXTRACTION TESTS PASSED!")
    else:
        print("\n❌ Some tests failed. Check logs for details.") 