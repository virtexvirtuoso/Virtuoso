#!/usr/bin/env python3
"""Fetch ticker data directly from Bybit API"""

import asyncio
import aiohttp
import json

async def fetch_bybit_tickers():
    """Fetch ticker data directly from Bybit API"""
    try:
        url = "https://api.bybit.com/v5/market/tickers"
        params = {"category": "linear"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        tickers = data.get('result', {}).get('list', [])
                        
                        # Convert to dict for easy lookup
                        ticker_dict = {}
                        for ticker in tickers:
                            symbol = ticker.get('symbol')
                            if symbol:
                                ticker_dict[symbol] = {
                                    'symbol': symbol,
                                    'price': float(ticker.get('lastPrice', 0)),
                                    'volume_24h_usd': float(ticker.get('turnover24h', 0)),
                                    'price_change_percent': float(ticker.get('price24hPcnt', 0)) * 100,
                                    'high_24h': float(ticker.get('highPrice24h', 0)),
                                    'low_24h': float(ticker.get('lowPrice24h', 0)),
                                    'volume': float(ticker.get('volume24h', 0))
                                }
                        
                        print(f"Fetched {len(ticker_dict)} tickers from Bybit")
                        
                        # Show sample data
                        for symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']:
                            if symbol in ticker_dict:
                                t = ticker_dict[symbol]
                                print(f"\n{symbol}:")
                                print(f"  Price: ${t['price']:,.2f}")
                                print(f"  Volume 24h: ${t['volume_24h_usd']:,.0f}")
                                print(f"  Change 24h: {t['price_change_percent']:.2f}%")
                        
                        return ticker_dict
                    else:
                        print(f"API error: {data.get('retMsg')}")
                else:
                    print(f"HTTP error: {response.status}")
    except Exception as e:
        print(f"Error fetching tickers: {e}")
        import traceback
        traceback.print_exc()
    
    return {}

async def main():
    tickers = await fetch_bybit_tickers()
    
    # Store in memcache for aggregation to use
    if tickers:
        import aiomcache
        client = aiomcache.Client('localhost', 11211)
        
        # Store as market:tickers
        await client.set(
            b'market:tickers',
            json.dumps({'tickers': list(tickers.values())}).encode(),
            exptime=300
        )
        print("\n✅ Stored ticker data in cache at 'market:tickers'")

if __name__ == "__main__":
    asyncio.run(main())