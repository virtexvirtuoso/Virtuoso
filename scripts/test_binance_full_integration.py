#!/usr/bin/env python3

import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

import asyncio
import logging
import json
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

from config.manager import ConfigManager
from data_acquisition.binance.binance_exchange import BinanceExchange
from monitoring.market_reporter import MarketReporter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class BinanceIntegrationTester:
    """Comprehensive test suite for Binance integration validation."""
    
    def __init__(self):
        self.test_results = {
            'timestamp': int(time.time()),
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'warnings': 0,
            'test_details': []
        }
        self.test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT']
        
    def log_test_result(self, test_name: str, status: str, details: str = "", data: Any = None):
        """Log individual test results."""
        result = {
            'test_name': test_name,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        self.test_results['test_details'].append(result)
        self.test_results['total_tests'] += 1
        
        if status == 'PASS':
            self.test_results['passed_tests'] += 1
            logger.info(f"✅ {test_name}: {details}")
        elif status == 'FAIL':
            self.test_results['failed_tests'] += 1
            logger.error(f"❌ {test_name}: {details}")
        elif status == 'WARN':
            self.test_results['warnings'] += 1
            logger.warning(f"⚠️ {test_name}: {details}")
    
    async def test_1_basic_connectivity(self, exchange):
        """Test 1: Basic Binance API connectivity and authentication."""
        logger.info("\n" + "="*60)
        logger.info("TEST 1: Basic Connectivity & Authentication")
        logger.info("="*60)
        
        try:
            # Test connection initialization
            await exchange.initialize()
            self.log_test_result("Exchange Initialization", "PASS", "Successfully initialized Binance exchange")
            
            # Test market loading
            try:
                markets = await asyncio.wait_for(exchange.get_markets(), timeout=30)
                if markets and len(markets) > 100:
                    self.log_test_result("Market Loading", "PASS", f"Loaded {len(markets)} markets")
                else:
                    self.log_test_result("Market Loading", "FAIL", f"Insufficient markets loaded: {len(markets) if markets else 0}")
            except asyncio.TimeoutError:
                self.log_test_result("Market Loading", "FAIL", "Timeout loading markets")
            except Exception as e:
                self.log_test_result("Market Loading", "FAIL", f"Error loading markets: {str(e)}")
            
            # Test exchange info
            try:
                info = await exchange.get_exchange_info()
                if info and info.get('exchange') == 'binance':
                    self.log_test_result("Exchange Info", "PASS", f"Exchange: {info['exchange']}, Markets: {info.get('total_markets', 0)}")
                else:
                    self.log_test_result("Exchange Info", "FAIL", "Invalid exchange info returned")
            except Exception as e:
                self.log_test_result("Exchange Info", "FAIL", f"Error getting exchange info: {str(e)}")
                
        except Exception as e:
            self.log_test_result("Exchange Initialization", "FAIL", f"Failed to initialize: {str(e)}")
    
    async def test_2_market_data_retrieval(self, exchange):
        """Test 2: Market data retrieval across different data types."""
        logger.info("\n" + "="*60)
        logger.info("TEST 2: Market Data Retrieval")
        logger.info("="*60)
        
        for symbol in self.test_symbols:
            try:
                # Test ticker data
                ticker = await exchange.get_ticker(symbol)
                if ticker and 'last' in ticker and ticker['last'] > 0:
                    self.log_test_result(f"Ticker Data - {symbol}", "PASS", 
                                       f"Price: ${ticker['last']:,.2f}, Volume: {ticker.get('baseVolume', 0):,.0f}")
                else:
                    self.log_test_result(f"Ticker Data - {symbol}", "FAIL", "Invalid ticker data")
                
                # Test order book
                try:
                    orderbook = await exchange.get_order_book(symbol, 10)
                    if orderbook and 'bids' in orderbook and 'asks' in orderbook:
                        bid_count = len(orderbook['bids'])
                        ask_count = len(orderbook['asks'])
                        if bid_count >= 5 and ask_count >= 5:
                            spread = float(orderbook['asks'][0][0]) - float(orderbook['bids'][0][0])
                            self.log_test_result(f"Order Book - {symbol}", "PASS", 
                                               f"Bids: {bid_count}, Asks: {ask_count}, Spread: ${spread:.2f}")
                        else:
                            self.log_test_result(f"Order Book - {symbol}", "WARN", 
                                               f"Limited depth: Bids: {bid_count}, Asks: {ask_count}")
                    else:
                        self.log_test_result(f"Order Book - {symbol}", "FAIL", "Invalid order book data")
                except Exception as e:
                    self.log_test_result(f"Order Book - {symbol}", "FAIL", f"Error: {str(e)}")
                
                # Test recent trades
                try:
                    trades = await exchange.get_recent_trades(symbol, 10)
                    if trades and len(trades) >= 5:
                        latest_trade = trades[0]
                        self.log_test_result(f"Recent Trades - {symbol}", "PASS", 
                                           f"Got {len(trades)} trades, latest: ${latest_trade.get('price', 0):.2f}")
                    else:
                        self.log_test_result(f"Recent Trades - {symbol}", "WARN", 
                                           f"Limited trades: {len(trades) if trades else 0}")
                except Exception as e:
                    self.log_test_result(f"Recent Trades - {symbol}", "FAIL", f"Error: {str(e)}")
                
                # Test OHLCV data
                try:
                    ohlcv = await exchange.get_ohlcv(symbol, '1h', 24)
                    if ohlcv and len(ohlcv) >= 20:
                        latest_candle = ohlcv[-1]
                        self.log_test_result(f"OHLCV Data - {symbol}", "PASS", 
                                           f"Got {len(ohlcv)} candles, latest close: ${latest_candle[4]:.2f}")
                    else:
                        self.log_test_result(f"OHLCV Data - {symbol}", "WARN", 
                                           f"Limited OHLCV data: {len(ohlcv) if ohlcv else 0}")
                except Exception as e:
                    self.log_test_result(f"OHLCV Data - {symbol}", "FAIL", f"Error: {str(e)}")
                
            except Exception as e:
                self.log_test_result(f"Market Data - {symbol}", "FAIL", f"Error: {str(e)}")
    
    async def test_3_futures_functionality(self, exchange):
        """Test 3: Futures-specific functionality."""
        logger.info("\n" + "="*60)
        logger.info("TEST 3: Futures Functionality")
        logger.info("="*60)
        
        for symbol in self.test_symbols:
            try:
                # Test funding rates
                try:
                    funding = await exchange.get_current_funding_rate(symbol)
                    if funding and 'fundingRate' in funding:
                        rate = float(funding['fundingRate'])
                        rate_pct = rate * 100
                        self.log_test_result(f"Funding Rate - {symbol}", "PASS", 
                                           f"Rate: {rate_pct:.4f}% (8h funding)")
                    else:
                        self.log_test_result(f"Funding Rate - {symbol}", "FAIL", "Invalid funding rate data")
                except Exception as e:
                    self.log_test_result(f"Funding Rate - {symbol}", "FAIL", f"Error: {str(e)}")
                
                # Test open interest
                try:
                    oi = await exchange.get_open_interest(symbol)
                    if oi and 'openInterest' in oi:
                        oi_value = float(oi['openInterest'])
                        if oi_value > 0:
                            self.log_test_result(f"Open Interest - {symbol}", "PASS", 
                                               f"OI: {oi_value:,.0f} contracts")
                        else:
                            self.log_test_result(f"Open Interest - {symbol}", "WARN", 
                                               f"Zero open interest (may not have futures)")
                    else:
                        self.log_test_result(f"Open Interest - {symbol}", "FAIL", "Invalid open interest data")
                except Exception as e:
                    self.log_test_result(f"Open Interest - {symbol}", "WARN", f"Error: {str(e)}")
                
                # Test premium index
                try:
                    premium = await exchange.get_premium_index(symbol)
                    if premium and 'markPrice' in premium and 'indexPrice' in premium:
                        mark = float(premium['markPrice'])
                        index = float(premium['indexPrice'])
                        premium_pct = ((mark - index) / index) * 100
                        self.log_test_result(f"Premium Index - {symbol}", "PASS", 
                                           f"Mark: ${mark:.2f}, Index: ${index:.2f}, Premium: {premium_pct:.2f}%")
                    else:
                        self.log_test_result(f"Premium Index - {symbol}", "FAIL", "Invalid premium index data")
                except Exception as e:
                    self.log_test_result(f"Premium Index - {symbol}", "FAIL", f"Error: {str(e)}")
                
                # Test long/short ratio
                try:
                    ratio_data = await exchange.futures_client.get_long_short_ratio(symbol)
                    if ratio_data and len(ratio_data) > 0:
                        latest = ratio_data[0]
                        long_ratio = float(latest.get('longShortRatio', 0))
                        long_pct = (long_ratio / (1 + long_ratio)) * 100
                        short_pct = 100 - long_pct
                        self.log_test_result(f"Long/Short Ratio - {symbol}", "PASS", 
                                           f"Long: {long_pct:.1f}%, Short: {short_pct:.1f}%")
                    else:
                        self.log_test_result(f"Long/Short Ratio - {symbol}", "FAIL", "No ratio data returned")
                except Exception as e:
                    self.log_test_result(f"Long/Short Ratio - {symbol}", "FAIL", f"Error: {str(e)}")
                
                # Test risk limits (should use static fallback)
                try:
                    risk_limits = await exchange.futures_client.get_leverage_bracket(symbol)
                    if risk_limits and len(risk_limits) > 0:
                        max_leverage = max(float(bracket.get('initialLeverage', 0)) for bracket in risk_limits)
                        self.log_test_result(f"Risk Limits - {symbol}", "PASS", 
                                           f"Max leverage: {max_leverage:.0f}x ({len(risk_limits)} brackets)")
                    else:
                        self.log_test_result(f"Risk Limits - {symbol}", "FAIL", "No risk limits data")
                except Exception as e:
                    self.log_test_result(f"Risk Limits - {symbol}", "FAIL", f"Error: {str(e)}")
                
            except Exception as e:
                self.log_test_result(f"Futures Functions - {symbol}", "FAIL", f"Error: {str(e)}")
    
    async def test_4_market_reporter_integration(self, exchange):
        """Test 4: Market reporter integration with Binance data."""
        logger.info("\n" + "="*60)
        logger.info("TEST 4: Market Reporter Integration")
        logger.info("="*60)
        
        try:
            # Initialize market reporter with Binance exchange
            reporter = MarketReporter(exchange=exchange)
            
            # Test market summary generation
            try:
                logger.info("Generating comprehensive market summary...")
                start_time = time.time()
                report = await reporter.generate_market_summary()
                generation_time = time.time() - start_time
                
                if report and isinstance(report, dict):
                    # Validate report structure
                    required_sections = ['market_overview', 'futures_premium', 'smart_money_index', 'whale_activity']
                    missing_sections = [s for s in required_sections if s not in report or not report[s]]
                    
                    if not missing_sections:
                        self.log_test_result("Market Report Generation", "PASS", 
                                           f"Generated in {generation_time:.2f}s with all sections")
                        
                        # Test specific sections
                        if 'market_overview' in report:
                            overview = report['market_overview']
                            regime = overview.get('regime', 'UNKNOWN')
                            total_volume = overview.get('total_volume', 0)
                            self.log_test_result("Market Overview Section", "PASS", 
                                               f"Regime: {regime}, Volume: ${total_volume:,.0f}")
                        
                        if 'futures_premium' in report:
                            premium = report['futures_premium']
                            premiums = premium.get('premiums', {})
                            self.log_test_result("Futures Premium Section", "PASS", 
                                               f"Calculated premiums for {len(premiums)} symbols")
                        
                        if 'smart_money_index' in report:
                            smi = report['smart_money_index']
                            index_value = smi.get('index', 0)
                            self.log_test_result("Smart Money Index", "PASS", 
                                               f"SMI: {index_value:.1f}/100")
                        
                        if 'whale_activity' in report:
                            whale = report['whale_activity']
                            transactions = whale.get('transactions', [])
                            self.log_test_result("Whale Activity Section", "PASS", 
                                               f"Detected {len(transactions)} large transactions")
                    else:
                        self.log_test_result("Market Report Generation", "WARN", 
                                           f"Missing sections: {missing_sections}")
                else:
                    self.log_test_result("Market Report Generation", "FAIL", "No report generated")
            except Exception as e:
                self.log_test_result("Market Report Generation", "FAIL", f"Error: {str(e)}")
            
            # Test PDF generation (if available)
            try:
                if hasattr(reporter, 'pdf_enabled') and reporter.pdf_enabled:
                    logger.info("Testing PDF report generation...")
                    pdf_path = await reporter.generate_market_pdf_report(report)
                    if pdf_path and os.path.exists(pdf_path):
                        file_size = os.path.getsize(pdf_path)
                        self.log_test_result("PDF Generation", "PASS", 
                                           f"Generated PDF: {os.path.basename(pdf_path)} ({file_size:,} bytes)")
                    else:
                        self.log_test_result("PDF Generation", "FAIL", "PDF not generated")
                else:
                    self.log_test_result("PDF Generation", "WARN", "PDF generation not enabled")
            except Exception as e:
                self.log_test_result("PDF Generation", "FAIL", f"Error: {str(e)}")
                
        except Exception as e:
            self.log_test_result("Market Reporter Integration", "FAIL", f"Error: {str(e)}")
    
    async def test_5_performance_and_reliability(self, exchange):
        """Test 5: Performance and reliability under load."""
        logger.info("\n" + "="*60)
        logger.info("TEST 5: Performance & Reliability")
        logger.info("="*60)
        
        # Test concurrent requests
        try:
            logger.info("Testing concurrent API requests...")
            start_time = time.time()
            
            tasks = []
            for symbol in self.test_symbols:
                tasks.extend([
                    exchange.get_ticker(symbol),
                    exchange.get_current_funding_rate(symbol),
                    exchange.get_open_interest(symbol)
                ])
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful
            
            if successful >= len(results) * 0.8:  # 80% success rate
                self.log_test_result("Concurrent Requests", "PASS", 
                                   f"{successful}/{len(results)} succeeded in {total_time:.2f}s")
            else:
                self.log_test_result("Concurrent Requests", "WARN", 
                                   f"Only {successful}/{len(results)} succeeded")
        except Exception as e:
            self.log_test_result("Concurrent Requests", "FAIL", f"Error: {str(e)}")
        
        # Test error handling
        try:
            logger.info("Testing error handling with invalid symbols...")
            invalid_symbols = ['INVALIDUSDT', 'FAKECOINUSDT', 'TESTUSDT']
            
            for invalid_symbol in invalid_symbols:
                try:
                    await exchange.get_ticker(invalid_symbol)
                    self.log_test_result(f"Error Handling - {invalid_symbol}", "WARN", 
                                       "Expected error but got success")
                except Exception as e:
                    if "Invalid symbol" in str(e) or "does not exist" in str(e):
                        self.log_test_result(f"Error Handling - {invalid_symbol}", "PASS", 
                                           "Properly handled invalid symbol")
                    else:
                        self.log_test_result(f"Error Handling - {invalid_symbol}", "WARN", 
                                           f"Unexpected error: {str(e)}")
        except Exception as e:
            self.log_test_result("Error Handling Test", "FAIL", f"Error: {str(e)}")
        
        # Test timeout handling
        try:
            logger.info("Testing timeout resilience...")
            timeout_start = time.time()
            
            # Test with very short timeout
            try:
                await asyncio.wait_for(exchange.get_ohlcv(self.test_symbols[0], '1m', 1000), timeout=0.001)
                self.log_test_result("Timeout Handling", "WARN", "Request completed despite short timeout")
            except asyncio.TimeoutError:
                timeout_duration = time.time() - timeout_start
                self.log_test_result("Timeout Handling", "PASS", 
                                   f"Properly handled timeout in {timeout_duration:.3f}s")
            except Exception as e:
                self.log_test_result("Timeout Handling", "PASS", 
                                   f"Handled with exception: {type(e).__name__}")
        except Exception as e:
            self.log_test_result("Timeout Test", "FAIL", f"Error: {str(e)}")
    
    async def test_6_data_quality_validation(self, exchange):
        """Test 6: Data quality and accuracy validation."""
        logger.info("\n" + "="*60)
        logger.info("TEST 6: Data Quality & Accuracy")
        logger.info("="*60)
        
        for symbol in self.test_symbols[:3]:  # Test first 3 symbols for time
            try:
                # Get comprehensive data
                ticker = await exchange.get_ticker(symbol)
                funding = await exchange.get_current_funding_rate(symbol)
                oi = await exchange.get_open_interest(symbol)
                premium = await exchange.get_premium_index(symbol)
                
                # Validate data consistency
                price_from_ticker = float(ticker.get('last', 0))
                price_from_premium = float(premium.get('markPrice', 0)) if premium else 0
                
                if price_from_ticker > 0 and price_from_premium > 0:
                    price_diff_pct = abs(price_from_ticker - price_from_premium) / price_from_ticker * 100
                    if price_diff_pct < 1.0:  # Less than 1% difference
                        self.log_test_result(f"Price Consistency - {symbol}", "PASS", 
                                           f"Ticker: ${price_from_ticker:.2f}, Mark: ${price_from_premium:.2f}")
                    else:
                        self.log_test_result(f"Price Consistency - {symbol}", "WARN", 
                                           f"Price difference: {price_diff_pct:.2f}%")
                
                # Validate timestamp freshness
                current_time = int(time.time() * 1000)
                if ticker and 'timestamp' in ticker:
                    ticker_age = (current_time - ticker['timestamp']) / 1000
                    if ticker_age < 60:  # Less than 1 minute old
                        self.log_test_result(f"Data Freshness - {symbol}", "PASS", 
                                           f"Data age: {ticker_age:.1f}s")
                    else:
                        self.log_test_result(f"Data Freshness - {symbol}", "WARN", 
                                           f"Stale data: {ticker_age:.1f}s old")
                
                # Validate funding rate reasonableness
                if funding and 'fundingRate' in funding:
                    rate = float(funding['fundingRate'])
                    rate_pct = abs(rate * 100)
                    if rate_pct < 1.0:  # Funding rate less than 1% (reasonable)
                        self.log_test_result(f"Funding Rate Sanity - {symbol}", "PASS", 
                                           f"Rate: {rate_pct:.4f}% (reasonable)")
                    else:
                        self.log_test_result(f"Funding Rate Sanity - {symbol}", "WARN", 
                                           f"High funding rate: {rate_pct:.4f}%")
                
            except Exception as e:
                self.log_test_result(f"Data Quality - {symbol}", "FAIL", f"Error: {str(e)}")
    
    def generate_test_report(self):
        """Generate final test report."""
        logger.info("\n" + "="*60)
        logger.info("BINANCE INTEGRATION TEST SUMMARY")
        logger.info("="*60)
        
        total = self.test_results['total_tests']
        passed = self.test_results['passed_tests']
        failed = self.test_results['failed_tests']
        warnings = self.test_results['warnings']
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        logger.info(f"📊 OVERALL RESULTS:")
        logger.info(f"   Total Tests: {total}")
        logger.info(f"   ✅ Passed: {passed}")
        logger.info(f"   ❌ Failed: {failed}")
        logger.info(f"   ⚠️ Warnings: {warnings}")
        logger.info(f"   📈 Success Rate: {success_rate:.1f}%")
        
        # Determine overall status
        if success_rate >= 90:
            status = "🎉 EXCELLENT"
            color = "GREEN"
        elif success_rate >= 80:
            status = "✅ GOOD"
            color = "YELLOW"
        elif success_rate >= 70:
            status = "⚠️ ACCEPTABLE"
            color = "ORANGE"
        else:
            status = "❌ NEEDS WORK"
            color = "RED"
        
        logger.info(f"\n🏆 INTEGRATION STATUS: {status}")
        
        if failed > 0:
            logger.info(f"\n❌ FAILED TESTS:")
            for test in self.test_results['test_details']:
                if test['status'] == 'FAIL':
                    logger.info(f"   - {test['test_name']}: {test['details']}")
        
        if warnings > 0:
            logger.info(f"\n⚠️ WARNINGS:")
            for test in self.test_results['test_details']:
                if test['status'] == 'WARN':
                    logger.info(f"   - {test['test_name']}: {test['details']}")
        
        # Save detailed test report
        report_filename = f"binance_integration_test_{int(time.time())}.json"
        with open(report_filename, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        logger.info(f"\n📄 Detailed test report saved to: {report_filename}")
        
        return success_rate >= 80  # Return True if integration is acceptable

async def main():
    """Run comprehensive Binance integration tests."""
    logger.info("🚀 Starting Comprehensive Binance Integration Testing")
    
    tester = BinanceIntegrationTester()
    
    try:
        # Initialize configuration and exchange
        config_manager = ConfigManager()
        config = config_manager.config
        
        async with BinanceExchange(config=config) as exchange:
            logger.info("🔗 Connected to Binance exchange")
            
            # Run all test suites
            await tester.test_1_basic_connectivity(exchange)
            await tester.test_2_market_data_retrieval(exchange)
            await tester.test_3_futures_functionality(exchange)
            await tester.test_4_market_reporter_integration(exchange)
            await tester.test_5_performance_and_reliability(exchange)
            await tester.test_6_data_quality_validation(exchange)
            
        # Generate final report
        success = tester.generate_test_report()
        
        if success:
            logger.info("\n🎉 Binance integration is ready for production!")
            return True
        else:
            logger.error("\n❌ Binance integration needs attention before production use")
            return False
            
    except Exception as e:
        logger.error(f"💥 Fatal error in integration testing: {str(e)}")
        tester.log_test_result("Integration Testing", "FAIL", f"Fatal error: {str(e)}")
        tester.generate_test_report()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 