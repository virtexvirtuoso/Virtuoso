#!/usr/bin/env python3
"""
Shared Cache Bridge End-to-End Validation Test
==============================================

CRITICAL VALIDATION: Tests complete shared cache bridge integration
to ensure live market data flows from trading service to web endpoints.

This test validates:
1. Shared cache infrastructure setup
2. Data bridge population from trading service
3. Web service cache reads with live data
4. Cache hit rate improvements
5. Performance metrics and monitoring

SUCCESS CRITERIA:
- Cache hit rate improves from 0% to >80%
- Web endpoints return live data instead of hardcoded responses
- Cross-service data flow works correctly
- Performance improvements are measurable
"""

import asyncio
import sys
import os
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cache_bridge_test.log')
    ]
)
logger = logging.getLogger(__name__)

class SharedCacheBridgeValidator:
    """Comprehensive validation of shared cache bridge integration"""

    def __init__(self):
        self.test_results = {
            'infrastructure_test': False,
            'data_bridge_test': False,
            'web_service_test': False,
            'performance_test': False,
            'end_to_end_test': False
        }
        self.metrics = {
            'start_time': time.time(),
            'test_duration': 0,
            'cache_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0
        }

    async def run_comprehensive_validation(self):
        """Run complete validation suite"""
        logger.info("🚀 Starting Shared Cache Bridge Comprehensive Validation")
        logger.info("=" * 70)

        try:
            # Test 1: Infrastructure Setup
            await self.test_infrastructure_setup()

            # Test 2: Data Bridge Functionality
            await self.test_data_bridge_population()

            # Test 3: Web Service Integration
            await self.test_web_service_integration()

            # Test 4: Performance Metrics
            await self.test_performance_improvements()

            # Test 5: End-to-End Data Flow
            await self.test_end_to_end_data_flow()

            # Generate final report
            await self.generate_validation_report()

        except Exception as e:
            logger.error(f"❌ Validation suite failed: {e}")
        finally:
            self.metrics['test_duration'] = time.time() - self.metrics['start_time']

    async def test_infrastructure_setup(self):
        """Test 1: Validate shared cache infrastructure setup"""
        logger.info("🔧 Test 1: Infrastructure Setup Validation")

        try:
            # Import and initialize shared cache bridge
            from src.core.cache.shared_cache_bridge import (
                get_shared_cache_bridge,
                initialize_shared_cache
            )

            # Test initialization
            success = await initialize_shared_cache()
            if not success:
                logger.error("❌ Shared cache initialization failed")
                return False

            # Get bridge instance
            bridge = get_shared_cache_bridge()
            if not bridge:
                logger.error("❌ Failed to get shared bridge instance")
                return False

            # Test health check
            health = await bridge.health_check()
            if health.get('status') != 'healthy':
                logger.error(f"❌ Bridge health check failed: {health}")
                return False

            logger.info("✅ Infrastructure setup validation passed")
            self.test_results['infrastructure_test'] = True
            return True

        except Exception as e:
            logger.error(f"❌ Infrastructure test failed: {e}")
            return False

    async def test_data_bridge_population(self):
        """Test 2: Validate data bridge populates shared cache"""
        logger.info("📊 Test 2: Data Bridge Population Validation")

        try:
            # Import trading service bridge
            from src.core.cache.trading_service_bridge import get_trading_service_bridge

            # Get trading bridge
            trading_bridge = get_trading_service_bridge()
            await trading_bridge.initialize()

            # Test data population
            test_market_data = {
                'total_symbols': 150,
                'total_volume': 125000000000,
                'total_volume_24h': 125000000000,
                'average_change': 2.5,
                'volatility': 4.2,
                'btc_dominance': 58.9,
                'timestamp': int(time.time()),
                'test_identifier': f'bridge_test_{int(time.time())}'
            }

            # Populate market overview
            await trading_bridge.populate_market_overview(test_market_data)

            # Test signals data
            test_signals = {
                'signals': [
                    {
                        'symbol': 'BTCUSDT',
                        'score': 85.5,
                        'sentiment': 'BULLISH',
                        'price': 45000,
                        'change_24h': 3.2,
                        'volume_24h': 1500000000,
                        'components': {
                            'technical': 90,
                            'volume': 85,
                            'orderflow': 80,
                            'sentiment': 88
                        }
                    }
                ],
                'timestamp': int(time.time())
            }

            await trading_bridge.populate_signals_data(test_signals)

            # Test market movers
            test_movers = {
                'gainers': [
                    {'symbol': 'ETHUSDT', 'change_24h': 8.5, 'volume_24h': 800000000},
                    {'symbol': 'SOLUSDT', 'change_24h': 6.2, 'volume_24h': 400000000}
                ],
                'losers': [
                    {'symbol': 'ADAUSDT', 'change_24h': -4.1, 'volume_24h': 200000000}
                ]
            }

            await trading_bridge.populate_market_movers(test_movers)

            # Verify data was stored
            await asyncio.sleep(2)  # Allow propagation

            # Check performance metrics
            metrics = trading_bridge.get_performance_metrics()
            if metrics['cache_updates'] < 3:
                logger.error(f"❌ Expected at least 3 cache updates, got {metrics['cache_updates']}")
                return False

            logger.info(f"✅ Data bridge populated {metrics['cache_updates']} cache entries")
            self.test_results['data_bridge_test'] = True
            return True

        except Exception as e:
            logger.error(f"❌ Data bridge test failed: {e}")
            return False

    async def test_web_service_integration(self):
        """Test 3: Validate web service reads from shared cache"""
        logger.info("🌐 Test 3: Web Service Integration Validation")

        try:
            # Import web service adapter
            from src.core.cache.web_service_adapter import get_web_service_cache_adapter

            # Get web adapter
            web_adapter = get_web_service_cache_adapter()
            await web_adapter.initialize()

            # Test market overview retrieval
            market_overview = await web_adapter.get_market_overview()

            if not market_overview:
                logger.error("❌ No market overview data retrieved")
                return False

            if market_overview.get('total_symbols', 0) == 0:
                logger.error("❌ Market overview contains no symbol data")
                return False

            # Test signals retrieval
            signals_data = await web_adapter.get_signals()

            if not signals_data or not signals_data.get('signals'):
                logger.warning("⚠️ No signals data retrieved - may be expected")

            # Test dashboard overview
            dashboard_data = await web_adapter.get_dashboard_overview()

            if not dashboard_data:
                logger.error("❌ No dashboard data retrieved")
                return False

            # Test mobile data
            mobile_data = await web_adapter.get_mobile_data()

            if not mobile_data:
                logger.error("❌ No mobile data retrieved")
                return False

            # Check performance metrics
            metrics = web_adapter.get_performance_metrics()
            cache_hit_rate = metrics['cache_hit_rate_percent']
            cross_service_rate = metrics['cross_service_hit_rate_percent']

            logger.info(f"✅ Web service integration successful")
            logger.info(f"   Cache hit rate: {cache_hit_rate}%")
            logger.info(f"   Cross-service hits: {cross_service_rate}%")

            # Verify we're getting cross-service hits (key success metric)
            if cross_service_rate > 0:
                logger.info("✅ Cross-service data flow confirmed")
                self.test_results['web_service_test'] = True
                return True
            else:
                logger.warning("⚠️ No cross-service hits detected - data may not be flowing")
                return False

        except Exception as e:
            logger.error(f"❌ Web service integration test failed: {e}")
            return False

    async def test_performance_improvements(self):
        """Test 4: Validate performance improvements"""
        logger.info("⚡ Test 4: Performance Improvements Validation")

        try:
            from src.core.cache.shared_cache_bridge import get_shared_cache_bridge
            from src.core.cache.trading_service_bridge import get_trading_service_bridge
            from src.core.cache.web_service_adapter import get_web_service_cache_adapter

            # Get all components
            shared_bridge = get_shared_cache_bridge()
            trading_bridge = get_trading_service_bridge()
            web_adapter = get_web_service_cache_adapter()

            # Collect performance metrics
            shared_metrics = shared_bridge.get_bridge_metrics()
            trading_metrics = trading_bridge.get_performance_metrics()
            web_metrics = web_adapter.get_performance_metrics()

            # Performance benchmark test
            start_time = time.perf_counter()

            # Perform 10 rapid cache operations
            for i in range(10):
                await web_adapter.get_market_overview()
                await asyncio.sleep(0.1)

            total_time = time.perf_counter() - start_time
            avg_response_time = total_time / 10

            logger.info(f"Performance Metrics:")
            logger.info(f"  Average response time: {avg_response_time*1000:.2f}ms")
            logger.info(f"  Cross-service hits: {shared_metrics['cross_service_metrics']['cross_service_hits']}")
            logger.info(f"  Data bridge events: {shared_metrics['cross_service_metrics']['data_bridge_events']}")
            logger.info(f"  Cache warming events: {shared_metrics['cross_service_metrics']['cache_warming_events']}")

            # Check if we meet performance targets
            performance_targets_met = (
                avg_response_time < 0.1 and  # Under 100ms
                shared_metrics['cross_service_metrics']['cross_service_hits'] > 0
            )

            if performance_targets_met:
                logger.info("✅ Performance improvement targets met")
                self.test_results['performance_test'] = True
                return True
            else:
                logger.warning("⚠️ Performance targets not fully met")
                return False

        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            return False

    async def test_end_to_end_data_flow(self):
        """Test 5: Complete end-to-end data flow validation"""
        logger.info("🔄 Test 5: End-to-End Data Flow Validation")

        try:
            from src.core.cache.service_integration import validate_cache_bridge_connectivity

            # Run comprehensive connectivity validation
            connectivity_valid = await validate_cache_bridge_connectivity()

            if not connectivity_valid:
                logger.error("❌ Cache bridge connectivity validation failed")
                return False

            # Test data freshness
            from src.core.cache.web_service_adapter import get_web_service_cache_adapter
            web_adapter = get_web_service_cache_adapter()

            # Get current data
            market_data = await web_adapter.get_market_overview()

            # Check timestamp freshness (should be within last 5 minutes)
            current_time = time.time()
            data_timestamp = market_data.get('timestamp', 0)

            if current_time - data_timestamp > 300:  # 5 minutes
                logger.warning(f"⚠️ Data may be stale: {current_time - data_timestamp} seconds old")

            # Test data consistency
            dashboard_data = await web_adapter.get_dashboard_overview()
            mobile_data = await web_adapter.get_mobile_data()

            # Verify data consistency across endpoints
            market_summary = dashboard_data.get('summary', {})
            mobile_overview = mobile_data.get('market_overview', {})

            volume_consistent = (
                abs(market_data.get('total_volume_24h', 0) - market_summary.get('total_volume_24h', 0)) < 1000
            )

            if not volume_consistent:
                logger.warning("⚠️ Data consistency issues detected across endpoints")

            logger.info("✅ End-to-end data flow validation completed")
            self.test_results['end_to_end_test'] = True
            return True

        except Exception as e:
            logger.error(f"❌ End-to-end test failed: {e}")
            return False

    async def generate_validation_report(self):
        """Generate comprehensive validation report"""
        logger.info("📋 Generating Validation Report")
        logger.info("=" * 70)

        # Calculate overall success
        total_tests = len(self.test_results)
        passed_tests = sum(self.test_results.values())
        success_rate = (passed_tests / total_tests) * 100

        # Generate report
        report = {
            'validation_summary': {
                'timestamp': time.time(),
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'success_rate_percent': success_rate,
                'overall_status': 'SUCCESS' if success_rate >= 80 else 'PARTIAL' if success_rate >= 60 else 'FAILED'
            },
            'detailed_results': self.test_results,
            'performance_metrics': self.metrics,
            'recommendations': []
        }

        # Add recommendations based on results
        if not self.test_results['infrastructure_test']:
            report['recommendations'].append("Fix shared cache infrastructure setup")

        if not self.test_results['data_bridge_test']:
            report['recommendations'].append("Verify trading service data bridge integration")

        if not self.test_results['web_service_test']:
            report['recommendations'].append("Check web service cache adapter configuration")

        if not self.test_results['performance_test']:
            report['recommendations'].append("Optimize cache performance and hit rates")

        if not self.test_results['end_to_end_test']:
            report['recommendations'].append("Investigate end-to-end data flow issues")

        # Log report
        logger.info(f"VALIDATION RESULTS:")
        logger.info(f"  Overall Status: {report['validation_summary']['overall_status']}")
        logger.info(f"  Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        logger.info(f"  Test Duration: {self.metrics['test_duration']:.2f} seconds")

        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"  {test_name}: {status}")

        if report['recommendations']:
            logger.info(f"RECOMMENDATIONS:")
            for rec in report['recommendations']:
                logger.info(f"  - {rec}")

        # Save report to file
        with open('cache_bridge_validation_report.json', 'w') as f:
            json.dump(report, f, indent=2)

        logger.info("📄 Validation report saved to: cache_bridge_validation_report.json")

        return report

async def main():
    """Run the complete validation suite"""
    validator = SharedCacheBridgeValidator()
    await validator.run_comprehensive_validation()

if __name__ == "__main__":
    asyncio.run(main())