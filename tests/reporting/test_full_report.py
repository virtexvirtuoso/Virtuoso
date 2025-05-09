#!/usr/bin/env python3
"""
Test script for generating a complete PDF report with the improved charts.
"""

import os
import logging
import random
import pandas as pd
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("report_test")

# Import test utils from our test_chart_improvements.py
from test_chart_improvements import generate_test_ohlcv_data, generate_test_components, generate_confluence_text

# Import the ReportGenerator
from src.core.reporting.pdf_generator import ReportGenerator

def main():
    """Generate a complete trading report PDF with our improved charts."""
    logger.info("Starting full report generation test")
    
    # Create output directory
    output_dir = "test_report_output"
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Report will be saved to: {os.path.abspath(output_dir)}")
    
    # Initialize ReportGenerator
    generator = ReportGenerator()
    
    # Generate sample OHLCV data
    ohlcv_data = generate_test_ohlcv_data(periods=100, base_price=45000)
    
    # Get the latest price
    current_price = ohlcv_data['close'].iloc[-1]
    
    # Prepare signal data
    signal_data = {
        'symbol': 'BTCUSDT',
        'score': 75.5,
        'reliability': 0.85,
        'price': current_price,
        'timestamp': datetime.now(),
        'signal_type': 'BULLISH',
        'components': generate_test_components(),
        'insights': [
            'Strong bullish momentum supported by multiple indicators',
            'Recent breakout above key resistance level at $42,000',
            'Increased institutional buying detected in on-chain data',
            'Reduced selling pressure from miners over the past week'
        ],
        'actionable_insights': [
            'Consider entering long positions with tight stop losses',
            f'Target the previous high at ${current_price * 1.10:.2f} for first take profit',
            'Monitor volume for confirmation of continued uptrend',
            f'Watch for potential resistance at ${current_price * 1.05:.2f} psychological level'
        ],
        'confluence_analysis': generate_confluence_text(),
        'trade_params': {
            'entry_price': current_price,
            'stop_loss': current_price * 0.95,  # 5% below current price
            'targets': [
                {'name': 'Target 1', 'price': current_price * 1.05, 'size': 50},  # 5% profit
                {'name': 'Target 2', 'price': current_price * 1.10, 'size': 30},  # 10% profit
                {'name': 'Target 3', 'price': current_price * 1.15, 'size': 20}   # 15% profit
            ]
        }
    }
    
    # Generate report
    logger.info("Generating PDF report...")
    pdf_path, json_path = generator.generate_trading_report(
        signal_data=signal_data,
        ohlcv_data=ohlcv_data,
        output_dir=output_dir
    )
    
    # Check results
    if pdf_path and os.path.exists(pdf_path):
        logger.info(f"✅ PDF report generated successfully: {pdf_path}")
    else:
        logger.error("❌ PDF report generation failed!")
    
    if json_path and os.path.exists(json_path):
        logger.info(f"✅ JSON data exported successfully: {json_path}")
    
    return pdf_path, json_path

if __name__ == "__main__":
    main() 