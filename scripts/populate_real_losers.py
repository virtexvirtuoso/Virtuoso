#!/usr/bin/env python3
"""Populate dashboard with REAL losers from Bybit market data."""

import asyncio
import aiomcache
import json
import logging
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_real_market_movers():
    """Get real gainers and losers from Bybit API."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.bybit.com/v5/market/tickers?category=linear&limit=500') as response:
                data = await response.json()
                
        tickers = data['result']['list']
        
        losers = []
        gainers = []
        
        for ticker in tickers:
            symbol = ticker['symbol']
            if 'USDT' in symbol:
                change = float(ticker['price24hPcnt']) * 100
                price = float(ticker['lastPrice'])
                volume = float(ticker.get('turnover24h', 0))
                
                ticker_data = {
                    'symbol': symbol,
                    'price': price,
                    'change_24h': change,
                    'volume_24h': volume
                }
                
                if change < 0:
                    losers.append(ticker_data)
                elif change > 0:
                    gainers.append(ticker_data)
        
        # Sort by change
        losers.sort(key=lambda x: x['change_24h'])
        gainers.sort(key=lambda x: x['change_24h'], reverse=True)
        
        # Get top 5 of each
        top_losers = losers[:5]
        top_gainers = gainers[:5]
        
        logger.info(f"Found {len(losers)} total losers, {len(gainers)} total gainers")
        logger.info(f"Top loser: {top_losers[0]['symbol']} at {top_losers[0]['change_24h']:.2f}%")
        logger.info(f"Top gainer: {top_gainers[0]['symbol']} at {top_gainers[0]['change_24h']:.2f}%")
        
        return top_gainers, top_losers
        
    except Exception as e:
        logger.error(f"Failed to get market movers: {e}")
        return [], []

async def update_cache_with_real_movers():
    """Update memcached with real market movers."""
    try:
        # Get real movers
        gainers, losers = await get_real_market_movers()
        
        if not gainers or not losers:
            logger.error("Failed to get real market movers")
            return False
        
        # Connect to memcached
        client = aiomcache.Client('localhost', 11211, pool_size=2)
        
        # Prepare movers data
        movers = {
            'gainers': gainers,
            'losers': losers,
            'timestamp': int(time.time())
        }
        
        # Push to cache
        await client.set(
            b'market:movers',
            json.dumps(movers).encode(),
            exptime=300  # 5 minute expiry
        )
        
        logger.info(f"✅ Pushed REAL market movers to cache:")
        logger.info(f"   Top gainers: {[g['symbol'] for g in gainers]}")
        logger.info(f"   Top losers: {[l['symbol'] for l in losers]}")
        
        await client.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to update cache: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import time
    asyncio.run(update_cache_with_real_movers())