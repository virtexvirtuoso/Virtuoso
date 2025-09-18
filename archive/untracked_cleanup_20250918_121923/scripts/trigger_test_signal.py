#!/usr/bin/env python3
"""
Trigger a test signal generation on VPS to verify fixes in production.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def trigger_test_signal():
    """Trigger a test signal with all parameters."""

    print("🚀 Triggering Test Signal Generation")
    print("="*50)

    # Import required components
    from src.monitoring.alert_manager import AlertManager
    from src.risk.risk_manager import RiskManager

    # Initialize components
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
        'alert': {
            'discord': {'enabled': False},
            'telegram': {'enabled': False}
        }
    }

    alert_manager = AlertManager(config)
    risk_manager = RiskManager(config)

    # Create test signal data
    test_signal = {
        'symbol': 'TEST/USDT',
        'signal_type': 'BUY',
        'price': 100.0,
        'entry_price': 100.0,
        'confluence_score': 75.0,
        'reliability': 0.95,  # 95% reliability (should display as 95%, not 9500%)
        'timestamp': datetime.now().isoformat(),
        'analysis_components': {
            'orderflow': {'score': 80, 'interpretation': 'Strong buying pressure'},
            'sentiment': {'score': 75, 'interpretation': 'Bullish sentiment'},
            'liquidity': {'score': 70, 'interpretation': 'Good liquidity'},
            'bitcoin_beta': {'score': 72, 'interpretation': 'Positive correlation'},
            'smart_money': {'score': 78, 'interpretation': 'Accumulation phase'},
            'price_structure': {'score': 75, 'interpretation': 'Uptrend confirmed'}
        }
    }

    # Calculate trade parameters
    from src.risk.risk_manager import OrderType
    sl_tp = risk_manager.calculate_stop_loss_take_profit(
        entry_price=test_signal['price'],
        order_type=OrderType.BUY
    )

    position_info = risk_manager.calculate_position_size(
        account_balance=10000,
        entry_price=test_signal['price'],
        stop_loss_price=sl_tp['stop_loss_price']
    )

    # Add trade parameters
    test_signal['trade_params'] = {
        'entry_price': test_signal['price'],
        'stop_loss': sl_tp['stop_loss_price'],
        'take_profit': sl_tp['take_profit_price'],
        'position_size': position_info['position_size_units'],
        'risk_reward_ratio': sl_tp['risk_reward_ratio'],
        'risk_percentage': position_info['risk_percentage']
    }

    print("\nTest Signal Details:")
    print(f"  Symbol: {test_signal['symbol']}")
    print(f"  Type: {test_signal['signal_type']}")
    print(f"  Price: ${test_signal['price']}")
    print(f"  Reliability: {test_signal['reliability'] * 100:.0f}%")
    print(f"  Stop Loss: ${test_signal['trade_params']['stop_loss']:.2f}")
    print(f"  Take Profit: ${test_signal['trade_params']['take_profit']:.2f}")

    # Process the signal (this will generate PDF if configured)
    try:
        await alert_manager.send_signal_alert(test_signal)
        print("\n✅ Test signal processed successfully")
        print("Check for generated PDF with:")
        print("  • Reliability showing as 95% (not 9500%)")
        print("  • Stop loss and take profit on chart")
    except Exception as e:
        print(f"\n❌ Error processing signal: {str(e)}")

    return test_signal


async def main():
    """Main function."""
    signal = await trigger_test_signal()

    # Save test signal for reference
    with open('reports/test/test_signal.json', 'w') as f:
        json.dump(signal, f, indent=2, default=str)

    print(f"\n📁 Test signal saved to: reports/test/test_signal.json")


if __name__ == "__main__":
    asyncio.run(main())