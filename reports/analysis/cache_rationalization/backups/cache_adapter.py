"""
Cache Adapter for Existing Dashboard Endpoints
Intercepts existing API calls and serves from cache
Provides backward compatibility with zero frontend changes
"""
import json
import time
import logging
from typing import Dict, Any, Optional, List
import aiomcache

logger = logging.getLogger(__name__)

class CacheAdapter:
    """
    Adapter to make existing dashboard endpoints use cache
    Drop-in replacement - no frontend changes needed
    """
    
    _instance = None
    _cache_client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def get_cache(self):
        """Get or create cache client"""
        if self._cache_client is None:
            self._cache_client = aiomcache.Client('localhost', 11211)
        return self._cache_client
    
    async def _get_from_cache(self, key: bytes, default: Any = None) -> Any:
        """Safe cache getter with fallback"""
        try:
            cache = await self.get_cache()
            data = await cache.get(key)
            if data:
                if key == b'analysis:market_regime':
                    return data.decode()
                return json.loads(data.decode())
            return default
        except Exception as e:
            logger.debug(f"Cache miss for {key}: {e}")
            return default
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """
        Replacement for /api/dashboard/market-overview
        Returns data from cache instead of calling services
        """
        overview = await self._get_from_cache(b'market:overview', {})
        analysis = await self._get_from_cache(b'analysis:results', {})
        
        # Return complete overview with all metrics
        return {
            'active_symbols': overview.get('total_symbols', overview.get('symbols_analyzed', 0)),
            'total_volume': overview.get('total_volume_24h', overview.get('total_volume', 0)),
            'market_regime': overview.get('market_regime') or await self._get_from_cache(b'analysis:market_regime', 'unknown'),
            'trend_strength': overview.get('trend_strength', 0),  # Now properly included
            'current_volatility': overview.get('current_volatility', 0),
            'avg_volatility': overview.get('avg_volatility', 20),
            'btc_dominance': overview.get('btc_dominance', 0),
            'volatility': overview.get('current_volatility', analysis.get('volatility', {}).get('std_deviation', 0) if analysis else 0),
            'market_breadth': overview.get('market_breadth', {}),
            'timestamp': int(time.time()),
            'source': 'cache'
        }
    
    async def get_market_movers(self) -> Dict[str, Any]:
        """
        Replacement for /api/market/movers
        Returns top gainers and losers from cache
        """
        gainers = await self._get_from_cache(b'market:top_gainers', [])
        losers = await self._get_from_cache(b'market:top_losers', [])
        
        return {
            'gainers': gainers[:10] if gainers else [],
            'losers': losers[:10] if losers else [],
            'timestamp': int(time.time()),
            'source': 'cache'
        }
    
    async def get_dashboard_overview(self) -> Dict[str, Any]:
        """
        Replacement for /api/dashboard/overview
        Aggregates all dashboard data from cache
        """
        overview = await self._get_from_cache(b'market:overview', {})
        analysis = await self._get_from_cache(b'analysis:results', {})
        tickers = await self._get_from_cache(b'market:tickers', {})
        
        # Calculate summary statistics
        total_symbols = len(tickers) if tickers else overview.get('total_symbols', 0)
        
        return {
            'summary': {
                'total_symbols': total_symbols,
                'total_volume': overview.get('total_volume_24h', 0),
                'average_change': overview.get('average_change_24h', 0),
                'timestamp': int(time.time())
            },
            'market_regime': await self._get_from_cache(b'analysis:market_regime', 'unknown'),
            'momentum': analysis.get('momentum', {}) if analysis else {},
            'volatility': analysis.get('volatility', {}) if analysis else {},
            'source': 'cache'
        }
    
    async def get_dashboard_symbols(self) -> Dict[str, Any]:
        """
        Replacement for /api/dashboard/symbols
        Returns symbol data from cache
        """
        tickers = await self._get_from_cache(b'market:tickers', {})
        
        # Format for existing dashboard
        symbols = []
        if tickers:
            for symbol, data in list(tickers.items())[:50]:  # Limit to 50
                symbols.append({
                    'symbol': symbol,
                    'price': data.get('price', 0),
                    'change_24h': data.get('change_24h', 0),
                    'volume': data.get('volume', 0),
                    'bid': data.get('bid', data.get('price', 0)),
                    'ask': data.get('ask', data.get('price', 0)),
                    'timestamp': data.get('timestamp', int(time.time()))
                })
        
        return {
            'symbols': symbols,
            'count': len(symbols),
            'timestamp': int(time.time()),
            'source': 'cache'
        }
    
    async def get_signals(self) -> Dict[str, Any]:
        """
        Replacement for /api/dashboard/signals
        Returns analysis-based signals from cache
        """
        # First try to get signals directly from enhanced service
        signals_data = await self._get_from_cache(b'analysis:signals', {})
        if signals_data and 'signals' in signals_data:
            return signals_data
        
        # Fallback to old analysis results
        analysis = await self._get_from_cache(b'analysis:results', {})
        momentum = analysis.get('momentum', {}) if analysis else {}
        
        # Generate signals based on analysis
        signals = []
        
        # Strong gainers as buy signals
        for symbol in momentum.get('strong_gainers', [])[:5]:
            signals.append({
                'symbol': symbol,
                'type': 'BUY',
                'strength': 'strong',
                'reason': 'Strong momentum',
                'timestamp': int(time.time())
            })
        
        # Strong losers as sell signals
        for symbol in momentum.get('strong_losers', [])[:5]:
            signals.append({
                'symbol': symbol,
                'type': 'SELL',
                'strength': 'strong',
                'reason': 'Negative momentum',
                'timestamp': int(time.time())
            })
        
        return {
            'signals': signals,
            'count': len(signals),
            'timestamp': int(time.time()),
            'source': 'cache'
        }
    
    async def get_market_analysis(self) -> Dict[str, Any]:
        """
        Replacement for /api/dashboard/market-analysis
        Returns complete analysis from cache
        """
        analysis = await self._get_from_cache(b'analysis:results', {})
        overview = await self._get_from_cache(b'market:overview', {})
        
        return {
            'market_stats': analysis.get('market_stats', {}) if analysis else {},
            'momentum': analysis.get('momentum', {}) if analysis else {},
            'volatility': analysis.get('volatility', {}) if analysis else {},
            'breadth': analysis.get('breadth', {}) if analysis else {},
            'volume_analysis': analysis.get('volume_analysis', {}) if analysis else {},
            'market_regime': await self._get_from_cache(b'analysis:market_regime', 'unknown'),
            'overview': overview,
            'timestamp': int(time.time()),
            'source': 'cache'
        }
    
    async def get_alpha_opportunities(self) -> Dict[str, Any]:
        """
        Replacement for /api/alpha/opportunities
        Identifies opportunities from cache data
        """
        gainers = await self._get_from_cache(b'market:top_gainers', [])
        analysis = await self._get_from_cache(b'analysis:results', {})
        
        opportunities = []
        
        # High momentum opportunities
        if gainers:
            for g in gainers[:5]:
                if g.get('change_24h', 0) > 10:
                    opportunities.append({
                        'symbol': g['symbol'],
                        'type': 'momentum',
                        'score': min(g['change_24h'] / 10, 10),  # Score 0-10
                        'change_24h': g['change_24h'],
                        'volume': g.get('volume', 0),
                        'reason': f"Strong momentum: +{g['change_24h']:.1f}%"
                    })
        
        # Add volatility opportunities
        if analysis and 'volatility' in analysis:
            if analysis['volatility'].get('level') == 'high':
                opportunities.append({
                    'type': 'volatility',
                    'score': 7,
                    'reason': 'High volatility environment - trading opportunities'
                })
        
        return {
            'opportunities': opportunities,
            'count': len(opportunities),
            'market_regime': await self._get_from_cache(b'analysis:market_regime', 'unknown'),
            'timestamp': int(time.time()),
            'source': 'cache'
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Check cache and data freshness
        """
        try:
            cache = await self.get_cache()
            
            # Test cache
            await cache.set(b'health:test', b'ok', exptime=5)
            test = await cache.get(b'health:test')
            cache_ok = (test == b'ok')
            
            # Check data freshness
            health = await self._get_from_cache(b'market:health', {})
            last_update = health.get('last_update', 0) if health else 0
            data_age = int(time.time() - last_update) if last_update else -1
            
            return {
                'status': 'healthy' if cache_ok and data_age < 60 else 'degraded',
                'cache_connected': cache_ok,
                'data_age_seconds': data_age,
                'data_fresh': data_age < 30 if data_age > 0 else False,
                'timestamp': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'error',
                'cache_connected': False,
                'error': str(e)
            }


# Global instance
cache_adapter = CacheAdapter()