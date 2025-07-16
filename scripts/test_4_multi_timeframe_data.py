#!/usr/bin/env python3

import sys
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

from config.manager import ConfigManager
from data_acquisition.binance.binance_exchange import BinanceExchange

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class MultiTimeframeDataTester:
    """Test multi-timeframe data consistency and quality."""
    
    def __init__(self):
        self.test_results = {'passed': 0, 'failed': 0, 'warnings': 0}
        self.timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        
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

    async def test_timeframe_data_availability(self, exchange):
        """Test data availability across different timeframes."""
        try:
            logger.info("Testing timeframe data availability...")
            
            symbol = 'BTCUSDT'
            available_timeframes = []
            
            for timeframe in self.timeframes:
                try:
                    ohlcv = await exchange.get_ohlcv(symbol, timeframe, 10)
                    if ohlcv and len(ohlcv) >= 5:
                        available_timeframes.append(timeframe)
                        logger.debug(f"✓ {timeframe}: {len(ohlcv)} candles")
                    else:
                        logger.debug(f"✗ {timeframe}: insufficient data")
                except Exception as e:
                    logger.debug(f"✗ {timeframe}: error - {str(e)}")
            
            availability_rate = (len(available_timeframes) / len(self.timeframes)) * 100
            
            if availability_rate >= 80:
                self.log_result("Timeframe Availability", "PASS", 
                               f"{len(available_timeframes)}/{len(self.timeframes)} timeframes available")
            else:
                self.log_result("Timeframe Availability", "FAIL", 
                               f"Low availability: {availability_rate:.1f}%")
                
        except Exception as e:
            self.log_result("Timeframe Availability", "FAIL", f"Error: {str(e)}")

    async def test_ohlcv_data_quality(self, exchange):
        """Test OHLCV data quality and consistency."""
        try:
            logger.info("Testing OHLCV data quality...")
            
            symbol = 'BTCUSDT'
            quality_issues = 0
            total_checks = 0
            
            for timeframe in ['1m', '5m', '1h']:
                try:
                    ohlcv = await exchange.get_ohlcv(symbol, timeframe, 50)
                    if not ohlcv or len(ohlcv) < 10:
                        continue
                    
                    for candle in ohlcv[-10:]:  # Check last 10 candles
                        total_checks += 1
                        
                        # Extract OHLCV values
                        timestamp, open_price, high, low, close, volume = candle[:6]
                        
                        # Quality checks
                        if not (low <= open_price <= high and low <= close <= high):
                            quality_issues += 1
                            logger.debug(f"OHLC consistency issue in {timeframe}")
                        
                        if high == low and volume > 0:
                            quality_issues += 1
                            logger.debug(f"Price/volume inconsistency in {timeframe}")
                        
                        if any(val < 0 for val in [open_price, high, low, close, volume]):
                            quality_issues += 1
                            logger.debug(f"Negative values in {timeframe}")
                
                except Exception as e:
                    logger.debug(f"Error checking {timeframe}: {str(e)}")
            
            if total_checks > 0:
                quality_rate = ((total_checks - quality_issues) / total_checks) * 100
                
                if quality_rate >= 95:
                    self.log_result("OHLCV Data Quality", "PASS", 
                                   f"{quality_issues}/{total_checks} quality issues ({quality_rate:.1f}%)")
                else:
                    self.log_result("OHLCV Data Quality", "FAIL", 
                                   f"High error rate: {100-quality_rate:.1f}%")
            else:
                self.log_result("OHLCV Data Quality", "FAIL", "No data to check")
                
        except Exception as e:
            self.log_result("OHLCV Data Quality", "FAIL", f"Error: {str(e)}")

    async def test_timestamp_consistency(self, exchange):
        """Test timestamp consistency across timeframes."""
        try:
            logger.info("Testing timestamp consistency...")
            
            symbol = 'BTCUSDT'
            timestamp_issues = 0
            timeframes_tested = 0
            
            for timeframe in ['1m', '5m', '15m', '1h']:
                try:
                    ohlcv = await exchange.get_ohlcv(symbol, timeframe, 20)
                    if not ohlcv or len(ohlcv) < 10:
                        continue
                    
                    timeframes_tested += 1
                    
                    # Check timestamp spacing
                    intervals = {'1m': 60000, '5m': 300000, '15m': 900000, '1h': 3600000}
                    expected_interval = intervals.get(timeframe, 0)
                    
                    if expected_interval > 0:
                        for i in range(1, min(10, len(ohlcv))):
                            time_diff = ohlcv[i][0] - ohlcv[i-1][0]
                            if abs(time_diff - expected_interval) > expected_interval * 0.1:  # 10% tolerance
                                timestamp_issues += 1
                                logger.debug(f"Timestamp gap in {timeframe}: {time_diff}ms vs {expected_interval}ms")
                
                except Exception as e:
                    logger.debug(f"Error checking timestamps for {timeframe}: {str(e)}")
            
            if timeframes_tested > 0:
                if timestamp_issues == 0:
                    self.log_result("Timestamp Consistency", "PASS", 
                                   f"No timestamp issues across {timeframes_tested} timeframes")
                elif timestamp_issues <= 2:
                    self.log_result("Timestamp Consistency", "WARN", 
                                   f"{timestamp_issues} minor timestamp issues")
                else:
                    self.log_result("Timestamp Consistency", "FAIL", 
                                   f"{timestamp_issues} timestamp issues")
            else:
                self.log_result("Timestamp Consistency", "FAIL", "No timeframes tested")
                
        except Exception as e:
            self.log_result("Timestamp Consistency", "FAIL", f"Error: {str(e)}")

    async def test_data_freshness(self, exchange):
        """Test data freshness and real-time updates."""
        try:
            logger.info("Testing data freshness...")
            
            symbol = 'BTCUSDT'
            fresh_data_count = 0
            total_tests = 0
            
            for timeframe in ['1m', '5m']:
                try:
                    ohlcv = await exchange.get_ohlcv(symbol, timeframe, 5)
                    if not ohlcv:
                        continue
                    
                    total_tests += 1
                    latest_candle = ohlcv[-1]
                    timestamp = latest_candle[0]
                    
                    # Check if data is fresh (within expected timeframe)
                    current_time = int(time.time() * 1000)
                    time_diff = current_time - timestamp
                    
                    max_age = {'1m': 120000, '5m': 360000}  # 2 min for 1m, 6 min for 5m
                    expected_max = max_age.get(timeframe, 600000)
                    
                    if time_diff <= expected_max:
                        fresh_data_count += 1
                        logger.debug(f"Fresh data for {timeframe}: {time_diff/1000:.0f}s old")
                    else:
                        logger.debug(f"Stale data for {timeframe}: {time_diff/1000:.0f}s old")
                
                except Exception as e:
                    logger.debug(f"Error checking freshness for {timeframe}: {str(e)}")
            
            if total_tests > 0:
                freshness_rate = (fresh_data_count / total_tests) * 100
                
                if freshness_rate >= 75:
                    self.log_result("Data Freshness", "PASS", 
                                   f"{fresh_data_count}/{total_tests} timeframes have fresh data")
                else:
                    self.log_result("Data Freshness", "WARN", 
                                   f"Some stale data: {freshness_rate:.1f}% fresh")
            else:
                self.log_result("Data Freshness", "FAIL", "No timeframes tested")
                
        except Exception as e:
            self.log_result("Data Freshness", "FAIL", f"Error: {str(e)}")

    async def test_cross_timeframe_consistency(self, exchange):
        """Test price consistency across different timeframes."""
        try:
            logger.info("Testing cross-timeframe consistency...")
            
            symbol = 'BTCUSDT'
            
            # Get current ticker price as reference
            ticker = await exchange.get_ticker(symbol)
            if not ticker or not ticker.get('last'):
                self.log_result("Cross-Timeframe Consistency", "FAIL", "No ticker price reference")
                return
            
            reference_price = float(ticker['last'])
            consistent_timeframes = 0
            total_timeframes = 0
            
            for timeframe in ['1m', '5m', '15m']:
                try:
                    ohlcv = await exchange.get_ohlcv(symbol, timeframe, 3)
                    if not ohlcv:
                        continue
                    
                    total_timeframes += 1
                    latest_close = float(ohlcv[-1][4])  # Close price
                    
                    # Check if close price is reasonably close to ticker price
                    price_diff_pct = abs(latest_close - reference_price) / reference_price * 100
                    
                    if price_diff_pct < 0.5:  # Within 0.5%
                        consistent_timeframes += 1
                        logger.debug(f"Consistent {timeframe}: ${latest_close:.2f} vs ${reference_price:.2f}")
                    else:
                        logger.debug(f"Inconsistent {timeframe}: {price_diff_pct:.2f}% difference")
                
                except Exception as e:
                    logger.debug(f"Error checking {timeframe} consistency: {str(e)}")
            
            if total_timeframes > 0:
                consistency_rate = (consistent_timeframes / total_timeframes) * 100
                
                if consistency_rate >= 80:
                    self.log_result("Cross-Timeframe Consistency", "PASS", 
                                   f"{consistent_timeframes}/{total_timeframes} timeframes consistent")
                else:
                    self.log_result("Cross-Timeframe Consistency", "WARN", 
                                   f"Low consistency: {consistency_rate:.1f}%")
            else:
                self.log_result("Cross-Timeframe Consistency", "FAIL", "No timeframes tested")
                
        except Exception as e:
            self.log_result("Cross-Timeframe Consistency", "FAIL", f"Error: {str(e)}")

    async def test_volume_aggregation(self, exchange):
        """Test volume aggregation consistency across timeframes."""
        try:
            logger.info("Testing volume aggregation...")
            
            symbol = 'BTCUSDT'
            
            # Get 1-minute data for aggregation comparison
            ohlcv_1m = await exchange.get_ohlcv(symbol, '1m', 60)
            ohlcv_5m = await exchange.get_ohlcv(symbol, '5m', 12)
            
            if not ohlcv_1m or not ohlcv_5m or len(ohlcv_1m) < 30 or len(ohlcv_5m) < 6:
                self.log_result("Volume Aggregation", "WARN", "Insufficient data for volume aggregation test")
                return
            
            # Compare aggregated 1m volumes with 5m volumes
            aggregation_tests = 0
            consistent_aggregations = 0
            
            for i in range(6):  # Test 6 five-minute periods
                try:
                    # Get 5-minute candle
                    five_min_candle = ohlcv_5m[-(i+1)]
                    five_min_volume = float(five_min_candle[5])
                    five_min_start = five_min_candle[0]
                    
                    # Sum corresponding 1-minute volumes
                    one_min_volume_sum = 0
                    valid_1m_candles = 0
                    
                    for candle_1m in ohlcv_1m:
                        candle_time = candle_1m[0]
                        if five_min_start <= candle_time < five_min_start + 300000:  # 5 minutes
                            one_min_volume_sum += float(candle_1m[5])
                            valid_1m_candles += 1
                    
                    if valid_1m_candles >= 4:  # At least 4 of 5 minutes
                        aggregation_tests += 1
                        
                        if five_min_volume > 0:
                            volume_diff_pct = abs(one_min_volume_sum - five_min_volume) / five_min_volume * 100
                            
                            if volume_diff_pct < 5:  # Within 5%
                                consistent_aggregations += 1
                            else:
                                logger.debug(f"Volume aggregation mismatch: {volume_diff_pct:.1f}%")
                
                except Exception as e:
                    logger.debug(f"Error in volume aggregation test {i}: {str(e)}")
            
            if aggregation_tests > 0:
                consistency_rate = (consistent_aggregations / aggregation_tests) * 100
                
                if consistency_rate >= 75:
                    self.log_result("Volume Aggregation", "PASS", 
                                   f"{consistent_aggregations}/{aggregation_tests} aggregations consistent")
                else:
                    self.log_result("Volume Aggregation", "WARN", 
                                   f"Aggregation issues: {consistency_rate:.1f}% consistent")
            else:
                self.log_result("Volume Aggregation", "WARN", "No aggregations tested")
                
        except Exception as e:
            self.log_result("Volume Aggregation", "FAIL", f"Error: {str(e)}")

    async def test_multi_symbol_timeframe_performance(self, exchange):
        """Test performance when fetching multiple symbols across timeframes."""
        try:
            logger.info("Testing multi-symbol timeframe performance...")
            
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
            timeframes = ['1m', '5m', '1h']
            
            start_time = time.time()
            successful_requests = 0
            total_requests = 0
            
            # Create tasks for all combinations
            tasks = []
            for symbol in symbols:
                for timeframe in timeframes:
                    task = exchange.get_ohlcv(symbol, timeframe, 10)
                    tasks.append((symbol, timeframe, task))
                    total_requests += 1
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*[task for _, _, task in tasks], return_exceptions=True)
            
            # Count successful requests
            for i, result in enumerate(results):
                if not isinstance(result, Exception) and result and len(result) >= 5:
                    successful_requests += 1
                else:
                    symbol, timeframe, _ = tasks[i]
                    logger.debug(f"Failed: {symbol} {timeframe}")
            
            total_time = time.time() - start_time
            requests_per_second = total_requests / total_time if total_time > 0 else 0
            success_rate = (successful_requests / total_requests) * 100
            
            if success_rate >= 80 and requests_per_second >= 2:
                self.log_result("Multi-Symbol Performance", "PASS", 
                               f"{successful_requests}/{total_requests} requests successful "
                               f"({requests_per_second:.1f} req/s)")
            else:
                self.log_result("Multi-Symbol Performance", "WARN", 
                               f"Performance issues: {success_rate:.1f}% success, {requests_per_second:.1f} req/s")
                
        except Exception as e:
            self.log_result("Multi-Symbol Performance", "FAIL", f"Error: {str(e)}")

    def generate_summary(self):
        """Generate test summary."""
        total = sum(self.test_results.values())
        passed = self.test_results['passed']
        
        logger.info("\n" + "="*60)
        logger.info("MULTI-TIMEFRAME DATA TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"📊 Total Tests: {total}")
        logger.info(f"✅ Passed: {self.test_results['passed']}")
        logger.info(f"❌ Failed: {self.test_results['failed']}")
        logger.info(f"⚠️ Warnings: {self.test_results['warnings']}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        logger.info(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 75:
            logger.info("🎉 Multi-timeframe data integration is robust!")
            return True
        else:
            logger.warning("⚠️ Multi-timeframe data needs attention")
            return False

async def main():
    """Run Multi-Timeframe Data tests."""
    logger.info("📊 TEST 4: Multi-Timeframe Data Integration")
    logger.info("="*50)
    
    tester = MultiTimeframeDataTester()
    
    try:
        # Initialize exchange
        config_manager = ConfigManager()
        config = config_manager.config
        
        async with BinanceExchange(config=config) as exchange:
            logger.info("🔗 Connected to Binance exchange")
            
            # Run multi-timeframe tests
            await tester.test_timeframe_data_availability(exchange)
            await tester.test_ohlcv_data_quality(exchange)
            await tester.test_timestamp_consistency(exchange)
            await tester.test_data_freshness(exchange)
            await tester.test_cross_timeframe_consistency(exchange)
            await tester.test_volume_aggregation(exchange)
            await tester.test_multi_symbol_timeframe_performance(exchange)
            
        return tester.generate_summary()
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 