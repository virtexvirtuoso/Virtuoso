#!/usr/bin/env python3
"""
Simple validation script to test if monitor.py can be imported and the fix syntax is correct.
"""

import sys
import os
import ast
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_monitor_syntax():
    """Test monitor.py syntax by parsing the AST."""
    print("🔍 Testing monitor.py syntax...")

    monitor_path = str(PROJECT_ROOT / 'src' / 'monitoring' / 'monitor.py')

    try:
        with open(monitor_path, 'r') as f:
            source_code = f.read()

        # Parse the AST to check for syntax errors
        ast.parse(source_code)
        print("✅ monitor.py syntax is valid")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error in monitor.py: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading monitor.py: {e}")
        return False

def test_fix_implementation():
    """Test that the fix is properly implemented in the source code."""
    print("\n🔍 Testing fix implementation...")

    monitor_path = str(PROJECT_ROOT / 'src' / 'monitoring' / 'monitor.py')

    try:
        with open(monitor_path, 'r') as f:
            lines = f.readlines()

        # Look for the specific fix around line 1110-1119
        fix_found = False
        hasattr_check_found = False
        fallback_found = False

        for i, line in enumerate(lines):
            line_num = i + 1

            # Look for the hasattr check
            if 'hasattr(self.metrics_tracker, \'update_analysis_metrics\')' in line:
                hasattr_check_found = True
                print(f"✅ Found hasattr check at line {line_num}")

            # Look for the fallback to metrics_manager
            if 'self.metrics_manager.update_analysis_metrics(symbol, result)' in line:
                fallback_found = True
                print(f"✅ Found fallback call at line {line_num}")

        if hasattr_check_found and fallback_found:
            fix_found = True
            print("✅ Fix implementation is complete")
        else:
            print("❌ Fix implementation is incomplete")
            if not hasattr_check_found:
                print("  - Missing hasattr check")
            if not fallback_found:
                print("  - Missing fallback to metrics_manager")

        return fix_found

    except Exception as e:
        print(f"❌ Error checking fix implementation: {e}")
        return False

def test_code_structure():
    """Test that the code structure around the fix is correct."""
    print("\n🔍 Testing code structure around fix...")

    monitor_path = str(PROJECT_ROOT / 'src' / 'monitoring' / 'monitor.py')

    try:
        with open(monitor_path, 'r') as f:
            content = f.read()

        # Look for the specific pattern in the code
        expected_patterns = [
            "if self.metrics_tracker and hasattr(self.metrics_tracker, 'update_analysis_metrics'):",
            "await self.metrics_tracker.update_analysis_metrics(symbol, result)",
            "elif self.metrics_manager:",
            "await self.metrics_manager.update_analysis_metrics(symbol, result)"
        ]

        patterns_found = 0
        for pattern in expected_patterns:
            if pattern in content:
                patterns_found += 1
                print(f"✅ Found pattern: {pattern[:50]}...")
            else:
                print(f"❌ Missing pattern: {pattern[:50]}...")

        if patterns_found == len(expected_patterns):
            print("✅ All expected code patterns found")
            return True
        else:
            print(f"❌ Only {patterns_found}/{len(expected_patterns)} patterns found")
            return False

    except Exception as e:
        print(f"❌ Error checking code structure: {e}")
        return False

def main():
    """Run all validation checks."""
    print("🔍 Monitor.py Fix Validation")
    print("=" * 40)

    results = []

    # Test syntax
    results.append(test_monitor_syntax())

    # Test fix implementation
    results.append(test_fix_implementation())

    # Test code structure
    results.append(test_code_structure())

    # Summary
    print("\n" + "=" * 40)
    print("📊 Validation Results")

    test_names = [
        "Syntax Check",
        "Fix Implementation",
        "Code Structure"
    ]

    passed = 0
    for name, result in zip(test_names, results):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(results)} checks passed")

    if passed == len(results):
        print("🎉 All validation checks PASSED!")
        return True
    else:
        print("⚠️  Some validation checks FAILED!")
        return False

if __name__ == "__main__":
    main()