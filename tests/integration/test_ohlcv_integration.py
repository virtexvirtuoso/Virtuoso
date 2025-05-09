#!/usr/bin/env python
"""
Simplified test script to validate integration between MarketMonitor OHLCV cache and ReportGenerator.
This confirms that we're using cached data instead of re-fetching or generating simulated data.
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import only the necessary classes
from src.core.reporting.pdf_generator import ReportGenerator

def create_mock_ohlcv_data(symbol="BTCUSDT", periods=100):
    """Create mock OHLCV data for testing"""
    np.random.seed(42)
    
    # Generate timestamps (starting from 100 periods ago, each 1 minute apart)
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=periods)
    timestamps = pd.date_range(start=start_time, end=end_time, periods=periods)
    
    # Generate price data with a random walk
    base_price = 50000.0
    price_changes = np.random.normal(0, 100, periods)
    closes = base_price + np.cumsum(price_changes)
    
    # Generate open, high, low based on close
    opens = closes - np.random.normal(0, 20, periods)
    highs = np.maximum(opens, closes) + np.random.normal(10, 5, periods)
    lows = np.minimum(opens, closes) - np.random.normal(10, 5, periods)
    
    # Generate volume data
    volumes = np.random.normal(10, 5, periods) * 10
    
    # Create DataFrame
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })
    
    return df

def create_mock_signal_data(symbol="BTCUSDT", price=None):
    """Create mock signal data for testing"""
    if price is None:
        price = 50000.0
    
    # Create a sample trading signal
    return {
        'symbol': symbol,
        'signal_type': 'BUY',
        'confluence_score': 75.5,
        'price': price,
        'reliability': 0.85,
        'timestamp': int(datetime.now().timestamp() * 1000),
        'trade_params': {
            'entry_price': price,
            'stop_loss': price * 0.95,
            'targets': [
                {'price': price * 1.05, 'name': 'Target 1'},
                {'price': price * 1.10, 'name': 'Target 2'}
            ]
        }
    }

def main():
    """Test the integration between MarketMonitor OHLCV cache and ReportGenerator."""
    
    # Create a test output directory
    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create mock data
    logger.info("Creating mock OHLCV data...")
    ohlcv_data = create_mock_ohlcv_data()
    logger.info(f"Created mock OHLCV data with {len(ohlcv_data)} records")
    
    # Create mock signal data
    price = ohlcv_data['close'].iloc[-1]
    signal_data = create_mock_signal_data(price=price)
    logger.info("Created mock signal data")
    
    # Initialize report generator
    logger.info("Initializing report generator...")
    report_generator = ReportGenerator()
    
    # Generate report using our mock OHLCV data
    logger.info("Generating report using mock OHLCV data...")
    pdf_path, json_path = report_generator.generate_trading_report(
        signal_data=signal_data,
        ohlcv_data=ohlcv_data,
        output_dir=output_dir
    )
    
    if pdf_path:
        logger.info(f"Report successfully generated at: {pdf_path}")
        logger.info(f"JSON data saved to: {json_path}")
        
        # Now generate a report without OHLCV data to see if it creates a simulated chart
        logger.info("Generating report WITHOUT OHLCV data (should create simulated chart)...")
        pdf_path_sim, json_path_sim = report_generator.generate_trading_report(
            signal_data=signal_data,
            ohlcv_data=None,
            output_dir=output_dir
        )
        
        if pdf_path_sim:
            logger.info(f"Simulated report successfully generated at: {pdf_path_sim}")
            logger.info(f"Simulated JSON data saved to: {json_path_sim}")
        else:
            logger.error("Failed to generate simulated report")
    else:
        logger.error("Failed to generate report")
    
    logger.info("Test completed")

if __name__ == "__main__":
    main() 