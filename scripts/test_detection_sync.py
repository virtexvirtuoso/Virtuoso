#!/usr/bin/env python3
"""Simple synchronous test"""

import ccxt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Testing manipulation detection on Bybit...")

# Fetch data
exchange = ccxt.bybit({'enableRateLimit': True, 'options': {'defaultType': 'linear'}})
exchange.load_markets()

print("Fetching orderbook...")
ob = exchange.fetch_order_book('BTC/USDT', 10)

print(f"Best bid: ${ob['bids'][0][0]:,.2f}")
print(f"Best ask: ${ob['asks'][0][0]:,.2f}")

# Check for potential layering
bids = ob['bids']
bid_prices = [b[0] for b in bids[:5]]
bid_sizes = [b[1] for b in bids[:5]]

print(f"\nTop 5 bid levels:")
for i, (price, size) in enumerate(zip(bid_prices, bid_sizes)):
    print(f"  {i+1}. ${price:,.2f} - {size:.4f} BTC")

# Simple layering check
size_variance = max(bid_sizes) / min(bid_sizes) if min(bid_sizes) > 0 else 999
print(f"\nSize variance ratio: {size_variance:.2f}")
if size_variance < 1.5:
    print("⚠️  Potential layering - uniform sizes detected!")
else:
    print("✓ No obvious layering pattern")

print("\nDone!")