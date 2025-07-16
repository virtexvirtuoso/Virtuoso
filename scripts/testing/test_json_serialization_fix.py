#!/usr/bin/env python3
"""
Test script to verify JSON serialization fixes for mappingproxy and numpy objects.
"""

import sys
import os
import json
import numpy as np
from types import MappingProxyType
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.utils.json_encoder import CustomJSONEncoder, json_serialize, safe_json_serialize

def test_mappingproxy_serialization():
    """Test that mappingproxy objects can be serialized."""
    print("Testing mappingproxy serialization...")
    
    # Create a mappingproxy object (like those from numpy)
    regular_dict = {'a': 1, 'b': 2, 'c': np.float64(3.14)}
    proxy = MappingProxyType(regular_dict)
    
    try:
        # Test with CustomJSONEncoder
        result = json.dumps(proxy, cls=CustomJSONEncoder)
        print(f"✅ Mappingproxy serialization successful: {result}")
        
        # Test with utility function
        result2 = json_serialize(proxy)
        print(f"✅ Utility function serialization successful: {result2}")
        
        return True
    except Exception as e:
        print(f"❌ Mappingproxy serialization failed: {e}")
        return False

def test_numpy_types_serialization():
    """Test that various numpy types can be serialized."""
    print("\nTesting numpy types serialization...")
    
    test_data = {
        'numpy_float64': np.float64(3.14159),
        'numpy_int64': np.int64(42),
        'numpy_array': np.array([1, 2, 3]),
        'numpy_bool': np.bool_(True),
        'numpy_str': np.str_('test_string'),
        'regular_data': {'score': 68.26, 'symbol': 'ETHUSDT'}
    }
    
    try:
        result = json_serialize(test_data, pretty=True)
        print(f"✅ Numpy types serialization successful:")
        print(result)
        return True
    except Exception as e:
        print(f"❌ Numpy types serialization failed: {e}")
        return False

def test_complex_trading_data():
    """Test serialization of complex trading data similar to what caused the original error."""
    print("\nTesting complex trading data serialization...")
    
    # Simulate the kind of data that was causing issues
    trading_data = {
        'symbol': 'ETHUSDT',
        'confluence_score': np.float64(68.26),
        'components': {
            'technical': np.float64(75.31),
            'orderflow': 73.97,
            'orderbook': 69.78
        },
        'results': {
            'technical': {
                'score': np.float64(75.31),
                'components': {
                    'rsi': 45.90,
                    'macd': np.float64(85.73),
                    'williams_r': 94.29
                }
            }
        },
        'metadata': MappingProxyType({
            'weights': {'orderflow': 0.25, 'orderbook': 0.25},
            'timestamp': datetime.now()
        }),
        'price': 2600.42,
        'reliability': 1.0
    }
    
    try:
        result = json_serialize(trading_data, pretty=True)
        print(f"✅ Complex trading data serialization successful:")
        print(result[:500] + "..." if len(result) > 500 else result)
        return True
    except Exception as e:
        print(f"❌ Complex trading data serialization failed: {e}")
        return False

def test_safe_serialization():
    """Test the safe serialization function with unserializable objects."""
    print("\nTesting safe serialization with unserializable objects...")
    
    def unserializable_function():
        return "This function cannot be serialized"
    
    test_data = {
        'good_data': {'score': 68.26},
        'bad_data': unserializable_function,
        'numpy_data': np.float64(42.0)
    }
    
    try:
        result = safe_json_serialize(test_data)
        print(f"✅ Safe serialization successful: {result}")
        return True
    except Exception as e:
        print(f"❌ Safe serialization failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing JSON Serialization Fixes")
    print("=" * 50)
    
    tests = [
        test_mappingproxy_serialization,
        test_numpy_types_serialization,
        test_complex_trading_data,
        test_safe_serialization
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! JSON serialization fixes are working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the fixes.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 