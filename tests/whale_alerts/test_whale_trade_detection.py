"""
Test Whale Trade Detection

Tests the new _detect_whale_trades functionality to ensure
it properly detects and alerts on large individual trade executions.

Test Scenarios:
1. Mega whale trade ($20M) - should trigger CRITICAL alert
2. Large whale trade ($2M) - should trigger WARNING alert
3. Multiple whale trades - should aggregate and alert
4. Mixed buy/sell whale trades - should show net direction
5. Trades below threshold - should NOT alert
"""

import asyncio
import time
from typing import Dict, Any
import yaml
from pathlib import Path


# Mock alert manager for testing
class MockAlertManager:
    """Mock AlertManager to capture alerts without sending to Discord."""

    def __init__(self):
        self.alerts = []

    async def send_alert(self, level: str, message: str, details: Dict[str, Any], throttle: bool = True):
        """Capture alert instead of sending."""
        alert = {
            'level': level,
            'message': message,
            'details': details,
            'throttle': throttle,
            'timestamp': time.time()
        }
        self.alerts.append(alert)
        print(f"\n{'='*80}")
        print(f"🚨 ALERT CAPTURED: {level.upper()}")
        print(f"{'='*80}")
        print(f"Message: {message}")
        print(f"\nDetails:")
        print(f"  Type: {details.get('type')}")
        print(f"  Priority: {details.get('priority')}")
        print(f"  Symbol: {details.get('symbol')}")

        if 'data' in details:
            data = details['data']
            print(f"\n  Whale Trade Data:")
            print(f"    Largest Trade: ${data.get('largest_trade_usd', 0):,.0f} {data.get('largest_trade_side', '').upper()}")
            print(f"    Total Whale Trades: {data.get('total_whale_trades', 0)}")
            print(f"    Total Buy USD: ${data.get('total_buy_usd', 0):,.0f}")
            print(f"    Total Sell USD: ${data.get('total_sell_usd', 0):,.0f}")
            print(f"    Net USD: ${data.get('net_usd', 0):,.0f}")
            print(f"    Direction: {data.get('direction')}")
            print(f"    Current Price: ${data.get('current_price', 0):,.2f}")

            if 'whale_trades' in data:
                print(f"\n  Top Whale Trades:")
                for i, trade in enumerate(data['whale_trades'][:5], 1):
                    print(f"    {i}. ${trade['value_usd']:,.0f} {trade['side'].upper()} @ ${trade['price']:,.2f} ({trade['time_ago']}s ago)")

        print(f"{'='*80}\n")
        return True

    def get_alert_count(self) -> int:
        """Get number of alerts captured."""
        return len(self.alerts)

    def clear_alerts(self):
        """Clear captured alerts."""
        self.alerts = []


def create_sample_market_data(scenario: str, symbol: str = 'BTC/USDT') -> Dict[str, Any]:
    """Create sample market data for testing different scenarios."""

    current_time = time.time()
    btc_price = 95000.0  # BTC at $95k

    # Base market data
    market_data = {
        'symbol': symbol,
        'ticker': {
            'last': btc_price,
            'bid': btc_price - 10,
            'ask': btc_price + 10,
            'volume': 15000.0
        },
        'orderbook': {
            'bids': [[btc_price - i*10, 0.5] for i in range(1, 50)],
            'asks': [[btc_price + i*10, 0.5] for i in range(1, 50)]
        }
    }

    # Scenario-specific trades
    if scenario == 'mega_whale_buy':
        # $20M whale buy (210.5 BTC @ $95k)
        market_data['trades'] = [
            {
                'timestamp': (current_time - 60) * 1000,  # 1 min ago
                'price': btc_price,
                'amount': 210.5,  # ~$20M
                'size': 210.5,
                'side': 'buy'
            },
            # Some normal trades
            {'timestamp': (current_time - 120) * 1000, 'price': btc_price - 50, 'amount': 0.5, 'size': 0.5, 'side': 'sell'},
            {'timestamp': (current_time - 150) * 1000, 'price': btc_price - 30, 'amount': 0.3, 'size': 0.3, 'side': 'buy'},
        ]

    elif scenario == 'large_whale_sell':
        # $2M whale sell (21 BTC @ $95k)
        market_data['trades'] = [
            {
                'timestamp': (current_time - 90) * 1000,  # 1.5 min ago
                'price': btc_price,
                'amount': 21.0,  # ~$2M
                'size': 21.0,
                'side': 'sell'
            },
            # Some normal trades
            {'timestamp': (current_time - 180) * 1000, 'price': btc_price + 20, 'amount': 0.8, 'size': 0.8, 'side': 'buy'},
        ]

    elif scenario == 'multiple_whales':
        # Multiple whale trades (should aggregate)
        market_data['trades'] = [
            # $5M buy
            {'timestamp': (current_time - 60) * 1000, 'price': btc_price, 'amount': 52.6, 'size': 52.6, 'side': 'buy'},
            # $3M buy
            {'timestamp': (current_time - 90) * 1000, 'price': btc_price + 100, 'amount': 31.5, 'size': 31.5, 'side': 'buy'},
            # $1M sell
            {'timestamp': (current_time - 120) * 1000, 'price': btc_price - 50, 'amount': 10.5, 'size': 10.5, 'side': 'sell'},
            # Normal trades
            {'timestamp': (current_time - 150) * 1000, 'price': btc_price, 'amount': 0.2, 'size': 0.2, 'side': 'buy'},
        ]

    elif scenario == 'mixed_direction':
        # Whale trades in both directions
        market_data['trades'] = [
            # $4M buy
            {'timestamp': (current_time - 60) * 1000, 'price': btc_price, 'amount': 42.1, 'size': 42.1, 'side': 'buy'},
            # $3M sell
            {'timestamp': (current_time - 90) * 1000, 'price': btc_price, 'amount': 31.5, 'size': 31.5, 'side': 'sell'},
            # $500k buy
            {'timestamp': (current_time - 120) * 1000, 'price': btc_price, 'amount': 5.2, 'size': 5.2, 'side': 'buy'},
        ]

    elif scenario == 'below_threshold':
        # Only small trades - should NOT trigger alert
        market_data['trades'] = [
            # $250k (below $300k threshold)
            {'timestamp': (current_time - 60) * 1000, 'price': btc_price, 'amount': 2.6, 'size': 2.6, 'side': 'buy'},
            # $100k
            {'timestamp': (current_time - 90) * 1000, 'price': btc_price, 'amount': 1.05, 'size': 1.05, 'side': 'sell'},
            # Normal small trades
            {'timestamp': (current_time - 120) * 1000, 'price': btc_price, 'amount': 0.5, 'size': 0.5, 'side': 'buy'},
            {'timestamp': (current_time - 150) * 1000, 'price': btc_price, 'amount': 0.3, 'size': 0.3, 'side': 'sell'},
        ]

    return market_data


async def test_whale_detection():
    """Test whale trade detection with various scenarios."""

    print("\n" + "="*80)
    print("WHALE TRADE DETECTION TEST SUITE")
    print("="*80)

    # Load config
    config_path = Path(__file__).parent.parent.parent / 'config' / 'config.yaml'
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Import after config is loaded
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.monitoring.monitor import MarketMonitor

    # Create monitor with mock alert manager
    mock_alert_manager = MockAlertManager()

    monitor = MarketMonitor(
        config=config,
        alert_manager=mock_alert_manager
    )

    # Test scenarios with different symbols to avoid cooldown conflicts
    scenarios = [
        ('mega_whale_buy', 'Mega Whale Buy ($20M)', 'BTCUSDT', True),
        ('large_whale_sell', 'Large Whale Sell ($2M)', 'ETHUSDT', True),
        ('multiple_whales', 'Multiple Whale Trades', 'SOLUSDT', True),
        ('mixed_direction', 'Mixed Buy/Sell Whales', 'BNBUSDT', True),
        ('below_threshold', 'Below Threshold (Should NOT Alert)', 'ADAUSDT', False)
    ]

    test_results = []

    for scenario, description, symbol, should_alert in scenarios:
        print(f"\n{'='*80}")
        print(f"TEST SCENARIO: {description}")
        print(f"{'='*80}")
        print(f"Expected: {'ALERT' if should_alert else 'NO ALERT'}")

        # Clear previous alerts
        mock_alert_manager.clear_alerts()

        # Create market data (use symbol to avoid cooldown)
        market_data = create_sample_market_data(scenario, symbol.replace('USDT', '/USDT'))

        # Run detection (use symbol-specific name to avoid cooldown conflicts)
        try:
            await monitor._detect_whale_trades(symbol, market_data)

            # Check results
            alert_count = mock_alert_manager.get_alert_count()

            if should_alert:
                if alert_count > 0:
                    print(f"\n✅ PASS: Alert triggered as expected ({alert_count} alert(s))")
                    test_results.append((description, 'PASS', alert_count))
                else:
                    print(f"\n❌ FAIL: Expected alert but none triggered")
                    test_results.append((description, 'FAIL', 0))
            else:
                if alert_count == 0:
                    print(f"\n✅ PASS: No alert triggered as expected")
                    test_results.append((description, 'PASS', 0))
                else:
                    print(f"\n❌ FAIL: Alert triggered but should not have ({alert_count} alert(s))")
                    test_results.append((description, 'FAIL', alert_count))

        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            test_results.append((description, 'ERROR', 0))

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, status, _ in test_results if status == 'PASS')
    failed = sum(1 for _, status, _ in test_results if status == 'FAIL')
    errors = sum(1 for _, status, _ in test_results if status == 'ERROR')

    for scenario, status, alert_count in test_results:
        emoji = '✅' if status == 'PASS' else '❌' if status == 'FAIL' else '⚠️'
        print(f"{emoji} {scenario}: {status} ({alert_count} alerts)")

    print(f"\nResults: {passed} passed, {failed} failed, {errors} errors out of {len(test_results)} tests")
    print("="*80)

    return passed == len(test_results)


if __name__ == '__main__':
    success = asyncio.run(test_whale_detection())
    exit(0 if success else 1)
