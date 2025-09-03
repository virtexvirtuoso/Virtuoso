"""
Direct Cache Manager - Phase 3 Implementation
Ultra-fast, zero-abstraction cache access
No adapters, no layers, just direct memcached reads
"""
import json
import time
import logging
from typing import Dict, Any, Optional
import aiomcache

logger = logging.getLogger(__name__)

class DirectCache:
    """Single shared cache connection for ultra-fast access"""
    
    # Class-level shared connection
    _client: Optional[aiomcache.Client] = None
    
    @classmethod
    async def get_client(cls) -> aiomcache.Client:
        """Get or create shared cache client"""
        if cls._client is None:
            cls._client = aiomcache.Client('localhost', 11211)
            logger.info("✅ Direct cache client initialized")
        return cls._client
    
    @classmethod
    async def get(cls, key: str, default: Any = None) -> Any:
        """Direct cache read - no abstractions"""
        try:
            client = await cls.get_client()
            data = await client.get(key.encode())
            if data:
                # Handle string values (like market_regime)
                if key == 'analysis:market_regime':
                    return data.decode()
                # Handle JSON values
                try:
                    return json.loads(data.decode())
                except:
                    return data.decode()
            return default
        except Exception as e:
            logger.debug(f"Cache read error for {key}: {e}")
            return default
    
    @classmethod
    async def get_dashboard_data(cls) -> Dict[str, Any]:
        """Get all dashboard data in one shot"""
        client = await cls.get_client()
        
        # Batch fetch all keys at once
        keys = [
            b'market:overview',
            b'market:tickers', 
            b'analysis:signals',
            b'analysis:market_regime',
            b'system:alerts',
            b'market:movers'
        ]
        
        # Use multi-get for efficiency
        results = {}
        for key in keys:
            try:
                data = await client.get(key)
                if data:
                    key_str = key.decode()
                    if key_str == 'analysis:market_regime':
                        results[key_str] = data.decode()
                    else:
                        results[key_str] = json.loads(data.decode())
            except:
                pass
        
        # Build response with correct field names
        overview = results.get('market:overview', {})
        return {
            'summary': {
                'total_symbols': overview.get('total_symbols', 0),
                'total_volume': overview.get('total_volume', overview.get('total_volume_24h', 0)),  # Handle both field names
                'average_change': overview.get('average_change', 0)
            },
            'market_regime': results.get('analysis:market_regime', 'unknown'),
            'signals': results.get('analysis:signals', {}).get('signals', []),
            'alerts': results.get('system:alerts', []),
            'movers': results.get('market:movers', {
                'gainers': [],
                'losers': []
            }),
            'cache_hit': len(results) > 0,
            'timestamp': int(time.time())
        }
    
    @classmethod
    async def get_market_overview(cls) -> Dict[str, Any]:
        """Direct market overview fetch"""
        overview = await cls.get('market:overview', {})
        return {
            'active_symbols': overview.get('total_symbols', 0),
            'total_volume': overview.get('total_volume_24h', 0),
            'market_regime': await cls.get('analysis:market_regime', 'unknown'),
            'timestamp': int(time.time())
        }
    
    @classmethod
    async def get_signals(cls) -> Dict[str, Any]:
        """Direct signals fetch"""
        signals = await cls.get('analysis:signals', {})
        return {
            'signals': signals.get('signals', []),
            'count': len(signals.get('signals', [])),
            'timestamp': int(time.time())
        }
    
    @classmethod  
    async def get_movers(cls) -> Dict[str, Any]:
        """Direct market movers fetch"""
        movers = await cls.get('market:movers', {})
        return {
            'gainers': movers.get('gainers', []),
            'losers': movers.get('losers', []),
            'timestamp': int(time.time())
        }
    
    @classmethod
    async def close(cls):
        """Close cache connection"""
        if cls._client:
            await cls._client.close()
            cls._client = None