#!/usr/bin/env python3
"""Test Bybit ticker fields to understand volume/turnover mapping"""

import asyncio
import ccxt.async_support as ccxt
import json

async def test_bybit_fields():
    exchange = ccxt.bybit({
        'sandbox': False,
        'enableRateLimit': True,
    })
    
    try:
        ticker = await exchange.fetch_ticker('BTCUSDT')
        print('=== CCXT Ticker Fields ===')
        print(f'baseVolume: {ticker.get("baseVolume")}')
        print(f'quoteVolume: {ticker.get("quoteVolume")}')
        print(f'volume: {ticker.get("volume")}')
        print(f'info keys: {list(ticker.get("info", {}).keys())}')
        print(f'info volume24h: {ticker.get("info", {}).get("volume24h")}')
        print(f'info turnover24h: {ticker.get("info", {}).get("turnover24h")}')
        
        print('\n=== Full Ticker Structure ===')
        print(json.dumps(ticker, indent=2, default=str))
        
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_bybit_fields()) 