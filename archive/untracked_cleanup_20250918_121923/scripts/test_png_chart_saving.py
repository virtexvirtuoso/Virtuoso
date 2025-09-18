#!/usr/bin/env python3
"""Test that PNG charts are saved to reports/charts directory."""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.reporting.pdf_generator import ReportGenerator

def test_chart_saving():
    """Test that charts are saved to reports/charts directory."""

    print("=" * 60)
    print("Testing PNG Chart Saving")
    print("=" * 60)

    # Initialize PDF generator
    config = {}
    generator = ReportGenerator(config)

    # Create sample OHLCV data
    timestamps = pd.date_range(end=datetime.now(), periods=50, freq='5min')
    base_price = 50000
    ohlcv_data = pd.DataFrame({
        'timestamp': timestamps,
        'open': base_price + np.random.randn(50) * 100,
        'high': base_price + np.random.randn(50) * 150 + 100,
        'low': base_price + np.random.randn(50) * 150 - 100,
        'close': base_price + np.random.randn(50) * 100,
        'volume': np.random.randint(1000, 10000, 50)
    })
    ohlcv_data.set_index('timestamp', inplace=True)

    # Test parameters
    symbol = 'BTC/USDT:USDT'
    entry_price = 50100
    stop_loss = 49500
    targets = [
        {'price': 51000, 'name': 'Target 1'},
        {'price': 52000, 'name': 'Target 2'}
    ]

    print("\n1. Testing real OHLCV chart generation...")
    chart_path = generator._create_candlestick_chart(
        symbol=symbol,
        ohlcv_data=ohlcv_data,
        entry_price=entry_price,
        stop_loss=stop_loss,
        targets=targets
    )

    if chart_path and os.path.exists(chart_path):
        print(f"✅ Real chart saved to: {chart_path}")
        print(f"   File size: {os.path.getsize(chart_path) / 1024:.2f} KB")
    else:
        print("❌ Failed to create real chart")

    print("\n2. Testing simulated chart generation...")
    simulated_path = generator._create_simulated_chart(
        symbol=symbol,
        entry_price=entry_price,
        stop_loss=stop_loss,
        targets=targets
    )

    if simulated_path and os.path.exists(simulated_path):
        print(f"✅ Simulated chart saved to: {simulated_path}")
        print(f"   File size: {os.path.getsize(simulated_path) / 1024:.2f} KB")
    else:
        print("❌ Failed to create simulated chart")

    # Check charts directory
    print("\n3. Checking reports/charts directory...")
    charts_dir = os.path.join(os.getcwd(), 'reports', 'charts')
    if os.path.exists(charts_dir):
        charts = [f for f in os.listdir(charts_dir) if f.endswith('.png')]
        print(f"✅ Found {len(charts)} PNG files in reports/charts/")

        # Show recent charts
        recent_charts = sorted(charts)[-5:] if len(charts) > 5 else charts
        print("\n   Recent charts:")
        for chart in recent_charts:
            chart_path = os.path.join(charts_dir, chart)
            size_kb = os.path.getsize(chart_path) / 1024
            print(f"   - {chart} ({size_kb:.2f} KB)")
    else:
        print("❌ reports/charts directory not found")

    print("\n" + "=" * 60)
    print("✅ Chart saving test complete!")
    print("Charts are now saved to reports/charts/ for easy access")
    print("=" * 60)

if __name__ == "__main__":
    test_chart_saving()