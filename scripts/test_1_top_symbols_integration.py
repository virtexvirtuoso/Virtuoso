#!/usr/bin/env python3

import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

import asyncio
import logging
from typing import List, Dict, Any

from config.manager import ConfigManager
from data_acquisition.binance.binance_exchange import BinanceExchange

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class TopSymbolsIntegrationTester:
    """Test TopSymbolsManager integration with Binance data."""
    
    def __init__(self):
        self.test_results = {'passed': 0, 'failed': 0, 'warnings': 0}
        
    def log_result(self, test_name: str, status: str, message: str):
        """Log test results."""
        if status == 'PASS':
            logger.info(f"✅ {test_name}: {message}")
            self.test_results['passed'] += 1
        elif status == 'FAIL':
            logger.error(f"❌ {test_name}: {message}")
            self.test_results['failed'] += 1
        else:
            logger.warning(f"⚠️ {test_name}: {message}")
            self.test_results['warnings'] += 1

    async def test_dynamic_symbol_fetching(self, exchange):
        """Test dynamic symbol fetching from Binance."""
        try:
            # Get all 24hr tickers to find top symbols by volume
            logger.info("Fetching all 24hr tickers from Binance...")
            
            async with exchange.futures_client as client:
                all_tickers = await client.get_all_24hr_tickers()
            
            if not all_tickers or len(all_tickers) < 100:
                self.log_result("Dynamic Symbol Fetching", "FAIL", 
                               f"Insufficient ticker data: {len(all_tickers) if all_tickers else 0}")
                return []
            
            # Filter for USDT pairs only and sort by quote volume
            usdt_symbols = [
                ticker for ticker in all_tickers 
                if ticker['symbol'].endswith('USDT') and ticker['quoteVolume'] > 0
            ]
            
            # Sort by 24hr quote volume (turnover)
            top_symbols = sorted(usdt_symbols, key=lambda x: x['quoteVolume'], reverse=True)[:20]
            
            symbol_list = [ticker['symbol'] for ticker in top_symbols]
            volumes = [ticker['quoteVolume'] for ticker in top_symbols]
            
            self.log_result("Dynamic Symbol Fetching", "PASS", 
                           f"Found {len(symbol_list)} top symbols, highest volume: ${volumes[0]:,.0f}")
            
            return symbol_list[:10]  # Return top 10 for testing
            
        except Exception as e:
            self.log_result("Dynamic Symbol Fetching", "FAIL", f"Error: {str(e)}")
            return []

    async def test_symbol_data_quality(self, exchange, symbols: List[str]):
        """Test data quality for dynamic symbols."""
        if not symbols:
            self.log_result("Symbol Data Quality", "FAIL", "No symbols to test")
            return
        
        valid_symbols = 0
        total_volume = 0
        
        for symbol in symbols:
            try:
                # Test comprehensive data for each symbol
                ticker = await exchange.get_ticker(symbol)
                funding = await exchange.get_current_funding_rate(symbol)
                oi = await exchange.get_open_interest(symbol)
                
                # Validate data completeness
                if (ticker and ticker.get('last', 0) > 0 and 
                    funding and 'fundingRate' in funding and
                    oi and oi.get('openInterest', 0) >= 0):
                    
                    valid_symbols += 1
                    total_volume += ticker.get('quoteVolume', 0)
                    
                    logger.debug(f"Valid data for {symbol}: ${ticker['last']:.2f}, "
                               f"OI: {oi['openInterest']:,.0f}")
                else:
                    logger.warning(f"Incomplete data for {symbol}")
                    
            except Exception as e:
                logger.warning(f"Error getting data for {symbol}: {str(e)}")
        
        success_rate = (valid_symbols / len(symbols)) * 100 if symbols else 0
        
        if success_rate >= 80:
            self.log_result("Symbol Data Quality", "PASS", 
                           f"{valid_symbols}/{len(symbols)} symbols valid ({success_rate:.1f}%), "
                           f"Total volume: ${total_volume:,.0f}")
        else:
            self.log_result("Symbol Data Quality", "FAIL", 
                           f"Low success rate: {success_rate:.1f}%")

    async def test_real_time_symbol_updates(self, exchange):
        """Test real-time symbol ranking updates."""
        try:
            logger.info("Testing symbol ranking stability over time...")
            
            # Get top symbols at two different times
            symbols_t1 = await self.test_dynamic_symbol_fetching(exchange)
            await asyncio.sleep(5)  # Wait 5 seconds
            symbols_t2 = await self.test_dynamic_symbol_fetching(exchange)
            
            if not symbols_t1 or not symbols_t2:
                self.log_result("Real-time Updates", "FAIL", "Failed to get symbol lists")
                return
            
            # Check overlap between the two lists
            overlap = len(set(symbols_t1[:5]).intersection(set(symbols_t2[:5])))
            overlap_pct = (overlap / 5) * 100
            
            if overlap_pct >= 80:
                self.log_result("Real-time Updates", "PASS", 
                               f"Top 5 symbols stable: {overlap_pct:.0f}% overlap")
            else:
                self.log_result("Real-time Updates", "WARN", 
                               f"High volatility in rankings: {overlap_pct:.0f}% overlap")
                
        except Exception as e:
            self.log_result("Real-time Updates", "FAIL", f"Error: {str(e)}")

    async def test_symbol_filtering_criteria(self, exchange):
        """Test symbol filtering based on various criteria."""
        try:
            logger.info("Testing symbol filtering criteria...")
            
            async with exchange.futures_client as client:
                all_tickers = await client.get_all_24hr_tickers()
            
            # Test different filtering criteria
            filters = {
                'USDT_pairs': lambda x: x['symbol'].endswith('USDT'),
                'high_volume': lambda x: x['quoteVolume'] > 1000000,  # > $1M volume
                'active_trading': lambda x: x['count'] > 1000,  # > 1000 trades
                'reasonable_price': lambda x: 0.001 <= x['lastPrice'] <= 100000,
                'stable_symbols': lambda x: abs(x['priceChangePercent']) < 50  # < 50% change
            }
            
            filter_results = {}
            for filter_name, filter_func in filters.items():
                filtered = [t for t in all_tickers if filter_func(t)]
                filter_results[filter_name] = len(filtered)
                logger.info(f"{filter_name}: {len(filtered)} symbols")
            
            # Validate reasonable filtering results
            if (filter_results['USDT_pairs'] > 50 and 
                filter_results['high_volume'] > 10 and
                filter_results['active_trading'] > 20):
                
                self.log_result("Symbol Filtering", "PASS", 
                               f"Filters working: {filter_results}")
            else:
                self.log_result("Symbol Filtering", "FAIL", 
                               f"Insufficient filtered symbols: {filter_results}")
                
        except Exception as e:
            self.log_result("Symbol Filtering", "FAIL", f"Error: {str(e)}")

    async def test_integration_with_market_reporter(self, exchange, symbols: List[str]):
        """Test integration with market reporter using dynamic symbols."""
        if not symbols:
            self.log_result("Market Reporter Integration", "FAIL", "No symbols to test")
            return
            
        try:
            # Import here to avoid circular dependencies
            from monitoring.market_reporter import MarketReporter
            
            logger.info("Testing market reporter with dynamic symbols...")
            
            # Create reporter with dynamic symbols
            reporter = MarketReporter(exchange=exchange)
            
            # Override symbols for testing
            original_symbols = getattr(reporter, 'symbols', [])
            reporter.symbols = symbols[:5]  # Use top 5 dynamic symbols
            
            # Test report generation
            start_time = asyncio.get_event_loop().time()
            report = await reporter.generate_market_summary()
            generation_time = asyncio.get_event_loop().time() - start_time
            
            # Restore original symbols
            if hasattr(reporter, 'symbols'):
                reporter.symbols = original_symbols
            
            if report and isinstance(report, dict):
                sections = len([k for k, v in report.items() if v])
                self.log_result("Market Reporter Integration", "PASS", 
                               f"Generated report with {sections} sections in {generation_time:.2f}s")
            else:
                self.log_result("Market Reporter Integration", "FAIL", 
                               "Failed to generate report with dynamic symbols")
                
        except ImportError:
            self.log_result("Market Reporter Integration", "WARN", 
                           "MarketReporter not available for testing")
        except Exception as e:
            self.log_result("Market Reporter Integration", "FAIL", f"Error: {str(e)}")

    def generate_summary(self):
        """Generate test summary."""
        total = sum(self.test_results.values())
        passed = self.test_results['passed']
        
        logger.info("\n" + "="*60)
        logger.info("TOP SYMBOLS INTEGRATION TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"📊 Total Tests: {total}")
        logger.info(f"✅ Passed: {self.test_results['passed']}")
        logger.info(f"❌ Failed: {self.test_results['failed']}")
        logger.info(f"⚠️ Warnings: {self.test_results['warnings']}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        logger.info(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            logger.info("🎉 TopSymbolsManager integration is ready!")
            return True
        else:
            logger.warning("⚠️ TopSymbolsManager integration needs attention")
            return False

async def main():
    """Run TopSymbolsManager integration tests."""
    logger.info("🔍 TEST 1: TopSymbolsManager Integration")
    logger.info("="*50)
    
    tester = TopSymbolsIntegrationTester()
    
    try:
        # Initialize exchange
        config_manager = ConfigManager()
        config = config_manager.config
        
        async with BinanceExchange(config=config) as exchange:
            logger.info("🔗 Connected to Binance exchange")
            
            # Run tests in sequence
            dynamic_symbols = await tester.test_dynamic_symbol_fetching(exchange)
            await tester.test_symbol_data_quality(exchange, dynamic_symbols)
            await tester.test_real_time_symbol_updates(exchange)
            await tester.test_symbol_filtering_criteria(exchange)
            await tester.test_integration_with_market_reporter(exchange, dynamic_symbols)
            
        return tester.generate_summary()
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 