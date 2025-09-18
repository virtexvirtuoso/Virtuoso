#!/usr/bin/env python3
"""Final comprehensive test of all fixes."""

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

async def final_test():
    """Run final comprehensive test."""
    
    print("="*60)
    print("FINAL COMPREHENSIVE TEST")
    print("="*60)
    
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
    
    # Test comprehensive signal
    print("\n1. Creating test signal with all parameters...")
    
    # Calculate trade params
    from src.risk.risk_manager import OrderType
    entry_price = 1850.50
    order_type = OrderType.BUY
    sl_tp = risk_manager.calculate_stop_loss_take_profit(
        entry_price=entry_price,
        order_type=order_type
    )
    
    position_info = risk_manager.calculate_position_size(
        account_balance=10000,
        entry_price=entry_price,
        stop_loss_price=sl_tp['stop_loss_price']
    )
    
    signal_data = {
        'symbol': 'ETH/USDT',
        'signal_type': 'BUY',
        'price': entry_price,
        'confluence_score': 78.3,
        'reliability': 0.92,  # 92% reliability
        'timestamp': datetime.now().isoformat(),
        'trade_params': {
            'entry_price': entry_price,
            'stop_loss': sl_tp['stop_loss_price'],
            'take_profit': sl_tp['take_profit_price'],
            'position_size': position_info['position_size_units'],
            'risk_reward_ratio': sl_tp['risk_reward_ratio'],
            'risk_percentage': position_info['risk_percentage']
        },
        'analysis_components': {
            'orderflow': {'score': 85, 'interpretation': 'Strong buying pressure'},
            'sentiment': {'score': 78, 'interpretation': 'Bullish market sentiment'},
            'liquidity': {'score': 72, 'interpretation': 'Good liquidity levels'},
            'bitcoin_beta': {'score': 80, 'interpretation': 'Positive BTC correlation'},
            'smart_money': {'score': 75, 'interpretation': 'Institutional accumulation'},
            'price_structure': {'score': 82, 'interpretation': 'Uptrend structure intact'}
        }
    }
    
    print(f"   Symbol: {signal_data['symbol']}")
    print(f"   Signal: {signal_data['signal_type']}")
    print(f"   Entry: ${entry_price:.2f}")
    print(f"   Reliability: {signal_data['reliability']*100:.0f}% (should display as 92%)")
    print(f"   Stop Loss: ${signal_data['trade_params']['stop_loss']:.2f}")
    print(f"   Take Profit: ${signal_data['trade_params']['take_profit']:.2f}")
    
    # Generate OHLCV data
    print("\n2. Generating OHLCV data with volume...")
    dates = pd.date_range(end=datetime.now(), periods=100, freq='1h')
    base_price = entry_price
    prices = base_price + np.cumsum(np.random.randn(100) * 10)
    
    ohlcv_data = pd.DataFrame({
        'timestamp': dates,
        'open': prices + np.random.randn(100) * 2,
        'high': prices + abs(np.random.randn(100) * 5),
        'low': prices - abs(np.random.randn(100) * 5),
        'close': prices,
        'volume': np.random.uniform(5000, 50000, 100)
    })
    
    # Generate PDF
    print("\n3. Generating PDF report...")
    pdf_path, json_path, png_path = pdf_generator.generate_trading_report(
        signal_data=signal_data,
        ohlcv_data=ohlcv_data,
        output_dir='reports/test'
    )
    
    if pdf_path:
        print(f"   ✅ PDF: {Path(pdf_path).name}")
    else:
        print(f"   ❌ PDF generation failed")
        
    if png_path:
        print(f"   ✅ Chart: {Path(png_path).name}")
    else:
        print(f"   ❌ Chart generation failed")
        
    if json_path:
        print(f"   ✅ JSON: {Path(json_path).name}")
    else:
        print(f"   ❌ JSON export failed")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print("\nPlease verify:")
    print("1. Reliability displays as 92% (not 0.92% or 9200%)")
    print("2. Volume panel is 1/3 height of price panel")
    print("3. Stop loss (red) and take profit (green) lines are visible")
    print("4. All trade parameters are included in the PDF")
    print("\nFiles generated in: reports/test/")

if __name__ == "__main__":
    asyncio.run(final_test())
