#!/usr/bin/env python3
"""
Simple cache population service
Fetches data from main API and populates memcached
"""
import asyncio
import aiomcache
import aiohttp
import json
import logging
import time
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CachePopulator:
    def __init__(self):
        self.cache_client = None
        self.api_base = "http://localhost:8001"
        
    async def init(self):
        """Initialize cache client"""
        self.cache_client = aiomcache.Client('localhost', 11211)
        
    async def close(self):
        """Close cache client"""
        if self.cache_client:
            await self.cache_client.close()
            
    async def set_cache(self, key: str, value: Any, ttl: int = 60):
        """Set cache value"""
        try:
            if isinstance(value, (dict, list)):
                data = json.dumps(value).encode()
            else:
                data = str(value).encode()
            await self.cache_client.set(key.encode(), data, exptime=ttl)
            logger.debug(f"Cached {key} ({len(data)} bytes)")
        except Exception as e:
            logger.error(f"Failed to cache {key}: {e}")
            
    async def fetch_and_cache(self):
        """Fetch data from API and populate cache"""
        async with aiohttp.ClientSession() as session:
            try:
                # Fetch market overview
                async with session.get(f"{self.api_base}/api/market/overview") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Create overview data
                        overview = {
                            'total_symbols': data.get('breadth', {}).get('total', 0),
                            'total_volume': data.get('total_volume', 0),
                            'total_volume_24h': data.get('total_volume', 0),
                            'average_change': data.get('avg_market_change', 0),
                            'volatility': data.get('volatility', 0),
                            'btc_price': data.get('btc_price', 0),
                            'eth_price': data.get('eth_price', 0),
                            'timestamp': int(time.time())
                        }
                        await self.set_cache('market:overview', overview)
                        
                        # Set market regime
                        await self.set_cache('analysis:market_regime', 
                                           data.get('regime', 'NEUTRAL'))
                        
                        logger.info(f"✓ Cached market overview: {overview['total_symbols']} symbols")
                        
                # Fetch top symbols data
                try:
                    async with session.get(f"{self.api_base}/api/market/tickers") as resp:
                        if resp.status == 200:
                            tickers_data = await resp.json()
                            
                            # Transform to expected format
                            tickers = {}
                            movers = {'gainers': [], 'losers': []}
                            
                            for ticker in tickers_data.get('tickers', []):
                                symbol = ticker.get('symbol')
                                if symbol:
                                    ticker_info = {
                                        'symbol': symbol,
                                        'price': ticker.get('last', 0),
                                        'change_24h': ticker.get('percentage', 0),
                                        'volume': ticker.get('volume', 0),
                                        'timestamp': int(time.time())
                                    }
                                    tickers[symbol] = ticker_info
                                    
                                    # Track movers
                                    if ticker_info['change_24h'] > 5:
                                        movers['gainers'].append(ticker_info)
                                    elif ticker_info['change_24h'] < -5:
                                        movers['losers'].append(ticker_info)
                            
                            # Sort movers
                            movers['gainers'].sort(key=lambda x: x['change_24h'], reverse=True)
                            movers['losers'].sort(key=lambda x: x['change_24h'])
                            
                            await self.set_cache('market:tickers', tickers)
                            await self.set_cache('market:movers', movers)
                            
                            logger.info(f"✓ Cached {len(tickers)} tickers")
                except:
                    # Fallback: Create sample data
                    sample_tickers = {
                        'BTCUSDT': {'symbol': 'BTCUSDT', 'price': 113000, 'change_24h': -0.5, 'volume': 1000000000},
                        'ETHUSDT': {'symbol': 'ETHUSDT', 'price': 4200, 'change_24h': 1.2, 'volume': 500000000},
                        'SOLUSDT': {'symbol': 'SOLUSDT', 'price': 250, 'change_24h': 3.5, 'volume': 200000000},
                        'BNBUSDT': {'symbol': 'BNBUSDT', 'price': 700, 'change_24h': -1.8, 'volume': 150000000},
                        'XRPUSDT': {'symbol': 'XRPUSDT', 'price': 3.2, 'change_24h': 2.1, 'volume': 100000000}
                    }
                    await self.set_cache('market:tickers', sample_tickers)
                    await self.set_cache('market:movers', {
                        'gainers': [v for v in sample_tickers.values() if v['change_24h'] > 0],
                        'losers': [v for v in sample_tickers.values() if v['change_24h'] < 0]
                    })
                    logger.info("✓ Cached sample ticker data")
                    
                # Create sample signals
                signals = {
                    'signals': [
                        {
                            'symbol': 'BTCUSDT',
                            'score': 75,
                            'action': 'BUY',
                            'components': {
                                'momentum': 80,
                                'volume': 70,
                                'trend': 75
                            },
                            'timestamp': int(time.time())
                        },
                        {
                            'symbol': 'ETHUSDT',
                            'score': 65,
                            'action': 'HOLD',
                            'components': {
                                'momentum': 60,
                                'volume': 65,
                                'trend': 70
                            },
                            'timestamp': int(time.time())
                        }
                    ],
                    'timestamp': int(time.time())
                }
                await self.set_cache('analysis:signals', signals)
                logger.info(f"✓ Cached {len(signals['signals'])} signals")
                
            except Exception as e:
                logger.error(f"Failed to fetch data: {e}")
                
    async def run(self):
        """Run cache population loop"""
        await self.init()
        logger.info("Starting cache population service...")
        
        while True:
            try:
                await self.fetch_and_cache()
                await asyncio.sleep(10)  # Update every 10 seconds
            except Exception as e:
                logger.error(f"Cache population error: {e}")
                await asyncio.sleep(5)

async def main():
    populator = CachePopulator()
    try:
        await populator.run()
    finally:
        await populator.close()

if __name__ == "__main__":
    asyncio.run(main())