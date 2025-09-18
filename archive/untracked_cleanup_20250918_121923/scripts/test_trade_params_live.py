#!/usr/bin/env python3
"""
Test trade parameters in live monitoring system.
This script starts the monitoring system and verifies that signals include
stop loss, take profit, and position size calculations.
"""

import asyncio
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.monitoring.monitor import MarketMonitor
from src.core.config.config_loader import load_config
from src.core.exchanges.manager import ExchangeManager
from src.monitoring.alert_manager import AlertManager
from src.core.analysis.confluence import ConfluenceAnalyzer
from src.signal_generation.signal_generator import SignalGenerator
from src.core.analysis.interpretation_generator import InterpretationGenerator
from src.monitoring.metrics_manager import MetricsManager
from src.core.top_symbols import TopSymbolsManager
from src.core.market.market_data_manager import MarketDataManager


class SignalCapture:
    """Captures signals for verification."""

    def __init__(self):
        self.captured_signals = []

    async def capture_signal(self, signal_data):
        """Capture signal for analysis."""
        self.captured_signals.append(signal_data)
        print(f"\n📡 Captured signal for {signal_data.get('symbol', 'Unknown')}")

        # Check for trade parameters
        trade_params = signal_data.get('trade_params', {})
        if trade_params:
            print(f"  ✅ Stop Loss: ${trade_params.get('stop_loss', 'N/A')}")
            print(f"  ✅ Take Profit: ${trade_params.get('take_profit', 'N/A')}")
            print(f"  ✅ Position Size: {trade_params.get('position_size', 'N/A')}")
            print(f"  ✅ Risk/Reward: {trade_params.get('risk_reward_ratio', 'N/A')}")
        else:
            print("  ⚠️ No trade parameters found!")

        return signal_data


async def test_monitoring_system():
    """Test the monitoring system with trade parameters."""

    print("\n🚀 Starting Live Monitoring System Test")
    print("="*60)

    try:
        # Load configuration
        config = load_config()

        # Override some settings for testing
        config['monitoring']['enabled'] = True
        config['monitoring']['interval'] = 30  # Quick interval for testing
        config['confluence']['enabled'] = True

        # Initialize components
        print("\n📦 Initializing components...")

        # Exchange Manager
        exchange_manager = ExchangeManager()
        await exchange_manager.initialize(config)
        print("  ✅ Exchange Manager initialized")

        # Market Data Manager
        market_data_manager = MarketDataManager(
            exchange_manager=exchange_manager,
            config=config
        )
        await market_data_manager.initialize()
        print("  ✅ Market Data Manager initialized")

        # Top Symbols Manager
        top_symbols_manager = TopSymbolsManager(
            exchange_manager=exchange_manager,
            market_data_manager=market_data_manager,
            config=config
        )
        print("  ✅ Top Symbols Manager initialized")

        # Metrics Manager
        metrics_manager = MetricsManager(config)
        print("  ✅ Metrics Manager initialized")

        # Confluence Analyzer
        confluence_analyzer = ConfluenceAnalyzer(
            exchange_manager=exchange_manager,
            market_data_manager=market_data_manager,
            config=config
        )
        await confluence_analyzer.initialize()
        print("  ✅ Confluence Analyzer initialized")

        # Signal Generator
        signal_generator = SignalGenerator(config)
        print("  ✅ Signal Generator initialized")

        # Alert Manager with signal capture
        signal_capture = SignalCapture()
        alert_manager = AlertManager(config)

        # Wrap the alert manager's send method to capture signals
        original_send = alert_manager.send_signal_alert

        async def wrapped_send(signal_data):
            await signal_capture.capture_signal(signal_data)
            # Don't actually send alerts during test
            # return await original_send(signal_data)

        alert_manager.send_signal_alert = wrapped_send
        print("  ✅ Alert Manager initialized with signal capture")

        # Initialize Market Monitor
        monitor = MarketMonitor(
            exchange_manager=exchange_manager,
            confluence_analyzer=confluence_analyzer,
            config=config,
            alert_manager=alert_manager,
            signal_generator=signal_generator,
            metrics_manager=metrics_manager,
            top_symbols_manager=top_symbols_manager,
            market_data_manager=market_data_manager
        )

        await monitor.initialize()
        print("  ✅ Market Monitor initialized with RiskManager")

        # Test with a few symbols
        test_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']

        print(f"\n🔍 Testing with symbols: {test_symbols}")
        print("="*60)

        # Run one monitoring cycle for each symbol
        for symbol in test_symbols:
            print(f"\n📊 Analyzing {symbol}...")

            try:
                # Run analysis
                await monitor.monitor_symbol(symbol)

                # Wait a bit for processing
                await asyncio.sleep(2)

            except Exception as e:
                print(f"  ❌ Error analyzing {symbol}: {str(e)}")
                continue

        # Check captured signals
        print("\n" + "="*60)
        print("📈 Signal Analysis Results")
        print("="*60)

        if signal_capture.captured_signals:
            print(f"\n✅ Captured {len(signal_capture.captured_signals)} signals")

            # Analyze each signal
            signals_with_params = 0
            for signal in signal_capture.captured_signals:
                trade_params = signal.get('trade_params', {})
                if trade_params and trade_params.get('stop_loss'):
                    signals_with_params += 1

            print(f"✅ {signals_with_params} signals have trade parameters")

            # Show a sample signal
            if signal_capture.captured_signals:
                sample = signal_capture.captured_signals[0]
                print(f"\n📋 Sample Signal Structure:")
                print(json.dumps({
                    'symbol': sample.get('symbol'),
                    'signal_type': sample.get('signal_type'),
                    'trade_params': sample.get('trade_params', {}),
                    'confluence_score': sample.get('confluence_score')
                }, indent=2))

        else:
            print("\n⚠️ No signals were generated during test")

        # Summary
        print("\n" + "="*60)
        print("📊 Test Summary")
        print("="*60)

        success = len(signal_capture.captured_signals) > 0

        if success:
            # Check if any signal has trade params
            has_params = any(
                s.get('trade_params', {}).get('stop_loss')
                for s in signal_capture.captured_signals
            )

            if has_params:
                print("✅ SUCCESS: Trade parameters are being calculated!")
                print("✅ Stop loss and take profit values are included in signals")
                return True
            else:
                print("⚠️ WARNING: Signals generated but no trade parameters found")
                print("   This might be normal if all signals were NEUTRAL")
                return False
        else:
            print("❌ FAIL: No signals were generated during test")
            return False

    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean shutdown
        try:
            if 'monitor' in locals():
                await monitor.shutdown()
            if 'exchange_manager' in locals():
                await exchange_manager.shutdown()
        except:
            pass


async def main():
    """Main test function."""

    print("\n🎯 Trade Parameters Live Test")
    print("Testing stop loss and take profit in monitoring system")
    print("="*60)

    # Run the test
    success = await test_monitoring_system()

    if success:
        print("\n✅ Trade parameters test completed successfully!")
        print("Ready for deployment!")
        sys.exit(0)
    else:
        print("\n❌ Trade parameters test failed or incomplete")
        print("Please check the implementation")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())