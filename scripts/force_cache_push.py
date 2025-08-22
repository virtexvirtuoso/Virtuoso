#!/usr/bin/env python3
"""Force push market data to cache for testing"""

import asyncio
import json
import time
import aiomcache
import random

async def push_test_data():
    """Push test market data to cache"""
    
    print("Pushing test market data to cache...")
    
    client = aiomcache.Client('localhost', 11211, pool_size=2)
    
    # Generate test symbols
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'XRPUSDT', 
               'DOGEUSDT', 'LINKUSDT', 'MATICUSDT', 'ADAUSDT', 'DOTUSDT']
    
    # Create symbol data
    symbols_data = []
    for symbol in symbols:
        price = random.uniform(0.1, 50000)
        change = random.uniform(-10, 10)
        volume = random.uniform(1000000, 100000000)
        
        symbols_data.append({
            'symbol': symbol,
            'price': price,
            'change_24h': change,
            'volume_24h': volume,
            'turnover_24h': price * volume
        })
    
    timestamp = int(time.time())
    
    # 1. Market Overview
    overview = {
        "total_symbols": len(symbols_data),
        "total_volume": sum(s['volume_24h'] for s in symbols_data),
        "total_volume_24h": sum(s['volume_24h'] for s in symbols_data),
        "average_change": sum(s['change_24h'] for s in symbols_data) / len(symbols_data),
        "volatility": random.uniform(0.5, 3.0),
        "timestamp": timestamp
    }
    
    result = await client.set(b'market:overview', json.dumps(overview).encode(), exptime=300)
    print(f"market:overview: {result} - {overview['total_symbols']} symbols")
    
    # 2. Tickers (as dict)
    tickers = {}
    for s in symbols_data:
        tickers[s['symbol']] = {
            'price': s['price'],
            'change_24h': s['change_24h'],
            'volume_24h': s['volume_24h']
        }
    
    result = await client.set(b'market:tickers', json.dumps(tickers).encode(), exptime=300)
    print(f"market:tickers: {result} - {len(tickers)} symbols")
    
    # 3. Movers
    sorted_by_change = sorted(symbols_data, key=lambda x: x['change_24h'])
    movers = {
        "gainers": sorted_by_change[-5:],
        "losers": sorted_by_change[:5]
    }
    
    result = await client.set(b'market:movers', json.dumps(movers).encode(), exptime=300)
    print(f"market:movers: {result}")
    
    # 4. Signals
    signals = {
        "signals": [
            {"symbol": s['symbol'], "signal": "buy" if s['change_24h'] > 2 else "sell" if s['change_24h'] < -2 else "neutral"}
            for s in symbols_data[:5]
        ]
    }
    
    result = await client.set(b'analysis:signals', json.dumps(signals).encode(), exptime=300)
    print(f"analysis:signals: {result}")
    
    # 5. Market regime
    avg_change = overview['average_change']
    regime = "bullish" if avg_change > 2 else "bearish" if avg_change < -2 else "neutral"
    
    result = await client.set(b'analysis:market_regime', regime.encode(), exptime=300)
    print(f"analysis:market_regime: {result} - {regime}")
    
    # 6. Volume leaders
    sorted_by_volume = sorted(symbols_data, key=lambda x: x['volume_24h'], reverse=True)
    volume_leaders = sorted_by_volume[:5]
    
    result = await client.set(b'market:volume_leaders', json.dumps(volume_leaders).encode(), exptime=300)
    print(f"market:volume_leaders: {result}")
    
    await client.close()
    print("\n✓ Data pushed successfully!")
    print(f"Total volume: ${overview['total_volume']:,.0f}")
    print(f"Average change: {overview['average_change']:.2f}%")
    print(f"Market regime: {regime}")

async def verify_data():
    """Verify the pushed data"""
    print("\nVerifying cached data...")
    print("-" * 30)
    
    client = aiomcache.Client('localhost', 11211, pool_size=2)
    
    keys = [b'market:overview', b'market:tickers', b'market:movers', 
            b'analysis:signals', b'analysis:market_regime', b'market:volume_leaders']
    
    for key in keys:
        data = await client.get(key)
        if data:
            if key == b'analysis:market_regime':
                print(f"{key.decode()}: {data.decode()}")
            else:
                parsed = json.loads(data.decode())
                if isinstance(parsed, dict):
                    print(f"{key.decode()}: {len(parsed)} keys")
                elif isinstance(parsed, list):
                    print(f"{key.decode()}: {len(parsed)} items")
        else:
            print(f"{key.decode()}: empty")
    
    await client.close()

async def main():
    await push_test_data()
    await verify_data()

if __name__ == "__main__":
    asyncio.run(main())