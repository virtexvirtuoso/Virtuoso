#!/usr/bin/env python3
"""
Test script to verify chart display fixes:
1. Daily VWAP visibility (now green instead of blue)
2. Volume panel display
3. Date formatting consistency
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.reporting.pdf_generator import ReportGenerator

def create_test_data():
    """Create test OHLCV data with proper volume."""
    # Create 48 hours of 5-minute data (576 candles)
    start_time = datetime.now() - timedelta(hours=48)
    timestamps = pd.date_range(start=start_time, periods=576, freq='5T')
    
    # Generate realistic price data
    np.random.seed(42)
    base_price = 0.196  # DOGEUSDT price from example
    
    # Create random walk for prices
    price_changes = np.random.normal(0, 0.001, 576)  # 0.1% volatility
    prices = [base_price]
    
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(max(0.001, new_price))  # Ensure positive prices
    
    # Create OHLCV data
    data = []
    for i, timestamp in enumerate(timestamps):
        price = prices[i]
        high = price * (1 + abs(np.random.normal(0, 0.002)))
        low = price * (1 - abs(np.random.normal(0, 0.002)))
        open_price = prices[i-1] if i > 0 else price
        close_price = price
        volume = np.random.gamma(2, 1000)  # Realistic volume distribution
        
        data.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    
    return df

def test_chart_generation():
    """Test chart generation with the fixes."""
    print("🧪 Testing chart display fixes...")
    
    # Setup logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Create test data
    print("📊 Creating test OHLCV data...")
    ohlcv_data = create_test_data()
    
    print(f"✅ Generated {len(ohlcv_data)} candles")
    print(f"📈 Price range: ${ohlcv_data['low'].min():.4f} - ${ohlcv_data['high'].max():.4f}")
    print(f"📊 Volume range: {ohlcv_data['volume'].min():.0f} - {ohlcv_data['volume'].max():.0f}")
    
    # Create report generator
    report_gen = ReportGenerator()
    
    # Test signal data
    signal_data = {
        'symbol': 'DOGEUSDT',
        'signal_type': 'BUY',
        'price': 0.196,
        'score': 72.6,
        'reliability': 100.0,
        'trade_params': {
            'entry_price': 0.196,
            'stop_loss': 0.190,
            'targets': [
                {'price': 0.205, 'percentage': 25},
                {'price': 0.215, 'percentage': 50}
            ]
        }
    }
    
    # Test chart generation
    print("\n🎨 Testing chart generation...")
    try:
        chart_path = report_gen._create_candlestick_chart(
            symbol='DOGEUSDT',
            ohlcv_data=ohlcv_data,
            entry_price=0.196,
            stop_loss=0.190,
            targets=signal_data['trade_params']['targets'],
            output_dir='./test_output'
        )
        
        if chart_path:
            print(f"✅ Chart generated successfully: {chart_path}")
            print("\n🔍 Expected improvements:")
            print("  • Daily VWAP should now be BLUE")
            print("  • Weekly VWAP should be PURPLE")
            print("  • Entry price should be GREEN")
            print("  • Volume panel should appear below price chart")
            print("  • Date formatting should be consistent")
            
            # Check if file exists
            if os.path.exists(chart_path):
                file_size = os.path.getsize(chart_path)
                print(f"  • Chart file size: {file_size:,} bytes")
            else:
                print("  ❌ Chart file not found")
                
        else:
            print("❌ Chart generation failed")
            
    except Exception as e:
        print(f"❌ Error during chart generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chart_generation() 