#!/usr/bin/env python3
"""
Comprehensive validation tests for the three log warning fixes:
1. Timeframe synchronization fix with auto-adjustment
2. Port 8004 connection error handling
3. Circular import fix with lazy loading

This test suite validates the fixes end-to-end in the local environment.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging to see all levels
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Test counters for validation
test_results = {
    'passed': 0,
    'failed': 0,
    'errors': []
}

def assert_test(condition, test_name, details=""):
    """Helper to track test results"""
    if condition:
        test_results['passed'] += 1
        print(f"✅ PASS: {test_name}")
        if details:
            print(f"   {details}")
    else:
        test_results['failed'] += 1
        error_msg = f"{test_name}{': ' + details if details else ''}"
        test_results['errors'].append(error_msg)
        print(f"❌ FAIL: {error_msg}")

print("=" * 80)
print("VALIDATION TEST SUITE: Log Warning Fixes")
print("=" * 80)

# ============================================================================
# TEST 1: Circular Import Fix Validation
# ============================================================================
print("\n" + "=" * 80)
print("TEST 1: CIRCULAR IMPORT FIX - Lazy Loading Pattern")
print("=" * 80)

try:
    # Test that the module can be imported without circular dependency errors
    from src.core.cache.shared_cache_bridge import (
        SharedCacheBridge,
        get_shared_cache_bridge,
        _lazy_import_cache_components
    )
    assert_test(True, "Import shared_cache_bridge without circular dependency errors")

    # Test that global variables start as None (deferred imports)
    from src.core.cache import shared_cache_bridge
    assert_test(
        shared_cache_bridge.DirectCacheAdapter is None,
        "DirectCacheAdapter initially None (deferred)",
        "Value before lazy load: None"
    )

    # Test lazy import function
    _lazy_import_cache_components()
    print(f"   After lazy import - DirectCacheAdapter: {shared_cache_bridge.DirectCacheAdapter}")
    assert_test(True, "Lazy import function executes without errors")

    # Test SharedCacheBridge initialization doesn't cause circular imports
    bridge = get_shared_cache_bridge()
    assert_test(
        isinstance(bridge, SharedCacheBridge),
        "SharedCacheBridge singleton instantiation",
        f"Instance type: {type(bridge).__name__}"
    )

except Exception as e:
    assert_test(False, "Circular import fix validation", str(e))
    import traceback
    traceback.print_exc()

# ============================================================================
# TEST 2: Timeframe Synchronization Fix Validation
# ============================================================================
print("\n" + "=" * 80)
print("TEST 2: TIMEFRAME SYNCHRONIZATION - Auto-Adjustment Logic")
print("=" * 80)

try:
    from src.utils.data_validation import TimestampValidator

    # TEST 2.1: Default behavior with small timeframes (1m, 5m)
    print("\n--- Test 2.1: Small timeframes (1m + 5m) ---")
    validator_small = TimestampValidator(max_delta_seconds=60, auto_adjust_for_timeframes=True)

    now = datetime.now(timezone.utc)
    market_data_small = {
        'base': pd.DataFrame({'close': [100]}, index=pd.DatetimeIndex([now])),
        'ltf': pd.DataFrame({'close': [100]}, index=pd.DatetimeIndex([now - timedelta(seconds=45)]))
    }

    is_valid, error = validator_small.validate_multi_timeframe_sync(market_data_small)
    assert_test(
        is_valid,
        "Small timeframes validation with 45s delta (within 60s limit)",
        f"Delta should be ~45s, max: 60s"
    )

    # TEST 2.2: Large timeframes (4h) with auto-adjustment
    print("\n--- Test 2.2: Large timeframe (4h) with auto-adjustment ---")
    validator_large = TimestampValidator(max_delta_seconds=60, auto_adjust_for_timeframes=True)

    # 4h timeframe has period of 14400s, so effective max_delta should be 14400 * 1.5 = 21600s
    market_data_large = {
        'base': pd.DataFrame({'close': [100]}, index=pd.DatetimeIndex([now])),
        'htf': pd.DataFrame({'close': [100]}, index=pd.DatetimeIndex([now - timedelta(hours=5)]))  # 5h = 18000s delta
    }

    is_valid, error = validator_large.validate_multi_timeframe_sync(market_data_large)
    assert_test(
        is_valid,
        "4h timeframe validation with 5h delta (within 21600s auto-adjusted limit)",
        f"4h period = 14400s, effective max = 21600s, delta = 18000s"
    )

    # TEST 2.3: Verify auto-adjustment prevents false warnings
    print("\n--- Test 2.3: Verify 4h timeframe doesn't trigger warnings for normal delays ---")
    validator_htf = TimestampValidator(max_delta_seconds=60, auto_adjust_for_timeframes=True)

    # Capture log output
    import io
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.WARNING)
    validator_htf.logger.addHandler(handler)

    market_data_htf = {
        'htf': pd.DataFrame({'close': [100]}, index=pd.DatetimeIndex([now])),
        'base': pd.DataFrame({'close': [100]}, index=pd.DatetimeIndex([now - timedelta(hours=3)]))  # 3h delta
    }

    is_valid, error = validator_htf.validate_multi_timeframe_sync(market_data_htf)
    log_output = log_stream.getvalue()

    assert_test(
        is_valid and 'WARNING' not in log_output,
        "No warnings for 3h delta with 4h timeframe",
        "Auto-adjusted limit handles normal 4h candle delays"
    )

    # TEST 2.4: Verify actual problems still get caught
    print("\n--- Test 2.4: Verify extremely stale data still triggers warnings ---")
    validator_stale = TimestampValidator(max_delta_seconds=60, auto_adjust_for_timeframes=True)

    market_data_stale = {
        'htf': pd.DataFrame({'close': [100]}, index=pd.DatetimeIndex([now])),
        'base': pd.DataFrame({'close': [100]}, index=pd.DatetimeIndex([now - timedelta(hours=8)]))  # 8h delta, exceeds 21600s
    }

    is_valid, error = validator_stale.validate_multi_timeframe_sync(market_data_stale)
    assert_test(
        not is_valid,
        "Extremely stale data (8h) still triggers validation failure",
        "28800s delta exceeds 21600s adjusted limit"
    )

    # TEST 2.5: Statistics tracking
    print("\n--- Test 2.5: Statistics tracking ---")
    stats = validator_large.get_statistics()
    assert_test(
        stats['validation_count'] > 0,
        "Validation statistics tracking",
        f"Stats: {stats}"
    )

except Exception as e:
    assert_test(False, "Timeframe synchronization fix validation", str(e))
    import traceback
    traceback.print_exc()

# ============================================================================
# TEST 3: Port 8004 Error Handling Fix Validation
# ============================================================================
print("\n" + "=" * 80)
print("TEST 3: PORT 8004 ERROR HANDLING - Debug Logging with Fallback")
print("=" * 80)

async def test_dashboard_proxy():
    try:
        from src.dashboard.dashboard_proxy import DashboardIntegrationProxy

        # TEST 3.1: Import and instantiation
        proxy = DashboardIntegrationProxy()
        assert_test(
            isinstance(proxy, DashboardIntegrationProxy),
            "DashboardIntegrationProxy instantiation"
        )

        # TEST 3.2: Connection error handling - capture logs
        print("\n--- Test 3.2: Connection error logging behavior ---")

        import io
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.DEBUG)

        proxy_logger = logging.getLogger('src.dashboard.dashboard_proxy')
        proxy_logger.addHandler(handler)
        proxy_logger.setLevel(logging.DEBUG)

        # Attempt to fetch from non-existent service
        data = await proxy._fetch_from_main("/api/dashboard/overview")

        log_output = log_stream.getvalue()
        print(f"   Log output:\n{log_output}")

        # Verify error is logged as DEBUG, not ERROR or WARNING
        has_error_level = 'ERROR' in log_output
        has_warning_level = 'WARNING' in log_output
        has_debug_level = 'DEBUG' in log_output and 'using fallback' in log_output

        assert_test(
            not has_error_level,
            "No ERROR logs for connection failure",
            "Connection errors downgraded to DEBUG"
        )

        assert_test(
            not has_warning_level,
            "No WARNING logs for connection failure",
            "Connection warnings downgraded to DEBUG"
        )

        assert_test(
            has_debug_level,
            "DEBUG log present with fallback message",
            "Clear indication that fallback will be used"
        )

        # TEST 3.3: Fallback behavior
        print("\n--- Test 3.3: Fallback response behavior ---")
        overview = await proxy.get_dashboard_overview()

        assert_test(
            overview is not None and 'status' in overview,
            "Fallback overview response provided",
            f"Status: {overview.get('status')}"
        )

        assert_test(
            overview.get('status') == 'no_integration',
            "Fallback status correctly indicates no integration",
            "Web service gracefully degrades when main service unavailable"
        )

        # TEST 3.4: Multiple endpoint fallbacks
        print("\n--- Test 3.4: Multiple endpoint fallback handling ---")
        signals = await proxy.get_signals_data()
        alerts = await proxy.get_alerts_data()
        market = await proxy.get_market_overview()

        assert_test(
            isinstance(signals, list) and isinstance(alerts, list) and isinstance(market, dict),
            "All endpoints provide fallback data",
            f"Signals: list({len(signals)}), Alerts: list({len(alerts)}), Market: dict"
        )

        # Cleanup
        await proxy.close()

    except Exception as e:
        assert_test(False, "Port 8004 error handling fix validation", str(e))
        import traceback
        traceback.print_exc()

# Run async test
asyncio.run(test_dashboard_proxy())

# ============================================================================
# FINAL RESULTS SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("VALIDATION TEST RESULTS SUMMARY")
print("=" * 80)

total_tests = test_results['passed'] + test_results['failed']
pass_rate = (test_results['passed'] / total_tests * 100) if total_tests > 0 else 0

print(f"\nTotal Tests: {total_tests}")
print(f"Passed: {test_results['passed']} ✅")
print(f"Failed: {test_results['failed']} ❌")
print(f"Pass Rate: {pass_rate:.1f}%")

if test_results['errors']:
    print("\nFailed Tests:")
    for error in test_results['errors']:
        print(f"  - {error}")

print("\n" + "=" * 80)
if test_results['failed'] == 0:
    print("✅ ALL TESTS PASSED - Fixes validated successfully")
    print("=" * 80)
    sys.exit(0)
else:
    print("❌ SOME TESTS FAILED - Review errors above")
    print("=" * 80)
    sys.exit(1)
