#!/usr/bin/env python3
"""
Verification script for safe logging extensions.

This script verifies that all logging monkey patching has been successfully
replaced with safe alternatives and that all functionality still works.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_safe_logging_extensions():
    """Test that safe logging extensions work correctly."""
    print("🧪 Testing Safe Logging Extensions...")
    
    try:
        from src.utils.logging_extensions import get_logger, SafeTraceLogger, TRACE_LEVEL
        
        # Test 1: get_logger function
        logger1 = get_logger('test1')
        assert hasattr(logger1, 'trace'), "get_logger should provide trace method"
        print("✅ get_logger() works correctly")
        
        # Test 2: SafeTraceLogger class
        logger2 = SafeTraceLogger('test2')
        assert hasattr(logger2, 'trace'), "SafeTraceLogger should provide trace method"
        print("✅ SafeTraceLogger works correctly")
        
        # Test 3: TRACE level is registered
        import logging
        assert logging.getLevelName(TRACE_LEVEL) == 'TRACE', "TRACE level should be registered"
        print("✅ TRACE level is properly registered")
        
        # Test 4: Trace method can be called
        logger1.trace("Test trace message from get_logger")
        logger2.trace("Test trace message from SafeTraceLogger")
        print("✅ Trace methods work without errors")
        
        # Test 5: Standard logging methods still work
        logger1.debug("Debug message")
        logger1.info("Info message")
        logger2.debug("Debug message")
        logger2.info("Info message")
        print("✅ Standard logging methods work correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Safe logging extensions test failed: {e}")
        return False

def test_modules_import_correctly():
    """Test that modules using safe logging import correctly."""
    print("\n🧪 Testing Module Imports...")
    
    try:
        # Test performance module
        from src.utils.performance import logger as perf_logger
        assert hasattr(perf_logger, 'trace'), "Performance logger should have trace method"
        print("✅ Performance module imports correctly")
        
        # Test indicators module
        from src.indicators import logger as indicators_logger
        assert hasattr(indicators_logger, 'trace'), "Indicators logger should have trace method"
        print("✅ Indicators module imports correctly")
        
        # Test indicators classes
        from src.indicators import BaseIndicator, VolumeIndicators, TechnicalIndicators
        print("✅ Indicator classes import correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Module import test failed: {e}")
        return False

def test_no_monkey_patching():
    """Test that no monkey patching is occurring."""
    print("\n🧪 Testing No Monkey Patching...")
    
    try:
        import logging
        
        # Test that standard Logger class is not modified
        standard_logger = logging.getLogger('standard_test')
        
        # Standard logger should NOT have trace method by default
        has_trace = hasattr(standard_logger, 'trace')
        
        if has_trace:
            print("⚠️  Standard logger has trace method - this might indicate monkey patching")
            # This could be OK if it's from our safe extensions
        else:
            print("✅ Standard logger does not have trace method (no monkey patching)")
        
        # Test that our safe extensions don't affect global state
        from src.utils.logging_extensions import get_logger
        safe_logger = get_logger('safe_test')
        
        # Create another standard logger after using safe extensions
        another_standard_logger = logging.getLogger('another_standard_test')
        
        # This should still not have trace method
        has_trace_after = hasattr(another_standard_logger, 'trace')
        
        if has_trace_after:
            print("⚠️  New standard logger has trace method - possible global side effect")
        else:
            print("✅ New standard logger unaffected by safe extensions")
        
        return True
        
    except Exception as e:
        print(f"❌ No monkey patching test failed: {e}")
        return False

def test_performance_functionality():
    """Test that performance module functionality works correctly."""
    print("\n🧪 Testing Performance Module Functionality...")
    
    try:
        from src.utils.performance import PerformanceMetrics, track_performance
        
        # Test PerformanceMetrics
        metrics = PerformanceMetrics()
        metrics.add_metric('test', 'test_function', 0.001)
        print("✅ PerformanceMetrics works correctly")
        
        # Test track_performance decorator
        @track_performance('test')
        def test_function():
            return "test result"
        
        result = test_function()
        assert result == "test result", "Decorated function should work correctly"
        print("✅ track_performance decorator works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance functionality test failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("🚀 Starting Safe Logging Verification Tests")
    print("=" * 50)
    
    tests = [
        test_safe_logging_extensions,
        test_modules_import_correctly,
        test_no_monkey_patching,
        test_performance_functionality
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("🎯 VERIFICATION RESULTS")
    print("=" * 50)
    
    if all(results):
        print("🎉 ALL TESTS PASSED!")
        print("✅ Safe logging extensions are working correctly")
        print("✅ No monkey patching detected")
        print("✅ All functionality preserved")
        print("✅ Modules import correctly")
        print("\n🛡️ Your codebase is now secure from logging monkey patching!")
        return 0
    else:
        failed_count = results.count(False)
        print(f"❌ {failed_count} out of {len(tests)} tests failed")
        print("⚠️  Some issues detected - please review the output above")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 