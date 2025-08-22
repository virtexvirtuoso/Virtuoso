#!/usr/bin/env python3
"""
Cache Monitor and Fix Service
Monitors market:overview and ensures it always has the required fields
"""

import asyncio
import json
import aiomcache
import aiohttp
import numpy as np
from datetime import datetime
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheMonitorFix:
    def __init__(self):
        self.client = None
        self.btc_dominance = 57.5
        self.last_btc_update = 0
        
    async def start(self):
        """Start monitoring and fixing cache"""
        self.client = aiomcache.Client('localhost', 11211)
        logger.info("Cache Monitor Fix Service started")
        
        while True:
            try:
                await self.fix_cache()
                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(5)
    
    async def fetch_btc_dominance(self):
        """Fetch BTC dominance (cached for 5 minutes)"""
        current_time = time.time()
        if current_time - self.last_btc_update > 300:  # 5 minutes
            try:
                async with aiohttp.ClientSession() as session:
                    url = "https://api.coingecko.com/api/v3/global"
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.btc_dominance = data.get('data', {}).get('market_cap_percentage', {}).get('btc', 57.5)
                            self.last_btc_update = current_time
                            logger.info(f"Updated BTC dominance: {self.btc_dominance:.1f}%")
            except Exception as e:
                logger.error(f"Error fetching BTC dominance: {e}")
        
        return self.btc_dominance
    
    async def fix_cache(self):
        """Check and fix market:overview cache"""
        try:
            # Get current overview
            overview_data = await self.client.get(b'market:overview')
            if not overview_data:
                return
            
            overview = json.loads(overview_data.decode())
            needs_update = False
            
            # Check if required fields are missing or zero
            if not overview.get('trend_strength') or overview.get('trend_strength') == 0:
                # Calculate trend strength
                avg_change = overview.get('average_change', 0)
                volatility = overview.get('volatility', 1)
                
                if volatility == 0:
                    volatility = 1
                
                raw_strength = abs(avg_change) / volatility
                if raw_strength == 0:
                    trend_strength = 0
                else:
                    trend_strength = min(100, 50 * (1 + np.log10(1 + raw_strength)))
                
                overview['trend_strength'] = round(trend_strength, 1)
                needs_update = True
                logger.info(f"Fixed trend_strength: {overview['trend_strength']}%")
            
            # Check BTC dominance
            if not overview.get('btc_dominance') or overview.get('btc_dominance') == 0:
                btc_dom = await self.fetch_btc_dominance()
                overview['btc_dominance'] = round(btc_dom, 1)
                needs_update = True
                logger.info(f"Fixed btc_dominance: {overview['btc_dominance']}%")
            
            # Check current volatility
            if overview.get('current_volatility') is None:
                overview['current_volatility'] = overview.get('volatility', 0)
                overview['avg_volatility'] = 20.0
                needs_update = True
                logger.info(f"Fixed current_volatility: {overview['current_volatility']}%")
            
            # Update cache if needed
            if needs_update:
                await self.client.set(b'market:overview', json.dumps(overview).encode(), exptime=120)
                logger.debug("Cache updated with fixed values")
                
        except Exception as e:
            logger.error(f"Error fixing cache: {e}")

async def main():
    monitor = CacheMonitorFix()
    await monitor.start()

if __name__ == "__main__":
    asyncio.run(main())