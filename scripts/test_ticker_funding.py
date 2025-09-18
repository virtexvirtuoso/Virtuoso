#!/usr/bin/env python3
"""Test script to check if ticker contains funding_rate"""

import asyncio
import ccxt.async_support as ccxt
import os
from dotenv import load_dotenv

async def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize Bybit exchange
    exchange = ccxt.bybit({
        'apiKey': os.getenv('BYBIT_API_KEY'),
        'secret': os.getenv('BYBIT_API_SECRET'),
        'enableRateLimit': True,
        'options': {
            'defaultType': 'linear'  # For USDT perpetual futures
        }
    })
    
    try:
        # Fetch ticker for BTCUSDT
        symbol = 'BTC/USDT:USDT'
        print(f"\nFetching ticker for {symbol}...")
        
        ticker = await exchange.fetch_ticker(symbol)
        
        print(f"\nTicker keys: {list(ticker.keys())}")
        
        # Check for funding_rate related fields
        funding_fields = ['info']  # CCXT raw response is in 'info'
        if 'info' in ticker:
            info = ticker['info']
            print(f"\nRaw info keys: {list(info.keys())}")
            
            # Check for funding rate in raw response
            if 'fundingRate' in info:
                print(f"\n✓ fundingRate found in raw info: {info['fundingRate']}")
            
            if 'nextFundingTime' in info:
                print(f"✓ nextFundingTime found in raw info: {info['nextFundingTime']}")
                
        # Check parsed fields
        print(f"\nParsed ticker fields:")
        for field in ['bid', 'ask', 'last', 'high', 'low', 'open', 'close', 'volume']:
            if field in ticker:
                print(f"  {field}: {ticker[field]}")
        
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())