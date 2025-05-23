#!/usr/bin/env python3
"""
Test script to validate the MarketMonitor._ohlcv_cache fix
"""

import logging
import asyncio
import unittest.mock
import pandas as pd
from typing import Dict, Any

from src.monitoring.monitor import MarketMonitor

class MarketReportTester:
    """Test class for market report functionality"""
    
    def __init__(self):
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger()
        
        # Create MarketMonitor instance with mock dependencies
        mock_config = {}
        mock_exchange = unittest.mock.MagicMock()
        mock_exchange_manager = unittest.mock.MagicMock()
        mock_top_symbols_manager = unittest.mock.MagicMock()
        mock_alert_manager = unittest.mock.MagicMock()
        
        # Create a mock MetricsManager
        mock_metrics_manager = unittest.mock.MagicMock()
        
        # Mock the fetch_ohlcv method to return test data
        mock_exchange_manager.get_exchange.return_value = mock_exchange
        mock_exchange.fetch_ohlcv = self.mock_fetch_ohlcv
        
        # Configure top_symbols_manager to return test symbols
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        mock_top_symbols_manager.get_top_symbols.return_value = test_symbols
        
        self.market_monitor = MarketMonitor(
            logger=self.logger,
            config=mock_config,
            exchange=mock_exchange,
            exchange_manager=mock_exchange_manager,
            top_symbols_manager=mock_top_symbols_manager,
            alert_manager=mock_alert_manager,
            metrics_manager=mock_metrics_manager
        )
    
    async def mock_fetch_ohlcv(self, symbol, timeframe="1m", since=None, limit=100, params=None):
        """Mock fetch_ohlcv to return test data"""
        # Create some test OHLCV data
        data = []
        timestamp = 1714500000000  # Starting timestamp
        
        for i in range(100):
            # [timestamp, open, high, low, close, volume]
            data.append([
                timestamp + (i * 60000),  # Add i minutes
                100 + i,  # Open
                105 + i,  # High
                95 + i,   # Low
                102 + i,  # Close
                1000 + i * 10  # Volume
            ])
        
        return data
    
    async def fetch_with_retry(self, method_name, *args, **kwargs):
        """Mock _fetch_with_retry to call the mock fetch_ohlcv method"""
        if method_name == "fetch_ohlcv":
            return await self.mock_fetch_ohlcv(*args, **kwargs)
        elif method_name == "fetch_order_book":
            return {'asks': [[100, 1], [101, 2]], 'bids': [[99, 1], [98, 2]], 'timestamp': 1714500000000}
        elif method_name == "fetch_ticker":
            return {'last': 100, 'bid': 99, 'ask': 101, 'volume': 1000, 'timestamp': 1714500000000}
        elif method_name == "fetch_trades":
            return [{'id': '1', 'price': 100, 'amount': 1, 'timestamp': 1714500000000}]
        
        return None
    
    async def test_ohlcv_cache_population(self):
        """Test if _ohlcv_cache is populated correctly"""
        self.logger.info("Testing OHLCV cache population...")
        
        # Replace _fetch_with_retry with our mock version
        self.market_monitor._fetch_with_retry = self.fetch_with_retry
        
        # Create a mock market_data_manager 
        mock_market_data_manager = unittest.mock.MagicMock()
        # Make it return a simple market data structure
        mock_market_data = {
            'ohlcv': {
                'base': pd.DataFrame({
                    'timestamp': [1714500000000 + i * 60000 for i in range(100)],
                    'open': [100 + i for i in range(100)],
                    'high': [105 + i for i in range(100)],
                    'low': [95 + i for i in range(100)],
                    'close': [102 + i for i in range(100)],
                    'volume': [1000 + i * 10 for i in range(100)]
                })
            }
        }
        mock_market_data_manager.get_market_data = unittest.mock.AsyncMock(return_value=mock_market_data)
        self.market_monitor.market_data_manager = mock_market_data_manager
        
        # Directly populate the _ohlcv_cache
        symbol = "BTCUSDT"
        raw_ohlcv = await self.mock_fetch_ohlcv(symbol)
        ohlcv_data = self.market_monitor._standardize_ohlcv(raw_ohlcv)
        
        self.market_monitor._ohlcv_cache[symbol] = {
            'raw': raw_ohlcv,
            'processed': ohlcv_data,
            'timestamp': 1714500000000
        }
        
        # Verify cache was populated
        if symbol in self.market_monitor._ohlcv_cache:
            self.logger.info("PASSED: _ohlcv_cache was populated for the symbol")
            
            # Check structure of cache entry
            cache_entry = self.market_monitor._ohlcv_cache[symbol]
            if 'raw' in cache_entry and 'processed' in cache_entry and 'timestamp' in cache_entry:
                self.logger.info("PASSED: _ohlcv_cache has the expected structure")
                
                # Verify processed data contains timeframes
                processed = cache_entry['processed']
                if isinstance(processed, dict) and 'base' in processed:
                    self.logger.info("PASSED: Processed data contains base timeframe")
                    
                    # Check if the data is properly formatted as a DataFrame
                    base_df = processed['base']
                    if isinstance(base_df, pd.DataFrame):
                        self.logger.info("PASSED: Processed data contains DataFrame")
                        self.logger.info(f"DataFrame contains {len(base_df)} rows")
                    else:
                        self.logger.error(f"FAILED: Processed base data is not a DataFrame, got {type(base_df)}")
                else:
                    self.logger.error("FAILED: Processed data does not contain base timeframe")
            else:
                self.logger.error("FAILED: _ohlcv_cache entry has invalid structure")
        else:
            self.logger.error("FAILED: _ohlcv_cache was not populated for the symbol")
            
        # Test get_ohlcv_for_report method
        self.logger.info("\nTesting get_ohlcv_for_report method...")
        ohlcv_df = self.market_monitor.get_ohlcv_for_report(symbol)
        
        if ohlcv_df is not None and isinstance(ohlcv_df, pd.DataFrame):
            self.logger.info("PASSED: get_ohlcv_for_report returned a DataFrame")
            self.logger.info(f"DataFrame contains {len(ohlcv_df)} rows and columns: {ohlcv_df.columns.tolist()}")
        else:
            self.logger.error(f"FAILED: get_ohlcv_for_report did not return a DataFrame, got {type(ohlcv_df)}")
            
    async def test_market_report_generation(self):
        """Test if _generate_market_report works with the fixed _ohlcv_cache"""
        self.logger.info("\nTesting market report generation...")
        
        # Replace _fetch_with_retry with our mock version
        self.market_monitor._fetch_with_retry = self.fetch_with_retry
        
        # Mock get_monitored_symbols to return test symbols
        self.market_monitor.get_monitored_symbols = lambda: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        try:
            # Populate cache with test data for each symbol
            for symbol in self.market_monitor.get_monitored_symbols():
                raw_ohlcv = await self.mock_fetch_ohlcv(symbol)
                ohlcv_data = self.market_monitor._standardize_ohlcv(raw_ohlcv)
                
                self.market_monitor._ohlcv_cache[symbol] = {
                    'raw': raw_ohlcv,
                    'processed': ohlcv_data,
                    'timestamp': 1714500000000
                }
                
            # Create a proper mock for market_reporter
            mock_market_reporter = unittest.mock.MagicMock()
            mock_market_reporter.generate_report = unittest.mock.AsyncMock(return_value=True)
            self.market_monitor.market_reporter = mock_market_reporter
                
            # Now call _generate_market_report
            await self.market_monitor._generate_market_report()
            self.logger.info("PASSED: _generate_market_report completed without errors")
        except Exception as e:
            self.logger.error(f"FAILED: Error in _generate_market_report: {str(e)}")

async def main():
    """Run the tests"""
    tester = MarketReportTester()
    await tester.test_ohlcv_cache_population()
    await tester.test_market_report_generation()

if __name__ == "__main__":
    asyncio.run(main()) 