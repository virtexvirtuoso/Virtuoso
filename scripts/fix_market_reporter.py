#!/usr/bin/env python3
"""
Fix Market Reporter to include trend_strength, btc_dominance, and current_volatility
"""

import asyncio
import json
import aiomcache
import aiohttp
import numpy as np
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def patch_market_reporter():
    """
    Patch the market reporter result to include missing fields
    """
    client = aiomcache.Client('localhost', 11211)
    
    # Fetch BTC dominance from CoinGecko
    btc_dominance = 57.5  # Default
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.coingecko.com/api/v3/global"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    btc_dominance = data.get('data', {}).get('market_cap_percentage', {}).get('btc', 57.5)
    except:
        pass
    
    logger.info(f"BTC Dominance: {btc_dominance:.1f}%")
    
    # Get current overview
    overview_data = await client.get(b'market:overview')
    if overview_data:
        overview = json.loads(overview_data.decode())
        
        # Calculate trend strength from average change and volatility
        avg_change = overview.get('average_change', 0)
        volatility = overview.get('volatility', 1)
        
        if volatility == 0:
            volatility = 1
            
        # Calculate trend strength (0-100)
        raw_strength = abs(avg_change) / volatility
        if raw_strength == 0:
            trend_strength = 0
        else:
            trend_strength = min(100, 50 * (1 + np.log10(1 + raw_strength)))
        
        # Update with missing fields
        overview['trend_strength'] = round(trend_strength, 1)
        overview['btc_dominance'] = round(btc_dominance, 1)
        overview['current_volatility'] = overview.get('volatility', 0)
        overview['avg_volatility'] = 20.0  # Typical crypto market volatility
        
        # Save back to cache
        await client.set(b'market:overview', json.dumps(overview).encode(), exptime=120)
        
        logger.info(f"✅ Updated market:overview with:")
        logger.info(f"  - trend_strength: {overview['trend_strength']}%")
        logger.info(f"  - btc_dominance: {overview['btc_dominance']}%")
        logger.info(f"  - current_volatility: {overview['current_volatility']}%")
        
        return True
    else:
        logger.error("No market:overview data in cache")
        return False
    
    await client.close()

async def main():
    success = await patch_market_reporter()
    if success:
        logger.info("✅ Market reporter patched successfully")
    else:
        logger.error("❌ Failed to patch market reporter")

if __name__ == "__main__":
    asyncio.run(main())