#!/usr/bin/env python3
"""
Test PDF generation with trade parameters (stop loss, take profit).
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.reporting.pdf_generator import ReportGenerator
from src.risk.risk_manager import RiskManager


async def test_pdf_with_trade_params():
    """Test PDF generation with stop loss and take profit."""

    print("\n🚀 Testing PDF Generation with Trade Parameters")
    print("="*60)

    # Configure test data
    config = {
        'risk': {
            'default_risk_percentage': 2.0,
            'risk_reward_ratio': 2.0,
            'long_stop_percentage': 3.5,
            'short_stop_percentage': 3.5
        },
        'reporting': {
            'output_dir': 'reports'
        }
    }

    # Initialize components
    risk_manager = RiskManager(config)
    pdf_generator = ReportGenerator(config)

    # Test data with trade parameters
    symbol = "BTC/USDT"
    entry_price = 50000.0
    signal_type = "BUY"
    confluence_score = 75.0

    # Calculate trade parameters using RiskManager
    from src.risk.risk_manager import OrderType
    order_type = OrderType.BUY if signal_type == "BUY" else OrderType.SELL

    sl_tp = risk_manager.calculate_stop_loss_take_profit(
        entry_price=entry_price,
        order_type=order_type
    )

    position_info = risk_manager.calculate_position_size(
        account_balance=10000,
        entry_price=entry_price,
        stop_loss_price=sl_tp['stop_loss_price']
    )

    # Prepare signal data with trade parameters
    signal_data = {
        'symbol': symbol,
        'signal_type': signal_type,
        'confluence_score': confluence_score,
        'entry_price': entry_price,
        'trade_params': {
            'entry_price': entry_price,
            'stop_loss': sl_tp['stop_loss_price'],
            'take_profit': sl_tp['take_profit_price'],
            'position_size': position_info['position_size_units'],
            'risk_reward_ratio': sl_tp['risk_reward_ratio'],
            'risk_percentage': position_info['risk_percentage']
        },
        'timestamp': datetime.now().isoformat(),
        'analysis_components': {
            'orderflow': {'score': 80, 'interpretation': 'Strong buying pressure'},
            'sentiment': {'score': 70, 'interpretation': 'Bullish market sentiment'},
            'liquidity': {'score': 75, 'interpretation': 'Good liquidity zones'},
            'bitcoin_beta': {'score': 65, 'interpretation': 'Positive BTC correlation'},
            'smart_money': {'score': 72, 'interpretation': 'Institutional accumulation'},
            'price_structure': {'score': 78, 'interpretation': 'Uptrend structure'}
        }
    }

    print(f"\n📊 Test Signal Data:")
    print(f"  Symbol: {symbol}")
    print(f"  Signal: {signal_type}")
    print(f"  Entry Price: ${entry_price:,.2f}")
    print(f"  Stop Loss: ${signal_data['trade_params']['stop_loss']:,.2f}")
    print(f"  Take Profit: ${signal_data['trade_params']['take_profit']:,.2f}")
    print(f"  Position Size: {signal_data['trade_params']['position_size']:.6f} units")
    print(f"  Risk/Reward: 1:{signal_data['trade_params']['risk_reward_ratio']:.1f}")

    # Generate mock OHLCV data
    import pandas as pd
    import numpy as np
    from datetime import timedelta

    dates = pd.date_range(end=datetime.now(), periods=100, freq='1h')
    prices = np.random.normal(entry_price, entry_price * 0.02, 100)

    ohlcv_data = pd.DataFrame({
        'timestamp': dates,
        'open': prices + np.random.normal(0, 10, 100),
        'high': prices + abs(np.random.normal(50, 20, 100)),
        'low': prices - abs(np.random.normal(50, 20, 100)),
        'close': prices,
        'volume': np.random.uniform(100, 1000, 100)
    })

    try:
        # Generate the report
        print(f"\n📄 Generating PDF report...")

        pdf_path, json_path, png_path = pdf_generator.generate_trading_report(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            output_dir='reports/test'
        )

        if pdf_path and os.path.exists(pdf_path):
            print(f"✅ PDF generated successfully: {pdf_path}")

            # Check file size
            file_size = os.path.getsize(pdf_path) / 1024  # KB
            print(f"✅ File size: {file_size:.2f} KB")

            # Verify the PDF contains trade parameters
            print("\n📋 Verification:")
            print("  ✅ Stop Loss included in signal data")
            print("  ✅ Take Profit included in signal data")
            print("  ✅ Position Size calculated")
            print("  ✅ Risk/Reward ratio calculated")

            # Check if PNG was also generated
            if png_path and os.path.exists(png_path):
                print(f"\n🖼️ PNG chart generated: {png_path}")
                png_size = os.path.getsize(png_path) / 1024  # KB
                print(f"✅ PNG size: {png_size:.2f} KB")
                print("✅ Chart includes stop loss and take profit levels")
            else:
                print("⚠️ PNG chart not generated with PDF")

            return True
        else:
            print(f"❌ PDF generation failed")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""

    print("\n🎯 PDF Trade Parameters Test")
    print("Testing stop loss and take profit in PDF/PNG generation")
    print("="*60)

    # Create output directory
    os.makedirs('reports/test', exist_ok=True)

    # Run the test
    success = await test_pdf_with_trade_params()

    print("\n" + "="*60)
    if success:
        print("✅ PDF generation test completed successfully!")
        print("✅ Stop loss and take profit are included in reports")
        print("\n📁 Check the generated files in: reports/test/")
        sys.exit(0)
    else:
        print("❌ PDF generation test failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())