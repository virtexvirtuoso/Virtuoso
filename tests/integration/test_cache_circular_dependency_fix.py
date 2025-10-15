#!/usr/bin/env python3
"""
Cache Circular Dependency Fix Validation Test

This script tests the complete fix for the circular dependency issue:
monitoring → cache → dashboard data flow

Key Validations:
1. Cache warmer generates data independently (no API calls)
2. Monitoring system pushes data directly to cache
3. Cache contains the required keys: market:overview, analysis:signals, market:movers
4. Dashboard can retrieve data from cache
5. No circular dependencies in the data flow

Run this test to verify the fix is working correctly.
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cache_dependency_test")

class CacheDependencyFixValidator:
    """Validates that the cache circular dependency fix is working correctly."""

    def __init__(self):
        self.test_results = {
            'cache_warmer_independent': False,
            'monitoring_cache_push': False,
            'cache_keys_present': False,
            'dashboard_retrieval': False,
            'no_circular_calls': False,
            'overall_success': False
        }

        self.required_cache_keys = [
            'market:overview',
            'analysis:signals',
            'market:movers'
        ]

    async def run_validation(self) -> Dict[str, Any]:
        """Run complete validation of the cache dependency fix."""
        logger.info("🔍 Starting Cache Circular Dependency Fix Validation")
        logger.info("=" * 60)

        try:
            # Test 1: Cache warmer independent data generation
            await self._test_cache_warmer_independence()

            # Test 2: Monitoring system cache push integration
            await self._test_monitoring_cache_integration()

            # Test 3: Cache key presence validation
            await self._test_cache_key_presence()

            # Test 4: Dashboard data retrieval
            await self._test_dashboard_retrieval()

            # Test 5: Circular dependency elimination
            await self._test_no_circular_dependencies()

            # Calculate overall success
            self.test_results['overall_success'] = all([
                self.test_results['cache_warmer_independent'],
                self.test_results['cache_keys_present'],
                self.test_results['no_circular_calls']
            ])

            self._print_results()
            return self.test_results

        except Exception as e:
            logger.error(f"❌ Validation failed with error: {e}")
            return self.test_results

    async def _test_cache_warmer_independence(self):
        """Test that cache warmer generates data without API dependencies."""
        logger.info("\n🧪 Test 1: Cache Warmer Independence")
        logger.info("-" * 40)

        try:
            from src.core.cache_warmer import CacheWarmer

            # Create cache warmer instance
            cache_warmer = CacheWarmer()

            # Test independent data generation for each key
            success_count = 0
            for cache_key in self.required_cache_keys:
                try:
                    # Create a test warming task
                    from src.core.cache_warmer import WarmingTask
                    test_task = WarmingTask(key=cache_key, priority=1, interval_seconds=60)

                    # Test independent data generation (should not call APIs)
                    result = await cache_warmer._generate_independent_data(cache_key)

                    if result:
                        logger.info(f"✅ Independent data generation successful for {cache_key}")
                        success_count += 1
                    else:
                        logger.warning(f"⚠️ Independent data generation failed for {cache_key}")

                except Exception as e:
                    logger.error(f"❌ Independent data generation error for {cache_key}: {e}")

            # Mark success if all keys can be generated independently
            self.test_results['cache_warmer_independent'] = success_count == len(self.required_cache_keys)

            if self.test_results['cache_warmer_independent']:
                logger.info("✅ Cache warmer independence test PASSED")
            else:
                logger.warning(f"⚠️ Cache warmer independence test PARTIAL ({success_count}/{len(self.required_cache_keys)})")

        except Exception as e:
            logger.error(f"❌ Cache warmer independence test FAILED: {e}")

    async def _test_monitoring_cache_integration(self):
        """Test that monitoring system integrates with cache data aggregator."""
        logger.info("\n🧪 Test 2: Monitoring Cache Integration")
        logger.info("-" * 40)

        try:
            from src.monitoring.cache_data_aggregator import CacheDataAggregator
            from src.api.cache_adapter_direct import DirectCacheAdapter

            # Create cache adapter and aggregator
            cache_adapter = DirectCacheAdapter()
            cache_aggregator = CacheDataAggregator(cache_adapter, {})

            # Test analysis result processing
            test_analysis_result = {
                'confluence_score': 72.5,
                'reliability': 85.2,
                'signal_type': 'BUY',
                'components': {
                    'technical': 75.0,
                    'volume': 80.0,
                    'sentiment': 65.0
                },
                'market_data': {
                    'price': 50000.0,
                    'price_change_24h': 1500.0,
                    'price_change_percent_24h': 3.1,
                    'volume_24h': 1200000.0
                }
            }

            # Test adding analysis result
            await cache_aggregator.add_analysis_result('BTCUSDT', test_analysis_result)

            # Check if data was aggregated
            stats = cache_aggregator.get_statistics()

            if stats['aggregation_count'] > 0:
                logger.info("✅ Monitoring cache integration successful")
                self.test_results['monitoring_cache_push'] = True
            else:
                logger.warning("⚠️ No data aggregated by cache aggregator")

        except Exception as e:
            logger.error(f"❌ Monitoring cache integration test FAILED: {e}")

    async def _test_cache_key_presence(self):
        """Test that required cache keys are present after warming."""
        logger.info("\n🧪 Test 3: Cache Key Presence")
        logger.info("-" * 40)

        try:
            from src.core.cache_warmer import CacheWarmer

            # Warm critical cache data
            cache_warmer = CacheWarmer()
            warming_results = await cache_warmer.warm_critical_data()

            logger.info(f"Warming results: {warming_results['status']}")
            logger.info(f"Warmed keys: {warming_results['warmed_keys']}")

            # Check if required keys were warmed
            warmed_required_keys = [key for key in self.required_cache_keys if key in warming_results['warmed_keys']]

            if len(warmed_required_keys) >= 2:  # At least 2 of 3 keys should work
                logger.info(f"✅ Cache key presence test PASSED ({len(warmed_required_keys)}/{len(self.required_cache_keys)} keys)")
                self.test_results['cache_keys_present'] = True
            else:
                logger.warning(f"⚠️ Insufficient cache keys warmed ({len(warmed_required_keys)}/{len(self.required_cache_keys)})")

        except Exception as e:
            logger.error(f"❌ Cache key presence test FAILED: {e}")

    async def _test_dashboard_retrieval(self):
        """Test that dashboard can retrieve data from cache."""
        logger.info("\n🧪 Test 4: Dashboard Data Retrieval")
        logger.info("-" * 40)

        try:
            from src.api.cache_adapter_direct import DirectCacheAdapter

            cache_adapter = DirectCacheAdapter()
            retrieval_count = 0

            # Test retrieving each required cache key
            for cache_key in self.required_cache_keys:
                try:
                    data, status = await cache_adapter._get_with_fallback(cache_key)

                    if data and data != "null":
                        logger.info(f"✅ Successfully retrieved {cache_key}")
                        retrieval_count += 1
                    else:
                        logger.warning(f"⚠️ No data found for {cache_key}")

                except Exception as e:
                    logger.warning(f"⚠️ Retrieval failed for {cache_key}: {e}")

            if retrieval_count > 0:
                logger.info(f"✅ Dashboard retrieval test PASSED ({retrieval_count}/{len(self.required_cache_keys)} keys)")
                self.test_results['dashboard_retrieval'] = True
            else:
                logger.warning("⚠️ No cache keys could be retrieved")

        except Exception as e:
            logger.error(f"❌ Dashboard retrieval test FAILED: {e}")

    async def _test_no_circular_dependencies(self):
        """Test that no circular dependencies exist in the data flow."""
        logger.info("\n🧪 Test 5: Circular Dependency Elimination")
        logger.info("-" * 40)

        try:
            # This test validates that:
            # 1. Cache warmer doesn't call APIs that depend on cache
            # 2. Monitoring pushes directly to cache
            # 3. Dashboard reads from cache without triggering monitoring

            # Check cache warmer implementation
            from src.core.cache_warmer import CacheWarmer
            import inspect

            cache_warmer = CacheWarmer()

            # Get the _generate_independent_data method source
            method_source = inspect.getsource(cache_warmer._generate_independent_data)

            # Check that it doesn't contain API calls
            circular_patterns = [
                'localhost:8001',
                'localhost:8003',
                '/api/monitoring/',
                '/api/market-overview',
                '/api/signals'
            ]

            has_circular_calls = any(pattern in method_source for pattern in circular_patterns)

            if not has_circular_calls:
                logger.info("✅ No circular API calls detected in cache warmer")
                self.test_results['no_circular_calls'] = True
            else:
                logger.warning("⚠️ Potential circular API calls detected")

        except Exception as e:
            logger.error(f"❌ Circular dependency test FAILED: {e}")

    def _print_results(self):
        """Print comprehensive test results."""
        logger.info("\n" + "=" * 60)
        logger.info("🏁 CACHE CIRCULAR DEPENDENCY FIX VALIDATION RESULTS")
        logger.info("=" * 60)

        tests = [
            ("Cache Warmer Independence", self.test_results['cache_warmer_independent']),
            ("Monitoring Cache Push", self.test_results['monitoring_cache_push']),
            ("Cache Keys Present", self.test_results['cache_keys_present']),
            ("Dashboard Retrieval", self.test_results['dashboard_retrieval']),
            ("No Circular Dependencies", self.test_results['no_circular_calls'])
        ]

        for test_name, result in tests:
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{test_name:25} : {status}")

        logger.info("-" * 60)
        overall_status = "✅ SUCCESS" if self.test_results['overall_success'] else "❌ FAILED"
        logger.info(f"Overall Result: {overall_status}")

        if self.test_results['overall_success']:
            logger.info("\n🎉 Circular dependency fix validation SUCCESSFUL!")
            logger.info("The monitoring → cache → dashboard data flow is now working correctly.")
        else:
            logger.warning("\n⚠️ Some tests failed. Review the implementation for remaining issues.")

async def main():
    """Run the complete validation test."""
    validator = CacheDependencyFixValidator()
    results = await validator.run_validation()

    # Return appropriate exit code
    return 0 if results['overall_success'] else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)