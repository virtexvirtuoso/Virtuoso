#!/usr/bin/env python3
"""
Ticker Cache Service - Updates market:tickers with complete data including high/low prices
This ensures 24h Range calculations work in confluence cards
"""

import asyncio
import json
import aiohttp
import aiomcache
import logging
from datetime import datetime
from typing import Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TickerCacheService')

class TickerCacheService:
    def __init__(self):
        self.cache_client = None
        self.update_interval = 10  # seconds
        self.running = False
        
    async def initialize(self):
        """Initialize cache connection"""
        try:
            self.cache_client = aiomcache.Client('localhost', 11211)
            logger.info("✅ Connected to memcached")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to memcached: {e}")
            return False
    
    async def fetch_tickers(self) -> Dict:
        """Fetch tickers from Bybit with all fields including high/low"""
        url = "https://api.bybit.com/v5/market/tickers"
        params = {"category": "spot"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('retCode') == 0:
                            return self.format_tickers(data['result']['list'])
        except Exception as e:
            logger.error(f"Error fetching tickers: {e}")
        
        return {}
    
    def format_tickers(self, raw_tickers: list) -> Dict:
        """Format tickers with all necessary fields"""
        tickers = {}
        
        # Sort by volume to get most active
        sorted_tickers = sorted(
            raw_tickers,
            key=lambda x: float(x.get('turnover24h', 0)),
            reverse=True
        )
        
        for item in sorted_tickers[:50]:  # Top 50 most active
            symbol = item.get('symbol', '')
            if not symbol:
                continue
                
            # Get all values (handle empty strings)
            def safe_float(val, default=0):
                try:
                    return float(val) if val and val != '' else default
                except (ValueError, TypeError):
                    return default
            
            last_price = safe_float(item.get('lastPrice', 0))
            high_price = safe_float(item.get('highPrice24h', 0))
            low_price = safe_float(item.get('lowPrice24h', 0))
            volume = safe_float(item.get('volume24h', 0))
            turnover = safe_float(item.get('turnover24h', 0))
            change_pct = safe_float(item.get('price24hPcnt', 0)) * 100
            
            # Store with all fields needed by dashboards
            tickers[symbol] = {
                'symbol': symbol,
                'price': last_price,
                'change_24h': change_pct,
                'volume': volume,
                'volume_24h': volume,
                'turnover_24h': turnover,
                'high': high_price,
                'low': low_price,
                'high_24h': high_price,  # Duplicate for compatibility
                'low_24h': low_price,    # Duplicate for compatibility
                'bid': safe_float(item.get('bid1Price', 0)),
                'ask': safe_float(item.get('ask1Price', 0)),
                'timestamp': int(datetime.now().timestamp())
            }
        
        return tickers
    
    async def update_cache(self, tickers: Dict):
        """Update the cache with new ticker data"""
        if not tickers:
            return
            
        try:
            # Store in cache with 30 second expiry
            await self.cache_client.set(
                b'market:tickers',
                json.dumps(tickers).encode(),
                exptime=30
            )
            
            # Log sample data
            if 'BTCUSDT' in tickers:
                btc = tickers['BTCUSDT']
                range_pct = 0
                if btc['high'] > 0 and btc['low'] > 0 and btc['price'] > 0:
                    range_pct = ((btc['high'] - btc['low']) / btc['price']) * 100
                
                logger.info(
                    f"✅ Updated {len(tickers)} tickers | "
                    f"BTC: ${btc['price']:,.0f} "
                    f"H:${btc['high']:,.0f} L:${btc['low']:,.0f} "
                    f"Range:{range_pct:.2f}%"
                )
            else:
                logger.info(f"✅ Updated {len(tickers)} tickers")
                
        except Exception as e:
            logger.error(f"Failed to update cache: {e}")
    
    async def run(self):
        """Main service loop"""
        if not await self.initialize():
            logger.error("Failed to initialize service")
            return
        
        self.running = True
        logger.info("🚀 Ticker Cache Service started")
        logger.info(f"📊 Updating every {self.update_interval} seconds")
        
        error_count = 0
        
        while self.running:
            try:
                # Fetch and update
                tickers = await self.fetch_tickers()
                if tickers:
                    await self.update_cache(tickers)
                    error_count = 0
                else:
                    error_count += 1
                    logger.warning(f"No data received (attempt {error_count})")
                    
                    # If too many errors, wait longer
                    if error_count > 5:
                        await asyncio.sleep(30)
                        continue
                        
            except Exception as e:
                error_count += 1
                logger.error(f"Service error: {e} (error #{error_count})")
                
                if error_count > 10:
                    logger.error("Too many errors, stopping service")
                    break
            
            # Regular interval
            await asyncio.sleep(self.update_interval)
        
        # Cleanup
        if self.cache_client:
            await self.cache_client.close()
        logger.info("Service stopped")
    
    async def stop(self):
        """Stop the service"""
        self.running = False

async def main():
    """Run the service"""
    service = TickerCacheService()
    
    # Handle shutdown
    import signal
    
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        asyncio.create_task(service.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await service.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("TICKER CACHE SERVICE")
    print("Updates market:tickers with complete data including high/low")
    print("=" * 60)
    
    asyncio.run(main())