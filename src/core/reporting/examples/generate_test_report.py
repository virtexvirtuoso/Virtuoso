#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for generating a trading report with confluence visualization.

This script creates sample data and uses the ReportGenerator to generate
a PDF trading report with the 6-dimensional confluence model visualization.
"""

import os
import sys
import logging
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add the project root directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
sys.path.insert(0, project_root)

from src.core.reporting.pdf_generator import ReportGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def create_sample_ohlcv_data():
    """Create sample OHLCV data for the report."""
    # Create sample dates
    num_days = 30
    end_date = pd.Timestamp.now()
    dates = pd.date_range(end=end_date, periods=num_days)
    
    # Generate some pseudo-random price data
    np.random.seed(42)  # For reproducibility
    
    # Start with a base price
    base_price = 50000.0
    
    # Create a trend
    trend = np.linspace(0, 0.2, num_days)  # Upward trend
    
    # Add some random noise
    noise = np.random.normal(0, 0.01, num_days)
    
    # Generate close prices
    close_prices = base_price * (1 + trend + noise)
    
    # Generate other OHLCV data
    daily_volatility = 0.02
    opens = close_prices * (1 + np.random.normal(0, daily_volatility, num_days))
    highs = np.maximum(close_prices, opens) * (1 + np.abs(np.random.normal(0, daily_volatility, num_days)))
    lows = np.minimum(close_prices, opens) * (1 - np.abs(np.random.normal(0, daily_volatility, num_days)))
    volumes = np.random.normal(1000000, 200000, num_days)
    
    # Create DataFrame
    df = pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': close_prices,
        'volume': volumes
    })
    
    # Set timestamp as index
    df.set_index('timestamp', inplace=True)
    
    return df

def create_sample_signal_data():
    """Create sample signal data for the report."""
    # Component scores - using a neutral-bullish scenario
    component_scores = {
        'technical': {
            'score': 44.74,
            'impact': 1.2,
            'subcomponents': {
                'rsi': {'value': 51.00, 'score': 51.00, 'impact': 1.0},
                'ao': {'value': -0.01, 'score': 49.92, 'impact': 1.0},
                'atr': {'value': 1650.32, 'score': 50.08, 'impact': 1.1},
                'macd': {'value': -2.12, 'score': 49.97, 'impact': 1.2},
                'cci': {'value': -98.56, 'score': 34.00, 'impact': 1.3},
                'williams_r': {'value': -72.45, 'score': 33.44, 'impact': 1.4}
            }
        },
        'volume': {
            'score': 43.15,
            'impact': 1.1,
            'subcomponents': {
                'cmf': {'value': 0.15, 'score': 100.00, 'impact': 1.0},
                'relative_volume': {'value': 1.03, 'score': 51.91, 'impact': 1.0},
                'obv': {'value': -125000, 'score': 38.80, 'impact': 1.2},
                'adl': {'value': -56700, 'score': 25.10, 'impact': 1.1},
                'volume_delta': {'value': -45600, 'score': 19.97, 'impact': 1.3}
            }
        },
        'orderbook': {
            'score': 60.08,
            'impact': 1.3,
            'subcomponents': {
                'spread': {'value': 0.01, 'score': 99.97, 'impact': 1.1},
                'liquidity': {'value': 5600000, 'score': 99.63, 'impact': 1.4},
                'depth': {'value': 12500000, 'score': 92.68, 'impact': 1.3},
                'market_pressure': {'value': -0.13, 'score': 43.47, 'impact': 1.2},
                'imbalance': {'value': -0.38, 'score': 30.76, 'impact': 1.0}
            }
        },
        'orderflow': {
            'score': 73.08,
            'impact': 1.4,
            'subcomponents': {
                'cvd': {'value': 845670, 'score': 90.88, 'impact': 1.5},
                'trade_flow': {'value': 0.38, 'score': 69.15, 'impact': 1.3},
                'imbalance_score': {'value': 0.42, 'score': 71.10, 'impact': 1.2},
                'open_interest': {'value': 0.41, 'score': 70.41, 'impact': 1.1},
                'liquidity_score': {'value': 0.07, 'score': 53.33, 'impact': 1.0}
            }
        },
        'sentiment': {
            'score': 62.10,
            'impact': 1.0,
            'subcomponents': {
                'market_activity': {'value': 0.93, 'score': 96.68, 'impact': 1.0},
                'risk': {'value': 0.45, 'score': 72.44, 'impact': 0.9},
                'long_short_ratio': {'value': 0.60, 'score': 59.93, 'impact': 1.1},
                'funding_rate': {'value': 0.0001, 'score': 55.07, 'impact': 1.2},
                'volatility': {'value': 0.035, 'score': 43.10, 'impact': 0.8}
            }
        },
        'price_structure': {
            'score': 46.82,
            'impact': 1.2,
            'subcomponents': {
                'vwap': {'value': 50345.67, 'score': 54.08, 'impact': 1.3},
                'composite_value': {'value': 0.07, 'score': 47.99, 'impact': 1.2},
                'swing_structure': {'value': -0.06, 'score': 47.00, 'impact': 1.1},
                'volume_profile': {'value': -0.07, 'score': 46.41, 'impact': 1.0},
                'order_blocks': {'value': -0.13, 'score': 43.52, 'impact': 1.4}
            }
        }
    }
    
    # Overall score (weighted average of component scores)
    overall_score = 56.87
    
    # Create the signal data
    current_price = 51245.67
    
    signal_data = {
        'symbol': 'BTCUSDT',
        'exchange': 'Bybit',
        'signal_type': 'LONG',
        'score': overall_score,
        'price': current_price,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'reliability': 0.87,
        'components': component_scores,
        'risk_level': 'MEDIUM',
        'timeframe': '1h',
        'trade_params': {
            'entry_price': current_price,
            'stop_loss': current_price * 0.95,  # 5% below entry price
            'targets': [
                {'price': current_price * 1.03, 'percentage': 30},  # Target 1: 3% above entry
                {'price': current_price * 1.08, 'percentage': 40},  # Target 2: 8% above entry
                {'price': current_price * 1.15, 'percentage': 30}   # Target 3: 15% above entry
            ]
        },
        'confluence_analysis': """
        BTC is showing signs of reversal from the recent downtrend. 
        The orderflow metrics are strongly bullish with large buyers stepping in and absorbing sell pressure.
        Volume profile indicates accumulation, though there's still some bearish structure that needs to resolve.
        RSI is neutral while the MACD is showing early signs of bullish crossover.
        Sentiment is improving with funding rates normalizing and long/short ratio becoming more balanced.
        Overall, this presents a moderate-confidence long opportunity with defined risk parameters.
        """
    }
    
    return signal_data

def main():
    """Generate a test trading report with confluence visualization."""
    # Create sample data
    logger.info("Creating sample data for test report...")
    ohlcv_data = create_sample_ohlcv_data()
    signal_data = create_sample_signal_data()
    
    # Define output directory
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize report generator
    logger.info("Initializing report generator...")
    report_generator = ReportGenerator()
    
    # Generate trading report
    logger.info("Generating trading report with confluence visualization...")
    pdf_path, json_path = report_generator.generate_trading_report(
        signal_data=signal_data,
        ohlcv_data=ohlcv_data,
        output_dir=output_dir
    )
    
    if pdf_path:
        logger.info(f"Trading report successfully generated: {pdf_path}")
        
        # Try to open the PDF report
        try:
            import webbrowser
            webbrowser.open(f"file://{os.path.abspath(pdf_path)}")
            logger.info("Report opened in browser.")
        except Exception as e:
            logger.error(f"Could not open report: {str(e)}")
    else:
        logger.error("Failed to generate trading report.")
    
    return pdf_path, json_path

if __name__ == "__main__":
    logger.info("Starting test report generation...")
    main()
    logger.info("Test completed.") 