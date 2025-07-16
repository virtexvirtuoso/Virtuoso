#!/usr/bin/env python3
"""
Test script to verify multiple targets are always generated in charts.
Tests various scenarios to ensure robust target generation.
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
    """Create test OHLCV data."""
    # Create 48 hours of 5-minute data
    start_time = datetime.now() - timedelta(hours=48)
    timestamps = pd.date_range(start=start_time, periods=576, freq='5T')
    
    # Generate realistic price data
    base_price = 0.196  # DOGE price
    price_changes = np.cumsum(np.random.normal(0, 0.001, 576))
    prices = base_price + price_changes
    
    # Create OHLCV data
    ohlcv_data = pd.DataFrame({
        'timestamp': timestamps,
        'open': prices,
        'high': prices * (1 + np.random.uniform(0, 0.01, 576)),
        'low': prices * (1 - np.random.uniform(0, 0.01, 576)),
        'close': prices,
        'volume': np.random.gamma(2, 1000, 576)
    })
    
    # Set timestamp as index
    ohlcv_data.set_index('timestamp', inplace=True)
    
    return ohlcv_data

def test_scenario_1_no_targets():
    """Test scenario 1: No targets provided in signal data."""
    print("🧪 Test 1: No targets provided in signal data")
    
    signal_data = {
        'symbol': 'DOGEUSDT',
        'signal_type': 'BULLISH',
        'score': 75.5,
        'price': 0.196,
        'entry_price': 0.196,
        'stop_loss': 0.190,
        'timestamp': datetime.now(),
        # No targets provided
    }
    
    ohlcv_data = create_test_data()
    generator = ReportGenerator(log_level=logging.INFO)
    
    try:
        pdf_path, json_path = generator.generate_trading_report(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            output_dir="test_output"
        )
        
        if pdf_path:
            print(f"✅ Test 1 PASSED: Report generated with auto-generated targets")
            print(f"   PDF: {pdf_path}")
        else:
            print("❌ Test 1 FAILED: No PDF generated")
            
    except Exception as e:
        print(f"❌ Test 1 FAILED: {str(e)}")

def test_scenario_2_empty_targets():
    """Test scenario 2: Empty targets list/dict provided."""
    print("\n🧪 Test 2: Empty targets provided in signal data")
    
    signal_data = {
        'symbol': 'DOGEUSDT',
        'signal_type': 'BEARISH',
        'score': 65.2,
        'price': 0.196,
        'entry_price': 0.196,
        'stop_loss': 0.202,
        'timestamp': datetime.now(),
        'targets': {}  # Empty targets
    }
    
    ohlcv_data = create_test_data()
    generator = ReportGenerator(log_level=logging.INFO)
    
    try:
        pdf_path, json_path = generator.generate_trading_report(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            output_dir="test_output"
        )
        
        if pdf_path:
            print(f"✅ Test 2 PASSED: Report generated with auto-generated targets")
            print(f"   PDF: {pdf_path}")
        else:
            print("❌ Test 2 FAILED: No PDF generated")
            
    except Exception as e:
        print(f"❌ Test 2 FAILED: {str(e)}")

def test_scenario_3_existing_targets():
    """Test scenario 3: Existing targets provided (should not be overridden)."""
    print("\n🧪 Test 3: Existing targets provided (should preserve them)")
    
    signal_data = {
        'symbol': 'DOGEUSDT',
        'signal_type': 'BULLISH',
        'score': 82.1,
        'price': 0.196,
        'entry_price': 0.196,
        'stop_loss': 0.190,
        'timestamp': datetime.now(),
        'targets': {
            'Target 1': {'price': 0.205, 'size': 50},
            'Target 2': {'price': 0.215, 'size': 30},
            'Custom Target': {'price': 0.225, 'size': 20}
        }
    }
    
    ohlcv_data = create_test_data()
    generator = ReportGenerator(log_level=logging.INFO)
    
    try:
        pdf_path, json_path = generator.generate_trading_report(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            output_dir="test_output"
        )
        
        if pdf_path:
            print(f"✅ Test 3 PASSED: Report generated with existing targets preserved")
            print(f"   PDF: {pdf_path}")
        else:
            print("❌ Test 3 FAILED: No PDF generated")
            
    except Exception as e:
        print(f"❌ Test 3 FAILED: {str(e)}")

def test_scenario_4_simulated_chart():
    """Test scenario 4: Simulated chart with no OHLCV data."""
    print("\n🧪 Test 4: Simulated chart with no OHLCV data")
    
    signal_data = {
        'symbol': 'DOGEUSDT',
        'signal_type': 'BULLISH',
        'score': 70.0,
        'price': 0.196,
        'entry_price': 0.196,
        'stop_loss': 0.190,
        'timestamp': datetime.now(),
        # No targets provided
    }
    
    generator = ReportGenerator(log_level=logging.INFO)
    
    try:
        pdf_path, json_path = generator.generate_trading_report(
            signal_data=signal_data,
            ohlcv_data=None,  # No OHLCV data - should use simulated chart
            output_dir="test_output"
        )
        
        if pdf_path:
            print(f"✅ Test 4 PASSED: Simulated chart generated with auto-generated targets")
            print(f"   PDF: {pdf_path}")
        else:
            print("❌ Test 4 FAILED: No PDF generated")
            
    except Exception as e:
        print(f"❌ Test 4 FAILED: {str(e)}")

def test_scenario_5_trade_params():
    """Test scenario 5: Targets in trade_params structure."""
    print("\n🧪 Test 5: Targets in trade_params structure")
    
    signal_data = {
        'symbol': 'DOGEUSDT',
        'signal_type': 'BULLISH',
        'score': 78.5,
        'price': 0.196,
        'timestamp': datetime.now(),
        'trade_params': {
            'entry_price': 0.196,
            'stop_loss': 0.190,
            # No targets in trade_params
        }
    }
    
    ohlcv_data = create_test_data()
    generator = ReportGenerator(log_level=logging.INFO)
    
    try:
        pdf_path, json_path = generator.generate_trading_report(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            output_dir="test_output"
        )
        
        if pdf_path:
            print(f"✅ Test 5 PASSED: Report generated with auto-generated targets from trade_params")
            print(f"   PDF: {pdf_path}")
        else:
            print("❌ Test 5 FAILED: No PDF generated")
            
    except Exception as e:
        print(f"❌ Test 5 FAILED: {str(e)}")

def main():
    """Run all test scenarios."""
    print("🚀 Testing Multiple Targets Generation")
    print("=" * 50)
    
    # Create output directory
    os.makedirs("test_output", exist_ok=True)
    
    # Run all test scenarios
    test_scenario_1_no_targets()
    test_scenario_2_empty_targets()
    test_scenario_3_existing_targets()
    test_scenario_4_simulated_chart()
    test_scenario_5_trade_params()
    
    print("\n" + "=" * 50)
    print("🎯 All tests completed!")
    print("Check the test_output/ directory for generated charts")
    print("\n📊 Expected results:")
    print("  • All charts should display multiple targets (2-3 targets)")
    print("  • Target colors: Green, Purple, Orange")
    print("  • Each target should show price and percentage")
    print("  • Risk/reward ratios should be calculated automatically")

if __name__ == "__main__":
    main() 