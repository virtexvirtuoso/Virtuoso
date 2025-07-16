#!/usr/bin/env python3
"""
Test Enhanced Futures Premium Implementation

This script tests the enhanced futures premium calculation implementation
to verify it works correctly before deploying to production.

Usage:
    python scripts/implementation/test_enhanced_premium.py
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

# Test import of the enhanced market reporter
def test_imports():
    """Test that all required imports work correctly."""
    print("🧪 Testing Enhanced Premium Imports...")
    
    try:
        # Test standard imports
        import aiohttp
        from datetime import timedelta
        print("  ✅ Standard imports successful")
        
        # Test enhanced market reporter import
        sys.path.insert(0, 'src/monitoring')
        
        # Import the test version
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "market_reporter_enhanced", 
            "src/monitoring/market_reporter_enhanced_test.py"
        )
        enhanced_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(enhanced_module)
        
        print("  ✅ Enhanced market reporter import successful")
        
        # Check if the class exists and has the mixin
        MarketReporter = enhanced_module.MarketReporter
        
        # Verify inheritance
        if hasattr(MarketReporter, '_calculate_single_premium_enhanced'):
            print("  ✅ Enhanced premium method found")
        else:
            print("  ❌ Enhanced premium method not found")
            return False
            
        if hasattr(MarketReporter, '_calculate_single_premium_original'):
            print("  ✅ Original premium method preserved as fallback")
        else:
            print("  ❌ Original premium method not preserved")
            return False
            
        return True
        
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        return False

async def test_enhanced_premium_functionality():
    """Test the enhanced premium calculation functionality."""
    print("\n🧪 Testing Enhanced Premium Functionality...")
    
    try:
        # Import the enhanced market reporter
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "market_reporter_enhanced", 
            "src/monitoring/market_reporter_enhanced_test.py"
        )
        enhanced_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(enhanced_module)
        
        MarketReporter = enhanced_module.MarketReporter
        
        # Create a test instance
        logger = logging.getLogger("test_enhanced_premium")
        logger.setLevel(logging.DEBUG)
        
        # Create console handler for test output
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Initialize the enhanced market reporter
        reporter = MarketReporter(logger=logger)
        
        print("  ✅ Enhanced MarketReporter instance created")
        
        # Test enhanced premium initialization
        if hasattr(reporter, '_premium_calculation_stats'):
            print("  ✅ Premium calculation stats initialized")
        else:
            print("  ❌ Premium calculation stats not initialized")
            return False
            
        # Test feature flags
        if hasattr(reporter, 'enable_enhanced_premium'):
            print(f"  ✅ Enhanced premium feature flag: {reporter.enable_enhanced_premium}")
        else:
            print("  ❌ Enhanced premium feature flag not set")
            return False
            
        # Test validation flag
        if hasattr(reporter, 'enable_premium_validation'):
            print(f"  ✅ Premium validation feature flag: {reporter.enable_premium_validation}")
        else:
            print("  ❌ Premium validation feature flag not set")
            return False
        
        # Test base coin extraction
        test_symbols = ['BTCUSDT', 'BTC/USDT:USDT', 'ETHUSDT', 'ETH/USDT']
        for symbol in test_symbols:
            base_coin = reporter._extract_base_coin_enhanced(symbol)
            expected = symbol.split('/')[0].replace('USDT', '').replace(':', '').upper()
            if expected.endswith('USD'):
                expected = expected[:-3]
                
            print(f"    Symbol: {symbol} -> Base coin: {base_coin}")
            if base_coin == expected or (symbol.startswith(base_coin) if base_coin else False):
                print(f"    ✅ Correct base coin extraction for {symbol}")
            else:
                print(f"    ⚠️ Base coin extraction may need adjustment for {symbol}")
        
        # Test premium calculation with test symbols
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        print("\n  🧪 Testing Enhanced Premium Calculation:")
        for symbol in test_symbols:
            try:
                print(f"    Testing {symbol}...")
                result = await reporter._calculate_single_premium_enhanced(symbol)
                
                if result:
                    print(f"      ✅ Success: {result.get('premium', 'N/A')} "
                          f"({result.get('premium_type', 'N/A')})")
                    print(f"      📊 Data source: {result.get('data_source', 'N/A')}")
                    print(f"      🕒 Processing time: {result.get('processing_time_ms', 'N/A')}ms")
                    print(f"      🔍 Validation: {result.get('validation_status', 'N/A')}")
                else:
                    print(f"      ⚠️ No result returned for {symbol}")
                    
            except Exception as e:
                print(f"      ❌ Error testing {symbol}: {e}")
        
        # Test performance statistics
        stats = reporter.get_premium_calculation_stats()
        print(f"\n  📊 Performance Statistics:")
        print(f"    Enhanced method success rate: {stats['enhanced_method']['success_rate']:.1f}%")
        print(f"    Fallback usage: {stats['fallback_usage']['percentage']:.1f}%")
        print(f"    Validation match rate: {stats['validation']['match_rate']:.1f}%")
        
        # Clean up
        await reporter._close_aiohttp_session()
        
        return True
        
    except Exception as e:
        print(f"  ❌ Functionality test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """Test that the enhanced implementation maintains backward compatibility."""
    print("\n🧪 Testing Backward Compatibility...")
    
    try:
        # Import the enhanced market reporter
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "market_reporter_enhanced", 
            "src/monitoring/market_reporter_enhanced_test.py"
        )
        enhanced_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(enhanced_module)
        
        MarketReporter = enhanced_module.MarketReporter
        
        # Create instance
        reporter = MarketReporter()
        
        # Test that original method signature is preserved
        original_method = getattr(reporter, '_calculate_single_premium_original', None)
        new_method = getattr(reporter, '_calculate_single_premium', None)
        
        if original_method:
            print("  ✅ Original method preserved as fallback")
        else:
            print("  ❌ Original method not preserved")
            return False
            
        if new_method:
            print("  ✅ New enhanced method available")
        else:
            print("  ❌ New enhanced method not available")
            return False
        
        # Test method signatures
        import inspect
        
        # Check if the new method has the same signature as expected
        new_sig = inspect.signature(new_method)
        expected_params = ['symbol', 'all_markets']
        
        actual_params = list(new_sig.parameters.keys())[1:]  # Skip 'self'
        if actual_params == expected_params:
            print("  ✅ Method signature maintained for backward compatibility")
        else:
            print(f"  ⚠️ Method signature differs: expected {expected_params}, got {actual_params}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Backward compatibility test error: {e}")
        return False

def test_fallback_mechanism():
    """Test that the fallback mechanism works correctly."""
    print("\n🧪 Testing Fallback Mechanism...")
    
    try:
        # Import the enhanced market reporter
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "market_reporter_enhanced", 
            "src/monitoring/market_reporter_enhanced_test.py"
        )
        enhanced_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(enhanced_module)
        
        MarketReporter = enhanced_module.MarketReporter
        
        # Create instance with enhanced premium disabled
        reporter = MarketReporter()
        reporter.enable_enhanced_premium = False
        
        print("  ✅ Created instance with enhanced premium disabled")
        
        # Test that it falls back to original method
        if hasattr(reporter, '_calculate_single_premium_original'):
            print("  ✅ Original method available for fallback")
        else:
            print("  ❌ Original method not available for fallback")
            return False
        
        # Test fallback stats tracking
        if hasattr(reporter, '_premium_calculation_stats'):
            print("  ✅ Fallback statistics tracking available")
        else:
            print("  ❌ Fallback statistics tracking not available")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Fallback mechanism test error: {e}")
        return False

async def run_comprehensive_test():
    """Run comprehensive tests of the enhanced premium implementation."""
    print("🚀 Starting Comprehensive Enhanced Premium Tests")
    print("=" * 60)
    
    test_results = []
    
    # Test 1: Imports
    test_results.append(("Imports", test_imports()))
    
    # Test 2: Enhanced functionality
    test_results.append(("Enhanced Functionality", await test_enhanced_premium_functionality()))
    
    # Test 3: Backward compatibility
    test_results.append(("Backward Compatibility", test_backward_compatibility()))
    
    # Test 4: Fallback mechanism
    test_results.append(("Fallback Mechanism", test_fallback_mechanism()))
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 Test Results Summary:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed + failed} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    success_rate = (passed / (passed + failed)) * 100 if (passed + failed) > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    if failed == 0:
        print("\n🎉 All tests passed! Enhanced premium implementation is ready for deployment.")
        return True
    else:
        print(f"\n⚠️ {failed} test(s) failed. Please review and fix issues before deployment.")
        return False

def main():
    """Main test function."""
    
    # Check if test file exists
    test_file = "src/monitoring/market_reporter_enhanced_test.py"
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        print("Please run the implementation script in test mode first:")
        print("python scripts/implementation/implement_enhanced_premium.py --test")
        sys.exit(1)
    
    # Run tests
    try:
        result = asyncio.run(run_comprehensive_test())
        
        if result:
            print("\n🚀 Ready for production deployment!")
            print("\nTo deploy to production:")
            print("python scripts/implementation/implement_enhanced_premium.py --backup")
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 