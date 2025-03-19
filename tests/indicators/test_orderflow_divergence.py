#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for OrderflowIndicators price-CVD and price-OI divergence calculations.
"""

import os
import sys
import yaml
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('test_orderflow_divergence')

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the OrderflowIndicators class
from src.indicators.orderflow_indicators import OrderflowIndicators
from src.core.logger import Logger

def create_sample_data(days=20, bullish_divergence=True):
    """
    Create sample market data with price-CVD and price-OI divergence.
    
    Args:
        days: Number of days of data to generate
        bullish_divergence: If True, create bullish divergence (price down, indicator up)
                           If False, create bearish divergence (price up, indicator down)
    
    Returns:
        Dict: Market data dictionary with OHLCV, trades, and sentiment data
    """
    # Create timestamps
    timestamps = [datetime.now() - timedelta(days=i) for i in range(days)]
    timestamps.reverse()  # Oldest first
    
    # Create price data
    if bullish_divergence:
        # Bullish divergence: Price down, indicators up
        price_trend = np.linspace(100, 80, days)  # Decreasing price
        cvd_values = np.linspace(-50, 50, days)   # Increasing CVD
        oi_values = np.linspace(1000, 1500, days) # Increasing OI
    else:
        # Bearish divergence: Price up, indicators down
        price_trend = np.linspace(80, 100, days)  # Increasing price
        cvd_values = np.linspace(50, -50, days)   # Decreasing CVD
        oi_values = np.linspace(1500, 1000, days) # Decreasing OI
    
    # Add some noise
    price_trend += np.random.normal(0, 1, days)
    cvd_values += np.random.normal(0, 5, days)
    oi_values += np.random.normal(0, 50, days)
    
    # Create OHLCV DataFrame
    ohlcv_df = pd.DataFrame({
        'timestamp': timestamps,
        'open': price_trend,
        'high': price_trend + np.random.uniform(0, 2, days),
        'low': price_trend - np.random.uniform(0, 2, days),
        'close': price_trend,
        'volume': np.random.uniform(1000, 5000, days)
    })
    
    # Create trades data
    trades = []
    for i in range(days):
        # Generate trades for each day
        day_trades = 100  # 100 trades per day
        
        # Calculate buy/sell ratio based on CVD for that day
        cvd = cvd_values[i]
        if cvd > 0:
            buy_ratio = 0.5 + (cvd / 200)  # More buys if CVD is positive
        else:
            buy_ratio = 0.5 + (cvd / 200)  # More sells if CVD is negative
            
        buy_ratio = max(0.1, min(0.9, buy_ratio))  # Keep between 0.1 and 0.9
        
        for j in range(day_trades):
            # Determine if this is a buy or sell
            is_buy = np.random.random() < buy_ratio
            
            # Create trade
            trade = {
                'id': f"{i}_{j}",
                'time': timestamps[i] + timedelta(minutes=int(j * 24 * 60 / day_trades)),
                'price': price_trend[i] + np.random.normal(0, 0.5),
                'amount': np.random.uniform(0.1, 2.0),
                'side': 'buy' if is_buy else 'sell'
            }
            trades.append(trade)
    
    # Create sentiment data with open interest
    oi_history = [{'timestamp': ts.timestamp(), 'value': val} for ts, val in zip(timestamps, oi_values)]
    
    # Assemble market data
    market_data = {
        'symbol': 'BTCUSDT',
        'ohlcv': {
            'base': ohlcv_df
        },
        'trades': trades,
        'orderbook': {
            'bids': [[price_trend[-1] - i*0.1, np.random.uniform(1, 10)] for i in range(10)],
            'asks': [[price_trend[-1] + i*0.1, np.random.uniform(1, 10)] for i in range(10)]
        },
        'sentiment': {
            'open_interest': {
                'current': oi_values[-1],
                'previous': oi_values[-2],
                'history': oi_history
            }
        }
    }
    
    return market_data, price_trend, cvd_values, oi_values

def plot_divergence(price, cvd, oi, title):
    """Plot price, CVD, and OI to visualize divergence"""
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    
    # Normalize values for better visualization
    price_norm = (price - np.min(price)) / (np.max(price) - np.min(price))
    cvd_norm = (cvd - np.min(cvd)) / (np.max(cvd) - np.min(cvd)) if np.max(cvd) > np.min(cvd) else cvd
    oi_norm = (oi - np.min(oi)) / (np.max(oi) - np.min(oi))
    
    # Plot price
    ax1.plot(price, 'b-', label='Price')
    ax1.set_title('Price')
    ax1.legend()
    ax1.grid(True)
    
    # Plot CVD
    ax2.plot(cvd, 'g-', label='CVD')
    ax2.set_title('Cumulative Volume Delta (CVD)')
    ax2.legend()
    ax2.grid(True)
    
    # Plot OI
    ax3.plot(oi, 'r-', label='Open Interest')
    ax3.set_title('Open Interest')
    ax3.legend()
    ax3.grid(True)
    
    plt.tight_layout()
    plt.suptitle(title, fontsize=16)
    plt.subplots_adjust(top=0.9)
    
    # Save the plot
    plt.savefig(f"{title.replace(' ', '_').lower()}.png")
    logger.info(f"Plot saved as {title.replace(' ', '_').lower()}.png")
    
    # Show the plot if in interactive mode
    if plt.isinteractive():
        plt.show()

def main():
    """Main test function"""
    # Load configuration
    try:
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        config = {}
    
    # Create logger
    log = Logger('test_orderflow_divergence')
    
    # Create OrderflowIndicators instance
    orderflow_indicators = OrderflowIndicators(config, log)
    
    # Test bullish divergence
    logger.info("\n=== Testing Bullish Divergence (Price Down, Indicators Up) ===")
    market_data_bullish, price_bullish, cvd_bullish, oi_bullish = create_sample_data(
        days=20, bullish_divergence=True
    )
    
    # Plot the data
    plot_divergence(price_bullish, cvd_bullish, oi_bullish, "Bullish Divergence Test Data")
    
    # Calculate price-CVD divergence
    cvd_divergence = orderflow_indicators._calculate_price_cvd_divergence(market_data_bullish)
    logger.info(f"Price-CVD Divergence: {cvd_divergence}")
    
    # Calculate price-OI divergence
    oi_divergence = orderflow_indicators._calculate_price_oi_divergence(market_data_bullish)
    logger.info(f"Price-OI Divergence: {oi_divergence}")
    
    # Test bearish divergence
    logger.info("\n=== Testing Bearish Divergence (Price Up, Indicators Down) ===")
    market_data_bearish, price_bearish, cvd_bearish, oi_bearish = create_sample_data(
        days=20, bullish_divergence=False
    )
    
    # Plot the data
    plot_divergence(price_bearish, cvd_bearish, oi_bearish, "Bearish Divergence Test Data")
    
    # Calculate price-CVD divergence
    cvd_divergence = orderflow_indicators._calculate_price_cvd_divergence(market_data_bearish)
    logger.info(f"Price-CVD Divergence: {cvd_divergence}")
    
    # Calculate price-OI divergence
    oi_divergence = orderflow_indicators._calculate_price_oi_divergence(market_data_bearish)
    logger.info(f"Price-OI Divergence: {oi_divergence}")
    
    # Test full calculation with divergence bonus
    logger.info("\n=== Testing Full Calculation with Divergence Bonus ===")
    result_bullish = orderflow_indicators.calculate(market_data_bullish)
    
    # Print divergences
    logger.info("Divergences in result:")
    for key, div_info in result_bullish.get('divergences', {}).items():
        logger.info(f"- {key}: {div_info}")
    
    # Print components to see if bonus was applied
    logger.info("Components with bonus applied:")
    for component, score in result_bullish.get('components', {}).items():
        logger.info(f"- {component}: {score}")
    
    logger.info("\n=== Test Complete ===")

if __name__ == "__main__":
    main() 