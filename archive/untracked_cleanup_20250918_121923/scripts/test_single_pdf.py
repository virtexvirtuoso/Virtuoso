#!/usr/bin/env python3
"""Quick test to generate a single PDF and inspect HTML."""

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

async def main():
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

    # Create test signal with interpretations
    from src.risk.risk_manager import OrderType
    entry_price = 50000
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
        'symbol': 'BTC/USDT',
        'signal_type': 'BUY',
        'price': entry_price,
        'confluence_score': 85.0,
        'reliability': 0.90,
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
            'orderflow': {
                'score': 88,
                'interpretation': 'Strong buying pressure detected'
            },
            'sentiment': {
                'score': 82,
                'interpretation': 'Bullish sentiment prevailing'
            },
            'liquidity': {
                'score': 85,
                'interpretation': 'Deep liquidity at support'
            },
            'bitcoin_beta': {
                'score': 90,
                'interpretation': 'Leading market movement'
            },
            'smart_money': {
                'score': 84,
                'interpretation': 'Accumulation phase detected'
            },
            'price_structure': {
                'score': 86,
                'interpretation': 'Bullish structure intact'
            }
        }
    }

    print("\nGenerating PDF with interpretations...")
    print("\nInterpretations included:")
    for comp, data in signal_data['analysis_components'].items():
        print(f"  • {comp}: {data['score']}% - {data['interpretation']}")

    # Generate simple OHLCV data
    dates = pd.date_range(end=datetime.now(), periods=50, freq='1h')
    prices = entry_price + np.random.randn(50) * 100

    ohlcv_data = pd.DataFrame({
        'timestamp': dates,
        'open': prices + np.random.randn(50) * 50,
        'high': prices + abs(np.random.randn(50) * 100),
        'low': prices - abs(np.random.randn(50) * 100),
        'close': prices,
        'volume': np.random.uniform(100000, 1000000, 50)
    })

    # Generate PDF
    pdf_path, json_path, png_path = pdf_generator.generate_trading_report(
        signal_data=signal_data,
        ohlcv_data=ohlcv_data,
        output_dir='reports/test'
    )

    print(f"\nFiles generated:")
    if pdf_path:
        print(f"  ✅ PDF: {Path(pdf_path).name}")
    if json_path:
        print(f"  ✅ JSON: {Path(json_path).name}")
    if png_path:
        print(f"  ✅ Chart: {Path(png_path).name}")

    # Check if HTML was also generated
    html_path = str(pdf_path).replace('/pdf/', '/html/').replace('.pdf', '.html')
    if Path(html_path).exists():
        print(f"  ✅ HTML: {Path(html_path).name}")

        # Read and check HTML content
        with open(html_path, 'r') as f:
            html_content = f.read()

        if 'Market Interpretations' in html_content:
            print("\n✅ SUCCESS: 'Market Interpretations' section found in HTML!")
        else:
            print("\n⚠️ WARNING: 'Market Interpretations' section NOT found in HTML")

        # Check for individual components
        components_found = []
        for comp in ['orderflow', 'sentiment', 'liquidity', 'bitcoin_beta', 'smart_money', 'price_structure']:
            if comp in html_content.lower() or comp.replace('_', ' ').title() in html_content:
                components_found.append(comp)

        if components_found:
            print(f"✅ Found {len(components_found)} components in HTML: {', '.join(components_found)}")
        else:
            print("⚠️ No component names found in HTML")

    print(f"\nOpen PDF to visually verify interpretations:")
    print(f"  open {pdf_path}")

if __name__ == "__main__":
    asyncio.run(main())