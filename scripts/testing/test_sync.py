#!/usr/bin/env python3
"""Synchronous test"""

import ccxt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Creating Bybit exchange...")
exchange = ccxt.bybit({
    'enableRateLimit': True,
    'options': {'defaultType': 'linear'},
    'timeout': 10000
})

try:
    print("Loading markets...")
    exchange.load_markets()
    print("✓ Markets loaded")
    
    print("Fetching BTC/USDT orderbook...")
    orderbook = exchange.fetch_order_book('BTC/USDT', limit=5)
    print(f"✓ Got {len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks")
    print(f"Best bid: ${orderbook['bids'][0][0]:,.2f}")
    print(f"Best ask: ${orderbook['asks'][0][0]:,.2f}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()