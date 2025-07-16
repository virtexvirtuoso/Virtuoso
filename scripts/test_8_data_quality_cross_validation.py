#!/usr/bin/env python3

import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

import asyncio
import logging
import time
import statistics
from typing import Dict, List, Any, Tuple

from config.manager import ConfigManager
from data_acquisition.binance.binance_exchange import BinanceExchange

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class DataQualityCrossValidationTester:
    """Test data quality through cross-validation across different data sources."""
    
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

    async def test_price_data_consistency(self, exchange):
        """Test price data consistency across different endpoints."""
        try:
            logger.info("Testing price data consistency...")
            
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
            consistency_results = []
            
            for symbol in symbols:
                try:
                    # Get price from multiple sources
                    ticker = await exchange.get_ticker(symbol)
                    orderbook = await exchange.get_order_book(symbol, 1)
                    
                    if not ticker or not orderbook:
                        continue
                    
                    # Extract prices
                    ticker_price = float(ticker.get('last', 0))
                    bid_price = float(orderbook['bids'][0][0]) if orderbook['bids'] else 0
                    ask_price = float(orderbook['asks'][0][0]) if orderbook['asks'] else 0
                    
                    if ticker_price > 0 and bid_price > 0 and ask_price > 0:
                        # Check if ticker price is within bid-ask spread
                        spread_pct = ((ask_price - bid_price) / bid_price) * 100
                        price_in_spread = bid_price <= ticker_price <= ask_price
                        
                        # Allow small deviation (0.1%) for ticker price
                        tolerance = 0.001
                        ticker_near_midpoint = abs(ticker_price - (bid_price + ask_price) / 2) / ticker_price <= tolerance
                        
                        if price_in_spread or ticker_near_midpoint:
                            consistency_results.append((symbol, True, spread_pct, 'consistent'))
                        else:
                            consistency_results.append((symbol, False, spread_pct, 'price_mismatch'))
                    else:
                        consistency_results.append((symbol, False, 0, 'missing_data'))
                        
                except Exception as e:
                    consistency_results.append((symbol, False, 0, f'error: {str(e)}'))
                    logger.debug(f"Error checking {symbol}: {str(e)}")
            
            # Evaluate results
            consistent_symbols = sum(1 for _, consistent, _, _ in consistency_results if consistent)
            total_symbols = len(consistency_results)
            
            if consistent_symbols >= total_symbols * 0.8:  # 80% consistency
                avg_spread = statistics.mean([spread for _, consistent, spread, _ in consistency_results if consistent and spread > 0])
                self.log_result("Price Data Consistency", "PASS", 
                               f"{consistent_symbols}/{total_symbols} symbols consistent, "
                               f"avg spread: {avg_spread:.3f}%")
            else:
                self.log_result("Price Data Consistency", "WARN", 
                               f"Price inconsistencies: {consistent_symbols}/{total_symbols} consistent")
                
        except Exception as e:
            self.log_result("Price Data Consistency", "FAIL", f"Error: {str(e)}")

    async def test_volume_data_validation(self, exchange):
        """Test volume data validation across timeframes."""
        try:
            logger.info("Testing volume data validation...")
            
            symbol = 'BTCUSDT'
            volume_tests = []
            
            # Test 1: 24hr volume consistency
            try:
                ticker = await exchange.get_ticker(symbol)
                if ticker and 'quoteVolume' in ticker:
                    volume_24h = float(ticker['quoteVolume'])
                    
                    # Check if volume is reasonable (> 0 and < extreme values)
                    if 0 < volume_24h < 1e12:  # Less than 1 trillion
                        volume_tests.append(('24h_volume_range', True, volume_24h))
                    else:
                        volume_tests.append(('24h_volume_range', False, volume_24h))
                else:
                    volume_tests.append(('24h_volume_range', False, 0))
            except Exception as e:
                volume_tests.append(('24h_volume_range', False, 0))
            
            # Test 2: OHLCV volume consistency
            try:
                ohlcv = await exchange.get_ohlcv(symbol, '1h', 24)
                if ohlcv and len(ohlcv) >= 12:  # At least 12 hours of data
                    volumes = [float(candle[5]) for candle in ohlcv[-12:]]  # Last 12 hours
                    
                    # Check for reasonable volume distribution
                    if all(v >= 0 for v in volumes):
                        volume_stddev = statistics.stdev(volumes) if len(volumes) > 1 else 0
                        volume_mean = statistics.mean(volumes)
                        cv = volume_stddev / volume_mean if volume_mean > 0 else 0
                        
                        # Coefficient of variation should be reasonable (< 2.0)
                        if cv < 2.0:
                            volume_tests.append(('volume_distribution', True, cv))
                        else:
                            volume_tests.append(('volume_distribution', False, cv))
                    else:
                        volume_tests.append(('volume_distribution', False, -1))
                else:
                    volume_tests.append(('volume_distribution', False, 0))
            except Exception as e:
                volume_tests.append(('volume_distribution', False, 0))
            
            # Test 3: Volume-price correlation check
            try:
                ohlcv = await exchange.get_ohlcv(symbol, '1h', 24)
                if ohlcv and len(ohlcv) >= 10:
                    prices = [float(candle[4]) for candle in ohlcv[-10:]]  # Close prices
                    volumes = [float(candle[5]) for candle in ohlcv[-10:]]
                    
                    # Check if there's some correlation (prices and volumes both move)
                    price_changes = [abs(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
                    volume_changes = [abs(volumes[i] - volumes[i-1]) / volumes[i-1] for i in range(1, len(volumes)) if volumes[i-1] > 0]
                    
                    if len(price_changes) > 0 and len(volume_changes) > 0:
                        # Both should show some activity
                        price_activity = sum(1 for pc in price_changes if pc > 0.001)  # > 0.1% change
                        volume_activity = sum(1 for vc in volume_changes if vc > 0.1)   # > 10% change
                        
                        if price_activity > 0 and volume_activity > 0:
                            volume_tests.append(('volume_price_activity', True, f"{price_activity}p/{volume_activity}v"))
                        else:
                            volume_tests.append(('volume_price_activity', False, f"{price_activity}p/{volume_activity}v"))
                    else:
                        volume_tests.append(('volume_price_activity', False, "no_data"))
                else:
                    volume_tests.append(('volume_price_activity', False, "insufficient_data"))
            except Exception as e:
                volume_tests.append(('volume_price_activity', False, f"error: {str(e)}"))
            
            # Evaluate volume tests
            passed_tests = sum(1 for _, passed, _ in volume_tests if passed)
            total_tests = len(volume_tests)
            
            if passed_tests >= total_tests * 0.8:
                self.log_result("Volume Data Validation", "PASS", 
                               f"{passed_tests}/{total_tests} volume tests passed")
            else:
                self.log_result("Volume Data Validation", "WARN", 
                               f"Volume data issues: {passed_tests}/{total_tests} passed")
                
        except Exception as e:
            self.log_result("Volume Data Validation", "FAIL", f"Error: {str(e)}")

    async def test_timestamp_accuracy(self, exchange):
        """Test timestamp accuracy and consistency."""
        try:
            logger.info("Testing timestamp accuracy...")
            
            timestamp_tests = []
            current_time = int(time.time() * 1000)  # Current time in milliseconds
            
            # Test 1: Ticker timestamp
            try:
                ticker = await exchange.get_ticker('BTCUSDT')
                if ticker and 'timestamp' in ticker:
                    ticker_timestamp = ticker['timestamp']
                    time_diff = abs(current_time - ticker_timestamp)
                    
                    # Should be within 5 minutes (300,000ms)
                    if time_diff < 300000:
                        timestamp_tests.append(('ticker_timestamp', True, time_diff / 1000))
                    else:
                        timestamp_tests.append(('ticker_timestamp', False, time_diff / 1000))
                else:
                    timestamp_tests.append(('ticker_timestamp', False, 0))
            except Exception as e:
                timestamp_tests.append(('ticker_timestamp', False, 0))
            
            # Test 2: OHLCV timestamp progression
            try:
                ohlcv = await exchange.get_ohlcv('BTCUSDT', '1h', 5)
                if ohlcv and len(ohlcv) >= 3:
                    timestamps = [candle[0] for candle in ohlcv]
                    
                    # Check if timestamps are in ascending order
                    ascending = all(timestamps[i] < timestamps[i+1] for i in range(len(timestamps)-1))
                    
                    # Check timestamp intervals (should be 1 hour = 3600000ms)
                    intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
                    expected_interval = 3600000  # 1 hour
                    
                    # Allow 10% tolerance
                    interval_consistent = all(abs(interval - expected_interval) < expected_interval * 0.1 for interval in intervals)
                    
                    if ascending and interval_consistent:
                        timestamp_tests.append(('ohlcv_timestamps', True, statistics.mean(intervals)))
                    else:
                        timestamp_tests.append(('ohlcv_timestamps', False, statistics.mean(intervals) if intervals else 0))
                else:
                    timestamp_tests.append(('ohlcv_timestamps', False, 0))
            except Exception as e:
                timestamp_tests.append(('ohlcv_timestamps', False, 0))
            
            # Test 3: Order book timestamp freshness
            try:
                orderbook = await exchange.get_order_book('BTCUSDT', 5)
                if orderbook and 'timestamp' in orderbook:
                    ob_timestamp = orderbook['timestamp']
                    time_diff = abs(current_time - ob_timestamp)
                    
                    # Should be very fresh (within 30 seconds)
                    if time_diff < 30000:
                        timestamp_tests.append(('orderbook_timestamp', True, time_diff / 1000))
                    else:
                        timestamp_tests.append(('orderbook_timestamp', False, time_diff / 1000))
                else:
                    timestamp_tests.append(('orderbook_timestamp', False, 0))
            except Exception as e:
                timestamp_tests.append(('orderbook_timestamp', False, 0))
            
            # Evaluate timestamp tests
            passed_tests = sum(1 for _, passed, _ in timestamp_tests if passed)
            total_tests = len(timestamp_tests)
            
            if passed_tests >= total_tests * 0.8:
                avg_freshness = statistics.mean([value for _, passed, value in timestamp_tests if passed and value > 0])
                self.log_result("Timestamp Accuracy", "PASS", 
                               f"{passed_tests}/{total_tests} timestamp tests passed, "
                               f"avg freshness: {avg_freshness:.1f}s")
            else:
                self.log_result("Timestamp Accuracy", "WARN", 
                               f"Timestamp issues: {passed_tests}/{total_tests} passed")
                
        except Exception as e:
            self.log_result("Timestamp Accuracy", "FAIL", f"Error: {str(e)}")

    async def test_data_completeness(self, exchange):
        """Test data completeness across different market data types."""
        try:
            logger.info("Testing data completeness...")
            
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
            completeness_results = {}
            
            for symbol in symbols:
                symbol_results = {}
                
                # Test ticker data completeness
                try:
                    ticker = await exchange.get_ticker(symbol)
                    required_fields = ['last', 'bid', 'ask', 'volume', 'quoteVolume']
                    available_fields = sum(1 for field in required_fields if field in ticker and ticker[field] is not None)
                    symbol_results['ticker'] = available_fields / len(required_fields)
                except Exception:
                    symbol_results['ticker'] = 0
                
                # Test order book completeness
                try:
                    orderbook = await exchange.get_order_book(symbol, 10)
                    if orderbook and 'bids' in orderbook and 'asks' in orderbook:
                        bid_count = len(orderbook['bids'])
                        ask_count = len(orderbook['asks'])
                        symbol_results['orderbook'] = min(bid_count, ask_count) / 10  # Expected 10 levels
                    else:
                        symbol_results['orderbook'] = 0
                except Exception:
                    symbol_results['orderbook'] = 0
                
                # Test OHLCV completeness
                try:
                    ohlcv = await exchange.get_ohlcv(symbol, '1h', 12)
                    if ohlcv:
                        complete_candles = sum(1 for candle in ohlcv if len(candle) >= 6 and all(val is not None for val in candle[:6]))
                        symbol_results['ohlcv'] = complete_candles / len(ohlcv)
                    else:
                        symbol_results['ohlcv'] = 0
                except Exception:
                    symbol_results['ohlcv'] = 0
                
                # Test futures data completeness (if available)
                try:
                    oi = await exchange.get_open_interest(symbol)
                    funding = await exchange.get_funding_rate(symbol)
                    futures_data = 0
                    if oi is not None:
                        futures_data += 0.5
                    if funding is not None:
                        futures_data += 0.5
                    symbol_results['futures'] = futures_data
                except Exception:
                    symbol_results['futures'] = 0
                
                completeness_results[symbol] = symbol_results
            
            # Calculate overall completeness
            data_types = ['ticker', 'orderbook', 'ohlcv', 'futures']
            completeness_scores = []
            
            for data_type in data_types:
                scores = [completeness_results[symbol].get(data_type, 0) for symbol in symbols]
                avg_score = statistics.mean(scores) if scores else 0
                completeness_scores.append((data_type, avg_score))
            
            overall_completeness = statistics.mean([score for _, score in completeness_scores])
            
            if overall_completeness >= 0.8:  # 80% completeness
                self.log_result("Data Completeness", "PASS", 
                               f"Overall completeness: {overall_completeness:.1%}, "
                               f"by type: {dict(completeness_scores)}")
            elif overall_completeness >= 0.6:  # 60% completeness
                self.log_result("Data Completeness", "WARN", 
                               f"Moderate completeness: {overall_completeness:.1%}")
            else:
                self.log_result("Data Completeness", "FAIL", 
                               f"Low completeness: {overall_completeness:.1%}")
                
        except Exception as e:
            self.log_result("Data Completeness", "FAIL", f"Error: {str(e)}")

    async def test_data_freshness_across_endpoints(self, exchange):
        """Test data freshness across different endpoints."""
        try:
            logger.info("Testing data freshness across endpoints...")
            
            current_time = int(time.time() * 1000)
            freshness_tests = []
            
            endpoints = [
                ('ticker', exchange.get_ticker, ('BTCUSDT',), 60000),      # 1 minute tolerance
                ('orderbook', exchange.get_order_book, ('BTCUSDT', 5), 30000),  # 30 seconds tolerance
                ('ohlcv', exchange.get_ohlcv, ('BTCUSDT', '1m', 3), 120000),   # 2 minutes tolerance
            ]
            
            for endpoint_name, method, args, tolerance in endpoints:
                try:
                    start_time = time.time()
                    data = await method(*args)
                    fetch_time = (time.time() - start_time) * 1000  # ms
                    
                    if data:
                        # Extract timestamp if available
                        timestamp = None
                        if isinstance(data, dict) and 'timestamp' in data:
                            timestamp = data['timestamp']
                        elif endpoint_name == 'ohlcv' and len(data) > 0:
                            timestamp = data[-1][0]  # Latest candle timestamp
                        
                        if timestamp:
                            age = current_time - timestamp
                            is_fresh = age <= tolerance
                            freshness_tests.append((endpoint_name, is_fresh, age / 1000, fetch_time))
                        else:
                            freshness_tests.append((endpoint_name, False, 0, fetch_time))
                    else:
                        freshness_tests.append((endpoint_name, False, 0, 0))
                        
                except Exception as e:
                    freshness_tests.append((endpoint_name, False, 0, 0))
                    logger.debug(f"Freshness test failed for {endpoint_name}: {str(e)}")
            
            # Evaluate freshness
            fresh_endpoints = sum(1 for _, fresh, _, _ in freshness_tests if fresh)
            total_endpoints = len(freshness_tests)
            
            if fresh_endpoints >= total_endpoints * 0.8:
                avg_age = statistics.mean([age for _, fresh, age, _ in freshness_tests if fresh and age > 0])
                avg_fetch_time = statistics.mean([ft for _, _, _, ft in freshness_tests if ft > 0])
                self.log_result("Data Freshness Across Endpoints", "PASS", 
                               f"{fresh_endpoints}/{total_endpoints} endpoints fresh, "
                               f"avg age: {avg_age:.1f}s, avg fetch: {avg_fetch_time:.0f}ms")
            else:
                self.log_result("Data Freshness Across Endpoints", "WARN", 
                               f"Freshness issues: {fresh_endpoints}/{total_endpoints} endpoints fresh")
                
        except Exception as e:
            self.log_result("Data Freshness Across Endpoints", "FAIL", f"Error: {str(e)}")

    async def test_numerical_data_sanity(self, exchange):
        """Test numerical data sanity checks."""
        try:
            logger.info("Testing numerical data sanity...")
            
            sanity_tests = []
            
            # Test 1: Price reasonableness
            try:
                ticker = await exchange.get_ticker('BTCUSDT')
                if ticker and 'last' in ticker:
                    price = float(ticker['last'])
                    
                    # BTC price should be in reasonable range (e.g., $1,000 - $1,000,000)
                    if 1000 <= price <= 1000000:
                        sanity_tests.append(('btc_price_range', True, price))
                    else:
                        sanity_tests.append(('btc_price_range', False, price))
                else:
                    sanity_tests.append(('btc_price_range', False, 0))
            except Exception:
                sanity_tests.append(('btc_price_range', False, 0))
            
            # Test 2: Bid-Ask spread reasonableness
            try:
                orderbook = await exchange.get_order_book('BTCUSDT', 1)
                if orderbook and orderbook['bids'] and orderbook['asks']:
                    bid = float(orderbook['bids'][0][0])
                    ask = float(orderbook['asks'][0][0])
                    
                    if bid > 0 and ask > bid:
                        spread_pct = ((ask - bid) / bid) * 100
                        
                        # Spread should be reasonable (< 5%)
                        if 0 < spread_pct < 5:
                            sanity_tests.append(('spread_reasonableness', True, spread_pct))
                        else:
                            sanity_tests.append(('spread_reasonableness', False, spread_pct))
                    else:
                        sanity_tests.append(('spread_reasonableness', False, 0))
                else:
                    sanity_tests.append(('spread_reasonableness', False, 0))
            except Exception:
                sanity_tests.append(('spread_reasonableness', False, 0))
            
            # Test 3: Volume reasonableness
            try:
                ticker = await exchange.get_ticker('BTCUSDT')
                if ticker and 'quoteVolume' in ticker:
                    volume = float(ticker['quoteVolume'])
                    
                    # 24h volume should be reasonable (> $1M, < $1T)
                    if 1000000 <= volume <= 1000000000000:
                        sanity_tests.append(('volume_reasonableness', True, volume))
                    else:
                        sanity_tests.append(('volume_reasonableness', False, volume))
                else:
                    sanity_tests.append(('volume_reasonableness', False, 0))
            except Exception:
                sanity_tests.append(('volume_reasonableness', False, 0))
            
            # Test 4: OHLC relationships
            try:
                ohlcv = await exchange.get_ohlcv('BTCUSDT', '1h', 5)
                if ohlcv and len(ohlcv) >= 3:
                    valid_ohlc = 0
                    total_candles = 0
                    
                    for candle in ohlcv[-3:]:  # Check last 3 candles
                        if len(candle) >= 6:
                            timestamp, open_p, high, low, close, volume = candle[:6]
                            total_candles += 1
                            
                            # Check OHLC relationships: low <= open,close <= high
                            if (float(low) <= float(open_p) <= float(high) and 
                                float(low) <= float(close) <= float(high) and
                                float(volume) >= 0):
                                valid_ohlc += 1
                    
                    if total_candles > 0:
                        ohlc_validity = valid_ohlc / total_candles
                        if ohlc_validity >= 0.8:
                            sanity_tests.append(('ohlc_relationships', True, ohlc_validity))
                        else:
                            sanity_tests.append(('ohlc_relationships', False, ohlc_validity))
                    else:
                        sanity_tests.append(('ohlc_relationships', False, 0))
                else:
                    sanity_tests.append(('ohlc_relationships', False, 0))
            except Exception:
                sanity_tests.append(('ohlc_relationships', False, 0))
            
            # Evaluate sanity tests
            passed_tests = sum(1 for _, passed, _ in sanity_tests if passed)
            total_tests = len(sanity_tests)
            
            if passed_tests >= total_tests * 0.8:
                self.log_result("Numerical Data Sanity", "PASS", 
                               f"{passed_tests}/{total_tests} sanity checks passed")
            else:
                failed_tests = [name for name, passed, _ in sanity_tests if not passed]
                self.log_result("Numerical Data Sanity", "WARN", 
                               f"Sanity check failures: {failed_tests}")
                
        except Exception as e:
            self.log_result("Numerical Data Sanity", "FAIL", f"Error: {str(e)}")

    def generate_summary(self):
        """Generate test summary."""
        total = sum(self.test_results.values())
        passed = self.test_results['passed']
        
        logger.info("\n" + "="*60)
        logger.info("DATA QUALITY CROSS-VALIDATION TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"📊 Total Tests: {total}")
        logger.info(f"✅ Passed: {self.test_results['passed']}")
        logger.info(f"❌ Failed: {self.test_results['failed']}")
        logger.info(f"⚠️ Warnings: {self.test_results['warnings']}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        logger.info(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 75:
            logger.info("🎉 Data quality validation passed!")
            return True
        else:
            logger.warning("⚠️ Data quality issues detected - needs attention")
            return False

async def main():
    """Run Data Quality Cross-Validation tests."""
    logger.info("🔍 TEST 8: Data Quality Cross-Validation")
    logger.info("="*50)
    
    tester = DataQualityCrossValidationTester()
    
    try:
        # Initialize exchange
        config_manager = ConfigManager()
        config = config_manager.config
        
        async with BinanceExchange(config=config) as exchange:
            logger.info("🔗 Connected to Binance exchange")
            
            # Run data quality tests
            await tester.test_price_data_consistency(exchange)
            await tester.test_volume_data_validation(exchange)
            await tester.test_timestamp_accuracy(exchange)
            await tester.test_data_completeness(exchange)
            await tester.test_data_freshness_across_endpoints(exchange)
            await tester.test_numerical_data_sanity(exchange)
            
        return tester.generate_summary()
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 