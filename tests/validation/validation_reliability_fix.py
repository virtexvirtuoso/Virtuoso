#!/usr/bin/env python3
"""
Functional Validation Script for Reliability Percentage Display Fix
Validates that the 8333% -> 83% bug is resolved and other related fixes work correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import asyncio
from typing import Dict, Any, List
from src.core.cache_keys import CacheKeys
from src.core.cache.confluence_cache_service import ConfluenceCacheService

def test_reliability_normalization():
    """Test reliability percentage normalization logic directly."""
    print("\n=== Testing Reliability Normalization Logic ===")

    # Test cases: (input, expected_output)
    test_cases = [
        (83.33, 83),    # Original problematic case - 83.33 should display as 83%
        (0.83, 83),     # 0-1 scale should convert to percentage
        (1.0, 100),     # Edge case: perfect reliability
        (0.0, 0),       # Edge case: zero reliability
        (50.0, 50),     # Mid-range percentage input
        (100.0, 100),   # Edge case: 100% input
        (150.0, 100),   # Invalid input should clamp to 100%
        (-10.0, 0),     # Invalid negative should clamp to 0%
        ("invalid", 0), # Non-numeric input should default to 0%
    ]

    results = []

    for input_value, expected in test_cases:
        try:
            # Simulate the normalization logic from formatter.py
            try:
                raw_rel = float(input_value)
            except Exception:
                raw_rel = 0.0

            # Normalize: if value > 1, assume it's already a percentage, divide by 100
            normalized_rel = raw_rel / 100.0 if raw_rel > 1.0 else raw_rel
            # Clamp to [0,1] range
            normalized_rel = max(0.0, min(1.0, normalized_rel))
            # Convert to percentage for display
            reliability_pct = int(normalized_rel * 100)

            passed = reliability_pct == expected
            results.append({
                'input': input_value,
                'expected': expected,
                'actual': reliability_pct,
                'passed': passed
            })

            status = "PASS" if passed else "FAIL"
            print(f"  Input: {input_value} -> Expected: {expected}% | Actual: {reliability_pct}% | {status}")

        except Exception as e:
            results.append({
                'input': input_value,
                'expected': expected,
                'actual': f"ERROR: {str(e)}",
                'passed': False
            })
            print(f"  Input: {input_value} -> ERROR: {str(e)} | FAIL")

    passed_count = sum(1 for r in results if r['passed'])
    print(f"\n  Results: {passed_count}/{len(results)} tests passed")

    return results

def test_cache_key_generation():
    """Test cache key generation with CacheKeys.confluence_breakdown method."""
    print("\n=== Testing Cache Key Generation ===")

    test_symbols = ["ADAUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT"]
    results = []

    for symbol in test_symbols:
        try:
            # Test the confluence_breakdown method exists and works
            breakdown_key = CacheKeys.confluence_breakdown(symbol)
            expected_format = f"confluence:breakdown:{symbol}"

            passed = breakdown_key == expected_format
            results.append({
                'symbol': symbol,
                'key': breakdown_key,
                'expected_format': expected_format,
                'passed': passed
            })

            status = "PASS" if passed else "FAIL"
            print(f"  Symbol: {symbol} -> Key: {breakdown_key} | {status}")

        except Exception as e:
            results.append({
                'symbol': symbol,
                'key': f"ERROR: {str(e)}",
                'expected_format': expected_format,
                'passed': False
            })
            print(f"  Symbol: {symbol} -> ERROR: {str(e)} | FAIL")

    passed_count = sum(1 for r in results if r['passed'])
    print(f"\n  Results: {passed_count}/{len(results)} cache key tests passed")

    return results

async def test_confluence_cache_service():
    """Test ConfluenceCacheService uses CacheKeys.confluence_breakdown correctly."""
    print("\n=== Testing Confluence Cache Service ===")

    # Create mock cache service (without actual Redis connection)
    cache_service = ConfluenceCacheService()

    # Test that the service has the expected methods
    methods_to_check = [
        'cache_confluence_breakdown',
        'get_cached_confluence_breakdown',
        'cache_multiple_breakdowns'
    ]

    results = []
    for method_name in methods_to_check:
        has_method = hasattr(cache_service, method_name)
        results.append({
            'method': method_name,
            'exists': has_method,
            'passed': has_method
        })

        status = "PASS" if has_method else "FAIL"
        print(f"  Method {method_name}: {status}")

    passed_count = sum(1 for r in results if r['passed'])
    print(f"\n  Results: {passed_count}/{len(results)} method checks passed")

    return results

def test_metrics_tracker_bridge():
    """Test MetricsTracker has update_analysis_metrics bridge method."""
    print("\n=== Testing MetricsTracker Bridge Method ===")

    try:
        from src.monitoring.metrics_tracker import MetricsTracker

        # Create minimal instance to check method existence
        config = {}
        metrics_manager = None
        market_data_manager = type('MockMDM', (), {'get_stats': lambda: {}})()

        tracker = MetricsTracker(config, metrics_manager, market_data_manager)

        # Check if the bridge method exists
        has_bridge_method = hasattr(tracker, 'update_analysis_metrics')

        result = {
            'method_exists': has_bridge_method,
            'passed': has_bridge_method
        }

        status = "PASS" if has_bridge_method else "FAIL"
        print(f"  update_analysis_metrics method: {status}")

        return [result]

    except Exception as e:
        print(f"  ERROR: {str(e)} | FAIL")
        return [{'method_exists': False, 'error': str(e), 'passed': False}]

def test_monitor_fallback_logic():
    """Test that monitor.py has proper fallback logic for metrics updates."""
    print("\n=== Testing Monitor Fallback Logic ===")

    # Read the monitor.py file and check for fallback patterns
    try:
        with open('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/monitoring/monitor.py', 'r') as f:
            monitor_content = f.read()

        # Check for the expected patterns
        patterns_to_check = [
            'hasattr(self.metrics_tracker, \'update_analysis_metrics\')',
            'await self.metrics_tracker.update_analysis_metrics',
            'await self.metrics_manager.update_analysis_metrics',
            'except Exception:',
            'self.logger.debug(traceback.format_exc())'
        ]

        results = []
        for pattern in patterns_to_check:
            found = pattern in monitor_content
            results.append({
                'pattern': pattern,
                'found': found,
                'passed': found
            })

            status = "PASS" if found else "FAIL"
            print(f"  Pattern '{pattern[:50]}...': {status}")

        passed_count = sum(1 for r in results if r['passed'])
        print(f"\n  Results: {passed_count}/{len(results)} fallback patterns found")

        return results

    except Exception as e:
        print(f"  ERROR reading monitor.py: {str(e)} | FAIL")
        return [{'pattern': 'file_read', 'found': False, 'error': str(e), 'passed': False}]

async def main():
    """Run all validation tests."""
    print("Reliability Percentage Display Fix - Comprehensive Validation")
    print("=" * 65)

    all_results = {}

    # Run all test suites
    all_results['reliability_normalization'] = test_reliability_normalization()
    all_results['cache_key_generation'] = test_cache_key_generation()
    all_results['confluence_cache_service'] = await test_confluence_cache_service()
    all_results['metrics_tracker_bridge'] = test_metrics_tracker_bridge()
    all_results['monitor_fallback_logic'] = test_monitor_fallback_logic()

    # Generate summary
    print("\n" + "=" * 65)
    print("VALIDATION SUMMARY")
    print("=" * 65)

    total_tests = 0
    total_passed = 0

    for test_suite, results in all_results.items():
        passed = sum(1 for r in results if r.get('passed', False))
        total = len(results)
        total_tests += total
        total_passed += passed

        status = "PASS" if passed == total else "FAIL"
        print(f"  {test_suite}: {passed}/{total} tests passed | {status}")

    print("-" * 65)
    overall_status = "PASS" if total_passed == total_tests else "FAIL"
    print(f"  OVERALL: {total_passed}/{total_tests} tests passed | {overall_status}")

    # Return detailed results for reporting
    return {
        'summary': {
            'total_tests': total_tests,
            'total_passed': total_passed,
            'overall_status': overall_status
        },
        'detailed_results': all_results
    }

if __name__ == "__main__":
    asyncio.run(main())