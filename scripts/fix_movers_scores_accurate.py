#!/usr/bin/env python3
"""Fix market movers to show accurate data - only real confluence scores for analyzed symbols."""

import asyncio
import aiomcache
import json
import logging
import time
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_movers_with_accurate_scores():
    """Update movers to only show real confluence scores for analyzed symbols."""
    try:
        # Get real market movers from Bybit
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.bybit.com/v5/market/tickers?category=linear&limit=500') as response:
                data = await response.json()
        
        tickers = data['result']['list']
        
        all_symbols = []
        for ticker in tickers:
            symbol = ticker['symbol']
            if 'USDT' in symbol:
                change = float(ticker['price24hPcnt']) * 100
                price = float(ticker['lastPrice'])
                volume = float(ticker.get('turnover24h', 0))
                
                symbol_data = {
                    'symbol': symbol,
                    'price': price,
                    'change_24h': change,
                    'volume_24h': volume
                }
                
                # DON'T add fake confluence scores!
                # Only symbols we actually analyze should have scores
                
                all_symbols.append(symbol_data)
        
        # Sort to find real movers
        sorted_by_change = sorted(all_symbols, key=lambda x: x['change_24h'])
        
        # Get actual losers and gainers
        losers = [s for s in sorted_by_change if s['change_24h'] < 0][:5]
        gainers = [s for s in sorted(all_symbols, key=lambda x: x['change_24h'], reverse=True) if s['change_24h'] > 0][:5]
        
        # Connect to cache
        client = aiomcache.Client('localhost', 11211, pool_size=2)
        
        # Get REAL confluence scores for top symbols only
        confluence_cache = {}
        top_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'LINKUSDT', 
                      'DOGEUSDT', 'ADAUSDT', 'SUIUSDT', 'BNBUSDT', 'AVAXUSDT']
        
        for symbol in top_symbols:
            key = f'confluence:{symbol}'.encode()
            data = await client.get(key)
            if data:
                try:
                    score_data = json.loads(data.decode())
                    confluence_cache[symbol] = score_data.get('score', None)
                except:
                    pass
        
        # Add real confluence scores ONLY for symbols we analyze
        for gainer in gainers:
            symbol = gainer['symbol']
            if symbol in confluence_cache:
                gainer['confluence_score'] = confluence_cache[symbol]
                gainer['has_analysis'] = True
            else:
                # Don't add fake scores - these symbols aren't analyzed
                gainer['has_analysis'] = False
                # Optionally set to None or don't include at all
                # gainer['confluence_score'] = None
        
        for loser in losers:
            symbol = loser['symbol']
            if symbol in confluence_cache:
                loser['confluence_score'] = confluence_cache[symbol]
                loser['has_analysis'] = True
            else:
                loser['has_analysis'] = False
        
        # Update movers in cache
        movers = {
            'gainers': gainers,
            'losers': losers,
            'timestamp': int(time.time()),
            'note': 'Confluence scores only available for actively analyzed symbols'
        }
        
        await client.set(
            b'market:movers',
            json.dumps(movers).encode(),
            exptime=300
        )
        
        logger.info("✅ Updated movers with accurate data:")
        logger.info(f"   Gainers: {[g['symbol'] + (' [analyzed]' if g.get('has_analysis') else '') for g in gainers]}")
        logger.info(f"   Losers: {[l['symbol'] + (' [analyzed]' if l.get('has_analysis') else '') for l in losers]}")
        
        await client.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to update movers: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(fix_movers_with_accurate_scores())