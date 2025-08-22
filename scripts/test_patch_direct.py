#!/usr/bin/env python3
"""Test if the patched method works"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test():
    from src.core.exchanges.bybit import BybitExchange
    from src.config.manager import ConfigManager
    
    print("Loading config...")
    config = ConfigManager()
    bybit_config = config.config['exchanges']['bybit']
    
    print("Creating exchange...")
    exchange = BybitExchange(bybit_config)
    
    print("Initializing...")
    await exchange.initialize()
    
    print("Testing get_market_tickers...")
    tickers = await exchange.get_market_tickers()
    
    if tickers:
        print(f"✅ SUCCESS! Got {len(tickers)} tickers")
        for symbol, data in list(tickers.items())[:3]:
            print(f"  {symbol}: ${data.get('last', 0)}")
    else:
        print("❌ No tickers returned")
        
        # Try the working method directly
        print("\nTrying get_market_tickers_working...")
        if hasattr(exchange, 'get_market_tickers_working'):
            tickers = await exchange.get_market_tickers_working()
            if tickers:
                print(f"✅ Working method got {len(tickers)} tickers")
            else:
                print("❌ Working method also failed")
        else:
            print("❌ Working method not found")
    
    await exchange.cleanup()

asyncio.run(test())