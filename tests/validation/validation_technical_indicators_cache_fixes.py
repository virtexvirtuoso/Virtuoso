#!/usr/bin/env python3
"""
Comprehensive Validation Test for Technical Indicator Cache Fixes
Tests the coroutine misuse fixes and fallback mechanisms implemented in technical indicators.
"""

import asyncio
import sys
import os
import pandas as pd
import numpy as np
import traceback
import time
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from indicators.technical_indicators import TechnicalIndicators
from indicators.base_indicator import BaseIndicator

class MockCoroutineCache:
    """Mock cache that behaves like a coroutine to test the fix"""
    def __init__(self, return_value=None):
        self.return_value = return_value

    def __await__(self):
        # This makes it behave like a coroutine
        async def _await():
            return MockRealCache(self.return_value)
        return _await().__await__()

class MockRealCache:
    """Mock real cache instance"""
    def __init__(self, return_value=None):
        self.return_value = return_value
        self._initialized = True

    async def get_indicator(self, **kwargs):
        if self.return_value is not None:
            return self.return_value
        # Simulate cache computation
        compute_func = kwargs.get('compute_func')
        if compute_func:
            return await compute_func()
        return 0.5

class MockFailingCache:
    """Mock cache that always fails"""
    def __init__(self):
        self._initialized = True

    async def get_indicator(self, **kwargs):
        raise Exception("Cache failure simulation")

class TechnicalIndicatorCacheFixValidation:
    """Comprehensive validation of technical indicator cache fixes"""

    def __init__(self):
        self.test_results = []
        self.errors = []

    def log_result(self, test_name: str, status: str, details: str = ""):
        """Log test result"""
        result = {
            'test_name': test_name,
            'status': status,
            'details': details,
            'timestamp': time.time()
        }
        self.test_results.append(result)
        print(f"[{status.upper()}] {test_name}: {details}")

    def create_test_data(self) -> pd.DataFrame:
        """Create synthetic test data for indicators"""
        dates = pd.date_range('2023-01-01', periods=100, freq='1H')
        np.random.seed(42)

        # Generate realistic OHLCV data
        base_price = 100
        price_changes = np.random.normal(0, 0.02, 100).cumsum()
        close_prices = base_price * (1 + price_changes)

        # Create OHLC from close prices
        high_offset = np.random.uniform(0, 0.01, 100)
        low_offset = np.random.uniform(-0.01, 0, 100)
        open_offset = np.random.uniform(-0.005, 0.005, 100)

        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices * (1 + open_offset),
            'high': close_prices * (1 + high_offset),
            'low': close_prices * (1 + low_offset),
            'close': close_prices,
            'volume': np.random.uniform(1000, 10000, 100)
        })

        return df

    async def test_ensure_cache_ready_with_coroutine(self):
        """Test _ensure_cache_ready with coroutine cache"""
        test_name = "Cache Ready - Coroutine Fix"

        try:
            # Create indicator with coroutine cache
            config = {'caching': {'indicators': {'enabled': True}}}
            indicator = TechnicalIndicators(config=config)

            # Manually assign a coroutine to cache (simulating the bug)
            indicator.cache = MockCoroutineCache(return_value=0.75)

            # Test the fix
            await indicator._ensure_cache_ready()

            # Verify cache is now a real cache instance
            if hasattr(indicator.cache, '_initialized'):
                self.log_result(test_name, "PASS", "Coroutine cache successfully converted to real cache")
                return True
            else:
                self.log_result(test_name, "FAIL", "Cache is not properly initialized after fix")
                return False

        except Exception as e:
            self.log_result(test_name, "FAIL", f"Exception: {str(e)}")
            self.errors.append(f"{test_name}: {traceback.format_exc()}")
            return False

    async def test_cached_methods_with_cache_guard(self):
        """Test all cached technical indicator methods with cache readiness guards"""
        test_name = "Cached Methods - Guard Implementation"

        try:
            df = self.create_test_data()
            config = {'caching': {'indicators': {'enabled': True}}}
            indicator = TechnicalIndicators(config=config)

            # Test all cached methods
            cached_methods = [
                ('_calculate_rsi_score_cached', 'RSI'),
                ('_calculate_macd_score_cached', 'MACD'),
                ('_calculate_ao_score_cached', 'AO'),
                ('_calculate_williams_r_score_cached', 'Williams %R'),
                ('_calculate_atr_score_cached', 'ATR'),
                ('_calculate_cci_score_cached', 'CCI')
            ]

            results = {}
            for method_name, indicator_name in cached_methods:
                method = getattr(indicator, method_name)

                # Test with coroutine cache (should auto-fix)
                indicator.cache = MockCoroutineCache(return_value=0.6)
                result = await method(df, symbol='TEST')
                results[indicator_name] = result

            # Verify all methods returned valid results
            if all(isinstance(r, (int, float)) and 0 <= r <= 1 for r in results.values()):
                self.log_result(test_name, "PASS", f"All cached methods working: {results}")
                return True
            else:
                self.log_result(test_name, "FAIL", f"Invalid results: {results}")
                return False

        except Exception as e:
            self.log_result(test_name, "FAIL", f"Exception: {str(e)}")
            self.errors.append(f"{test_name}: {traceback.format_exc()}")
            return False

    async def test_fallback_mechanism(self):
        """Test fallback to direct computation when cache fails"""
        test_name = "Fallback Mechanism"

        try:
            df = self.create_test_data()
            config = {'caching': {'indicators': {'enabled': True}}}
            indicator = TechnicalIndicators(config=config)

            # Test with failing cache
            indicator.cache = MockFailingCache()

            # Test RSI calculation with failing cache
            result = await indicator._calculate_rsi_score_cached(df, symbol='TEST')

            # Verify fallback worked (should return direct calculation result)
            if isinstance(result, (int, float)) and 0 <= result <= 1:
                self.log_result(test_name, "PASS", f"Fallback successful, result: {result}")
                return True
            else:
                self.log_result(test_name, "FAIL", f"Fallback failed, invalid result: {result}")
                return False

        except Exception as e:
            self.log_result(test_name, "FAIL", f"Exception: {str(e)}")
            self.errors.append(f"{test_name}: {traceback.format_exc()}")
            return False

    async def test_cache_disabled_scenario(self):
        """Test behavior when caching is disabled"""
        test_name = "Cache Disabled Scenario"

        try:
            df = self.create_test_data()
            config = {'caching': {'indicators': {'enabled': False}}}
            indicator = TechnicalIndicators(config=config)

            # Test cached method when caching is disabled
            result = await indicator._calculate_rsi_score_cached(df, symbol='TEST')

            if isinstance(result, (int, float)) and 0 <= result <= 1:
                self.log_result(test_name, "PASS", f"Direct calculation when cache disabled: {result}")
                return True
            else:
                self.log_result(test_name, "FAIL", f"Invalid result when cache disabled: {result}")
                return False

        except Exception as e:
            self.log_result(test_name, "FAIL", f"Exception: {str(e)}")
            self.errors.append(f"{test_name}: {traceback.format_exc()}")
            return False

    async def test_concurrent_cache_access(self):
        """Test concurrent access to cached methods"""
        test_name = "Concurrent Cache Access"

        try:
            df = self.create_test_data()
            config = {'caching': {'indicators': {'enabled': True}}}
            indicator = TechnicalIndicators(config=config)

            # Set up working cache
            indicator.cache = MockRealCache(return_value=0.7)

            # Create multiple concurrent tasks
            tasks = []
            for i in range(10):
                task = indicator._calculate_rsi_score_cached(df, symbol=f'TEST{i}')
                tasks.append(task)

            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check results
            success_count = sum(1 for r in results if isinstance(r, (int, float)))
            error_count = len(results) - success_count

            if error_count == 0:
                self.log_result(test_name, "PASS", f"All {len(results)} concurrent operations successful")
                return True
            else:
                self.log_result(test_name, "FAIL", f"{error_count} errors out of {len(results)} operations")
                return False

        except Exception as e:
            self.log_result(test_name, "FAIL", f"Exception: {str(e)}")
            self.errors.append(f"{test_name}: {traceback.format_exc()}")
            return False

    async def test_performance_comparison(self):
        """Test performance of cached vs non-cached operations"""
        test_name = "Performance Comparison"

        try:
            df = self.create_test_data()
            config = {'caching': {'indicators': {'enabled': True}}}
            indicator = TechnicalIndicators(config=config)

            # Test direct calculation
            start_time = time.time()
            direct_result = indicator._calculate_rsi_score(df)
            direct_time = time.time() - start_time

            # Test cached calculation (cache hit)
            indicator.cache = MockRealCache(return_value=direct_result)
            start_time = time.time()
            cached_result = await indicator._calculate_rsi_score_cached(df, symbol='TEST')
            cached_time = time.time() - start_time

            # Performance validation
            performance_ratio = direct_time / cached_time if cached_time > 0 else float('inf')

            self.log_result(test_name, "PASS",
                          f"Direct: {direct_time:.4f}s, Cached: {cached_time:.4f}s, "
                          f"Ratio: {performance_ratio:.2f}x")
            return True

        except Exception as e:
            self.log_result(test_name, "FAIL", f"Exception: {str(e)}")
            self.errors.append(f"{test_name}: {traceback.format_exc()}")
            return False

    async def test_error_handling_completeness(self):
        """Test comprehensive error handling in cached methods"""
        test_name = "Error Handling Completeness"

        try:
            df = self.create_test_data()
            config = {'caching': {'indicators': {'enabled': True}}}
            indicator = TechnicalIndicators(config=config)

            # Test various error scenarios
            error_scenarios = [
                ("None cache", None),
                ("Corrupted cache", "not_a_cache"),
                ("Exception during await", MockCoroutineCache()),
            ]

            for scenario_name, cache_obj in error_scenarios:
                indicator.cache = cache_obj

                try:
                    result = await indicator._calculate_rsi_score_cached(df, symbol='TEST')
                    if isinstance(result, (int, float)):
                        self.log_result(f"{test_name} - {scenario_name}", "PASS",
                                      f"Graceful fallback with result: {result}")
                    else:
                        self.log_result(f"{test_name} - {scenario_name}", "FAIL",
                                      f"Invalid fallback result: {result}")
                        return False
                except Exception as e:
                    self.log_result(f"{test_name} - {scenario_name}", "FAIL",
                                  f"Unhandled exception: {str(e)}")
                    return False

            return True

        except Exception as e:
            self.log_result(test_name, "FAIL", f"Exception: {str(e)}")
            self.errors.append(f"{test_name}: {traceback.format_exc()}")
            return False

    async def run_all_tests(self):
        """Run all validation tests"""
        print("=" * 60)
        print("TECHNICAL INDICATOR CACHE FIXES VALIDATION")
        print("=" * 60)

        test_methods = [
            self.test_ensure_cache_ready_with_coroutine,
            self.test_cached_methods_with_cache_guard,
            self.test_fallback_mechanism,
            self.test_cache_disabled_scenario,
            self.test_concurrent_cache_access,
            self.test_performance_comparison,
            self.test_error_handling_completeness
        ]

        results = []
        for test_method in test_methods:
            try:
                result = await test_method()
                results.append(result)
            except Exception as e:
                print(f"[ERROR] Test {test_method.__name__} failed with exception: {e}")
                results.append(False)

        # Summary
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)

        passed = sum(results)
        total = len(results)

        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")

        if self.errors:
            print("\nERRORS DETECTED:")
            for error in self.errors:
                print(f"- {error}")

        return passed == total

def main():
    """Main validation entry point"""
    validator = TechnicalIndicatorCacheFixValidation()

    try:
        # Run validation
        success = asyncio.run(validator.run_all_tests())

        if success:
            print("\n✅ ALL VALIDATIONS PASSED - Cache fixes are working correctly")
            sys.exit(0)
        else:
            print("\n❌ SOME VALIDATIONS FAILED - Issues detected in cache fixes")
            sys.exit(1)

    except Exception as e:
        print(f"\n💥 VALIDATION CRASHED: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()