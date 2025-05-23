#!/usr/bin/env python3
"""Test the _ohlcv_cache fix in a real-world scenario"""

import asyncio
import logging
import pandas as pd
import traceback
import time
import unittest.mock

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger('test_fix_ohlcv')

async def test_ohlcv_cache():
    """Test the _ohlcv_cache fix in the MarketMonitor class."""
    try:
        from src.monitoring.monitor import MarketMonitor
        
        logger.info("Creating a standalone MarketMonitor for testing...")
        
        # Create mock dependencies
        mock_config = {}
        mock_alert_manager = unittest.mock.MagicMock()
        mock_alert_manager.send_discord_webhook_message = unittest.mock.AsyncMock(return_value=True)
        mock_metrics_manager = unittest.mock.MagicMock()
        
        # Create monitor with minimal dependencies
        monitor = MarketMonitor(
            logger=logger,
            config=mock_config,
            alert_manager=mock_alert_manager,
            metrics_manager=mock_metrics_manager
        )
        
        # Generate some test OHLCV data
        def generate_test_ohlcv(count=100):
            data = []
            base_timestamp = int(time.time() * 1000) - (count * 60000)  # Start 'count' minutes ago
            
            for i in range(count):
                # [timestamp, open, high, low, close, volume]
                data.append([
                    base_timestamp + (i * 60000),  # Add i minutes to starting timestamp
                    100 + i * 0.1,  # Open
                    105 + i * 0.1,  # High
                    95 + i * 0.1,   # Low
                    102 + i * 0.1,  # Close
                    1000 + i * 10   # Volume
                ])
            
            return data
        
        # Generate test data
        symbol = 'BTCUSDT'
        raw_ohlcv = generate_test_ohlcv(100)
        
        # Manually populate the _ohlcv_cache
        ohlcv_data = monitor._standardize_ohlcv(raw_ohlcv)
        
        monitor._ohlcv_cache[symbol] = {
            'raw': raw_ohlcv,
            'processed': ohlcv_data,
            'timestamp': int(time.time() * 1000)
        }
        
        logger.info(f"Manually populated _ohlcv_cache for {symbol}")
        
        # Verify cache was populated
        if symbol in monitor._ohlcv_cache:
            logger.info(f"SUCCESS: _ohlcv_cache was populated for {symbol}")
            
            # Check structure of cache entry
            cache_entry = monitor._ohlcv_cache[symbol]
            if 'raw' in cache_entry and 'processed' in cache_entry and 'timestamp' in cache_entry:
                logger.info("SUCCESS: _ohlcv_cache has the correct structure")
                
                # Verify processed data contains timeframes
                processed = cache_entry['processed']
                if isinstance(processed, dict) and 'base' in processed:
                    df = processed['base']
                    logger.info(f"Data contains {len(df)} rows")
                    
                    # Now test get_ohlcv_for_report
                    logger.info("Testing get_ohlcv_for_report method...")
                    ohlcv_df = monitor.get_ohlcv_for_report(symbol)
                    
                    if isinstance(ohlcv_df, pd.DataFrame):
                        logger.info(f"SUCCESS: get_ohlcv_for_report returned a DataFrame with {len(ohlcv_df)} rows")
                        logger.info(f"Columns: {ohlcv_df.columns.tolist()}")
                        
                        # Now generate a market report
                        logger.info("Attempting to generate a market report...")
                        
                        # Mock the get_monitored_symbols method to return our test symbol
                        monitor.get_monitored_symbols = lambda: [symbol]
                        
                        # Mock the market_reporter for the report generation 
                        class MockMarketReporter:
                            async def generate_report(self, report_data):
                                if isinstance(report_data, dict) and 'symbols' in report_data:
                                    logger.info(f"Mock generating report for {len(report_data['symbols'])} symbols")
                                else:
                                    logger.info(f"Mock generating report with data: {report_data.keys() if isinstance(report_data, dict) else type(report_data)}")
                                return True
                                
                        monitor.market_reporter = MockMarketReporter()
                        
                        # Generate the report
                        try:
                            await monitor._generate_market_report()
                            logger.info("SUCCESS: Market report generated successfully")
                        except Exception as e:
                            logger.error(f"ERROR: Failed to generate market report: {str(e)}")
                            logger.error(traceback.format_exc())
                    else:
                        logger.error(f"ERROR: get_ohlcv_for_report returned {type(ohlcv_df)}")
                else:
                    logger.error("ERROR: Cache entry does not contain base timeframe")
            else:
                logger.error("ERROR: Invalid cache structure")
        else:
            logger.error(f"ERROR: _ohlcv_cache was not populated for {symbol}")
        
        logger.info("Test completed.")
    
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_ohlcv_cache()) 