#!/usr/bin/env python3
"""
Fix to ensure DashboardCacheManager properly connects and writes to memcached
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_fixed_cache_manager():
    """Create a fixed version of DashboardCacheManager that properly connects"""
    
    code = '''"""
Dashboard Cache Manager - Fixed version that ensures connection
"""
import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional
import aiomcache

logger = logging.getLogger(__name__)

class DashboardCacheManager:
    """Manages cache data for all dashboards - FIXED VERSION"""
    
    def __init__(self):
        self.client = None
        self.connected = False
        self._connection_lock = asyncio.Lock()
        
    async def connect(self):
        """Connect to Memcached with proper error handling"""
        async with self._connection_lock:
            if self.connected and self.client:
                return True
                
            try:
                # Always create a fresh client
                self.client = aiomcache.Client('localhost', 11211, pool_size=4)
                
                # Test the connection
                await self.client.set(b'test:connection', b'ok', exptime=1)
                test = await self.client.get(b'test:connection')
                
                if test == b'ok':
                    self.connected = True
                    logger.info("✅ Dashboard Cache Manager connected to Memcached")
                    return True
                else:
                    logger.error("❌ Memcached connection test failed")
                    self.connected = False
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Failed to connect to Memcached: {e}")
                self.connected = False
                self.client = None
                return False
    
    async def push_complete_market_data(self, market_data: Dict[str, Any]):
        """Push comprehensive market data for all dashboards"""
        # Ensure connection
        if not self.connected or not self.client:
            connected = await self.connect()
            if not connected:
                logger.error("Cannot push data - not connected to cache")
                return False
            
        try:
            timestamp = int(time.time())
            
            # 1. Market Overview (used by all dashboards)
            symbols_list = market_data.get('symbols', [])
            overview = {
                "total_symbols": len(symbols_list),
                "total_volume": sum(s.get('volume', 0) for s in symbols_list),
                "total_volume_24h": sum(s.get('volume_24h', 0) for s in symbols_list),
                "average_change": sum(s.get('change_24h', 0) for s in symbols_list) / max(len(symbols_list), 1),
                "timestamp": timestamp
            }
            
            # Write with explicit error handling
            result = await self.client.set(b'market:overview', json.dumps(overview).encode(), exptime=60)
            if result:
                logger.debug(f"Pushed market overview: {len(symbols_list)} symbols")
            
            # 2. Tickers (convert list to dict for compatibility)
            tickers_dict = {}
            for symbol_data in symbols_list[:100]:
                symbol = symbol_data.get('symbol', '')
                if symbol:
                    tickers_dict[symbol] = {
                        'price': symbol_data.get('price', 0),
                        'change_24h': symbol_data.get('change_24h', 0),
                        'volume_24h': symbol_data.get('volume_24h', 0)
                    }
            
            result = await self.client.set(b'market:tickers', json.dumps(tickers_dict).encode(), exptime=60)
            if result:
                logger.debug(f"Pushed tickers: {len(tickers_dict)} symbols")
            
            # 3. Movers
            sorted_by_change = sorted(symbols_list, key=lambda x: x.get('change_24h', 0))
            movers = {
                "gainers": sorted_by_change[-5:] if len(sorted_by_change) >= 5 else sorted_by_change,
                "losers": sorted_by_change[:5] if len(sorted_by_change) >= 5 else []
            }
            
            if movers['gainers'] or movers['losers']:
                await self.client.set(b'market:movers', json.dumps(movers).encode(), exptime=60)
            
            # 4. Volume Leaders
            sorted_by_volume = sorted(symbols_list, key=lambda x: x.get('volume_24h', 0), reverse=True)
            volume_leaders = sorted_by_volume[:10]
            
            if volume_leaders:
                await self.client.set(b'market:volume_leaders', json.dumps(volume_leaders).encode(), exptime=60)
            
            # 5. Statistics
            stats = {
                "avg_price": sum(s.get('price', 0) for s in symbols_list) / max(len(symbols_list), 1),
                "avg_volume": sum(s.get('volume_24h', 0) for s in symbols_list) / max(len(symbols_list), 1),
                "positive_count": len([s for s in symbols_list if s.get('change_24h', 0) > 0]),
                "negative_count": len([s for s in symbols_list if s.get('change_24h', 0) < 0]),
                "neutral_count": len([s for s in symbols_list if s.get('change_24h', 0) == 0]),
                "timestamp": timestamp
            }
            await self.client.set(b'market:statistics', json.dumps(stats).encode(), exptime=60)
            
            logger.info(f"✅ Pushed comprehensive market data: {len(symbols_list)} symbols to cache")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error pushing market data to cache: {e}")
            # Reset connection on error
            self.connected = False
            self.client = None
            return False
    
    async def get_cache_data(self, key: str) -> Any:
        """Get data from cache"""
        if not self.connected or not self.client:
            await self.connect()
            
        if not self.client:
            return None
            
        try:
            data = await self.client.get(key.encode())
            if data:
                return json.loads(data.decode())
            return None
        except Exception as e:
            logger.debug(f"Cache read error for {key}: {e}")
            return None

# Singleton instance
dashboard_cache = DashboardCacheManager()
'''
    
    # Write the fixed version
    output_path = '/home/linuxuser/trading/Virtuoso_ccxt/src/core/dashboard_cache_manager.py'
    print(f"Creating fixed cache manager at: {output_path}")
    
    with open('fix_cache_manager.py', 'w') as f:
        f.write(code)
    
    print("Fixed cache manager created locally")
    return 'fix_cache_manager.py'

if __name__ == '__main__':
    file_path = create_fixed_cache_manager()
    print(f"Fixed file created: {file_path}")
    print("\nTo deploy:")
    print(f"scp {file_path} linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/core/dashboard_cache_manager.py")