#!/usr/bin/env python
"""
Test script to validate integration between MarketMonitor OHLCV cache and ReportGenerator.
This confirms that we're using cached data instead of re-fetching or generating simulated data.
"""

import asyncio
import logging
import os
import sys
import pandas as pd
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src directory to path to resolve imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.monitoring.monitor import MarketMonitor
from src.core.reporting.pdf_generator import ReportGenerator
from src.core.exchanges.exchange_manager import ExchangeManager

async def main():
    """Test the integration between MarketMonitor OHLCV cache and ReportGenerator."""
    
    # Load configuration or set defaults
    logger.info("Initializing test environment...")
    config = {
        'exchanges': {
            'bybit': {
                'api_key': os.environ.get('BYBIT_API_KEY', ''),
                'api_secret': os.environ.get('BYBIT_API_SECRET', ''),
                'rest_endpoint': 'https://api.bybit.com',
                'category': 'linear'
            }
        },
        'monitor': {
            'timeframes': {
                'base': '1',
                'ltf': '5',
                'mtf': '30',
                'htf': '240'
            }
        },
        'cache': {
            'enabled': True,
            'ttl': 300  # 5 minutes
        }
    }
    
    # Initialize components
    logger.info("Initializing exchange manager...")
    exchange_manager = ExchangeManager(config)
    await exchange_manager.initialize()
    
    logger.info("Initializing market monitor...")
    market_monitor = MarketMonitor(
        config=config,
        exchange_manager=exchange_manager
    )
    
    logger.info("Initializing report generator...")
    report_generator = ReportGenerator()
    
    # Test symbol
    symbol = 'BTCUSDT'
    
    # First, fetch market data to populate the cache
    logger.info(f"Fetching market data for {symbol} to populate cache...")
    market_data = await market_monitor.fetch_market_data(symbol, force_refresh=True)
    
    if not market_data:
        logger.error("Failed to fetch market data")
        return
    
    logger.info(f"Market data fetched for {symbol}")
    
    # Get OHLCV data from cache formatted for report
    logger.info("Getting OHLCV data from cache for report generation...")
    ohlcv_data = market_monitor.get_ohlcv_for_report(symbol)
    
    if ohlcv_data is None:
        logger.error("Failed to get OHLCV data from cache")
        return
    
    logger.info(f"Successfully retrieved {len(ohlcv_data)} OHLCV records from cache")
    logger.info(f"OHLCV columns: {ohlcv_data.columns.tolist()}")
    logger.info(f"OHLCV data sample:\n{ohlcv_data.head(3)}")
    
    # Create sample signal data
    signal_data = {
        'symbol': symbol,
        'signal_type': 'BUY',
        'confluence_score': 75.5,
        'price': float(market_data['ticker']['last']),
        'reliability': 0.85,
        'timestamp': int(datetime.now().timestamp() * 1000),
        'trade_params': {
            'entry_price': float(market_data['ticker']['last']),
            'stop_loss': float(market_data['ticker']['last']) * 0.95,
            'targets': [
                {'price': float(market_data['ticker']['last']) * 1.05, 'name': 'Target 1'},
                {'price': float(market_data['ticker']['last']) * 1.10, 'name': 'Target 2'}
            ]
        }
    }
    
    # Generate a report using the cached OHLCV data
    logger.info("Generating report using cached OHLCV data...")
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output")
    os.makedirs(output_dir, exist_ok=True)
    
    pdf_path, json_path = report_generator.generate_trading_report(
        signal_data=signal_data,
        ohlcv_data=ohlcv_data,
        output_dir=output_dir
    )
    
    if pdf_path:
        logger.info(f"Report successfully generated at: {pdf_path}")
    else:
        logger.error("Failed to generate report")
    
    # Also test with direct API integration in MarketMonitor
    logger.info("Testing signal generation with integrated OHLCV cache...")
    
    # Create a sample analysis result
    analysis_result = {
        'symbol': symbol,
        'confluence_score': 75.5,
        'components': {'momentum': 80, 'trend': 70, 'volume': 60},
        'price': float(market_data['ticker']['last']),
        'reliability': 0.85
    }
    
    # Set the report generator on the market monitor for testing
    market_monitor.signal_generator = type('MockSignalGenerator', (), {'report_generator': report_generator})
    
    # Generate signal which should use the cached OHLCV data
    signal = await market_monitor._generate_signal(symbol, analysis_result)
    
    if signal:
        logger.info("Signal generation complete, report should have been generated using cached data")
    else:
        logger.error("Failed to generate signal")
    
    # Clean up
    await exchange_manager.close()
    
    logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(main()) 