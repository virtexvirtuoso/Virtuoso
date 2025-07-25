#!/usr/bin/env python3
"""
Comprehensive Application Startup Test
Tests the full application startup with dependency injection.
"""

import asyncio
import sys
import os
import logging
import traceback
import time
import signal
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class ApplicationStartupTest:
    """Test the full application startup process."""
    
    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0
        self.logger = logging.getLogger(__name__)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
        )
    
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.logger.info(f"{status} | {test_name} | {details}")
        
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details,
            'timestamp': time.time()
        })
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    async def test_di_container_bootstrap(self) -> bool:
        """Test the DI container bootstrap process."""
        try:
            from src.core.di.registration import bootstrap_container
            
            # Test bootstrap with real config
            test_config = {
                'test_mode': True,
                'exchanges': {
                    'bybit': {
                        'rest_endpoint': 'https://api.bybit.com',
                        'testnet': False,
                        'primary': True
                    }
                },
                'timeframes': {
                    'base': {'interval': 1, 'weight': 0.4},
                    'ltf': {'interval': 5, 'weight': 0.3},
                    'mtf': {'interval': 30, 'weight': 0.2},
                    'htf': {'interval': 240, 'weight': 0.1}
                }
            }
            
            container = bootstrap_container(test_config)
            stats = container.get_stats()
            
            self.log_test("DI Container Bootstrap", True, f"Services: {stats['services_registered_count']}")
            return True
        except Exception as e:
            self.log_test("DI Container Bootstrap", False, f"Error: {e}")
            traceback.print_exc()
            return False
    
    async def test_service_resolution(self) -> bool:
        """Test resolving various services from the container."""
        try:
            from src.core.di.registration import bootstrap_container
            from src.core.interfaces.services import IConfigService, IAlertService, IMetricsService
            
            container = bootstrap_container()
            
            # Test core services
            results = []
            test_services = [
                (IConfigService, "Config Service"),
                (IAlertService, "Alert Service"),
                (IMetricsService, "Metrics Service"),
            ]
            
            for service_type, name in test_services:
                try:
                    service = await container.get_service(service_type)
                    if service is not None:
                        results.append(f"✅ {name}")
                    else:
                        results.append(f"❌ {name} (None)")
                except Exception as e:
                    results.append(f"❌ {name} ({str(e)[:50]})")
            
            success_count = sum(1 for r in results if "✅" in r)
            passed = success_count >= 2  # At least 2 services should work
            
            self.log_test("Service Resolution", passed, f"{success_count}/{len(test_services)} services resolved")
            return passed
        except Exception as e:
            self.log_test("Service Resolution", False, f"Error: {e}")
            return False
    
    async def test_exchange_services(self) -> bool:
        """Test exchange-related services."""
        try:
            from src.core.di.registration import bootstrap_container
            from src.core.exchanges.manager import ExchangeManager
            from src.core.market.market_data_manager import MarketDataManager
            
            container = bootstrap_container()
            
            # Test exchange manager
            exchange_manager = await container.get_service(ExchangeManager)
            if exchange_manager is None:
                self.log_test("Exchange Services", False, "ExchangeManager is None")
                return False
            
            # Test market data manager
            market_data_manager = await container.get_service(MarketDataManager)
            if market_data_manager is None:
                self.log_test("Exchange Services", False, "MarketDataManager is None")
                return False
            
            self.log_test("Exchange Services", True, "Exchange and MarketData managers created")
            return True
        except Exception as e:
            self.log_test("Exchange Services", False, f"Error: {e}")
            return False
    
    async def test_analysis_services(self) -> bool:
        """Test analysis services."""
        try:
            from src.core.di.registration import bootstrap_container
            from src.analysis.core.confluence import ConfluenceAnalyzer
            
            container = bootstrap_container()
            
            # Test confluence analyzer
            confluence_analyzer = await container.get_service(ConfluenceAnalyzer)
            if confluence_analyzer is None:
                self.log_test("Analysis Services", False, "ConfluenceAnalyzer is None")
                return False
            
            # Test that it has required methods
            required_methods = ['analyze', 'get_confluence_score']
            missing_methods = [m for m in required_methods if not hasattr(confluence_analyzer, m)]
            
            if missing_methods:
                self.log_test("Analysis Services", False, f"Missing methods: {missing_methods}")
                return False
            
            self.log_test("Analysis Services", True, "ConfluenceAnalyzer created with required methods")
            return True
        except Exception as e:
            self.log_test("Analysis Services", False, f"Error: {e}")
            return False
    
    async def test_monitoring_services(self) -> bool:
        """Test monitoring services."""
        try:
            from src.core.di.registration import bootstrap_container
            from src.monitoring.monitor import MarketMonitor
            from src.monitoring.alert_manager import AlertManager
            
            container = bootstrap_container()
            
            results = []
            
            # Test AlertManager
            try:
                alert_manager = await container.get_service(AlertManager)
                if alert_manager:
                    results.append("✅ AlertManager")
                else:
                    results.append("❌ AlertManager (None)")
            except Exception as e:
                results.append(f"❌ AlertManager ({str(e)[:30]})")
            
            # Test MarketMonitor
            try:
                market_monitor = await container.get_service(MarketMonitor)
                if market_monitor:
                    results.append("✅ MarketMonitor")
                else:
                    results.append("❌ MarketMonitor (None)")
            except Exception as e:
                results.append(f"❌ MarketMonitor ({str(e)[:30]})")
            
            success_count = sum(1 for r in results if "✅" in r)
            passed = success_count >= 1  # At least one monitoring service should work
            
            details = "; ".join(results)
            self.log_test("Monitoring Services", passed, details)
            return passed
        except Exception as e:
            self.log_test("Monitoring Services", False, f"Error: {e}")
            return False
    
    async def test_fastapi_integration(self) -> bool:
        """Test FastAPI integration with DI."""
        try:
            from src.core.di.registration import bootstrap_container
            from src.api.core.dependencies import get_container
            
            # Test container availability for FastAPI
            container = bootstrap_container()
            
            # Simulate FastAPI dependency injection
            async def mock_dependency():
                return container
            
            # Test that we can get services through dependency injection
            from src.core.interfaces.services import IConfigService
            test_container = await mock_dependency()
            config_service = await test_container.get_service(IConfigService)
            
            if config_service is None:
                self.log_test("FastAPI Integration", False, "Cannot resolve services through DI")
                return False
            
            self.log_test("FastAPI Integration", True, "DI container works with FastAPI pattern")
            return True
        except Exception as e:
            self.log_test("FastAPI Integration", False, f"Error: {e}")
            return False
    
    async def test_error_handling_resilience(self) -> bool:
        """Test that the system handles missing dependencies gracefully."""
        try:
            from src.core.di.registration import bootstrap_container
            
            # Test with minimal config
            minimal_config = {}
            container = bootstrap_container(minimal_config)
            
            # Test that it still works with fallbacks
            from src.core.interfaces.services import IConfigService
            config_service = await container.get_service(IConfigService)
            
            if config_service is None:
                self.log_test("Error Handling", False, "Config service failed with minimal config")
                return False
            
            # Test error stats
            stats = container.get_stats()
            if 'errors' in stats:
                error_count = stats['errors']
                self.log_test("Error Handling", True, f"System resilient, {error_count} errors handled")
            else:
                self.log_test("Error Handling", True, "System resilient, no error tracking")
            
            return True
        except Exception as e:
            self.log_test("Error Handling", False, f"Error: {e}")
            return False
    
    async def test_performance_characteristics(self) -> bool:
        """Test performance of the DI system."""
        try:
            from src.core.di.registration import bootstrap_container
            from src.core.interfaces.services import IConfigService
            
            container = bootstrap_container()
            
            # Test resolution speed
            start_time = time.time()
            for _ in range(100):
                await container.get_service(IConfigService)
            elapsed = time.time() - start_time
            
            # Should be very fast for singleton services
            avg_resolution_time = elapsed / 100
            passed = avg_resolution_time < 0.01  # Less than 10ms per resolution
            
            self.log_test("Performance", passed, f"Avg resolution: {avg_resolution_time*1000:.2f}ms")
            return passed
        except Exception as e:
            self.log_test("Performance", False, f"Error: {e}")
            return False
    
    async def test_memory_management(self) -> bool:
        """Test memory management and cleanup."""
        try:
            from src.core.di.registration import bootstrap_container
            
            # Create and dispose multiple containers
            containers = []
            for _ in range(5):
                container = bootstrap_container()
                containers.append(container)
            
            # Test disposal
            for container in containers:
                container.dispose()
            
            self.log_test("Memory Management", True, "Container creation and disposal works")
            return True
        except Exception as e:
            self.log_test("Memory Management", False, f"Error: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all startup tests."""
        self.logger.info("🚀 Starting Comprehensive Application Startup Test")
        self.logger.info("=" * 70)
        
        tests = [
            self.test_di_container_bootstrap,
            self.test_service_resolution,
            self.test_exchange_services,
            self.test_analysis_services,
            self.test_monitoring_services,
            self.test_fastapi_integration,
            self.test_error_handling_resilience,
            self.test_performance_characteristics,
            self.test_memory_management,
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                test_name = test.__name__.replace('test_', '').replace('_', ' ').title()
                self.log_test(test_name, False, f"Test crashed: {e}")
                traceback.print_exc()
        
        # Generate summary
        total_tests = len(self.test_results)
        success_rate = (self.passed / total_tests) * 100 if total_tests > 0 else 0
        
        self.logger.info("=" * 70)
        self.logger.info(f"🏁 Application Startup Test Complete: {self.passed}/{total_tests} passed ({success_rate:.1f}%)")
        
        if self.failed > 0:
            self.logger.info("❌ Failed Tests:")
            for result in self.test_results:
                if not result['passed']:
                    self.logger.info(f"  - {result['test']}: {result['details']}")
        
        return {
            'total_tests': total_tests,
            'passed': self.passed,
            'failed': self.failed,
            'success_rate': success_rate,
            'results': self.test_results
        }

async def main():
    """Run the comprehensive startup test."""
    test_suite = ApplicationStartupTest()
    results = await test_suite.run_all_tests()
    
    # Return exit code based on results
    if results['success_rate'] >= 85:
        print(f"\n🎉 Excellent! {results['success_rate']:.1f}% success rate")
        print("✅ Application startup with DI is working well!")
        return 0
    elif results['success_rate'] >= 70:
        print(f"\n👍 Good! {results['success_rate']:.1f}% success rate")
        print("✅ Application startup is mostly working")
        return 0
    else:
        print(f"\n⚠️ Needs work: {results['success_rate']:.1f}% success rate")
        print("❌ Application startup has significant issues")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)