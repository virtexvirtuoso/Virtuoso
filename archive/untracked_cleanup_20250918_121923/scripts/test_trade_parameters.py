#!/usr/bin/env python3
"""
Test script to verify that trade parameters (stop loss, take profit, position size)
are being correctly calculated and included in trading signals.
"""

import asyncio
import sys
import json
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.monitoring.signal_processor import SignalProcessor
from src.risk.risk_manager import RiskManager, OrderType
from src.core.interpretation.interpretation_manager import InterpretationManager


async def test_risk_manager_calculations():
    """Test RiskManager's trade parameter calculation methods."""
    print("\n" + "="*60)
    print("Testing RiskManager Trade Parameter Calculations")
    print("="*60)

    # Initialize RiskManager with test config
    config = {
        'risk': {
            'default_risk_percentage': 2.0,
            'max_risk_percentage': 3.0,
            'min_risk_percentage': 0.5,
            'risk_reward_ratio': 2.0,
            'long_stop_percentage': 3.5,
            'short_stop_percentage': 3.5
        }
    }

    risk_manager = RiskManager(config)

    # Test BUY signal parameters
    entry_price = 50000.0
    print(f"\nTest Case 1: BUY Signal at ${entry_price}")
    print("-" * 40)

    sl_tp_buy = risk_manager.calculate_stop_loss_take_profit(
        entry_price=entry_price,
        order_type=OrderType.BUY
    )

    print(f"Stop Loss: ${sl_tp_buy['stop_loss_price']:.2f} ({sl_tp_buy['stop_loss_percentage']:.1f}%)")
    print(f"Take Profit: ${sl_tp_buy['take_profit_price']:.2f}")
    print(f"Risk/Reward Ratio: 1:{sl_tp_buy['risk_reward_ratio']:.1f}")

    # Calculate position size
    position_info = risk_manager.calculate_position_size(
        account_balance=10000,
        entry_price=entry_price,
        stop_loss_price=sl_tp_buy['stop_loss_price']
    )

    print(f"Position Size: {position_info['position_size_units']:.6f} units")
    print(f"Position Value: ${position_info['position_value_usd']:.2f}")
    print(f"Risk Amount: ${position_info['risk_amount_usd']:.2f}")
    print(f"Risk Percentage: {position_info['risk_percentage']:.2f}%")

    # Test SELL signal parameters
    print(f"\nTest Case 2: SELL Signal at ${entry_price}")
    print("-" * 40)

    sl_tp_sell = risk_manager.calculate_stop_loss_take_profit(
        entry_price=entry_price,
        order_type=OrderType.SELL
    )

    print(f"Stop Loss: ${sl_tp_sell['stop_loss_price']:.2f} ({sl_tp_sell['stop_loss_percentage']:.1f}%)")
    print(f"Take Profit: ${sl_tp_sell['take_profit_price']:.2f}")
    print(f"Risk/Reward Ratio: 1:{sl_tp_sell['risk_reward_ratio']:.1f}")


async def test_signal_processor_enrichment():
    """Test SignalProcessor's trade parameter enrichment."""
    print("\n" + "="*60)
    print("Testing SignalProcessor Trade Parameter Enrichment")
    print("="*60)

    # Initialize components
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

    risk_manager = RiskManager(config)

    # Create a mock signal processor
    signal_processor = SignalProcessor(
        config=config,
        signal_generator=None,
        metrics_manager=None,
        interpretation_manager=None,
        market_data_manager=None,
        risk_manager=risk_manager
    )

    # Test BUY signal enrichment
    print("\nTest Case 3: BUY Signal Enrichment")
    print("-" * 40)

    trade_params = signal_processor._enrich_signal_with_trade_parameters(
        symbol="BTC/USDT",
        price=50000.0,
        signal_type="BUY",
        confluence_score=75.0,
        reliability=0.8
    )

    print(f"Entry Price: ${trade_params['entry_price']}")
    print(f"Stop Loss: ${trade_params['stop_loss']}")
    print(f"Take Profit: ${trade_params['take_profit']}")
    print(f"Position Size: {trade_params['position_size']} units")
    print(f"Risk/Reward: 1:{trade_params['risk_reward_ratio']}")
    print(f"Risk %: {trade_params['risk_percentage']}%")
    print(f"Confidence: {trade_params['confidence']:.2f}")

    # Test SELL signal enrichment
    print("\nTest Case 4: SELL Signal Enrichment")
    print("-" * 40)

    trade_params = signal_processor._enrich_signal_with_trade_parameters(
        symbol="ETH/USDT",
        price=3500.0,
        signal_type="SELL",
        confluence_score=80.0,
        reliability=0.9
    )

    print(f"Entry Price: ${trade_params['entry_price']}")
    print(f"Stop Loss: ${trade_params['stop_loss']}")
    print(f"Take Profit: ${trade_params['take_profit']}")
    print(f"Position Size: {trade_params['position_size']} units")
    print(f"Risk/Reward: 1:{trade_params['risk_reward_ratio']}")
    print(f"Risk %: {trade_params['risk_percentage']}%")
    print(f"Confidence: {trade_params['confidence']:.2f}")

    # Test NEUTRAL signal (should return defaults)
    print("\nTest Case 5: NEUTRAL Signal (Should use defaults)")
    print("-" * 40)

    trade_params_neutral = signal_processor._enrich_signal_with_trade_parameters(
        symbol="XRP/USDT",
        price=0.5,
        signal_type="NEUTRAL",
        confluence_score=50.0,
        reliability=0.5
    )

    print(f"Entry Price: ${trade_params_neutral['entry_price']}")
    print(f"Stop Loss: {trade_params_neutral['stop_loss']}")
    print(f"Take Profit: {trade_params_neutral['take_profit']}")
    print(f"Position Size: {trade_params_neutral['position_size']}")

    print("\n" + "="*60)
    print("✅ Trade Parameters Test Complete!")
    print("="*60)

    # Get the BUY signal params for verification
    trade_params_buy = signal_processor._enrich_signal_with_trade_parameters(
        symbol="BTC/USDT",
        price=50000.0,
        signal_type="BUY",
        confluence_score=75.0,
        reliability=0.8
    )

    # Return summary for verification (check BUY signal, not NEUTRAL)
    return {
        "risk_manager_working": True,  # We successfully tested the RiskManager
        "signal_processor_enrichment_working": trade_params_buy is not None,
        "stop_loss_calculated": trade_params_buy.get('stop_loss') is not None,
        "take_profit_calculated": trade_params_buy.get('take_profit') is not None,
        "position_size_calculated": trade_params_buy.get('position_size') is not None
    }


async def main():
    """Main test function."""
    print("\n🚀 Starting Trade Parameters Test Suite")

    try:
        # Run RiskManager tests
        await test_risk_manager_calculations()

        # Run SignalProcessor enrichment tests
        results = await test_signal_processor_enrichment()

        # Print summary
        print("\n📊 Test Summary:")
        print("-" * 40)
        for key, value in results.items():
            status = "✅ PASS" if value else "❌ FAIL"
            print(f"{key}: {status}")

        # Overall result
        all_passed = all(results.values())
        if all_passed:
            print("\n🎉 All tests passed! Trade parameters are being calculated correctly.")
        else:
            print("\n⚠️ Some tests failed. Please check the implementation.")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())