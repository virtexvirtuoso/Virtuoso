#!/usr/bin/env python3
"""
Test script for verifying the chart improvements in pdf_generator.py.
This script generates sample data and tests the charting methods directly.
"""

import os
import logging
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("chart_test")

# Import the ReportGenerator
from src.core.reporting.pdf_generator import ReportGenerator

def generate_test_ohlcv_data(periods=50, base_price=50000):
    """Generate sample OHLCV data for testing."""
    logger.info(f"Generating {periods} periods of test OHLCV data")
    
    dates = pd.date_range(end=datetime.now(), periods=periods)
    
    # Create a dataframe with timestamp, open, high, low, close, volume
    df = pd.DataFrame({
        'timestamp': dates,
        'open': [base_price * (1 + random.uniform(-0.02, 0.02)) for _ in range(periods)],
        'close': [base_price * (1 + random.uniform(-0.02, 0.02)) for _ in range(periods)]
    })
    
    # Add high and low values
    for i in range(periods):
        if df.loc[i, 'open'] > df.loc[i, 'close']:
            df.loc[i, 'high'] = df.loc[i, 'open'] * (1 + random.uniform(0, 0.01))
            df.loc[i, 'low'] = df.loc[i, 'close'] * (1 - random.uniform(0, 0.01))
        else:
            df.loc[i, 'high'] = df.loc[i, 'close'] * (1 + random.uniform(0, 0.01))
            df.loc[i, 'low'] = df.loc[i, 'open'] * (1 - random.uniform(0, 0.01))
    
    # Generate random volume
    df['volume'] = [random.uniform(100, 1000) for _ in range(periods)]
    
    # Create a price trend at the end (eg. a bull run)
    for i in range(periods-10, periods):
        df.loc[i, 'close'] = df.loc[i-1, 'close'] * (1 + random.uniform(0.001, 0.02))
        df.loc[i, 'open'] = df.loc[i-1, 'close'] * (1 + random.uniform(-0.005, 0.01))
        df.loc[i, 'high'] = max(df.loc[i, 'open'], df.loc[i, 'close']) * (1 + random.uniform(0.001, 0.01))
        df.loc[i, 'low'] = min(df.loc[i, 'open'], df.loc[i, 'close']) * (1 - random.uniform(0, 0.005))
        df.loc[i, 'volume'] = df.loc[i-1, 'volume'] * (1 + random.uniform(0, 0.2))
    
    return df

def generate_test_components():
    """Generate sample component data for testing."""
    logger.info("Generating test component data")
    
    return {
        'RSI': {'score': 82, 'impact': 3.2, 'interpretation': 'Overbought conditions indicating potential reversal'},
        'MACD': {'score': 71, 'impact': 2.5, 'interpretation': 'Bullish crossover suggesting upward momentum'},
        'Bollinger Bands': {'score': 68, 'impact': 1.8, 'interpretation': 'Price near upper band with expanding volatility'},
        'Volume': {'score': 65, 'impact': 1.5, 'interpretation': 'Above average volume supporting the move'},
        'Moving Averages': {'score': 80, 'impact': 3.0, 'interpretation': 'Price above all major MAs in a bullish alignment'},
        'Support/Resistance': {'score': 60, 'impact': 1.2, 'interpretation': 'Trading above recent resistance turned support'},
        'Ichimoku Cloud': {'score': 72, 'impact': 2.0, 'interpretation': 'Price above the cloud in a bullish trend'}
    }

def generate_confluence_text():
    """Generate sample confluence analysis text for testing."""
    logger.info("Generating test confluence text")
    
    return """
CONFLUENCE ANALYSIS: BULLISH SIGNAL

Technical Indicators:
✅ RSI: Value 68.5 - Bullish but approaching overbought territory
✅ MACD: Bullish crossover with increasing histogram values
✅ Bollinger Bands: Price testing upper band with expanding bands
✅ Moving Averages: Trading above 8, 20, 50, and 200 EMA

Volume Analysis:
✅ Volume increasing on up days
✅ OBV showing steady accumulation
✅ No divergence between price and volume

Price Structure:
✅ Higher highs and higher lows forming
✅ Recently broke a key resistance level
✅ Current price action respecting newly formed support
✅ No significant overhead resistance until 57000

Market Context:
✅ Sector strength
✅ Positive correlation with market leaders
✅ Overall risk-on market environment

Confluence Summary:
Strong bullish bias with multiple confirming factors across
different indicator categories. Near-term momentum is likely
to continue with support holding at current levels.
"""

def test_candlestick_chart(generator, output_dir):
    """Test the candlestick chart implementation."""
    logger.info("Testing candlestick chart generation")
    
    # Generate test data
    ohlcv_data = generate_test_ohlcv_data()
    
    # Create trade parameters for visualization
    symbol = "BTCUSDT"
    entry_price = ohlcv_data['close'].iloc[-1]
    stop_loss = entry_price * 0.95  # 5% below entry
    
    targets = [
        {'name': 'Target 1', 'price': entry_price * 1.05},  # 5% profit
        {'name': 'Target 2', 'price': entry_price * 1.10},  # 10% profit
        {'name': 'Target 3', 'price': entry_price * 1.20}   # 20% profit
    ]
    
    # Generate the chart
    result = generator._create_candlestick_chart(
        symbol=symbol,
        ohlcv_data=ohlcv_data,
        entry_price=entry_price,
        stop_loss=stop_loss,
        targets=targets,
        output_dir=output_dir
    )
    
    if result:
        logger.info(f"✅ Candlestick chart created successfully: {result}")
    else:
        logger.error("❌ Candlestick chart creation failed!")
    
    return result

def test_component_chart(generator, output_dir):
    """Test the component chart implementation."""
    logger.info("Testing component chart generation")
    
    # Generate test data
    components = generate_test_components()
    
    # Generate the chart
    result = generator._create_component_chart(
        components=components,
        output_dir=output_dir
    )
    
    if result:
        logger.info(f"✅ Component chart created successfully: {result}")
    else:
        logger.error("❌ Component chart creation failed!")
    
    return result

def test_confluence_image(generator, output_dir):
    """Test the confluence image implementation."""
    logger.info("Testing confluence image generation")
    
    # Generate test data
    confluence_text = generate_confluence_text()
    
    # Generate the chart
    result = generator._create_confluence_image(
        confluence_text=confluence_text,
        output_dir=output_dir,
        symbol="BTCUSDT",
        timestamp=datetime.now(),
        signal_type="BULLISH"
    )
    
    if result:
        logger.info(f"✅ Confluence image created successfully: {result}")
    else:
        logger.error("❌ Confluence image creation failed!")
    
    return result

def test_simulated_chart(generator, output_dir):
    """Test the simulated chart implementation."""
    logger.info("Testing simulated chart generation")
    
    # Create trade parameters for visualization
    symbol = "ETHUSDT"
    entry_price = 2500
    stop_loss = entry_price * 0.95  # 5% below entry
    
    targets = [
        {'name': 'Target 1', 'price': entry_price * 1.05},  # 5% profit
        {'name': 'Target 2', 'price': entry_price * 1.10}   # 10% profit
    ]
    
    # Generate the chart
    result = generator._create_simulated_chart(
        symbol=symbol,
        entry_price=entry_price,
        stop_loss=stop_loss,
        targets=targets,
        output_dir=output_dir
    )
    
    if result:
        logger.info(f"✅ Simulated chart created successfully: {result}")
    else:
        logger.error("❌ Simulated chart creation failed!")
    
    return result

def main():
    """Main test function."""
    logger.info("Starting chart improvement tests")
    
    # Create output directory for test charts
    output_dir = "test_charts_output"
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Test charts will be saved to: {os.path.abspath(output_dir)}")
    
    # Initialize ReportGenerator
    generator = ReportGenerator()
    
    # Run tests
    candlestick_result = test_candlestick_chart(generator, output_dir)
    component_result = test_component_chart(generator, output_dir)
    confluence_result = test_confluence_image(generator, output_dir)
    simulated_result = test_simulated_chart(generator, output_dir)
    
    # Check overall results
    all_tests = [
        ("Candlestick chart", candlestick_result), 
        ("Component chart", component_result),
        ("Confluence image", confluence_result),
        ("Simulated chart", simulated_result)
    ]
    
    print("\n--- TEST RESULTS SUMMARY ---")
    all_passed = True
    for test_name, result in all_tests:
        status = "✅ PASSED" if result else "❌ FAILED"
        if not result:
            all_passed = False
        print(f"{test_name}: {status}")
    
    print("\nOverall test result:", "✅ PASSED" if all_passed else "❌ FAILED")
    print(f"Output files are in: {os.path.abspath(output_dir)}")
    
    return all_passed

if __name__ == "__main__":
    main() 