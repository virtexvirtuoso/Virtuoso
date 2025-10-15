#!/usr/bin/env python3
"""
Test script for Bybit ticker/trades Error: 0 fix
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.exchanges.bybit import BybitExchange

async def test_ticker_trades_fix():
    """Test the Error: 0 fix with problematic symbols"""

    print("🚀 Testing Bybit Ticker/Trades Error: 0 Fix")
    print("=" * 50)

    # Initialize exchange
    exchange = BybitExchange()

    # Test symbols that were causing "Error: 0"
    test_symbols = [
        '10000SATSUSDT',
        '1000BONKUSDT',
        'BTCUSDT',
        'ETHUSDT',
        'SOLUSDT'
    ]

    success_count = 0
    total_tests = len(test_symbols) * 2  # ticker + trades for each symbol

    for symbol in test_symbols:
        print(f"\n🔍 Testing {symbol}:")

        # Test ticker
        try:
            ticker = await exchange._fetch_ticker(symbol)
            if ticker and ticker.get('last'):
                print(f"  ✅ Ticker: ${ticker['last']} (bid: ${ticker.get('bid', 'N/A')}, ask: ${ticker.get('ask', 'N/A')})")
                success_count += 1
            else:
                print(f"  ❌ Ticker: Empty response")
        except Exception as e:
            print(f"  ❌ Ticker: {str(e)}")

        # Test trades
        try:
            trades = await exchange.fetch_trades(symbol, limit=5)
            if trades and len(trades) > 0:
                latest_trade = trades[0]
                print(f"  ✅ Trades: {len(trades)} trades, latest: ${latest_trade.get('price', 'N/A')} @ {latest_trade.get('amount', 'N/A')}")
                success_count += 1
            else:
                print(f"  ❌ Trades: Empty response")
        except Exception as e:
            print(f"  ❌ Trades: {str(e)}")

    await exchange.close()

    print(f"\n📊 Test Results: {success_count}/{total_tests} successful")
    print(f"Success Rate: {(success_count/total_tests)*100:.1f}%")

    if success_count == total_tests:
        print("🎉 All tests passed! Error: 0 fix is working correctly.")
        return True
    elif success_count > total_tests * 0.8:
        print("✅ Most tests passed. Fix is working but some symbols may still have issues.")
        return True
    else:
        print("❌ Many tests failed. Fix may need adjustments.")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_ticker_trades_fix())
    sys.exit(0 if result else 1)