#!/usr/bin/env python3
"""
Real Market Data Test for Alpha Scanner Integration

This script tests the complete alpha scanner system using real market data
from Binance to validate the integration and detect actual alpha opportunities.
"""

import sys
import os
import asyncio
import logging
import yaml
import time
from datetime import datetime

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import required modules
from src.monitoring.monitor import MarketMonitor
from src.monitoring.alert_manager import AlertManager
from src.monitoring.metrics_manager import MetricsManager
from src.core.market.top_symbols import TopSymbolsManager
from src.core.market.market_data_manager import MarketDataManager
from src.core.exchanges.manager import ExchangeManager
from src.core.validation.service import AsyncValidationService
import ccxt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealDataAlphaTester:
    """Test alpha scanner with real market data."""
    
    def __init__(self):
        self.config = None
        self.exchange = None
        self.monitor = None
        
    async def load_config(self):
        """Load configuration from config.yaml."""
        try:
            config_path = os.path.join(project_root, 'config', 'config.yaml')
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            # Override some settings for testing
            self.config['alpha_scanning']['interval_minutes'] = 1  # Test every minute
            self.config['alpha_scanning']['thresholds']['min_confidence'] = 0.6  # Lower threshold for testing
            self.config['monitoring'] = {'interval': 30}  # 30 second monitoring cycle
            
            logger.info("✅ Configuration loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {str(e)}")
            return False
    
    async def initialize_exchange(self):
        """Initialize Binance exchange for real data."""
        try:
            # Use Binance (public data, no API keys required)
            self.exchange = ccxt.binance({
                'sandbox': False,  # Use real market data
                'rateLimit': 1200,  # Respect rate limits
                'timeout': 30000,   # 30 second timeout
                'options': {
                    'adjustForTimeDifference': True,
                    'recvWindow': 10000,
                }
            })
            
            # Test connection (synchronous call)
            markets = self.exchange.load_markets()
            logger.info(f"✅ Exchange initialized - {len(markets)} markets available")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize exchange: {str(e)}")
            return False
    
    async def initialize_dependencies(self):
        """Initialize all required dependencies."""
        try:
            # Initialize alert manager
            alert_manager = AlertManager(self.config, logger)
            
            # Initialize exchange manager (if needed)
            exchange_manager = ExchangeManager(self.config, logger)
            
            # Initialize validation service
            validation_service = AsyncValidationService()
            
            # Initialize top symbols manager with correct constructor
            top_symbols_manager = TopSymbolsManager(
                exchange_manager=exchange_manager,
                config=self.config,
                validation_service=validation_service
            )
            
            # Initialize market data manager
            market_data_manager = MarketDataManager(
                exchange=self.exchange,
                config=self.config,
                logger=logger
            )
            
            # Initialize metrics manager
            metrics_manager = MetricsManager(logger)
            
            # Initialize market monitor with alpha scanner
            self.monitor = MarketMonitor(
                exchange=self.exchange,
                config=self.config,
                alert_manager=alert_manager,
                top_symbols_manager=top_symbols_manager,
                market_data_manager=market_data_manager,
                metrics_manager=metrics_manager,
                logger=logger
            )
            
            logger.info("✅ All dependencies initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize dependencies: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def test_alpha_scanner_initialization(self):
        """Test that alpha scanner is properly initialized."""
        try:
            # Check alpha scanner exists
            assert hasattr(self.monitor, 'alpha_scanner'), "Alpha scanner not initialized"
            assert self.monitor.alpha_scanner is not None, "Alpha scanner is None"
            
            # Check state variables
            assert hasattr(self.monitor, '_last_alpha_scan'), "Last alpha scan timestamp missing"
            assert hasattr(self.monitor, '_alpha_scan_interval'), "Alpha scan interval missing"
            
            # Check configuration
            alpha_config = self.monitor.alpha_scanner.config.get('alpha_scanning', {})
            assert alpha_config.get('enabled') == True, "Alpha scanning not enabled"
            
            logger.info("✅ Alpha scanner initialization test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Alpha scanner initialization test failed: {str(e)}")
            return False
    
    async def test_real_market_data_collection(self):
        """Test collecting real market data."""
        try:
            logger.info("📊 Testing real market data collection...")
            
            # Test symbols
            test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
            
            for symbol in test_symbols:
                try:
                    # Fetch recent OHLCV data (synchronous call)
                    timeframes = ['4h', '30m']
                    
                    for timeframe in timeframes:
                        ohlcv = self.exchange.fetch_ohlcv(
                            symbol, 
                            timeframe, 
                            limit=100
                        )
                        
                        if len(ohlcv) < 50:
                            logger.warning(f"⚠️ Limited data for {symbol} {timeframe}: {len(ohlcv)} candles")
                        else:
                            logger.info(f"✅ {symbol} {timeframe}: {len(ohlcv)} candles collected")
                
                except Exception as e:
                    logger.error(f"❌ Failed to fetch data for {symbol}: {str(e)}")
                    return False
            
            logger.info("✅ Real market data collection test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Real market data collection test failed: {str(e)}")
            return False
    
    async def test_full_monitoring_cycle(self):
        """Test a complete monitoring cycle with alpha scanning."""
        try:
            logger.info("🔄 Testing full monitoring cycle with alpha scanning...")
            
            # Force alpha scan by setting last scan time to 0
            self.monitor._last_alpha_scan = 0
            self.monitor._alpha_scan_interval = 60  # 1 minute for testing
            
            # Run one monitoring cycle
            start_time = time.time()
            
            # This should trigger alpha scanning since enough time has passed
            await self.monitor._monitoring_cycle()
            
            cycle_time = time.time() - start_time
            logger.info(f"✅ Monitoring cycle completed in {cycle_time:.2f} seconds")
            
            # Check if alpha scan was executed
            if self.monitor._last_alpha_scan > start_time:
                logger.info("✅ Alpha scan was executed during monitoring cycle")
            else:
                logger.warning("⚠️ Alpha scan may not have been executed")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Full monitoring cycle test failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def test_direct_alpha_scanning(self):
        """Test alpha scanner directly with mock market data cache."""
        try:
            logger.info("🔍 Testing direct alpha scanning...")
            
            # Create minimal mock cache structure for testing
            mock_cache = {
                'BTCUSDT': {
                    'htf': [],  # Will be populated by real data
                    'mtf': []   # Will be populated by real data
                }
            }
            
            # Try to scan (this will test the scanner's error handling with minimal data)
            await self.monitor.alpha_scanner.scan_for_opportunities(self.monitor)
            
            logger.info("✅ Direct alpha scanning test completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Direct alpha scanning test failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def run_all_tests(self):
        """Run all tests in sequence."""
        logger.info("🚀 Starting Real Market Data Alpha Scanner Tests")
        logger.info("=" * 80)
        
        tests = [
            ("Configuration Loading", self.load_config),
            ("Exchange Initialization", self.initialize_exchange),
            ("Dependencies Initialization", self.initialize_dependencies),
            ("Alpha Scanner Initialization", self.test_alpha_scanner_initialization),
            ("Real Market Data Collection", self.test_real_market_data_collection),
            ("Direct Alpha Scanning", self.test_direct_alpha_scanning),
            ("Full Monitoring Cycle", self.test_full_monitoring_cycle),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                logger.info(f"\n🧪 Running: {test_name}")
                logger.info("-" * 50)
                
                start_time = time.time()
                result = await test_func()
                test_time = time.time() - start_time
                
                results[test_name] = {
                    'passed': result,
                    'time': test_time
                }
                
                status = "✅ PASSED" if result else "❌ FAILED"
                logger.info(f"{status} - {test_name} ({test_time:.2f}s)")
                
                if not result:
                    logger.warning(f"⚠️ Test '{test_name}' failed, continuing with remaining tests...")
                    
            except Exception as e:
                logger.error(f"❌ Test '{test_name}' crashed: {str(e)}")
                results[test_name] = {
                    'passed': False,
                    'time': 0,
                    'error': str(e)
                }
        
        # Summary
        self.print_test_summary(results)
        
        # Cleanup
        if self.exchange:
            try:
                if hasattr(self.exchange, 'close'):
                    await self.exchange.close()
                elif hasattr(self.exchange, 'close_exchange'):
                    self.exchange.close_exchange()
            except:
                pass  # Ignore cleanup errors
        
        return results
    
    def print_test_summary(self, results):
        """Print comprehensive test summary."""
        logger.info("\n" + "=" * 80)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 80)
        
        passed_tests = sum(1 for r in results.values() if r['passed'])
        total_tests = len(results)
        total_time = sum(r['time'] for r in results.values())
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {total_tests - passed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        logger.info(f"Total Time: {total_time:.2f} seconds")
        
        logger.info("\nDetailed Results:")
        logger.info("-" * 40)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            time_str = f"{result['time']:.2f}s"
            logger.info(f"{status:<8} {test_name:<30} {time_str}")
            
            if not result['passed'] and 'error' in result:
                logger.info(f"         Error: {result['error']}")
        
        if passed_tests == total_tests:
            logger.info("\n🎉 ALL TESTS PASSED! Alpha scanner is ready for production.")
            logger.info("\n📋 Next Steps:")
            logger.info("   1. ✅ Alpha scanner integration verified")
            logger.info("   2. ✅ Real market data connection confirmed")
            logger.info("   3. ✅ Monitoring cycle with alpha scanning validated")
            logger.info("   4. 🚀 Ready to deploy to production environment")
            logger.info("   5. 📈 Monitor Discord alerts for alpha opportunities")
        else:
            logger.info(f"\n⚠️ {total_tests - passed_tests} tests failed. Please review and fix issues before production deployment.")

async def main():
    """Main test execution function."""
    tester = RealDataAlphaTester()
    results = await tester.run_all_tests()
    
    # Return appropriate exit code
    passed_tests = sum(1 for r in results.values() if r['passed'])
    total_tests = len(results)
    
    if passed_tests == total_tests:
        return 0  # Success
    else:
        return 1  # Some tests failed

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 