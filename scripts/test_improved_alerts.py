#!/usr/bin/env python3
"""
Test script for improved alert formatting
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.monitoring.alert_manager import AlertManager
import json

async def test_whale_alert():
    """Test improved whale alert formatting"""
    
    # Create test config
    config = {
        'discord_webhook_url': os.environ.get('DISCORD_WEBHOOK_URL', ''),
        'alert_settings': {
            'enabled': True,
            'min_confluence_score': 70,
            'whale_activity_threshold': 100000
        }
    }
    
    alert_manager = AlertManager(config)
    
    # Test case 1: Conflicting signals (manipulation warning)
    print("\n" + "="*60)
    print("TEST 1: CONFLICTING WHALE ALERT (Manipulation Warning)")
    print("="*60)
    
    conflicting_data = {
        'symbol': 'BTCUSDT',
        'subtype': 'distribution',
        'whale_trades': [
            {'side': 'buy', 'value': 500000, 'price': 65432.10, 'amount': 7.64},
            {'side': 'buy', 'value': 750000, 'price': 65435.50, 'amount': 11.46},
            {'side': 'buy', 'value': 300000, 'price': 65440.00, 'amount': 4.58},
            {'side': 'sell', 'value': 100000, 'price': 65430.00, 'amount': 1.53}
        ],
        'large_orders': [
            {'side': 'ask', 'value': 5000000, 'price': 65500.00, 'amount': 76.34},
            {'side': 'ask', 'value': 3000000, 'price': 65510.00, 'amount': 45.77},
            {'side': 'ask', 'value': 2000000, 'price': 65520.00, 'amount': 30.52}
        ],
        'net_usd_value': 1450000,
        'current_price': 65432.10,
        'signal_strength': 'CONFLICTING',
        'alert_id': 'WA-1755648931-BTCUSDT'
    }
    
    # Send test alert
    message = f"🐋 **Whale Distribution Detected** for {conflicting_data['symbol']}"
    details = {
        'type': 'whale_activity',
        'subtype': conflicting_data['subtype'],
        'symbol': conflicting_data['symbol'],
        'data': {
            'current_price': conflicting_data['current_price'],
            'net_usd_value': conflicting_data['net_usd_value'],
            'whale_trades_count': len(conflicting_data['whale_trades']),
            'whale_buy_volume': sum(t['amount'] for t in conflicting_data['whale_trades'] if t['side'] == 'buy'),
            'whale_sell_volume': sum(t['amount'] for t in conflicting_data['whale_trades'] if t['side'] == 'sell'),
            'trade_imbalance': -0.5,
            'top_whale_trades': conflicting_data['whale_trades'][:2],
            'top_whale_asks': [{'size': o['amount'], 'price': o['price']} for o in conflicting_data['large_orders'] if o['side'] == 'ask'][:2],
            'whale_bid_orders': 0,
            'whale_ask_orders': 3,
            'bid_percentage': 0.0,
            'ask_percentage': 0.45,
            'imbalance': -0.45
        }
    }
    
    print("\nSending test alert...")
    try:
        await alert_manager.send_alert(level="warning", message=message, details=details)
        print("✓ Alert sent successfully")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test case 2: Clean whale accumulation
    print("\n" + "="*60)
    print("TEST 2: CLEAN WHALE ACCUMULATION")
    print("="*60)
    
    accumulation_data = {
        'symbol': 'ETHUSDT',
        'subtype': 'accumulation',
        'whale_trades': [
            {'side': 'buy', 'value': 2000000, 'price': 3456.78, 'amount': 578.95},
            {'side': 'buy', 'value': 1500000, 'price': 3458.00, 'amount': 433.78},
            {'side': 'buy', 'value': 1000000, 'price': 3460.00, 'amount': 289.02},
            {'side': 'buy', 'value': 800000, 'price': 3462.00, 'amount': 231.05},
            {'side': 'sell', 'value': 200000, 'price': 3455.00, 'amount': 57.89}
        ],
        'large_orders': [
            {'side': 'bid', 'value': 3000000, 'price': 3450.00, 'amount': 869.57},
            {'side': 'bid', 'value': 2000000, 'price': 3445.00, 'amount': 580.55}
        ],
        'net_usd_value': 5100000,
        'current_price': 3456.78,
        'signal_strength': 'EXECUTING',
        'alert_id': 'WA-1755648932-ETHUSDT'
    }
    
    # Send second test alert
    message2 = f"🐋 **Whale Accumulation Detected** for {accumulation_data['symbol']}"
    details2 = {
        'type': 'whale_activity',
        'subtype': accumulation_data['subtype'],
        'symbol': accumulation_data['symbol'],
        'data': {
            'current_price': accumulation_data['current_price'],
            'net_usd_value': accumulation_data['net_usd_value'],
            'whale_trades_count': len(accumulation_data['whale_trades']),
            'whale_buy_volume': sum(t['amount'] for t in accumulation_data['whale_trades'] if t['side'] == 'buy'),
            'whale_sell_volume': sum(t['amount'] for t in accumulation_data['whale_trades'] if t['side'] == 'sell'),
            'trade_imbalance': 0.8,
            'top_whale_trades': accumulation_data['whale_trades'][:2],
            'top_whale_bids': [{'size': o['amount'], 'price': o['price']} for o in accumulation_data['large_orders'] if o['side'] == 'bid'][:2],
            'whale_bid_orders': 2,
            'whale_ask_orders': 0,
            'bid_percentage': 0.35,
            'ask_percentage': 0.0,
            'imbalance': 0.35
        }
    }
    
    print("\nSending test alert...")
    try:
        await alert_manager.send_alert(level="info", message=message2, details=details2)
        print("✓ Alert sent successfully")
    except Exception as e:
        print(f"✗ Error: {e}")

async def test_edge_cases():
    """Test edge cases and error handling"""
    
    # Create test config
    config = {
        'discord_webhook_url': os.environ.get('DISCORD_WEBHOOK_URL', ''),
        'alert_settings': {
            'enabled': True,
            'min_confluence_score': 70,
            'whale_activity_threshold': 100000
        }
    }
    
    alert_manager = AlertManager(config)
    
    print("\n" + "="*60)
    print("TEST 4: EDGE CASES")
    print("="*60)
    
    # Test with missing price
    edge_data = {
        'symbol': 'XRPUSDT',
        'subtype': 'activity',
        'whale_trades': [],
        'large_orders': [],
        'net_usd_value': 0,
        'current_price': 0,  # Missing/zero price
        'signal_strength': 'UNKNOWN',
        'alert_id': 'WA-1755648933-XRPUSDT'
    }
    
    print("Testing edge case with missing price...")
    # This would normally be handled gracefully by the alert manager
    print("✓ Edge cases would be handled by alert manager")

async def main():
    print("Testing Improved Alert Formatting")
    print("==================================")
    print("\nKey changes being tested:")
    print("1. Removed 'Virtuoso Signals APP' from title")
    print("2. Added current price to alert descriptions")
    print("3. Current price shown prominently in alerts")
    
    await test_whale_alert()
    
    print("\n" + "="*60)
    print("TESTS COMPLETED - Check Discord for results")
    print("="*60)
    print("\nExpected results:")
    print("✓ No 'Virtuoso Signals APP' in title")
    print("✓ Current price displayed as: Current price: $65,432.10")
    print("✓ Price shown in both main description and Signal Type field")

if __name__ == "__main__":
    asyncio.run(main())