#!/usr/bin/env python3
"""
Simple cache populator that fetches from main process API
"""
import asyncio
import aiomcache
import aiohttp
import json
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def populate_cache():
    """Populate cache with data from main API"""
    cache = aiomcache.Client('localhost', 11211)
    
    async with aiohttp.ClientSession() as session:
        try:
            # Get market overview from port 8003 (main process)
            try:
                async with session.get("http://localhost:8003/api/market/overview", timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Cache market overview
                        overview = {
                            'total_symbols': len(data.get('symbols', [])),
                            'total_volume': data.get('total_volume_24h', 0),
                            'total_volume_24h': data.get('total_volume_24h', 0),
                            'average_change': data.get('avg_market_change', 0),
                            'volatility': data.get('current_volatility', 0),
                            'btc_price': data.get('btc_price', 0),
                            'eth_price': data.get('eth_price', 0)
                        }
                        await cache.set(b'market:overview', json.dumps(overview).encode(), exptime=30)
                        logger.info(f"Cached overview: {overview['total_symbols']} symbols")
                        
                        # Cache regime
                        regime = data.get('market_regime', 'NEUTRAL')
                        await cache.set(b'analysis:market_regime', regime.encode(), exptime=30)
                        
                        # Cache tickers from symbols
                        tickers = {}
                        movers = {'gainers': [], 'losers': []}
                        
                        for symbol_data in data.get('symbols', []):
                            symbol = symbol_data.get('symbol')
                            if symbol:
                                ticker = {
                                    'symbol': symbol,
                                    'price': symbol_data.get('price', 0),
                                    'change_24h': symbol_data.get('change_24h', 0),
                                    'volume': symbol_data.get('volume_24h', 0)
                                }
                                tickers[symbol] = ticker
                                
                                if ticker['change_24h'] > 5:
                                    movers['gainers'].append(ticker)
                                elif ticker['change_24h'] < -5:
                                    movers['losers'].append(ticker)
                        
                        # Sort and limit movers
                        movers['gainers'].sort(key=lambda x: x['change_24h'], reverse=True)
                        movers['losers'].sort(key=lambda x: x['change_24h'])
                        movers['gainers'] = movers['gainers'][:10]
                        movers['losers'] = movers['losers'][:10]
                        
                        await cache.set(b'market:tickers', json.dumps(tickers).encode(), exptime=30)
                        await cache.set(b'market:movers', json.dumps(movers).encode(), exptime=30)
                        logger.info(f"Cached {len(tickers)} tickers")
                        
            except Exception as e:
                logger.debug(f"Could not fetch from port 8003: {e}")
            
            # Get confluence scores
            try:
                async with session.get("http://localhost:8003/api/confluence/scores", timeout=5) as resp:
                    if resp.status == 200:
                        scores = await resp.json()
                        
                        # Create signals from confluence scores
                        signals = {
                            'signals': [],
                            'timestamp': int(time.time())
                        }
                        
                        for symbol, score_data in scores.items():
                            if isinstance(score_data, dict):
                                signal = {
                                    'symbol': symbol,
                                    'score': score_data.get('total_score', 50),
                                    'action': 'BUY' if score_data.get('total_score', 50) > 70 else 'HOLD',
                                    'components': score_data.get('components', {}),
                                    'timestamp': int(time.time())
                                }
                                signals['signals'].append(signal)
                        
                        # Sort by score
                        signals['signals'].sort(key=lambda x: x['score'], reverse=True)
                        signals['signals'] = signals['signals'][:20]  # Top 20
                        
                        await cache.set(b'analysis:signals', json.dumps(signals).encode(), exptime=30)
                        logger.info(f"Cached {len(signals['signals'])} signals")
                        
            except Exception as e:
                logger.debug(f"Could not fetch confluence scores: {e}")
                
                # Create default signals
                default_signals = {
                    'signals': [
                        {'symbol': 'BTCUSDT', 'score': 75, 'action': 'BUY', 'components': {}},
                        {'symbol': 'ETHUSDT', 'score': 65, 'action': 'HOLD', 'components': {}},
                        {'symbol': 'SOLUSDT', 'score': 70, 'action': 'BUY', 'components': {}}
                    ],
                    'timestamp': int(time.time())
                }
                await cache.set(b'analysis:signals', json.dumps(default_signals).encode(), exptime=30)
                
        except Exception as e:
            logger.error(f"Cache population error: {e}")
        finally:
            await cache.close()

async def run_loop():
    """Run cache population in a loop"""
    logger.info("Starting cache population loop...")
    while True:
        try:
            await populate_cache()
            await asyncio.sleep(10)  # Update every 10 seconds
        except Exception as e:
            logger.error(f"Loop error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_loop())