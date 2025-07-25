#!/usr/bin/env python3
"""
Test to ensure all migrations are complete and working correctly.
"""

import sys
import importlib
import traceback
from pathlib import Path

# Add project root to path
project_root = Path('/Users/ffv_macmini/Desktop/Virtuoso_ccxt')
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all migrated imports work correctly."""
    results = []
    
    print("=== Testing Migrated Imports ===\n")
    
    # Test 1: Error handling imports
    print("1. Testing error handling imports...")
    try:
        from src.core.error.utils import (
            handle_calculation_error, 
            handle_indicator_error, 
            validate_input,
            ConfigurationError,
            ValidationError
        )
        from src.core.error.decorators import handle_errors
        print("✓ Error handling imports successful")
        results.append(("Error handling", True, None))
    except Exception as e:
        print(f"✗ Error handling imports failed: {e}")
        results.append(("Error handling", False, str(e)))
        traceback.print_exc()
    
    # Test 2: Validation imports
    print("\n2. Testing validation imports...")
    try:
        from src.validation.data.analysis_validator import DataValidator
        print("✓ Validation imports successful")
        results.append(("Validation", True, None))
    except Exception as e:
        print(f"✗ Validation imports failed: {e}")
        results.append(("Validation", False, str(e)))
        traceback.print_exc()
    
    # Test 3: Liquidation cache imports
    print("\n3. Testing liquidation cache imports...")
    try:
        from src.core.cache.liquidation_cache import liquidation_cache, LiquidationCache
        print("✓ Liquidation cache imports successful")
        results.append(("Liquidation cache", True, None))
    except Exception as e:
        print(f"✗ Liquidation cache imports failed: {e}")
        results.append(("Liquidation cache", False, str(e)))
        traceback.print_exc()
    
    # Test 4: Verify old imports fail
    print("\n4. Verifying old imports are disabled...")
    old_import_tests = [
        ("src.utils.error_handling", "Error handling"),
        ("src.utils.validation", "Validation"),
        ("src.utils.liquidation_cache", "Liquidation cache"),
    ]
    
    for module_name, description in old_import_tests:
        try:
            importlib.import_module(module_name)
            print(f"✗ Old {description} import still works (should fail!)")
            results.append((f"Old {description} disabled", False, "Module still importable"))
        except ImportError:
            print(f"✓ Old {description} import correctly disabled")
            results.append((f"Old {description} disabled", True, None))
        except Exception as e:
            print(f"✗ Unexpected error for old {description}: {e}")
            results.append((f"Old {description} disabled", False, str(e)))
    
    # Test 5: Test specific module imports
    print("\n5. Testing specific module imports...")
    test_modules = [
        "src.indicators.technical_indicators",
        "src.indicators.volume_indicators",
        "src.monitoring.monitor",
        "src.core.market.data_manager",
        "src.analysis.session_analyzer",
    ]
    
    for module in test_modules:
        try:
            importlib.import_module(module)
            print(f"✓ {module} imports successfully")
            results.append((module, True, None))
        except Exception as e:
            print(f"✗ {module} import failed: {e}")
            results.append((module, False, str(e)))
    
    # Test 6: Check file existence
    print("\n6. Checking file locations...")
    files_to_check = [
        ("src/core/error/utils.py", "Error utils"),
        ("src/validation/data/analysis_validator.py", "Validation"),
        ("src/core/cache/liquidation_cache.py", "Liquidation cache"),
        ("src/utils/error_handling.py.old", "Old error handling backup"),
        ("src/utils/validation.py.old", "Old validation backup"),
        ("src/utils/liquidation_cache.py.old", "Old liquidation cache backup"),
    ]
    
    for file_path, description in files_to_check:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✓ {description} exists at: {file_path}")
            results.append((f"{description} file", True, None))
        else:
            print(f"✗ {description} not found at: {file_path}")
            results.append((f"{description} file", False, "File not found"))
    
    return results

def print_summary(results):
    """Print test summary."""
    print("\n" + "="*50)
    print("=== TEST SUMMARY ===")
    print("="*50 + "\n")
    
    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed
    
    print(f"Total tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\nFailed tests:")
        for name, success, error in results:
            if not success:
                print(f"  - {name}: {error}")
    
    print("\n" + "="*50)
    
    return failed == 0

def main():
    """Run all tests."""
    try:
        results = test_imports()
        all_passed = print_summary(results)
        
        if all_passed:
            print("\n✅ All migration tests passed! The migration is complete and working correctly.")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed. Please check the errors above.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()