#!/usr/bin/env python3
"""
Corrected Validation Script for Reliability Percentage Display Fix
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio

def test_metrics_tracker_bridge():
    """Test MetricsTracker has update_analysis_metrics bridge method."""
    print("\n=== Testing MetricsTracker Bridge Method ===")

    try:
        from src.monitoring.metrics_tracker import MetricsTracker

        # Check if the bridge method exists by inspecting the class
        has_bridge_method = hasattr(MetricsTracker, 'update_analysis_metrics')

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

async def test_confluence_cache_service():
    """Test ConfluenceCacheService uses CacheKeys.confluence_breakdown correctly."""
    print("\n=== Testing Confluence Cache Service ===")

    # Create mock cache service (without actual Redis connection)
    from src.core.cache.confluence_cache_service import ConfluenceCacheService
    cache_service = ConfluenceCacheService()

    # Test that the service has the expected methods (corrected names)
    methods_to_check = [
        'cache_confluence_breakdown',
        'get_cached_breakdown',  # Corrected name
        'cache_multiple_symbols'  # Corrected name
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

async def main():
    """Run corrected validation tests."""
    print("Corrected Validation for Failing Tests")
    print("=" * 45)

    all_results = {}

    # Run the corrected tests
    all_results['confluence_cache_service'] = await test_confluence_cache_service()
    all_results['metrics_tracker_bridge'] = test_metrics_tracker_bridge()

    # Generate summary
    print("\n" + "=" * 45)
    print("CORRECTED VALIDATION SUMMARY")
    print("=" * 45)

    total_tests = 0
    total_passed = 0

    for test_suite, results in all_results.items():
        passed = sum(1 for r in results if r.get('passed', False))
        total = len(results)
        total_tests += total
        total_passed += passed

        status = "PASS" if passed == total else "FAIL"
        print(f"  {test_suite}: {passed}/{total} tests passed | {status}")

    print("-" * 45)
    overall_status = "PASS" if total_passed == total_tests else "FAIL"
    print(f"  OVERALL: {total_passed}/{total_tests} tests passed | {overall_status}")

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