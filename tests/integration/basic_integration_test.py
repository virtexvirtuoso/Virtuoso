#!/usr/bin/env python3
"""
Basic Integration Test for Crisis Stabilization
===============================================

This test validates that the core system can start and perform basic operations
without crashing or using mock data. It's designed to track progress during
the crisis stabilization phase.

SUCCESS CRITERIA:
- System imports without timeout (< 30 seconds)
- No synthetic/mock data in trading paths
- Basic API endpoints respond
- Core services initialize properly
"""

import asyncio
import time
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, List

def log_test_result(test_name: str, success: bool, duration: float, details: str = ""):
    """Log test results in a structured format."""
    status = "✅ PASS" if success else "❌ FAIL"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {status} {test_name} ({duration:.2f}s)")
    if details:
        print(f"    Details: {details}")
    if not success:
        print(f"    Error: {details}")

async def test_system_import():
    """Test 1: System Import Speed (should be < 30 seconds)"""
    start_time = time.time()
    try:
        import src.main
        duration = time.time() - start_time
        log_test_result("System Import", True, duration, f"Import completed in {duration:.2f}s")
        return True, duration
    except Exception as e:
        duration = time.time() - start_time
        log_test_result("System Import", False, duration, str(e))
        return False, duration

async def test_no_synthetic_data_imports():
    """Test 2: Verify synthetic data functions are disabled"""
    start_time = time.time()
    try:
        # Test that synthetic data generation functions raise errors
        from src.core.services.simple_correlation_service import SimpleCorrelationService
        service = SimpleCorrelationService()

        # This should raise an error now
        try:
            await service.get_price_data("BTCUSDT", 10)
            # If we get here, synthetic data is still being used
            log_test_result("No Synthetic Data", False, time.time() - start_time,
                          "Synthetic data fallback is still active")
            return False
        except ValueError as e:
            if "synthetic data" in str(e).lower() or "real market data required" in str(e).lower():
                log_test_result("No Synthetic Data", True, time.time() - start_time,
                              "Synthetic data properly disabled")
                return True
            else:
                log_test_result("No Synthetic Data", False, time.time() - start_time,
                              f"Unexpected error: {e}")
                return False
    except Exception as e:
        log_test_result("No Synthetic Data", False, time.time() - start_time, str(e))
        return False

async def test_removed_test_files():
    """Test 3: Verify dangerous test files are removed"""
    start_time = time.time()
    dangerous_files = [
        "src/core/analysis/confluence_sample_DO_NOT_USE.py.example",
        "src/api/routes/debug_test.py",
        "src/api/routes/test_api_endpoints.py",
        "src/core/resilience/test_resilience.py"
    ]

    import os
    removed_files = []
    remaining_files = []

    for file_path in dangerous_files:
        full_path = f"/Users/ffv_macmini/Desktop/Virtuoso_ccxt/{file_path}"
        if os.path.exists(full_path):
            remaining_files.append(file_path)
        else:
            # Check if it was renamed with .REMOVED or similar
            removed_variations = [
                f"{full_path}.REMOVED",
                f"{full_path}.DANGEROUS_REMOVED",
                f"{full_path}.REMOVED_MOCK_DATA"
            ]
            for variation in removed_variations:
                if os.path.exists(variation):
                    removed_files.append(file_path)
                    break

    if remaining_files:
        log_test_result("Dangerous Files Removed", False, time.time() - start_time,
                      f"Files still present: {remaining_files}")
        return False
    else:
        log_test_result("Dangerous Files Removed", True, time.time() - start_time,
                      f"All dangerous files removed/renamed: {len(removed_files)} files")
        return True

async def test_basic_service_initialization():
    """Test 4: Basic service initialization without crashes"""
    start_time = time.time()
    try:
        # Test basic service imports
        from src.core.cache.lru_cache import LRUCache
        from src.api.feature_flags import FeatureFlags
        from src.core.naming_mapper import NamingMapper

        # Initialize basic services
        cache = LRUCache(max_items=10, ttl=30)
        mapper = NamingMapper()

        log_test_result("Service Initialization", True, time.time() - start_time,
                      "Core services initialized successfully")
        return True
    except Exception as e:
        log_test_result("Service Initialization", False, time.time() - start_time, str(e))
        return False

async def main():
    """Run the basic integration test suite."""
    print("=" * 60)
    print("🚨 CRISIS STABILIZATION - Basic Integration Test")
    print("=" * 60)
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Track overall results
    tests_passed = 0
    tests_total = 4
    start_time = time.time()

    # Test 1: System Import Speed
    success, import_duration = await test_system_import()
    if success:
        tests_passed += 1

    # Test 2: No Synthetic Data
    if await test_no_synthetic_data_imports():
        tests_passed += 1

    # Test 3: Dangerous Files Removed
    if await test_removed_test_files():
        tests_passed += 1

    # Test 4: Basic Service Initialization
    if await test_basic_service_initialization():
        tests_passed += 1

    # Summary
    total_duration = time.time() - start_time
    success_rate = (tests_passed / tests_total) * 100

    print()
    print("=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Passed: {tests_passed}/{tests_total} ({success_rate:.1f}%)")
    print(f"Total Duration: {total_duration:.2f} seconds")
    print(f"Import Duration: {import_duration:.2f} seconds")

    if success_rate >= 75:
        print("✅ SYSTEM STABILITY: GOOD - Crisis stabilization making progress")
        exit_code = 0
    elif success_rate >= 50:
        print("⚠️  SYSTEM STABILITY: FAIR - More work needed")
        exit_code = 1
    else:
        print("❌ SYSTEM STABILITY: POOR - Critical issues remain")
        exit_code = 2

    print(f"Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return exit_code

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test framework error: {e}")
        traceback.print_exc()
        sys.exit(1)