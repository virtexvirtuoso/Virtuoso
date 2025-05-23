#!/usr/bin/env python
# Test script to verify PDF chart generation fixes

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("pdf_test")

# Add project root to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_data(periods=50):
    """Create sample OHLCV data for testing."""
    logger.info(f"Creating test data with {periods} periods")
    
    base_price = 50000
    timestamps = [(datetime.now() - timedelta(minutes=i)).timestamp() * 1000 for i in range(periods)]
    
    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": [base_price * (1 + np.random.uniform(-0.02, 0.02)) for _ in range(periods)],
        "high": [base_price * (1 + np.random.uniform(0, 0.04)) for _ in range(periods)],
        "low": [base_price * (1 + np.random.uniform(-0.04, 0)) for _ in range(periods)],
        "close": [base_price * (1 + np.random.uniform(-0.02, 0.02)) for _ in range(periods)],
        "volume": [np.random.randint(1000, 10000) for _ in range(periods)]
    })
    
    logger.info(f"Created DataFrame with shape {df.shape}")
    return df

def test_candlestick_chart():
    """Test the candlestick chart generation with DataFrame index handling."""
    from src.core.reporting.pdf_generator import ReportGenerator
    
    logger.info("Initializing ReportGenerator")
    generator = ReportGenerator(log_level=logging.DEBUG)
    
    # Create test data
    df = create_test_data(periods=50)
    
    # Log DataFrame info
    logger.info(f"Test DataFrame columns: {df.columns.tolist()}")
    logger.info(f"Test DataFrame index type: {type(df.index)}")
    
    # Convert timestamp to DatetimeIndex explicitly for testing
    logger.info("Converting timestamp to DatetimeIndex manually")
    try:
        # Convert the timestamp column to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        # Set it as the index
        df = df.set_index('timestamp')
        logger.info(f"Manual conversion successful, new index type: {type(df.index)}")
        logger.info(f"Index sample: {df.index[0]} to {df.index[-1]}")
    except Exception as e:
        logger.error(f"Manual conversion failed: {str(e)}")
    
    # Create output directory
    output_dir = os.path.join(os.getcwd(), "test_output")
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("Generating candlestick chart")
    chart_path = generator._create_candlestick_chart(
        symbol="BTCUSDT",
        ohlcv_data=df,
        entry_price=50000,
        stop_loss=48000,
        targets=[
            {"name": "Target 1", "price": 52000},
            {"name": "Target 2", "price": 54000}
        ],
        output_dir=output_dir
    )
    
    if chart_path and os.path.exists(chart_path):
        logger.info(f"Chart generated successfully at: {chart_path}")
        return True
    else:
        logger.error("Failed to generate chart")
        return False

def test_simulated_chart():
    """Test the simulated chart generation."""
    from src.core.reporting.pdf_generator import ReportGenerator
    
    logger.info("Initializing ReportGenerator")
    generator = ReportGenerator(log_level=logging.DEBUG)
    
    # Create output directory
    output_dir = os.path.join(os.getcwd(), "test_output")
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("Generating simulated chart")
    chart_path = generator._create_simulated_chart(
        symbol="BTCUSDT",
        entry_price=50000,
        stop_loss=48000,
        targets=[
            {"name": "Target 1", "price": 52000},
            {"name": "Target 2", "price": 54000}
        ],
        output_dir=output_dir
    )
    
    if chart_path and os.path.exists(chart_path):
        logger.info(f"Simulated chart generated successfully at: {chart_path}")
        return True
    else:
        logger.error("Failed to generate simulated chart")
        return False

if __name__ == "__main__":
    logger.info("Starting PDF chart generation tests")
    
    candlestick_result = test_candlestick_chart()
    simulated_result = test_simulated_chart()
    
    logger.info(f"Candlestick chart test: {'PASSED' if candlestick_result else 'FAILED'}")
    logger.info(f"Simulated chart test: {'PASSED' if simulated_result else 'FAILED'}")
    
    if candlestick_result and simulated_result:
        logger.info("All tests PASSED")
        sys.exit(0)
    else:
        logger.error("Some tests FAILED")
        sys.exit(1) 