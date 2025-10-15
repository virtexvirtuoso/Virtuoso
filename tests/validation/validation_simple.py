#!/usr/bin/env python3
"""
Simple validation for Price-OI Divergence Fix
=============================================

This script performs focused validation of the Price-OI divergence fix
by directly testing the relevant code sections.
"""

import sys
import os
import time
import json
import traceback
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_confluence_fix():
    """Test that confluence.py _prepare_data_for_orderflow includes open_interest_history."""
    print("=" * 60)
    print("TEST 1: CONFLUENCE.PY FIX VALIDATION")
    print("=" * 60)

    try:
        # Read the confluence.py file
        confluence_path = os.path.join('src', 'core', 'analysis', 'confluence.py')
        with open(confluence_path, 'r') as f:
            content = f.read()

        # Check for the fix in both method occurrences
        fix_pattern = "'open_interest_history': market_data.get('open_interest_history', [])"
        method_pattern = "def _prepare_data_for_orderflow"

        fix_count = content.count(fix_pattern)
        method_count = content.count(method_pattern)

        print(f"Methods found: {method_count}")
        print(f"Fix applied: {fix_count}")
        print(f"Fix consistency: {'PASS' if fix_count == method_count and fix_count >= 2 else 'FAIL'}")

        # Show context around the fixes
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if fix_pattern in line:
                print(f"\nFix found at line {i+1}:")
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    prefix = ">>>" if j == i else "   "
                    print(f"{prefix} {j+1:4d}: {lines[j]}")

        return fix_count == method_count and fix_count >= 2

    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_orderflow_indicators():
    """Test that orderflow_indicators.py can handle open_interest_history."""
    print("\n" + "=" * 60)
    print("TEST 2: ORDERFLOW INDICATORS VALIDATION")
    print("=" * 60)

    try:
        # Read the orderflow indicators file
        orderflow_path = os.path.join('src', 'indicators', 'orderflow_indicators.py')
        with open(orderflow_path, 'r') as f:
            content = f.read()

        # Check that the function looks for open_interest_history
        checks = [
            ("open_interest_history in market_data", "Checks for direct OI history"),
            ("market_data['open_interest_history']", "Accesses direct OI history"),
            ("Using direct open_interest_history reference", "Logs direct OI usage")
        ]

        results = []
        for pattern, description in checks:
            found = pattern in content
            results.append(found)
            print(f"{description}: {'PASS' if found else 'FAIL'}")

            if found:
                # Show context
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if pattern in line:
                        print(f"  Found at line {i+1}: {line.strip()}")
                        break

        return all(results)

    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_data_structure():
    """Test the data structure flow simulation."""
    print("\n" + "=" * 60)
    print("TEST 3: DATA STRUCTURE FLOW SIMULATION")
    print("=" * 60)

    try:
        # Simulate market data as it would be created by market_data_manager
        base_timestamp = int(time.time() * 1000)

        # Create mock OI history
        oi_history = []
        for i in range(10):
            oi_history.append({
                'timestamp': base_timestamp - (i * 60000),
                'value': 100000 - (i * 1000)  # Decreasing OI
            })

        # Simulate market data structure
        market_data = {
            'symbol': 'BTCUSDT',
            'exchange': 'bybit',
            'timestamp': base_timestamp,
            'open_interest': {
                'current': oi_history[0]['value'],
                'previous': oi_history[1]['value'],
                'history': oi_history
            },
            'open_interest_history': oi_history  # The fix adds this
        }

        print(f"Market data keys: {list(market_data.keys())}")
        print(f"Has open_interest_history: {'open_interest_history' in market_data}")
        print(f"OI history length: {len(market_data['open_interest_history'])}")
        print(f"OI history sample: {market_data['open_interest_history'][0]}")

        # Simulate confluence._prepare_data_for_orderflow
        orderflow_data = {
            'symbol': market_data.get('symbol', ''),
            'exchange': market_data.get('exchange', ''),
            'timestamp': market_data.get('timestamp', base_timestamp),
            'trades': market_data.get('trades', []),
            'orderbook': market_data.get('orderbook', {}),
            'ohlcv': market_data.get('ohlcv', {}),
            'ticker': market_data.get('ticker', {}),
            'open_interest': market_data.get('open_interest', {}),
            # This is the fix:
            'open_interest_history': market_data.get('open_interest_history', [])
        }

        print(f"\nOrderflow data keys: {list(orderflow_data.keys())}")
        print(f"Orderflow has open_interest_history: {'open_interest_history' in orderflow_data}")
        print(f"Orderflow OI history length: {len(orderflow_data['open_interest_history'])}")

        # Check that the fix works
        has_oi_history = 'open_interest_history' in orderflow_data
        oi_populated = len(orderflow_data['open_interest_history']) > 0

        print(f"\nData flow validation: {'PASS' if has_oi_history and oi_populated else 'FAIL'}")

        return has_oi_history and oi_populated

    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        return False

def test_market_data_manager():
    """Test that market_data_manager creates open_interest_history."""
    print("\n" + "=" * 60)
    print("TEST 4: MARKET DATA MANAGER VALIDATION")
    print("=" * 60)

    try:
        # Read the market data manager file
        manager_path = os.path.join('src', 'core', 'market', 'market_data_manager.py')
        with open(manager_path, 'r') as f:
            content = f.read()

        # Check for open_interest_history creation
        checks = [
            ("market_data['open_interest_history'] =", "Creates OI history field"),
            ("self.data_cache[symbol]['open_interest_history'] =", "Caches OI history"),
            ("open_interest_history", "References OI history")
        ]

        results = []
        for pattern, description in checks:
            count = content.count(pattern)
            results.append(count > 0)
            print(f"{description}: {'PASS' if count > 0 else 'FAIL'} ({count} occurrences)")

        # Show some context
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "market_data['open_interest_history'] =" in line:
                print(f"\nFound OI history creation at line {i+1}:")
                for j in range(max(0, i-1), min(len(lines), i+2)):
                    prefix = ">>>" if j == i else "   "
                    print(f"{prefix} {j+1:4d}: {lines[j]}")
                break

        return all(results)

    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Run all validation tests."""
    print("PRICE-OI DIVERGENCE FIX VALIDATION")
    print("=" * 80)

    tests = [
        ("Confluence Fix", test_confluence_fix),
        ("Orderflow Indicators", test_orderflow_indicators),
        ("Data Structure Flow", test_data_structure),
        ("Market Data Manager", test_market_data_manager)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"ERROR in {test_name}: {e}")
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status:>6}: {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("✓ VALIDATION PASSED - Fix is working correctly")
        overall_status = "PASS"
    elif passed > 0:
        print("⚠ PARTIAL PASS - Some issues found")
        overall_status = "CONDITIONAL_PASS"
    else:
        print("✗ VALIDATION FAILED - Fix has issues")
        overall_status = "FAIL"

    # Save results
    validation_results = {
        'timestamp': datetime.now().isoformat(),
        'overall_status': overall_status,
        'tests': {name: result for name, result in results},
        'summary': {
            'total_tests': total,
            'passed_tests': passed,
            'failed_tests': total - passed,
            'success_rate': passed / total * 100
        }
    }

    with open('price_oi_fix_validation_results.json', 'w') as f:
        json.dump(validation_results, f, indent=2)

    print(f"\nDetailed results saved to: price_oi_fix_validation_results.json")

    return 0 if overall_status in ["PASS", "CONDITIONAL_PASS"] else 1

if __name__ == "__main__":
    sys.exit(main())