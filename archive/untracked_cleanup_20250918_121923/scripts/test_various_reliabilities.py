#!/usr/bin/env python3
"""Test PDF generation with various reliability values."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.reporting.pdf_generator import ReportGenerator
from src.risk.risk_manager import RiskManager

async def test_reliability_values():
    """Test different reliability values."""
    
    config = {
        'risk': {
            'default_risk_percentage': 2.0,
            'risk_reward_ratio': 2.0,
            'long_stop_percentage': 3.5,
            'short_stop_percentage': 3.5
        },
        'trading': {
            'account_balance': 10000
        },
        'reporting': {
            'output_dir': 'reports/test'
        }
    }
    
    pdf_generator = ReportGenerator(config)
    risk_manager = RiskManager(config)
    
    # Test different reliability values
    test_cases = [
        (0.5, "50%"),
        (0.75, "75%"),
        (0.95, "95%"),
        (1.0, "100%"),
    ]
    
    for decimal_val, expected in test_cases:
        print(f"\nTesting reliability: {decimal_val} (should display as {expected})")
        
        # Create test signal
        signal_data = {
            'symbol': 'BTC/USDT',
            'signal_type': 'BUY',
            'price': 50000,
            'confluence_score': 72.5,
            'reliability': decimal_val,  # Test value
            'timestamp': datetime.now().isoformat(),
            'trade_params': {
                'entry_price': 50000,
                'stop_loss': 48250,
                'take_profit': 53500,
                'position_size': 0.2,
                'risk_reward_ratio': 2.0,
                'risk_percentage': 2.0
            },
            'analysis_components': {
                'orderflow': {'score': 80, 'interpretation': 'Strong buying'},
                'sentiment': {'score': 70, 'interpretation': 'Bullish'},
                'liquidity': {'score': 75, 'interpretation': 'Good liquidity'},
                'bitcoin_beta': {'score': 65, 'interpretation': 'Positive'},
                'smart_money': {'score': 72, 'interpretation': 'Accumulation'},
                'price_structure': {'score': 73, 'interpretation': 'Uptrend'}
            }
        }
        
        # Generate simple OHLCV data
        dates = pd.date_range(end=datetime.now(), periods=50, freq='1h')
        prices = np.random.normal(50000, 500, 50)
        ohlcv_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.normal(0, 100, 50),
            'high': prices + abs(np.random.normal(200, 100, 50)),
            'low': prices - abs(np.random.normal(200, 100, 50)),
            'close': prices,
            'volume': np.random.uniform(100, 1000, 50)
        })
        
        # Generate PDF
        pdf_path, json_path, png_path = pdf_generator.generate_trading_report(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            output_dir='reports/test'
        )
        
        if pdf_path:
            print(f"✅ PDF generated: {Path(pdf_path).name}")
            print(f"   Should show reliability as: {expected}")
        else:
            print(f"❌ Failed to generate PDF")

if __name__ == "__main__":
    asyncio.run(test_reliability_values())
