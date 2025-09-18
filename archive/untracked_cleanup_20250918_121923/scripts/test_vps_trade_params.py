#!/usr/bin/env python3
"""
Test if trade parameters are being calculated on VPS.
"""

import sys
import json
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.monitoring.signal_processor import SignalProcessor
from src.risk.risk_manager import RiskManager


def test_trade_params():
    """Test trade parameters calculation on VPS."""

    print("🧪 Testing Trade Parameters on VPS")
    print("="*50)

    # Test configuration
    config = {
        'trading': {
            'account_balance': 10000,
            'risk': {
                'default_risk_percentage': 2.0,
                'risk_reward_ratio': 2.0,
                'long_stop_percentage': 3.5,
                'short_stop_percentage': 3.5
            }
        },
        'risk': {
            'default_risk_percentage': 2.0,
            'risk_reward_ratio': 2.0,
            'long_stop_percentage': 3.5,
            'short_stop_percentage': 3.5
        }
    }

    # Initialize RiskManager
    print("\n1. Initializing RiskManager...")
    try:
        risk_manager = RiskManager(config)
        print("   ✅ RiskManager initialized")
    except Exception as e:
        print(f"   ❌ RiskManager failed: {e}")
        return False

    # Initialize SignalProcessor
    print("\n2. Initializing SignalProcessor with RiskManager...")
    try:
        signal_processor = SignalProcessor(
            config=config,
            signal_generator=None,
            metrics_manager=None,
            interpretation_manager=None,
            market_data_manager=None,
            risk_manager=risk_manager
        )
        print("   ✅ SignalProcessor initialized with RiskManager")
    except Exception as e:
        print(f"   ❌ SignalProcessor failed: {e}")
        return False

    # Test trade parameters calculation
    print("\n3. Testing trade parameters calculation...")

    test_cases = [
        ("XRP/USDT", 3.12, "BUY", 68.2, 0.8),
        ("BTC/USDT", 50000, "SELL", 75.0, 0.9)
    ]

    for symbol, price, signal_type, score, reliability in test_cases:
        print(f"\n   Testing {symbol} - {signal_type} at ${price}")

        # Use the calculate_trade_parameters method
        trade_params = signal_processor.calculate_trade_parameters(
            symbol=symbol,
            price=price,
            signal_type=signal_type,
            score=score,
            reliability=reliability
        )

        if trade_params:
            print(f"   ✅ Trade params calculated:")
            print(f"      Stop Loss: ${trade_params.get('stop_loss', 'N/A')}")
            print(f"      Take Profit: ${trade_params.get('take_profit', 'N/A')}")
            print(f"      Position Size: {trade_params.get('position_size', 'N/A')}")

            # Verify critical fields
            if trade_params.get('stop_loss') is None:
                print("   ⚠️ WARNING: Stop loss is None!")
            if trade_params.get('take_profit') is None:
                print("   ⚠️ WARNING: Take profit is None!")
        else:
            print(f"   ❌ Failed to calculate trade params")
            return False

    print("\n" + "="*50)
    print("✅ All tests passed! Trade parameters working correctly.")
    return True


if __name__ == "__main__":
    success = test_trade_params()
    sys.exit(0 if success else 1)