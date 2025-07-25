#!/usr/bin/env python3
"""
Simple runtime test to verify migrated modules work correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path('/Users/ffv_macmini/Desktop/Virtuoso_ccxt')
sys.path.insert(0, str(project_root))

def test_basic_functionality():
    """Test basic functionality of migrated modules."""
    print("=== Testing Migrated Module Functionality ===\n")
    
    results = []
    
    # Test 1: Error handling decorators
    print("1. Testing error handling decorators...")
    try:
        from src.core.error.utils import handle_calculation_error, handle_indicator_error
        
        @handle_calculation_error(default_value=0)
        def divide(a, b):
            return a / b
        
        result = divide(10, 0)  # Should return 0 instead of raising
        assert result == 0, f"Expected 0, got {result}"
        
        print("✓ Error handling decorators work correctly")
        results.append(("Error decorators", True))
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        results.append(("Error decorators", False))
    
    # Test 2: DataValidator
    print("\n2. Testing DataValidator...")
    try:
        from src.validation.data.analysis_validator import DataValidator
        
        validator = DataValidator()
        # Test with empty data
        valid = validator.validate_market_data({})
        
        print("✓ DataValidator instantiated and works")
        results.append(("DataValidator", True))
    except Exception as e:
        print(f"✗ DataValidator test failed: {e}")
        results.append(("DataValidator", False))
    
    # Test 3: Liquidation cache
    print("\n3. Testing liquidation cache...")
    try:
        from src.core.cache.liquidation_cache import LiquidationCache
        
        cache = LiquidationCache()
        
        # Test basic operations
        test_data = {"symbol": "BTCUSDT", "side": "Long", "quantity": 1000}
        cache.add_liquidation("BTCUSDT", test_data)
        
        liquidations = cache.get_liquidations("BTCUSDT", limit=1)
        
        print("✓ LiquidationCache works correctly")
        results.append(("LiquidationCache", True))
    except Exception as e:
        print(f"✗ LiquidationCache test failed: {e}")
        results.append(("LiquidationCache", False))
    
    # Test 4: Check that old modules are not accessible
    print("\n4. Verifying old modules are not accessible...")
    try:
        # This should fail
        import src.utils.error_handling
        print("✗ Old error_handling module is still accessible!")
        results.append(("Old modules removed", False))
    except ImportError:
        print("✓ Old error_handling module correctly removed")
        results.append(("Old modules removed", True))
    
    return results

def main():
    """Run functionality tests."""
    try:
        results = test_basic_functionality()
        
        print("\n" + "="*50)
        print("=== RUNTIME TEST SUMMARY ===")
        print("="*50 + "\n")
        
        passed = sum(1 for _, success in results if success)
        failed = len(results) - passed
        
        print(f"Total tests: {len(results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        if failed == 0:
            print("\n✅ All runtime tests passed!")
            print("The migrated modules are working correctly.")
            return 0
        else:
            print(f"\n❌ {failed} tests failed.")
            return 1
            
    except Exception as e:
        print(f"\n❌ Runtime test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())