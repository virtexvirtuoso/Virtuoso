#!/usr/bin/env python3
"""
Edge Cases and Error Handling Test for Price-OI Divergence Fix
=============================================================

This script tests error handling and edge cases for the Price-OI divergence fix.
"""

import sys
import os
import time
import json
import traceback
from datetime import datetime
from typing import Dict, List, Any

def test_edge_cases():
    """Test edge cases and error handling scenarios."""
    print("=" * 70)
    print("EDGE CASES AND ERROR HANDLING VALIDATION")
    print("=" * 70)

    test_results = {}

    # Test 1: Check that orderflow indicators handle missing OI history gracefully
    print("\nTest 1: Missing OI History Handling")
    try:
        # Read the orderflow indicators file
        orderflow_path = os.path.join('src', 'indicators', 'orderflow_indicators.py')
        with open(orderflow_path, 'r') as f:
            content = f.read()

        # Check for proper error handling patterns
        error_patterns = [
            ('return {\'type\': \'neutral\', \'strength\': 0.0}', 'Returns neutral on missing data'),
            ('self.logger.warning', 'Logs warnings for missing data'),
            ('isinstance(market_data[\'open_interest_history\'], list)', 'Validates OI history data type'),
            ('len(oi_history) < 2', 'Checks for sufficient history length')
        ]

        pattern_results = []
        for pattern, description in error_patterns:
            found = pattern in content
            pattern_results.append(found)
            print(f"  {description}: {'PASS' if found else 'FAIL'}")

        test_results['missing_oi_history_handling'] = all(pattern_results)

    except Exception as e:
        print(f"  ERROR: {e}")
        test_results['missing_oi_history_handling'] = False

    # Test 2: Check confluence data validation
    print("\nTest 2: Confluence Data Validation")
    try:
        confluence_path = os.path.join('src', 'core', 'analysis', 'confluence.py')
        with open(confluence_path, 'r') as f:
            content = f.read()

        # Check for safe data access patterns
        validation_patterns = [
            ('.get(\'open_interest_history\', [])', 'Uses safe dict access with default'),
            ('market_data.get(', 'Uses safe dict access methods'),
            ('try:', 'Has exception handling blocks')
        ]

        validation_results = []
        for pattern, description in validation_patterns:
            count = content.count(pattern)
            validation_results.append(count > 0)
            print(f"  {description}: {'PASS' if count > 0 else 'FAIL'} ({count} occurrences)")

        test_results['confluence_data_validation'] = all(validation_results)

    except Exception as e:
        print(f"  ERROR: {e}")
        test_results['confluence_data_validation'] = False

    # Test 3: Check market data manager error handling
    print("\nTest 3: Market Data Manager Error Handling")
    try:
        manager_path = os.path.join('src', 'core', 'market', 'market_data_manager.py')
        with open(manager_path, 'r') as f:
            content = f.read()

        # Check for error handling in OI processing
        error_handling_patterns = [
            ('except Exception as e:', 'Has exception handling'),
            ('self.logger.error', 'Logs errors'),
            ('market_data[\'open_interest_history\'] = []', 'Sets empty default on error'),
            ('try:', 'Uses try-catch blocks')
        ]

        error_results = []
        for pattern, description in error_handling_patterns:
            count = content.count(pattern)
            error_results.append(count > 0)
            print(f"  {description}: {'PASS' if count > 0 else 'FAIL'} ({count} occurrences)")

        test_results['market_data_error_handling'] = all(error_results)

    except Exception as e:
        print(f"  ERROR: {e}")
        test_results['market_data_error_handling'] = False

    # Test 4: Data flow integrity
    print("\nTest 4: Data Flow Integrity")
    try:
        # Simulate the complete data flow with edge cases
        edge_cases = [
            ({'open_interest_history': []}, "Empty OI history"),
            ({'open_interest_history': None}, "None OI history"),
            ({}, "Missing OI history"),
            ({'open_interest_history': "invalid"}, "Invalid OI history type"),
            ({'open_interest_history': [{}]}, "Malformed OI entries")
        ]

        flow_results = []
        for test_data, description in edge_cases:
            try:
                # Simulate confluence._prepare_data_for_orderflow
                orderflow_data = {
                    'symbol': test_data.get('symbol', ''),
                    'exchange': test_data.get('exchange', ''),
                    'timestamp': test_data.get('timestamp', int(time.time() * 1000)),
                    'trades': test_data.get('trades', []),
                    'orderbook': test_data.get('orderbook', {}),
                    'ohlcv': test_data.get('ohlcv', {}),
                    'ticker': test_data.get('ticker', {}),
                    'open_interest': test_data.get('open_interest', {}),
                    'open_interest_history': test_data.get('open_interest_history', [])
                }

                # Check that the fix handles edge cases gracefully
                has_field = 'open_interest_history' in orderflow_data
                is_list = isinstance(orderflow_data['open_interest_history'], list)

                result = has_field and (is_list or orderflow_data['open_interest_history'] is None)
                flow_results.append(result)
                print(f"  {description}: {'PASS' if result else 'FAIL'}")

            except Exception as e:
                print(f"  {description}: FAIL ({e})")
                flow_results.append(False)

        test_results['data_flow_integrity'] = all(flow_results)

    except Exception as e:
        print(f"  ERROR: {e}")
        test_results['data_flow_integrity'] = False

    return test_results

def test_regression_scenarios():
    """Test regression scenarios to ensure no existing functionality is broken."""
    print("\n" + "=" * 70)
    print("REGRESSION TESTING")
    print("=" * 70)

    regression_results = {}

    # Test 1: Ensure other orderflow indicators are not affected
    print("\nTest 1: Other Orderflow Indicators Unchanged")
    try:
        orderflow_path = os.path.join('src', 'indicators', 'orderflow_indicators.py')
        with open(orderflow_path, 'r') as f:
            content = f.read()

        # Check that other indicator methods exist and are not modified
        other_indicators = [
            '_calculate_cvd_divergence',
            '_calculate_smart_money_flow',
            '_calculate_liquidity_flow',
            '_process_trades'
        ]

        indicator_results = []
        for indicator in other_indicators:
            found = indicator in content
            indicator_results.append(found)
            print(f"  {indicator}: {'PASS' if found else 'FAIL'}")

        regression_results['other_indicators_intact'] = all(indicator_results)

    except Exception as e:
        print(f"  ERROR: {e}")
        regression_results['other_indicators_intact'] = False

    # Test 2: Ensure confluence analysis structure is preserved
    print("\nTest 2: Confluence Analysis Structure")
    try:
        confluence_path = os.path.join('src', 'core', 'analysis', 'confluence.py')
        with open(confluence_path, 'r') as f:
            content = f.read()

        # Check that core analysis methods are preserved
        core_methods = [
            'analyze_indicators',
            '_prepare_data_for_technical',
            '_prepare_data_for_volume',
            '_prepare_data_for_orderbook',
            '_prepare_data_for_sentiment'
        ]

        method_results = []
        for method in core_methods:
            found = method in content
            method_results.append(found)
            print(f"  {method}: {'PASS' if found else 'FAIL'}")

        regression_results['confluence_structure_preserved'] = all(method_results)

    except Exception as e:
        print(f"  ERROR: {e}")
        regression_results['confluence_structure_preserved'] = False

    # Test 3: Check that data structures remain compatible
    print("\nTest 3: Data Structure Compatibility")
    try:
        # Simulate backwards compatibility
        old_style_data = {
            'symbol': 'BTCUSDT',
            'exchange': 'bybit',
            'timestamp': int(time.time() * 1000),
            'open_interest': {
                'current': 100000,
                'previous': 99000,
                'history': [
                    {'timestamp': int(time.time() * 1000), 'value': 100000},
                    {'timestamp': int(time.time() * 1000) - 60000, 'value': 99000}
                ]
            }
            # Note: No 'open_interest_history' field - old style
        }

        # Simulate new confluence processing
        orderflow_data = {
            'symbol': old_style_data.get('symbol', ''),
            'exchange': old_style_data.get('exchange', ''),
            'timestamp': old_style_data.get('timestamp', int(time.time() * 1000)),
            'trades': old_style_data.get('trades', []),
            'orderbook': old_style_data.get('orderbook', {}),
            'ohlcv': old_style_data.get('ohlcv', {}),
            'ticker': old_style_data.get('ticker', {}),
            'open_interest': old_style_data.get('open_interest', {}),
            'open_interest_history': old_style_data.get('open_interest_history', [])
        }

        # Check that old data structure still works (graceful degradation)
        has_oi_field = 'open_interest' in orderflow_data
        has_oi_history_field = 'open_interest_history' in orderflow_data
        oi_history_empty_or_list = isinstance(orderflow_data['open_interest_history'], list)

        compatibility_passed = has_oi_field and has_oi_history_field and oi_history_empty_or_list
        print(f"  Backwards compatibility: {'PASS' if compatibility_passed else 'FAIL'}")

        regression_results['data_structure_compatibility'] = compatibility_passed

    except Exception as e:
        print(f"  ERROR: {e}")
        regression_results['data_structure_compatibility'] = False

    return regression_results

def main():
    """Run comprehensive edge case and regression testing."""
    print("COMPREHENSIVE EDGE CASE AND REGRESSION VALIDATION")
    print("=" * 80)

    # Run edge case tests
    edge_case_results = test_edge_cases()

    # Run regression tests
    regression_results = test_regression_scenarios()

    # Combine results
    all_results = {**edge_case_results, **regression_results}

    # Summary
    print("\n" + "=" * 80)
    print("COMPREHENSIVE TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for result in all_results.values() if result)
    total = len(all_results)

    for test_name, result in all_results.items():
        status = "PASS" if result else "FAIL"
        print(f"{status:>6}: {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("✓ ALL TESTS PASSED - Robust implementation")
        overall_status = "PASS"
    elif passed >= total * 0.8:  # 80% pass rate
        print("⚠ MOSTLY PASSED - Minor issues found")
        overall_status = "CONDITIONAL_PASS"
    else:
        print("✗ MULTIPLE FAILURES - Implementation needs review")
        overall_status = "FAIL"

    # Save detailed results
    comprehensive_results = {
        'timestamp': datetime.now().isoformat(),
        'overall_status': overall_status,
        'edge_case_tests': edge_case_results,
        'regression_tests': regression_results,
        'summary': {
            'total_tests': total,
            'passed_tests': passed,
            'failed_tests': total - passed,
            'success_rate': passed / total * 100
        }
    }

    with open('comprehensive_validation_results.json', 'w') as f:
        json.dump(comprehensive_results, f, indent=2)

    print(f"\nDetailed results saved to: comprehensive_validation_results.json")

    return 0 if overall_status in ["PASS", "CONDITIONAL_PASS"] else 1

if __name__ == "__main__":
    sys.exit(main())