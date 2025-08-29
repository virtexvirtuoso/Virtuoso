#!/usr/bin/env python3
"""
Local Cache Optimization Testing Suite
Comprehensive tests for all dashboard cache optimization components.
"""

import sys
import os
import asyncio
import time
import json
import logging
from typing import Dict, Any, List
from datetime import datetime

# Add project root to path
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Colors for output
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.NC}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.NC}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️ {msg}{Colors.NC}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️ {msg}{Colors.NC}")

class CacheOptimizationTester:
    """Comprehensive tester for cache optimization components"""
    
    def __init__(self):
        self.test_results = {}
        self.performance_metrics = {}
        
    async def run_all_tests(self):
        """Run complete test suite"""
        print(f"{Colors.BLUE}🧪 Starting Cache Optimization Test Suite{Colors.NC}")
        print("=" * 60)
        
        test_methods = [
            self.test_cache_key_generator,
            self.test_ttl_strategy,
            self.test_batch_operations,
            self.test_cache_warming,
            self.test_websocket_broadcaster,
            self.test_unified_dashboard,
            self.test_performance_benchmarks,
            self.test_integration
        ]
        
        total_tests = len(test_methods)
        passed_tests = 0
        
        for test_method in test_methods:
            try:
                result = await test_method()
                if result:
                    passed_tests += 1
                    print_success(f"{test_method.__name__} passed")
                else:
                    print_error(f"{test_method.__name__} failed")
            except Exception as e:
                print_error(f"{test_method.__name__} error: {e}")
                logger.exception(f"Error in {test_method.__name__}")
        
        # Summary
        print("\n" + "=" * 60)
        print(f"{Colors.BLUE}📊 Test Results Summary{Colors.NC}")
        print(f"Tests Passed: {passed_tests}/{total_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            print_success("All tests passed! Ready for VPS deployment.")
            return True
        else:
            print_warning("Some tests failed. Review issues before deploying.")
            return False
    
    async def test_cache_key_generator(self):
        """Test cache key generator functionality"""
        print(f"\n{Colors.BLUE}Testing Cache Key Generator...{Colors.NC}")
        
        try:
            from src.core.cache.key_generator import CacheKeyGenerator
            
            # Test dashboard keys
            dashboard_key = CacheKeyGenerator.dashboard_data()
            mobile_key = CacheKeyGenerator.mobile_overview()
            confluence_key = CacheKeyGenerator.confluence_scores("BTCUSDT")
            
            # Validate key format
            assert "dashboard:data" in dashboard_key
            assert "mobile:overview" in mobile_key
            assert "confluence:BTCUSDT" in confluence_key
            
            print_info(f"Dashboard key: {dashboard_key}")
            print_info(f"Mobile key: {mobile_key}")
            print_info(f"Confluence key: {confluence_key}")
            
            # Test TTL calculation
            dashboard_ttl = CacheKeyGenerator.get_ttl_for_key(dashboard_key)
            mobile_ttl = CacheKeyGenerator.get_ttl_for_key(mobile_key)
            
            assert isinstance(dashboard_ttl, int)
            assert isinstance(mobile_ttl, int)
            assert dashboard_ttl > 0
            assert mobile_ttl > 0
            
            print_info(f"Dashboard TTL: {dashboard_ttl}s")
            print_info(f"Mobile TTL: {mobile_ttl}s")
            
            # Test validation
            assert CacheKeyGenerator.validate_key(dashboard_key)
            assert CacheKeyGenerator.validate_key(mobile_key)
            assert not CacheKeyGenerator.validate_key("invalid:key")
            
            self.test_results['cache_key_generator'] = True
            return True
            
        except Exception as e:
            logger.error(f"Cache key generator test failed: {e}")
            self.test_results['cache_key_generator'] = False
            return False
    
    async def test_ttl_strategy(self):
        """Test TTL strategy implementation"""
        print(f"\n{Colors.BLUE}Testing TTL Strategy...{Colors.NC}")
        
        try:
            from src.core.cache.ttl_strategy import TTLStrategy, DataType, UpdateFrequency
            
            ttl_strategy = TTLStrategy()
            
            # Test basic TTL calculation
            market_ttl = ttl_strategy.get_ttl("market:overview", dependency_level=0)
            dashboard_ttl = ttl_strategy.get_ttl("dashboard:data", dependency_level=1)
            confluence_ttl = ttl_strategy.get_ttl("confluence:BTCUSDT", dependency_level=0)
            
            assert isinstance(market_ttl, int)
            assert isinstance(dashboard_ttl, int)
            assert isinstance(confluence_ttl, int)
            
            print_info(f"Market TTL: {market_ttl}s")
            print_info(f"Dashboard TTL: {dashboard_ttl}s")
            print_info(f"Confluence TTL: {confluence_ttl}s")
            
            # Test dependency levels
            base_ttl = ttl_strategy.get_ttl("market:overview", dependency_level=0)
            dep_ttl = ttl_strategy.get_ttl("market:overview", dependency_level=2)
            assert dep_ttl > base_ttl  # Dependent data should live longer
            
            # Test access pattern recording
            test_key = "test:access:pattern"
            ttl_strategy.record_access(test_key, hit=True)
            ttl_strategy.record_access(test_key, hit=False)
            
            assert test_key in ttl_strategy.access_patterns
            
            # Test frequency-based optimization
            freq_ttl = ttl_strategy.get_ttl("market:overview", access_frequency=UpdateFrequency.HIGH)
            static_ttl = ttl_strategy.get_ttl("market:overview", access_frequency=UpdateFrequency.STATIC)
            
            assert freq_ttl != static_ttl
            
            print_info(f"High frequency TTL: {freq_ttl}s")
            print_info(f"Static TTL: {static_ttl}s")
            
            # Test strategy summary
            summary = ttl_strategy.get_cache_strategy_summary()
            assert 'strategy' in summary
            assert 'performance' in summary
            
            self.test_results['ttl_strategy'] = True
            return True
            
        except Exception as e:
            logger.error(f"TTL strategy test failed: {e}")
            self.test_results['ttl_strategy'] = False
            return False
    
    async def test_batch_operations(self):
        """Test batch cache operations"""
        print(f"\n{Colors.BLUE}Testing Batch Operations...{Colors.NC}")
        
        try:
            from src.core.cache_adapter_pooled import cache_adapter
            from src.core.cache.batch_operations import BatchCacheManager
            
            batch_manager = BatchCacheManager(cache_adapter)
            
            # Test batch set
            test_data = {
                "batch:test:1": {"data": "test1", "timestamp": time.time()},
                "batch:test:2": {"data": "test2", "timestamp": time.time()},
                "batch:test:3": {"data": "test3", "timestamp": time.time()},
            }
            
            start_time = time.time()
            set_results = await batch_manager.multi_set(test_data, ttl=60)
            set_time = (time.time() - start_time) * 1000
            
            print_info(f"Batch set time: {set_time:.2f}ms")
            
            # Verify all sets succeeded
            success_count = sum(1 for result in set_results.values() if result)
            assert success_count == len(test_data)
            
            # Test batch get
            start_time = time.time()
            get_results = await batch_manager.multi_get(list(test_data.keys()))
            get_time = (time.time() - start_time) * 1000
            
            print_info(f"Batch get time: {get_time:.2f}ms")
            
            # Verify all gets succeeded
            assert len(get_results) == len(test_data)
            for key, expected_data in test_data.items():
                assert key in get_results
                assert get_results[key]['data'] == expected_data['data']
            
            # Test get_or_compute
            async def compute_func():
                return {"computed": True, "timestamp": time.time()}
            
            computed_result = await batch_manager.get_or_compute(
                "batch:test:computed", compute_func, ttl=30
            )
            assert computed_result is not None
            assert computed_result['computed'] is True
            
            # Test batch delete
            delete_results = await batch_manager.multi_delete(list(test_data.keys()) + ["batch:test:computed"])
            delete_count = sum(1 for result in delete_results.values() if result)
            assert delete_count >= len(test_data)  # Allow for already deleted keys
            
            # Performance metrics
            self.performance_metrics['batch_set_time'] = set_time
            self.performance_metrics['batch_get_time'] = get_time
            
            print_info(f"Batch operations performance: Set {set_time:.1f}ms, Get {get_time:.1f}ms")
            
            self.test_results['batch_operations'] = True
            return True
            
        except Exception as e:
            logger.error(f"Batch operations test failed: {e}")
            self.test_results['batch_operations'] = False
            return False
    
    async def test_cache_warming(self):
        """Test cache warming service"""
        print(f"\n{Colors.BLUE}Testing Cache Warming Service...{Colors.NC}")
        
        try:
            from src.core.cache_adapter_pooled import cache_adapter
            from src.core.cache.batch_operations import BatchCacheManager
            from src.core.cache.ttl_strategy import TTLStrategy
            from src.core.cache.warming import CacheWarmingService
            
            batch_manager = BatchCacheManager(cache_adapter)
            ttl_strategy = TTLStrategy()
            warming_service = CacheWarmingService(cache_adapter, batch_manager, ttl_strategy)
            
            # Test service initialization
            await warming_service.start()
            assert warming_service._running
            
            print_info("Warming service started")
            
            # Test access pattern recording
            test_key = "warm:test:pattern"
            warming_service.record_access(test_key, hit=True)
            warming_service.record_access(test_key, hit=False)
            
            assert test_key in warming_service.access_patterns
            pattern = warming_service.access_patterns[test_key]
            assert len(pattern.access_times) == 2
            
            # Test manual warming
            warming_keys = ["warm:test:1", "warm:test:2"]
            warm_results = await warming_service.manual_warm(warming_keys)
            
            print_info(f"Manual warming results: {warm_results}")
            
            # Test critical path warming
            critical_results = await warming_service.warm_critical_paths()
            
            print_info(f"Critical path warming: {len(critical_results)} paths")
            
            # Test statistics
            stats = warming_service.get_warming_stats()
            assert 'service' in stats
            assert 'statistics' in stats
            assert stats['service'] == 'cache_warming'
            
            print_info(f"Warming statistics: {stats['statistics']}")
            
            # Test shutdown
            await warming_service.stop()
            assert not warming_service._running
            
            print_info("Warming service stopped")
            
            self.test_results['cache_warming'] = True
            return True
            
        except Exception as e:
            logger.error(f"Cache warming test failed: {e}")
            self.test_results['cache_warming'] = False
            return False
    
    async def test_websocket_broadcaster(self):
        """Test WebSocket broadcaster"""
        print(f"\n{Colors.BLUE}Testing WebSocket Broadcaster...{Colors.NC}")
        
        try:
            from src.api.websocket.smart_broadcaster import SmartWebSocketBroadcaster, MessageType, Priority
            
            broadcaster = SmartWebSocketBroadcaster()
            
            # Test initialization
            await broadcaster.start()
            assert broadcaster._running
            
            print_info("WebSocket broadcaster started")
            
            # Test message queuing (without actual WebSocket connections)
            test_data = {"test": "message", "timestamp": time.time()}
            
            # This will queue but not deliver due to no connections
            await broadcaster.broadcast_update(
                "test_topic", test_data, MessageType.MARKET_UPDATE, Priority.MEDIUM
            )
            
            # Test statistics
            stats = broadcaster.get_statistics()
            assert 'active_clients' in stats
            assert 'queue_size' in stats
            
            print_info(f"Broadcaster stats: Active clients: {stats['active_clients']}")
            
            # Test client info (empty since no real clients)
            client_info = broadcaster.get_client_info()
            assert isinstance(client_info, list)
            
            # Test shutdown
            await broadcaster.stop()
            assert not broadcaster._running
            
            print_info("WebSocket broadcaster stopped")
            
            self.test_results['websocket_broadcaster'] = True
            return True
            
        except Exception as e:
            logger.error(f"WebSocket broadcaster test failed: {e}")
            self.test_results['websocket_broadcaster'] = False
            return False
    
    async def test_unified_dashboard(self):
        """Test unified dashboard service"""
        print(f"\n{Colors.BLUE}Testing Unified Dashboard Service...{Colors.NC}")
        
        try:
            from src.core.cache_adapter_pooled import cache_adapter
            from src.core.cache.batch_operations import BatchCacheManager
            from src.api.services.unified_dashboard import UnifiedDashboardService
            
            batch_manager = BatchCacheManager(cache_adapter)
            dashboard_service = UnifiedDashboardService(cache_adapter, batch_manager)
            
            # Test desktop view data
            start_time = time.time()
            desktop_data = await dashboard_service.get_comprehensive_data("desktop")
            desktop_time = (time.time() - start_time) * 1000
            
            assert isinstance(desktop_data, dict)
            assert '_metadata' in desktop_data
            assert desktop_data['_metadata']['view_type'] == 'desktop'
            
            print_info(f"Desktop data fetch time: {desktop_time:.2f}ms")
            
            # Test mobile view data
            start_time = time.time()
            mobile_data = await dashboard_service.get_comprehensive_data("mobile")
            mobile_time = (time.time() - start_time) * 1000
            
            assert isinstance(mobile_data, dict)
            assert '_metadata' in mobile_data
            assert mobile_data['_metadata']['view_type'] == 'mobile'
            
            print_info(f"Mobile data fetch time: {mobile_time:.2f}ms")
            
            # Test service statistics
            service_stats = dashboard_service.get_service_stats()
            assert 'service' in service_stats
            assert service_stats['service'] == 'unified_dashboard'
            
            print_info(f"Service stats: {service_stats['statistics']}")
            
            # Performance metrics
            self.performance_metrics['desktop_fetch_time'] = desktop_time
            self.performance_metrics['mobile_fetch_time'] = mobile_time
            
            self.test_results['unified_dashboard'] = True
            return True
            
        except Exception as e:
            logger.error(f"Unified dashboard test failed: {e}")
            self.test_results['unified_dashboard'] = False
            return False
    
    async def test_performance_benchmarks(self):
        """Run performance benchmarks"""
        print(f"\n{Colors.BLUE}Running Performance Benchmarks...{Colors.NC}")
        
        try:
            from src.core.cache_adapter_pooled import cache_adapter
            from src.core.cache.batch_operations import BatchCacheManager
            
            batch_manager = BatchCacheManager(cache_adapter)
            
            # Benchmark 1: Single cache operations
            print_info("Benchmark 1: Single cache operations")
            
            single_ops_times = []
            for i in range(10):
                start_time = time.time()
                await cache_adapter.set(f"bench:single:{i}", {"data": f"test{i}"}, 30)
                result = await cache_adapter.get(f"bench:single:{i}")
                await cache_adapter.delete(f"bench:single:{i}")
                single_ops_times.append((time.time() - start_time) * 1000)
            
            avg_single_time = sum(single_ops_times) / len(single_ops_times)
            print_info(f"Average single operation time: {avg_single_time:.2f}ms")
            
            # Benchmark 2: Batch operations
            print_info("Benchmark 2: Batch operations")
            
            batch_data = {f"bench:batch:{i}": {"data": f"test{i}"} for i in range(10)}
            
            start_time = time.time()
            await batch_manager.multi_set(batch_data, ttl=30)
            batch_results = await batch_manager.multi_get(list(batch_data.keys()))
            await batch_manager.multi_delete(list(batch_data.keys()))
            batch_time = (time.time() - start_time) * 1000
            
            print_info(f"Batch operation time (10 items): {batch_time:.2f}ms")
            
            # Calculate improvement
            equivalent_single_time = avg_single_time * 10
            improvement = ((equivalent_single_time - batch_time) / equivalent_single_time) * 100
            
            print_info(f"Batch vs Single improvement: {improvement:.1f}%")
            
            # Benchmark 3: Cache hit performance
            print_info("Benchmark 3: Cache hit performance")
            
            # Pre-populate cache
            test_key = "bench:hit:test"
            await cache_adapter.set(test_key, {"cached": "data"}, 60)
            
            hit_times = []
            for _ in range(20):
                start_time = time.time()
                result = await cache_adapter.get(test_key)
                hit_times.append((time.time() - start_time) * 1000)
            
            avg_hit_time = sum(hit_times) / len(hit_times)
            print_info(f"Average cache hit time: {avg_hit_time:.2f}ms")
            
            # Cleanup
            await cache_adapter.delete(test_key)
            
            # Store performance metrics
            self.performance_metrics.update({
                'avg_single_operation_time': avg_single_time,
                'batch_operation_time': batch_time,
                'batch_improvement_percent': improvement,
                'avg_cache_hit_time': avg_hit_time
            })
            
            self.test_results['performance_benchmarks'] = True
            return True
            
        except Exception as e:
            logger.error(f"Performance benchmarks failed: {e}")
            self.test_results['performance_benchmarks'] = False
            return False
    
    async def test_integration(self):
        """Test integration of all components"""
        print(f"\n{Colors.BLUE}Testing Integration...{Colors.NC}")
        
        try:
            from src.core.cache_adapter_pooled import cache_adapter
            from src.core.cache.batch_operations import BatchCacheManager
            from src.core.cache.ttl_strategy import TTLStrategy
            from src.core.cache.key_generator import CacheKeyGenerator
            
            batch_manager = BatchCacheManager(cache_adapter)
            ttl_strategy = TTLStrategy()
            
            # Test integrated workflow
            print_info("Testing integrated dashboard data workflow")
            
            # Generate keys using key generator
            dashboard_key = CacheKeyGenerator.dashboard_data()
            mobile_key = CacheKeyGenerator.mobile_overview()
            
            # Calculate TTLs using strategy
            dashboard_ttl = ttl_strategy.get_ttl(dashboard_key)
            mobile_ttl = ttl_strategy.get_ttl(mobile_key)
            
            # Use batch operations to set data
            integrated_data = {
                dashboard_key: {
                    "signals": [{"symbol": "BTCUSDT", "score": 85}],
                    "timestamp": time.time()
                },
                mobile_key: {
                    "market_regime": "BULLISH",
                    "volatility": 15.5,
                    "timestamp": time.time()
                }
            }
            
            # Set with calculated TTLs
            set_results = await batch_manager.multi_set(integrated_data)
            assert all(set_results.values())
            
            # Record access patterns
            ttl_strategy.record_access(dashboard_key, hit=True)
            ttl_strategy.record_access(mobile_key, hit=True)
            
            # Retrieve using batch operations
            retrieved_data = await batch_manager.multi_get([dashboard_key, mobile_key])
            assert len(retrieved_data) == 2
            assert dashboard_key in retrieved_data
            assert mobile_key in retrieved_data
            
            # Verify data integrity
            assert retrieved_data[dashboard_key]['signals'][0]['symbol'] == 'BTCUSDT'
            assert retrieved_data[mobile_key]['market_regime'] == 'BULLISH'
            
            print_info("Integrated workflow completed successfully")
            
            # Test error handling
            print_info("Testing error handling")
            
            # Try to get non-existent keys
            empty_results = await batch_manager.multi_get(["non:existent:1", "non:existent:2"])
            assert len(empty_results) == 0
            
            # Test invalid operations
            invalid_results = await batch_manager.multi_set({})
            assert len(invalid_results) == 0
            
            # Cleanup
            await batch_manager.multi_delete([dashboard_key, mobile_key])
            
            print_info("Error handling tests passed")
            
            self.test_results['integration'] = True
            return True
            
        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            self.test_results['integration'] = False
            return False
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        report = {
            "test_execution": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(self.test_results),
                "passed_tests": sum(1 for result in self.test_results.values() if result),
                "success_rate": sum(1 for result in self.test_results.values() if result) / len(self.test_results) * 100
            },
            "test_results": self.test_results,
            "performance_metrics": self.performance_metrics,
            "recommendations": []
        }
        
        # Add recommendations based on results
        if report["test_execution"]["success_rate"] == 100:
            report["recommendations"].append("✅ All tests passed - Ready for VPS deployment")
        else:
            failed_tests = [test for test, result in self.test_results.items() if not result]
            report["recommendations"].append(f"❌ Failed tests: {', '.join(failed_tests)}")
            report["recommendations"].append("⚠️ Review failed components before deploying")
        
        if self.performance_metrics.get('batch_improvement_percent', 0) > 50:
            report["recommendations"].append("🚀 Excellent batch operation performance")
        
        if self.performance_metrics.get('avg_cache_hit_time', 100) < 5:
            report["recommendations"].append("⚡ Exceptional cache hit performance")
        
        return report

async def main():
    """Main test execution"""
    print(f"{Colors.BLUE}🧪 Virtuoso CCXT - Cache Optimization Local Testing{Colors.NC}")
    print(f"Testing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tester = CacheOptimizationTester()
    
    try:
        # Run all tests
        success = await tester.run_all_tests()
        
        # Generate report
        report = tester.generate_test_report()
        
        # Save report
        report_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/test_reports/cache_optimization_test_report.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n{Colors.BLUE}📊 Test Report Generated{Colors.NC}")
        print(f"Report saved to: {report_path}")
        
        # Display performance summary
        if tester.performance_metrics:
            print(f"\n{Colors.BLUE}⚡ Performance Summary{Colors.NC}")
            for metric, value in tester.performance_metrics.items():
                print(f"  {metric}: {value:.2f}ms" if 'time' in metric else f"  {metric}: {value}")
        
        # Display recommendations
        if report["recommendations"]:
            print(f"\n{Colors.BLUE}📋 Recommendations{Colors.NC}")
            for rec in report["recommendations"]:
                print(f"  {rec}")
        
        return success
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️ Test suite interrupted by user{Colors.NC}")
        return False
    except Exception as e:
        print_error(f"Test suite failed: {e}")
        logger.exception("Test suite error")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)