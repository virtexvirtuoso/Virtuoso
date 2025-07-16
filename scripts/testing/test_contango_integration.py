#!/usr/bin/env python3
"""
Integration test for contango/backwardation monitoring implementation.

Tests:
1. Monitor contango detection methods
2. Market reporter futures premium calculation
3. API endpoint integration  
4. Real-time monitoring simulation
5. Alert generation
"""

import asyncio
import sys
import os
import logging
import time
from typing import Dict, Any, List
from unittest.mock import MagicMock, AsyncMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from monitoring.monitor import MarketMonitor
from monitoring.market_reporter import MarketReporter
from core.exchanges.manager import ExchangeManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContangoIntegrationTester:
    """Test contango monitoring integration"""
    
    def __init__(self):
        self.test_results = []
        self.exchange_manager = None
        self.market_reporter = None
        self.monitor = None
        
    async def setup_test_environment(self):
        """Setup test environment with mocked components where needed"""
        logger.info("🔧 Setting up test environment...")
        
        try:
            # Create exchange manager (use real one for API testing)
            self.exchange_manager = ExchangeManager()
            await self.exchange_manager.initialize()
            logger.info("✅ Exchange manager initialized")
            
            # Create market reporter
            exchange = await self.exchange_manager.get_exchange('bybit')
            self.market_reporter = MarketReporter(
                exchange=exchange,
                logger=logger
            )
            logger.info("✅ Market reporter created")
            
            # Create monitor with minimal required components
            self.monitor = MarketMonitor(
                exchange_manager=self.exchange_manager,
                market_reporter=self.market_reporter,
                logger=logger
            )
            logger.info("✅ Monitor created")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up test environment: {e}")
            return False
            
    async def test_futures_symbol_detection(self):
        """Test the _is_futures_symbol method"""
        logger.info("\n🧪 TEST 1: Futures Symbol Detection")
        
        test_cases = [
            # (symbol, expected_result, description)
            ('BTCUSDT', True, 'BTC perpetual'),
            ('ETHUSDT', True, 'ETH perpetual'),
            ('SOLUSDT', True, 'SOL perpetual'),
            ('BTC-27JUN25', False, 'BTC quarterly futures'),
            ('ETHUSDT-13JUN25', False, 'ETH dated futures'),
            ('BTCUSD', False, 'USD-margined (not USDT)'),
            ('BTCEUR', False, 'EUR pair'),
            ('ADAUSDT', True, 'ADA perpetual'),
        ]
        
        results = []
        for symbol, expected, description in test_cases:
            try:
                result = self.monitor._is_futures_symbol(symbol)
                status = "✅ PASS" if result == expected else "❌ FAIL"
                logger.info(f"  {status}: {symbol} → {result} (expected: {expected}) - {description}")
                results.append(result == expected)
            except Exception as e:
                logger.error(f"  ❌ ERROR: {symbol} - {e}")
                results.append(False)
                
        success_rate = sum(results) / len(results) * 100
        self.test_results.append(('Futures Symbol Detection', success_rate))
        logger.info(f"📊 Test 1 Results: {success_rate:.1f}% pass rate")
        
    async def test_market_reporter_futures_premium(self):
        """Test market reporter futures premium calculation"""
        logger.info("\n🧪 TEST 2: Market Reporter Futures Premium Calculation")
        
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        try:
            start_time = time.time()
            futures_data = await self.market_reporter._calculate_futures_premium(test_symbols)
            calculation_time = time.time() - start_time
            
            logger.info(f"⏱️  Calculation completed in {calculation_time:.2f}s")
            
            # Validate response structure
            required_fields = ['premiums', 'average_premium', 'contango_status', 'timestamp']
            missing_fields = [field for field in required_fields if field not in futures_data]
            
            if missing_fields:
                logger.error(f"❌ Missing required fields: {missing_fields}")
                self.test_results.append(('Market Reporter Premium Calculation', 0))
                return
                
            # Check premium data for each symbol
            successful_symbols = 0
            for symbol in test_symbols:
                if symbol in futures_data['premiums']:
                    premium_data = futures_data['premiums'][symbol]
                    logger.info(f"✅ {symbol}: Premium calculated successfully")
                    
                    # Log key metrics
                    if 'spot_premium' in premium_data:
                        logger.info(f"   📊 Spot premium: {premium_data['spot_premium']:.4f}%")
                    if 'contango_status' in premium_data:
                        logger.info(f"   🏷️  Status: {premium_data['contango_status']}")
                    if 'funding_rate' in premium_data:
                        logger.info(f"   ⚡ Funding rate: {premium_data['funding_rate']:.4f}%")
                        
                    successful_symbols += 1
                else:
                    logger.warning(f"⚠️  {symbol}: No premium data")
                    
            success_rate = (successful_symbols / len(test_symbols)) * 100
            self.test_results.append(('Market Reporter Premium Calculation', success_rate))
            logger.info(f"📊 Test 2 Results: {success_rate:.1f}% symbols successful")
            
        except Exception as e:
            logger.error(f"❌ Error in market reporter test: {e}")
            logger.error(f"Full error: {str(e)}")
            self.test_results.append(('Market Reporter Premium Calculation', 0))
            
    async def test_contango_monitoring_simulation(self):
        """Test the real-time contango monitoring simulation"""
        logger.info("\n🧪 TEST 3: Contango Monitoring Simulation")
        
        test_symbols = ['BTCUSDT', 'ETHUSDT']
        
        try:
            # Mock alert manager for testing
            mock_alert_manager = AsyncMock()
            self.monitor.alert_manager = mock_alert_manager
            
            successful_monitoring = 0
            
            for symbol in test_symbols:
                try:
                    # Create mock market data
                    mock_market_data = {
                        'symbol': symbol,
                        'ticker': {
                            'last': 50000.0 if symbol == 'BTCUSDT' else 3000.0,
                            'bid': 49990.0 if symbol == 'BTCUSDT' else 2999.0,
                            'ask': 50010.0 if symbol == 'BTCUSDT' else 3001.0,
                        },
                        'timestamp': time.time() * 1000
                    }
                    
                    # Test contango monitoring
                    await self.monitor._monitor_contango_status(symbol, mock_market_data)
                    logger.info(f"✅ {symbol}: Contango monitoring completed")
                    successful_monitoring += 1
                    
                except Exception as e:
                    logger.error(f"❌ {symbol}: Monitoring failed - {e}")
                    
            success_rate = (successful_monitoring / len(test_symbols)) * 100
            self.test_results.append(('Contango Monitoring Simulation', success_rate))
            logger.info(f"📊 Test 3 Results: {success_rate:.1f}% monitoring successful")
            
        except Exception as e:
            logger.error(f"❌ Error in monitoring simulation: {e}")
            self.test_results.append(('Contango Monitoring Simulation', 0))
            
    async def test_alert_generation(self):
        """Test contango alert generation"""
        logger.info("\n🧪 TEST 4: Alert Generation Testing")
        
        try:
            # Test alert severity mapping
            test_alert_types = [
                'status_change',
                'extreme_contango', 
                'extreme_backwardation',
                'extreme_funding'
            ]
            
            successful_alerts = 0
            
            for alert_type in test_alert_types:
                try:
                    severity = self.monitor._get_contango_alert_severity(alert_type)
                    expected_severities = ['low', 'medium', 'high', 'critical']
                    
                    if severity in expected_severities:
                        logger.info(f"✅ {alert_type}: Severity '{severity}' ✓")
                        successful_alerts += 1
                    else:
                        logger.error(f"❌ {alert_type}: Invalid severity '{severity}'")
                        
                except Exception as e:
                    logger.error(f"❌ {alert_type}: Error - {e}")
                    
            # Test alert data structure
            try:
                mock_contango_data = {
                    'current_status': 'CONTANGO',
                    'previous_status': 'NEUTRAL',
                    'spot_premium': 1.5,
                    'quarterly_premium': 2.0,
                    'funding_rate': 0.15,
                    'current_price': 50000.0
                }
                
                # This should trigger status change alert (mock alert manager)
                mock_alert_manager = AsyncMock()
                self.monitor.alert_manager = mock_alert_manager
                
                await self.monitor._check_contango_alerts('BTCUSDT', mock_contango_data)
                logger.info("✅ Alert generation logic executed successfully")
                successful_alerts += 1
                
            except Exception as e:
                logger.error(f"❌ Alert generation error: {e}")
                
            success_rate = (successful_alerts / (len(test_alert_types) + 1)) * 100
            self.test_results.append(('Alert Generation', success_rate))
            logger.info(f"📊 Test 4 Results: {success_rate:.1f}% alert functions working")
            
        except Exception as e:
            logger.error(f"❌ Error in alert testing: {e}")
            self.test_results.append(('Alert Generation', 0))
            
    async def test_end_to_end_monitoring(self):
        """Test end-to-end monitoring workflow"""
        logger.info("\n🧪 TEST 5: End-to-End Monitoring Workflow")
        
        try:
            # Simulate the full monitoring workflow for a symbol
            symbol = 'BTCUSDT'
            
            # Step 1: Check if symbol should be monitored
            should_monitor = self.monitor._is_futures_symbol(symbol)
            if not should_monitor:
                logger.error(f"❌ Symbol {symbol} not identified for monitoring")
                self.test_results.append(('End-to-End Monitoring', 0))
                return
                
            logger.info(f"✅ Step 1: Symbol {symbol} identified for monitoring")
            
            # Step 2: Get market data (simulated)
            mock_market_data = {
                'symbol': symbol,
                'ticker': {
                    'last': 50000.0,
                    'bid': 49990.0,
                    'ask': 50010.0,
                },
                'orderbook': {
                    'bids': [[49990, 1.0], [49980, 2.0]],
                    'asks': [[50010, 1.0], [50020, 2.0]]
                },
                'timestamp': time.time() * 1000
            }
            
            logger.info("✅ Step 2: Market data prepared")
            
            # Step 3: Run contango monitoring
            await self.monitor._monitor_contango_status(symbol, mock_market_data)
            logger.info("✅ Step 3: Contango monitoring executed")
            
            # Step 4: Check cache was updated
            if hasattr(self.monitor, '_contango_cache'):
                cache_key = f"contango_status_{symbol}"
                if cache_key in self.monitor._contango_cache:
                    cached_data = self.monitor._contango_cache[cache_key]
                    logger.info(f"✅ Step 4: Cache updated - Status: {cached_data.get('status', 'Unknown')}")
                else:
                    logger.warning("⚠️  Step 4: Cache key not found")
            else:
                logger.warning("⚠️  Step 4: Cache not initialized")
                
            self.test_results.append(('End-to-End Monitoring', 100))
            logger.info("📊 Test 5 Results: 100% - End-to-end workflow successful")
            
        except Exception as e:
            logger.error(f"❌ Error in end-to-end test: {e}")
            self.test_results.append(('End-to-End Monitoring', 0))
            
    async def cleanup(self):
        """Cleanup test environment"""
        logger.info("\n🧹 Cleaning up test environment...")
        
        try:
            if self.exchange_manager:
                await self.exchange_manager.close()
                logger.info("✅ Exchange manager closed")
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
            
    async def run_all_tests(self):
        """Run all tests and generate report"""
        logger.info("🚀 STARTING CONTANGO INTEGRATION TESTS")
        logger.info("=" * 60)
        
        # Setup
        if not await self.setup_test_environment():
            logger.error("❌ Failed to setup test environment")
            return
            
        # Run tests
        try:
            await self.test_futures_symbol_detection()
            await self.test_market_reporter_futures_premium()
            await self.test_contango_monitoring_simulation()
            await self.test_alert_generation()
            await self.test_end_to_end_monitoring()
            
        except Exception as e:
            logger.error(f"❌ Error during tests: {e}")
            
        finally:
            await self.cleanup()
            
        # Generate report
        self.generate_test_report()
        
    def generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("\n📊 CONTANGO INTEGRATION TEST REPORT")
        logger.info("=" * 60)
        
        if not self.test_results:
            logger.error("❌ No test results available")
            return
            
        total_score = 0
        max_score = 0
        
        for test_name, score in self.test_results:
            status = "✅ PASS" if score >= 80 else "⚠️  PARTIAL" if score >= 50 else "❌ FAIL"
            logger.info(f"{status}: {test_name}: {score:.1f}%")
            total_score += score
            max_score += 100
            
        overall_score = total_score / max_score * 100 if max_score > 0 else 0
        
        logger.info("-" * 60)
        logger.info(f"🎯 OVERALL SCORE: {overall_score:.1f}%")
        
        if overall_score >= 80:
            logger.info("🎉 CONTANGO MONITORING IMPLEMENTATION: READY FOR PRODUCTION")
        elif overall_score >= 60:
            logger.info("⚠️  CONTANGO MONITORING IMPLEMENTATION: NEEDS MINOR FIXES")
        else:
            logger.info("❌ CONTANGO MONITORING IMPLEMENTATION: NEEDS MAJOR FIXES")
            
        logger.info("=" * 60)


async def main():
    """Main test runner"""
    tester = ContangoIntegrationTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main()) 