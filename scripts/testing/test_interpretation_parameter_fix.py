#!/usr/bin/env python3
"""
Test script to verify that the _generate_enhanced_synthesis parameter fix works correctly.
"""

import sys
import os
import asyncio
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.interpretation.interpretation_manager import InterpretationManager

def test_generate_enhanced_synthesis():
    """Test that _generate_enhanced_synthesis works with correct parameters."""
    print("Testing _generate_enhanced_synthesis parameter fix...")
    
    try:
        # Initialize interpretation manager
        interpretation_manager = InterpretationManager()
        
        # Create test raw interpretations
        raw_interpretations = [
            {
                'component': 'orderbook',
                'display_name': 'Orderbook',
                'interpretation': 'Strong bullish orderbook with tight spreads and high liquidity'
            },
            {
                'component': 'technical',
                'display_name': 'Technical',
                'interpretation': 'Strong bearish technical indicators with MACD showing downward momentum'
            },
            {
                'component': 'orderflow',
                'display_name': 'Orderflow',
                'interpretation': 'Moderate bearish orderflow with selling pressure evident'
            }
        ]
        
        # Process interpretations
        interpretation_set = interpretation_manager.process_interpretations(
            raw_interpretations,
            "test_signal",
            market_data=None,  # No market data for this test
            timestamp=datetime.now()
        )
        
        print(f"✅ Successfully processed {len(interpretation_set.interpretations)} interpretations")
        
        # Test _generate_enhanced_synthesis with correct parameters (only interpretation_set)
        enhanced_synthesis = interpretation_manager._generate_enhanced_synthesis(
            interpretation_set
        )
        
        print(f"✅ Successfully generated enhanced synthesis")
        print(f"📊 Enhanced synthesis preview: {enhanced_synthesis[:200]}...")
        
        # Verify that conflicts are detected (bullish orderbook vs bearish technical/orderflow)
        if "CONFLICTED" in enhanced_synthesis or "conflict" in enhanced_synthesis.lower():
            print("✅ Conflict detection working correctly")
        else:
            print("⚠️  Conflict detection may need review")
            
        return True
        
    except TypeError as e:
        if "takes 2 positional arguments but 3 were given" in str(e):
            print(f"❌ Parameter error still exists: {e}")
            return False
        else:
            print(f"❌ Unexpected TypeError: {e}")
            return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def test_signal_generator_integration():
    """Test that signal generator method signature is correct."""
    print("\nTesting signal generator integration...")
    
    try:
        # Just test that the method signature is correct without instantiating SignalGenerator
        from src.core.interpretation.interpretation_manager import InterpretationManager
        
        interpretation_manager = InterpretationManager()
        
        # Test the method exists and has correct signature
        method = getattr(interpretation_manager, '_generate_enhanced_synthesis', None)
        if method:
            print("✅ _generate_enhanced_synthesis method exists")
            
            # Check method signature (should only take self + interpretation_set)
            import inspect
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            
            if len(params) == 1 and params[0] == 'interpretation_set':
                print("✅ Method signature is correct (only interpretation_set parameter)")
                return True
            else:
                print(f"❌ Method signature incorrect. Parameters: {params}")
                return False
        else:
            print("❌ _generate_enhanced_synthesis method not found")
            return False
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        print(f"Error details: {traceback.format_exc()}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Interpretation Parameter Fixes")
    print("=" * 50)
    
    tests = [
        test_generate_enhanced_synthesis,
        test_signal_generator_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Parameter fixes are working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the fixes.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 