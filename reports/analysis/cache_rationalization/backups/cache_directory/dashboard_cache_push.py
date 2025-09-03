"""Dashboard cache push functionality to populate memcached with market data."""

import asyncio
import aiomcache
import json
import logging
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class DashboardCachePusher:
    """Handles pushing dashboard data to memcached."""
    
    def __init__(self):
        self._client = None
        self._last_push = 0
        self._push_interval = 10  # Push every 10 seconds
        
    async def _get_client(self):
        """Get or create memcached client."""
        if self._client is None:
            self._client = aiomcache.Client('localhost', 11211, pool_size=2)
        return self._client
    
    async def push_symbols_data(self, symbols_data: List[Dict[str, Any]]) -> bool:
        """Push symbols data to cache.
        
        Args:
            symbols_data: List of symbol dictionaries with price, change, volume, etc.
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = await self._get_client()
            
            # Prepare tickers data
            tickers = {}
            for symbol_data in symbols_data:
                symbol = symbol_data.get('symbol', '')
                if symbol:
                    tickers[symbol] = {
                        'price': symbol_data.get('price', 0),
                        'change_24h': symbol_data.get('change_24h', 0),
                        'volume_24h': symbol_data.get('volume_24h', 0),
                        'confluence_score': symbol_data.get('confluence_score', 0),
                        'signal': symbol_data.get('signal', 'neutral')
                    }
            
            # Push tickers
            await client.set(
                b'market:tickers',
                json.dumps(tickers).encode(),
                exptime=300  # 5 minute expiry
            )
            
            # Calculate and push overview
            total_volume = sum(s.get('volume_24h', 0) for s in symbols_data)
            avg_change = sum(s.get('change_24h', 0) for s in symbols_data) / max(len(symbols_data), 1)
            
            overview = {
                'total_symbols': len(symbols_data),
                'total_volume': total_volume,
                'total_volume_24h': total_volume,
                'average_change': avg_change,
                'volatility': abs(avg_change) * 0.5,  # Simple volatility estimate
                'timestamp': int(time.time())
            }
            
            await client.set(
                b'market:overview',
                json.dumps(overview).encode(),
                exptime=300
            )
            
            # Push signals
            signals = {
                'signals': symbols_data[:10],  # Top 10 for signals
                'timestamp': int(time.time())
            }
            
            await client.set(
                b'analysis:signals',
                json.dumps(signals).encode(),
                exptime=300
            )
            
            # Determine and push market regime
            if avg_change > 2:
                regime = 'bullish'
            elif avg_change < -2:
                regime = 'bearish'
            else:
                regime = 'neutral'
            
            await client.set(
                b'analysis:market_regime',
                regime.encode(),
                exptime=300
            )
            
            # Push top movers
            sorted_by_change = sorted(symbols_data, key=lambda x: x.get('change_24h', 0), reverse=True)
            gainers = [s for s in sorted_by_change if s.get('change_24h', 0) > 0][:5]
            losers = [s for s in sorted_by_change if s.get('change_24h', 0) < 0][-5:]
            
            movers = {
                'gainers': gainers,
                'losers': losers,
                'timestamp': int(time.time())
            }
            
            await client.set(
                b'market:movers',
                json.dumps(movers).encode(),
                exptime=300
            )
            
            logger.debug(f"Pushed {len(symbols_data)} symbols to cache")
            self._last_push = time.time()
            return True
            
        except Exception as e:
            logger.error(f"Failed to push symbols to cache: {e}")
            return False
    
    async def push_confluence_score(self, symbol: str, score: float, analysis: Dict[str, Any]) -> bool:
        """Push confluence score for a symbol.
        
        Args:
            symbol: Symbol name
            score: Confluence score
            analysis: Full analysis data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = await self._get_client()
            
            data = {
                'symbol': symbol,
                'score': score,
                'analysis': analysis,
                'timestamp': int(time.time())
            }
            
            key = f'confluence:{symbol}'.encode()
            await client.set(
                key,
                json.dumps(data).encode(),
                exptime=300
            )
            
            logger.debug(f"Pushed confluence score {score} for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to push confluence score for {symbol}: {e}")
            return False
    
    async def push_complete_market_data(self, market_data: Dict[str, Any]) -> bool:
        """Push complete market data to cache.
        
        Args:
            market_data: Complete market data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract symbols data if present
            if 'symbols' in market_data:
                await self.push_symbols_data(market_data['symbols'])
            
            # Push any additional market data
            client = await self._get_client()
            
            if 'alerts' in market_data:
                await client.set(
                    b'market:alerts',
                    json.dumps(market_data['alerts']).encode(),
                    exptime=300
                )
            
            if 'opportunities' in market_data:
                await client.set(
                    b'market:opportunities',
                    json.dumps(market_data['opportunities']).encode(),
                    exptime=300
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to push complete market data: {e}")
            return False
    
    async def close(self):
        """Close the cache connection."""
        if self._client:
            await self._client.close()
            self._client = None

# Global instance
_cache_pusher = None

def get_cache_pusher() -> DashboardCachePusher:
    """Get the global cache pusher instance."""
    global _cache_pusher
    if _cache_pusher is None:
        _cache_pusher = DashboardCachePusher()
    return _cache_pusher

# Convenience function for backward compatibility
async def push_complete_market_data(market_data: Dict[str, Any]) -> bool:
    """Push complete market data using the global pusher."""
    pusher = get_cache_pusher()
    return await pusher.push_complete_market_data(market_data)