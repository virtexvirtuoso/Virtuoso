#!/usr/bin/env python3
"""Create a fixed version of DashboardCacheManager with proper persistence"""

dashboard_cache_code = '''"""
Dashboard Cache Manager - FIXED VERSION
Handles data flow from main service to all dashboard endpoints
"""
import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional
import aiomcache

logger = logging.getLogger(__name__)

class DashboardCacheManager:
    """Manages cache data for all dashboard types - FIXED VERSION"""
    
    def __init__(self):
        self.client = None
        self.connected = False
        self._connection_lock = asyncio.Lock()
        self._last_push = 0
        
    async def connect(self):
        """Connect to Memcached with robust error handling"""
        async with self._connection_lock:
            if self.connected and self.client:
                # Test existing connection
                try:
                    await self.client.set(b'test:heartbeat', b'ok', exptime=1)
                    return True
                except:
                    # Connection failed, recreate
                    self.connected = False
                    self.client = None
                
            try:
                # Create fresh client
                self.client = aiomcache.Client('localhost', 11211, pool_size=4)
                
                # Test connection
                await self.client.set(b'test:connection', b'ok', exptime=1)
                test = await self.client.get(b'test:connection')
                
                if test == b'ok':
                    self.connected = True
                    logger.info("✅ Dashboard Cache Manager connected to Memcached")
                    return True
                else:
                    raise Exception("Connection test failed")
                    
            except Exception as e:
                logger.error(f"❌ Failed to connect to Memcached: {e}")
                self.connected = False
                self.client = None
                return False
    
    async def push_complete_market_data(self, market_data: Dict[str, Any]):
        """Push comprehensive market data for all dashboards"""
        # Rate limiting - don't push more than once per 10 seconds
        now = time.time()
        if now - self._last_push < 10:
            logger.debug("Rate limiting cache push")
            return True
            
        # Ensure connection
        if not await self.connect():
            logger.error("Cannot push data - not connected to cache")
            return False
            
        try:
            timestamp = int(time.time())
            symbols_list = market_data.get('symbols', [])
            
            if not symbols_list:
                logger.warning("No symbols data to push to cache")
                return False
            
            # 1. Market Overview (used by all dashboards)
            total_volume = sum(s.get('volume_24h', s.get('volume', 0)) for s in symbols_list)
            total_change = sum(s.get('change_24h', 0) for s in symbols_list)
            avg_change = total_change / max(len(symbols_list), 1)
            
            overview = {
                "total_symbols": len(symbols_list),
                "total_volume": total_volume,
                "total_volume_24h": total_volume,
                "average_change": avg_change,
                "volatility": abs(avg_change) * 0.5,  # Simple volatility estimate
                "timestamp": timestamp
            }
            
            # Use longer expiration (5 minutes) and handle set errors
            try:
                result = await self.client.set(b'market:overview', json.dumps(overview).encode(), exptime=300)
                if result:
                    logger.debug(f"✓ Pushed market overview: {len(symbols_list)} symbols")
                else:
                    logger.warning("Failed to set market:overview")
            except Exception as e:
                logger.error(f"Error setting market:overview: {e}")
                return False
            
            # 2. Tickers (as dict for compatibility)
            tickers_dict = {}
            for symbol_data in symbols_list[:50]:  # Limit to 50 symbols
                symbol = symbol_data.get('symbol', '')
                if symbol:
                    tickers_dict[symbol] = {
                        'price': symbol_data.get('price', 0),
                        'change_24h': symbol_data.get('change_24h', 0),
                        'volume_24h': symbol_data.get('volume_24h', symbol_data.get('volume', 0)),
                        'signal': self._derive_signal(symbol_data.get('change_24h', 0))
                    }
            
            try:
                result = await self.client.set(b'market:tickers', json.dumps(tickers_dict).encode(), exptime=300)
                if result:
                    logger.debug(f"✓ Pushed tickers: {len(tickers_dict)} symbols")
            except Exception as e:
                logger.error(f"Error setting market:tickers: {e}")
            
            # 3. Movers
            try:
                sorted_by_change = sorted(symbols_list, key=lambda x: x.get('change_24h', 0))
                movers = {
                    "gainers": sorted_by_change[-5:] if len(sorted_by_change) >= 5 else sorted_by_change,
                    "losers": sorted_by_change[:5] if len(sorted_by_change) >= 5 else []
                }
                
                await self.client.set(b'market:movers', json.dumps(movers).encode(), exptime=300)
                logger.debug("✓ Pushed market movers")
            except Exception as e:
                logger.error(f"Error setting market:movers: {e}")
            
            # 4. Signals summary
            try:
                signals_summary = {
                    "signals": [
                        {
                            "symbol": s.get('symbol', ''),
                            "signal": self._derive_signal(s.get('change_24h', 0)),
                            "confidence": min(abs(s.get('change_24h', 0)) * 10, 100)
                        }
                        for s in symbols_list[:10]  # Top 10
                        if s.get('symbol')
                    ]
                }
                
                await self.client.set(b'analysis:signals', json.dumps(signals_summary).encode(), exptime=300)
                logger.debug("✓ Pushed signals summary")
            except Exception as e:
                logger.error(f"Error setting analysis:signals: {e}")
            
            # 5. Market regime
            try:
                regime = "bullish" if avg_change > 1 else "bearish" if avg_change < -1 else "neutral"
                await self.client.set(b'analysis:market_regime', regime.encode(), exptime=300)
                logger.debug(f"✓ Pushed market regime: {regime}")
            except Exception as e:
                logger.error(f"Error setting analysis:market_regime: {e}")
            
            # 6. Volume leaders
            try:
                sorted_by_volume = sorted(symbols_list, key=lambda x: x.get('volume_24h', x.get('volume', 0)), reverse=True)
                volume_leaders = sorted_by_volume[:10]
                
                await self.client.set(b'market:volume_leaders', json.dumps(volume_leaders).encode(), exptime=300)
                logger.debug("✓ Pushed volume leaders")
            except Exception as e:
                logger.error(f"Error setting market:volume_leaders: {e}")
            
            self._last_push = now
            logger.info(f"✅ Pushed comprehensive market data: {len(symbols_list)} symbols to cache")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error pushing market data to cache: {e}")
            # Reset connection on error
            self.connected = False
            self.client = None
            return False
    
    def _derive_signal(self, change_24h: float) -> str:
        """Derive trading signal from price change"""
        if change_24h > 3:
            return "strong_buy"
        elif change_24h > 1:
            return "buy"
        elif change_24h < -3:
            return "strong_sell"
        elif change_24h < -1:
            return "sell"
        else:
            return "neutral"
    
    async def get_cache_data(self, key: str) -> Any:
        """Get data from cache"""
        if not await self.connect():
            return None
            
        try:
            data = await self.client.get(key.encode())
            if data:
                if key == 'analysis:market_regime':
                    return data.decode()
                return json.loads(data.decode())
            return None
        except Exception as e:
            logger.debug(f"Cache read error for {key}: {e}")
            return None

# Singleton instance
dashboard_cache = DashboardCacheManager()
'''

# Write the fixed version
with open('dashboard_cache_manager_fixed.py', 'w') as f:
    f.write(dashboard_cache_code)

print("Fixed DashboardCacheManager created!")
print("\nKey improvements:")
print("- Longer cache expiration (5 minutes vs 1 minute)")
print("- Better error handling for each cache operation")
print("- Connection testing and recovery")
print("- Rate limiting to prevent spam")
print("- Signal derivation from price changes")
print("- Limited tickers to 50 symbols (performance)")
print("\nTo deploy:")
print("scp dashboard_cache_manager_fixed.py linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/core/dashboard_cache_manager.py")