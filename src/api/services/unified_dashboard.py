"""
Unified Dashboard Data Pipeline
Single source of truth for both desktop and mobile dashboards with optimized caching.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import aiohttp
from datetime import datetime, timezone

# Import our cache components
from src.core.cache.key_generator import CacheKeyGenerator
from src.core.cache.batch_operations import BatchCacheManager
from src.core.cache.ttl_strategy import TTLStrategy, DataType, UpdateFrequency

logger = logging.getLogger(__name__)

@dataclass
class DataSource:
    """Configuration for a data source"""
    name: str
    url: str
    timeout: float
    cache_key: str
    ttl: int
    required: bool = True
    fallback_data: Optional[Dict[str, Any]] = None

class UnifiedDashboardService:
    """Single pipeline for both desktop and mobile dashboards with intelligent caching"""
    
    def __init__(self, cache_adapter, batch_manager: Optional[BatchCacheManager] = None):
        self.cache_adapter = cache_adapter
        self.batch_manager = batch_manager or BatchCacheManager(cache_adapter)
        self.ttl_strategy = TTLStrategy()
        
        # Data source configurations
        self.data_sources = {
            'market_overview': DataSource(
                name='market_overview',
                url='http://localhost:8002/api/dashboard-cached/market-overview',
                timeout=2.0,
                cache_key=CacheKeyGenerator.market_overview(),
                ttl=60,
                fallback_data={'market_regime': 'NEUTRAL', 'volatility': 0, 'trend_strength': 0}
            ),
            'market_breadth': DataSource(
                name='market_breadth',
                url='http://localhost:8002/api/dashboard-cached/market-breadth',
                timeout=2.0,
                cache_key=CacheKeyGenerator.market_breadth(),
                ttl=30,
                fallback_data={'up_count': 0, 'down_count': 0, 'breadth_percentage': 50.0}
            ),
            'confluence_scores': DataSource(
                name='confluence_scores',
                url='http://localhost:8002/api/dashboard-cached/confluence-scores',
                timeout=3.0,
                cache_key=CacheKeyGenerator.confluence_scores('all'),
                ttl=30,
                fallback_data={'scores': []}
            ),
            'alerts': DataSource(
                name='alerts',
                url='http://localhost:8001/api/monitoring/alerts',
                timeout=1.5,
                cache_key=CacheKeyGenerator.alerts_active(),
                ttl=120,
                required=False,
                fallback_data={'alerts': []}
            ),
            'performance': DataSource(
                name='performance',
                url='http://localhost:8001/api/monitoring/performance',
                timeout=1.0,
                cache_key=CacheKeyGenerator.performance_metrics(),
                ttl=30,
                required=False,
                fallback_data={'cpu_usage': 0, 'memory_usage': 0}
            )
        }
        
        self._stats = {
            'requests_served': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'data_source_failures': 0,
            'avg_response_time': 0
        }
    
    async def get_comprehensive_data(self, view_type: str = "desktop", symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Unified data fetching with view-specific filtering and intelligent caching"""
        start_time = time.time()
        
        try:
            # Generate cache keys for batch operation
            cache_keys = [source.cache_key for source in self.data_sources.values()]
            
            # Batch fetch from cache
            cached_data = await self.batch_manager.multi_get(cache_keys)
            
            # Identify missing data
            missing_sources = []
            for source_name, source in self.data_sources.items():
                if source.cache_key not in cached_data or cached_data[source.cache_key] is None:
                    missing_sources.append(source)
                    self._stats['cache_misses'] += 1
                else:
                    self._stats['cache_hits'] += 1
            
            # Fetch missing data in parallel
            fresh_data = {}
            if missing_sources:
                fresh_data = await self._fetch_missing_data(missing_sources)
                
                # Cache fresh data
                if fresh_data:
                    cache_data = {
                        source.cache_key: fresh_data.get(source.name)
                        for source in missing_sources
                        if fresh_data.get(source.name) is not None
                    }
                    if cache_data:
                        await self.batch_manager.multi_set(cache_data)
            
            # Combine cached and fresh data
            complete_data = self._combine_data_sources(cached_data, fresh_data)
            
            # Apply view-specific optimizations
            if view_type == "mobile":
                complete_data = await self._optimize_for_mobile(complete_data, symbols)
            elif view_type == "desktop":
                complete_data = self._optimize_for_desktop(complete_data)
            
            # Add metadata
            complete_data['_metadata'] = {
                'view_type': view_type,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'response_time_ms': round((time.time() - start_time) * 1000, 2),
                'cache_performance': {
                    'hits': len(cache_keys) - len(missing_sources),
                    'misses': len(missing_sources),
                    'hit_rate': round(((len(cache_keys) - len(missing_sources)) / len(cache_keys)) * 100, 1)
                },
                'data_sources_used': len(self.data_sources),
                'external_calls_made': len(missing_sources)
            }
            
            # Update statistics
            self._update_stats(time.time() - start_time)
            
            return complete_data
            
        except Exception as e:
            logger.error(f"Error in unified data pipeline: {e}")
            return self._get_fallback_data(view_type)
    
    async def _fetch_missing_data(self, missing_sources: List[DataSource]) -> Dict[str, Any]:
        """Fetch missing data from external sources in parallel"""
        fetch_tasks = []
        
        for source in missing_sources:
            task = self._fetch_from_source(source)
            fetch_tasks.append((source.name, task))
        
        # Execute all fetches in parallel
        results = await asyncio.gather(
            *[task for _, task in fetch_tasks], 
            return_exceptions=True
        )
        
        # Process results
        fresh_data = {}
        for i, (source_name, _) in enumerate(fetch_tasks):
            result = results[i]
            
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch {source_name}: {result}")
                self._stats['data_source_failures'] += 1
                # Use fallback data if available
                source = next(s for s in missing_sources if s.name == source_name)
                if source.fallback_data:
                    fresh_data[source_name] = source.fallback_data
            else:
                fresh_data[source_name] = result
        
        return fresh_data
    
    async def _fetch_from_source(self, source: DataSource) -> Dict[str, Any]:
        """Fetch data from a single source with timeout protection"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(source.url, timeout=source.timeout) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise Exception(f"HTTP {response.status}")
        
        except Exception as e:
            if source.required:
                logger.error(f"Required source {source.name} failed: {e}")
            else:
                logger.debug(f"Optional source {source.name} failed: {e}")
            raise
    
    def _combine_data_sources(self, cached_data: Dict[str, Any], fresh_data: Dict[str, Any]) -> Dict[str, Any]:
        """Combine cached and fresh data into unified structure"""
        combined = {}
        
        # Process each data source
        for source_name, source in self.data_sources.items():
            # Get data from cache or fresh fetch
            data = cached_data.get(source.cache_key)
            if data is None and source_name in fresh_data:
                data = fresh_data[source_name]
            
            # Use fallback if still no data and source is required
            if data is None and source.required and source.fallback_data:
                data = source.fallback_data
            
            if data:
                combined[source_name] = data
        
        return combined
    
    async def _optimize_for_mobile(self, data: Dict[str, Any], symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Optimize data payload for mobile consumption"""
        mobile_data = {
            'market_overview': self._compress_market_overview(data.get('market_overview', {})),
            'market_breadth': data.get('market_breadth', {}),
            'top_signals': self._get_top_signals_mobile(data.get('confluence_scores', {}), limit=15),
            'alerts': self._compress_alerts_mobile(data.get('alerts', {})),
            'performance': self._compress_performance_mobile(data.get('performance', {}))
        }
        
        # Add top movers with external API integration
        mobile_data['top_movers'] = await self._get_top_movers_mobile()
        
        return mobile_data
    
    def _optimize_for_desktop(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize data payload for desktop consumption"""
        return {
            'overview': data.get('market_overview', {}),
            'breadth': data.get('market_breadth', {}),
            'signals': self._format_signals_desktop(data.get('confluence_scores', {})),
            'alerts': data.get('alerts', {}),
            'performance': data.get('performance', {}),
            'system_status': self._generate_system_status(data)
        }
    
    def _compress_market_overview(self, overview: Dict[str, Any]) -> Dict[str, Any]:
        """Compress market overview for mobile"""
        return {
            'regime': overview.get('market_regime', 'NEUTRAL'),
            'trend': round(overview.get('trend_strength', 0), 1),
            'volatility': round(overview.get('current_volatility', overview.get('volatility', 0)), 1),
            'btc_dominance': round(overview.get('btc_dominance', 0), 1),
            'volume_24h': overview.get('total_volume_24h', 0)
        }
    
    def _get_top_signals_mobile(self, confluence_data: Dict[str, Any], limit: int = 15) -> List[Dict[str, Any]]:
        """Extract top signals optimized for mobile display"""
        scores = confluence_data.get('scores', [])
        if not scores:
            return []
        
        # Sort by confluence score and take top signals
        sorted_signals = sorted(scores, key=lambda x: x.get('score', 0), reverse=True)[:limit]
        
        # Compress signal data for mobile
        mobile_signals = []
        for signal in sorted_signals:
            mobile_signals.append({
                'symbol': signal.get('symbol', ''),
                'score': round(signal.get('score', 0), 1),
                'price': signal.get('price', 0),
                'change_24h': round(signal.get('change_24h', 0), 2),
                'volume': signal.get('volume_24h', 0),
                'components': {
                    k: round(v, 1) for k, v in signal.get('components', {}).items()
                }
            })
        
        return mobile_signals
    
    def _compress_alerts_mobile(self, alerts_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compress alerts for mobile"""
        alerts = alerts_data.get('alerts', [])
        
        return {
            'total': len(alerts),
            'critical': len([a for a in alerts if a.get('priority') == 'critical']),
            'recent': alerts[:5]  # Only show 5 most recent
        }
    
    def _compress_performance_mobile(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compress performance metrics for mobile"""
        return {
            'cpu': round(performance_data.get('cpu_usage', 0), 1),
            'memory': round(performance_data.get('memory_usage', 0), 1),
            'latency': round(performance_data.get('api_latency', 0), 1)
        }
    
    async def _get_top_movers_mobile(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get top market movers optimized for mobile"""
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.bybit.com/v5/market/tickers?category=linear"
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('retCode') == 0:
                            tickers = data['result']['list']
                            
                            # Process for top movers
                            movers = []
                            for ticker in tickers:
                                try:
                                    symbol = ticker['symbol']
                                    if symbol.endswith('USDT') and 'PERP' not in symbol:
                                        change_24h = float(ticker['price24hPcnt']) * 100
                                        turnover_24h = float(ticker['turnover24h'])
                                        
                                        if turnover_24h > 1000000:  # $1M minimum
                                            movers.append({
                                                'symbol': symbol,
                                                'change': round(change_24h, 2),
                                                'price': float(ticker['lastPrice']),
                                                'volume': float(ticker['volume24h'])
                                            })
                                except:
                                    continue
                            
                            # Sort and get top gainers/losers
                            gainers = [m for m in movers if m['change'] > 0]
                            losers = [m for m in movers if m['change'] < 0]
                            
                            gainers.sort(key=lambda x: x['change'], reverse=True)
                            losers.sort(key=lambda x: x['change'])
                            
                            return {
                                'gainers': gainers[:5],
                                'losers': losers[:5]
                            }
        except Exception as e:
            logger.warning(f"Failed to fetch top movers: {e}")
        
        return {'gainers': [], 'losers': []}
    
    def _format_signals_desktop(self, confluence_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format signals for desktop display with full details"""
        scores = confluence_data.get('scores', [])
        return sorted(scores, key=lambda x: x.get('score', 0), reverse=True)
    
    def _generate_system_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate system status summary"""
        return {
            'data_sources': len(self.data_sources),
            'cache_performance': {
                'hit_rate': round((self._stats['cache_hits'] / max(1, self._stats['cache_hits'] + self._stats['cache_misses'])) * 100, 1),
                'total_requests': self._stats['cache_hits'] + self._stats['cache_misses']
            },
            'service_health': {
                'market_data': 'healthy' if data.get('market_overview') else 'degraded',
                'confluence': 'healthy' if data.get('confluence_scores') else 'degraded',
                'alerts': 'healthy' if data.get('alerts') else 'optional',
                'performance': 'healthy' if data.get('performance') else 'optional'
            }
        }
    
    def _get_fallback_data(self, view_type: str) -> Dict[str, Any]:
        """Generate fallback data when all else fails"""
        fallback = {
            'market_overview': {'market_regime': 'UNKNOWN', 'volatility': 0},
            'alerts': {'total': 0, 'critical': 0, 'recent': []},
            'confluence_scores': [],
            'top_movers': {'gainers': [], 'losers': []},
            '_metadata': {
                'view_type': view_type,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'fallback_mode',
                'message': 'Using fallback data due to service unavailability'
            }
        }
        
        return fallback
    
    def _update_stats(self, response_time: float):
        """Update internal statistics"""
        self._stats['requests_served'] += 1
        
        # Update average response time
        current_avg = self._stats['avg_response_time']
        total_requests = self._stats['requests_served']
        self._stats['avg_response_time'] = ((current_avg * (total_requests - 1)) + (response_time * 1000)) / total_requests
    
    async def warm_cache(self) -> Dict[str, bool]:
        """Warm cache with fresh data from all sources"""
        logger.info("Starting cache warming for unified dashboard")
        
        # Fetch all data sources
        fresh_data = await self._fetch_missing_data(list(self.data_sources.values()))
        
        # Prepare cache data
        cache_data = {}
        for source_name, source in self.data_sources.items():
            if source_name in fresh_data:
                cache_data[source.cache_key] = fresh_data[source_name]
        
        # Batch set cache data
        if cache_data:
            results = await self.batch_manager.multi_set(cache_data)
            logger.info(f"Cache warmed: {sum(results.values())}/{len(results)} keys cached successfully")
            return results
        
        return {}
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics and performance metrics"""
        return {
            'service': 'unified_dashboard',
            'statistics': self._stats,
            'data_sources': {
                source.name: {
                    'url': source.url,
                    'timeout': source.timeout,
                    'ttl': source.ttl,
                    'required': source.required
                }
                for source in self.data_sources.values()
            },
            'cache_performance': self.batch_manager.get_stats() if hasattr(self.batch_manager, 'get_stats') else {},
            'ttl_strategy': self.ttl_strategy.get_cache_strategy_summary()
        }