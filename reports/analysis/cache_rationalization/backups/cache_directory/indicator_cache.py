#!/usr/bin/env python3
"""
Specialized cache layer for indicator calculations
Extends UnifiedCache with indicator-specific optimizations
"""

from src.core.cache.unified_cache import UnifiedCache
from typing import Any, Callable, Optional, Dict
import hashlib
import json
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class IndicatorCache(UnifiedCache):
    """
    Specialized cache for technical indicator calculations
    Provides intelligent TTL management and cache key generation
    """
    
    # TTL configurations for different indicator types (seconds)
    TTL_CONFIG = {
        'technical': 120,     # 2 minutes for technical indicators (RSI, MACD, etc) - increased from 30s
        'orderbook': 2,       # 2 seconds for orderbook-based indicators (real-time)
        'orderflow': 5,       # 5 seconds for orderflow indicators
        'volume': 120,        # 2 minutes for volume indicators - increased from 60s
        'sentiment': 300,     # 5 minutes for sentiment indicators
        'structure': 300,     # 5 minutes for price structure patterns
        'confluence': 30,     # 30 seconds for confluence scores - increased from 15s
        # MTF (Multi-TimeFrame) indicators cache longer as they're more expensive to compute
        'technical_mtf': 300, # 5 minutes for MTF technical indicators
        'williams_r_mtf': 300,# 5 minutes for Williams %R MTF
        'atr_mtf': 300,       # 5 minutes for ATR MTF
    }
    
    # Cache hit metrics by indicator type
    def __init__(self, host: str = '127.0.0.1', port: int = 11211):
        """Initialize indicator cache with enhanced metrics"""
        super().__init__(host, port)
        
        # Track metrics per indicator type
        self.indicator_metrics = {
            'technical': {'hits': 0, 'misses': 0, 'compute_time_saved': 0},
            'orderbook': {'hits': 0, 'misses': 0, 'compute_time_saved': 0},
            'orderflow': {'hits': 0, 'misses': 0, 'compute_time_saved': 0},
            'volume': {'hits': 0, 'misses': 0, 'compute_time_saved': 0},
            'sentiment': {'hits': 0, 'misses': 0, 'compute_time_saved': 0},
            'structure': {'hits': 0, 'misses': 0, 'compute_time_saved': 0},
        }
        
        # Track commonly accessed indicators for warming
        self.access_patterns = {}
        
    async def get_indicator(self, 
                          indicator_type: str,
                          symbol: str,
                          component: str,
                          params: Optional[Dict] = None,
                          compute_func: Optional[Callable] = None,
                          ttl: Optional[int] = None) -> Any:
        """
        Get cached indicator value or compute if missing
        
        Args:
            indicator_type: Type of indicator (technical, orderbook, etc)
            symbol: Trading symbol (e.g., BTCUSDT)
            component: Specific indicator component (e.g., rsi, macd)
            params: Parameters for the indicator calculation
            compute_func: Async function to compute the indicator
            ttl: Override TTL for this specific cache entry
            
        Returns:
            Cached or computed indicator value
        """
        # Generate cache key
        cache_key = self._generate_indicator_key(indicator_type, symbol, component, params)
        
        # Track access pattern
        self._track_access(cache_key, indicator_type)
        
        # Use configured TTL or override
        if ttl is None:
            ttl = self.TTL_CONFIG.get(indicator_type, 30)
        
        # Try to get from cache
        try:
            cached = await self.get(cache_key)
            if cached is not None:
                self.indicator_metrics[indicator_type]['hits'] += 1
                if hasattr(self.metrics, 'get'):
                    self.metrics['indicator_hits'] = self.metrics.get('indicator_hits', 0) + 1
                else:
                    self.metrics.indicator_hits = getattr(self.metrics, 'indicator_hits', 0) + 1
                # Only log cache hits at TRACE level to reduce log spam
                if logger.isEnabledFor(logging.DEBUG - 5):  # TRACE level
                    logger.log(logging.DEBUG - 5, f"Indicator cache HIT: {cache_key}")
                return cached
        except Exception as e:
            logger.warning(f"Cache get error for {cache_key}: {e}")
        
        # Cache miss - compute if function provided
        self.indicator_metrics[indicator_type]['misses'] += 1
        if hasattr(self.metrics, 'get'):
            self.metrics['indicator_misses'] = self.metrics.get('indicator_misses', 0) + 1
        else:
            self.metrics.indicator_misses = getattr(self.metrics, 'indicator_misses', 0) + 1
        
        if compute_func:
            # Log cache misses at INFO level only for expensive indicators, DEBUG for others
            if indicator_type in ['technical_mtf', 'williams_r_mtf', 'atr_mtf']:
                logger.info(f"Computing expensive indicator (cache miss): {cache_key}")
            else:
                logger.debug(f"Indicator cache MISS: {cache_key}, computing...")
            
            # Measure computation time
            start_time = asyncio.get_event_loop().time()
            value = await compute_func()
            compute_time = asyncio.get_event_loop().time() - start_time
            
            # Track time saved for future hits
            self.indicator_metrics[indicator_type]['compute_time_saved'] += compute_time
            
            # Cache the computed value
            await self.set(cache_key, value, ttl)
            
            return value
        
        return None
    
    def _generate_indicator_key(self, indicator_type: str, symbol: str, 
                               component: str, params: Optional[Dict] = None) -> str:
        """
        Generate standardized cache key for indicators
        
        Format: indicator:{type}:{symbol}:{component}:{params_hash}
        """
        if params:
            # Filter out timestamp-based parameters that cause unnecessary cache misses
            stable_params = {k: v for k, v in params.items() 
                           if k not in ['timestamp', 'current_time', 'request_id']}
            
            if stable_params:
                # Create deterministic hash of stable parameters only
                params_str = json.dumps(stable_params, sort_keys=True)
                params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
                return f"indicator:{indicator_type}:{symbol}:{component}:{params_hash}"
        
        return f"indicator:{indicator_type}:{symbol}:{component}"
    
    def _track_access(self, cache_key: str, indicator_type: str):
        """Track access patterns for cache warming"""
        now = datetime.now()
        hour_key = now.strftime("%Y%m%d_%H")
        
        if hour_key not in self.access_patterns:
            self.access_patterns[hour_key] = {}
        
        if cache_key not in self.access_patterns[hour_key]:
            self.access_patterns[hour_key][cache_key] = {
                'count': 0,
                'type': indicator_type,
                'last_access': now
            }
        
        self.access_patterns[hour_key][cache_key]['count'] += 1
        self.access_patterns[hour_key][cache_key]['last_access'] = now
    
    async def invalidate_symbol(self, symbol: str):
        """
        Invalidate all cached indicators for a symbol
        Note: Memcached doesn't support pattern deletion, so we track keys
        """
        # In production, would maintain a set of keys per symbol
        # For now, rely on TTL expiration
        logger.info(f"Invalidation requested for symbol: {symbol}")
        
    async def get_indicator_metrics(self) -> Dict:
        """Get detailed metrics for indicator caching"""
        total_hits = sum(m['hits'] for m in self.indicator_metrics.values())
        total_misses = sum(m['misses'] for m in self.indicator_metrics.values())
        total_requests = total_hits + total_misses
        
        metrics = {
            'overall': {
                'hit_rate': (total_hits / total_requests * 100) if total_requests > 0 else 0,
                'total_hits': total_hits,
                'total_misses': total_misses,
                'total_requests': total_requests,
                'time_saved_seconds': sum(m['compute_time_saved'] for m in self.indicator_metrics.values())
            },
            'by_type': {}
        }
        
        # Calculate per-type metrics
        for ind_type, type_metrics in self.indicator_metrics.items():
            type_total = type_metrics['hits'] + type_metrics['misses']
            if type_total > 0:
                metrics['by_type'][ind_type] = {
                    'hit_rate': (type_metrics['hits'] / type_total * 100),
                    'hits': type_metrics['hits'],
                    'misses': type_metrics['misses'],
                    'compute_time_saved': type_metrics['compute_time_saved'],
                    'avg_time_saved_per_hit': (
                        type_metrics['compute_time_saved'] / type_metrics['hits']
                        if type_metrics['hits'] > 0 else 0
                    )
                }
        
        return metrics
    
    async def get_indicators_batch(self, requests: list) -> Dict[str, Any]:
        """
        Batch retrieve multiple indicators efficiently
        
        Args:
            requests: List of dicts with keys: indicator_type, symbol, component, params, compute_func, ttl
            
        Returns:
            Dictionary mapping cache keys to values
        """
        results = {}
        compute_tasks = []
        
        for req in requests:
            cache_key = self._generate_indicator_key(
                req['indicator_type'], 
                req['symbol'], 
                req['component'], 
                req.get('params')
            )
            
            # Try cache first
            try:
                cached = await self.get(cache_key)
                if cached is not None:
                    results[cache_key] = cached
                    continue
            except Exception as e:
                logger.warning(f"Batch cache get error for {cache_key}: {e}")
            
            # Schedule computation for misses
            if req.get('compute_func'):
                compute_tasks.append({
                    'key': cache_key,
                    'func': req['compute_func'],
                    'ttl': req.get('ttl', self.TTL_CONFIG.get(req['indicator_type'], 30)),
                    'type': req['indicator_type']
                })
        
        # Compute all misses in parallel
        if compute_tasks:
            computed_values = await asyncio.gather(
                *[task['func']() for task in compute_tasks],
                return_exceptions=True
            )
            
            for task, value in zip(compute_tasks, computed_values):
                if not isinstance(value, Exception):
                    results[task['key']] = value
                    # Cache the computed value
                    await self.set(task['key'], value, task['ttl'])
                else:
                    logger.error(f"Batch compute failed for {task['key']}: {value}")
        
        return results
    
    async def warmup_common_indicators(self, symbols: list, compute_funcs: Dict):
        """
        Pre-warm cache with commonly used indicators based on access patterns
        
        Args:
            symbols: List of symbols to warm up
            compute_funcs: Dictionary of compute functions by indicator type
        """
        warmup_count = 0
        
        # Identify frequently accessed indicators from patterns
        frequent_indicators = self._get_frequent_indicators()
        
        # Warm up MTF indicators first (they're most expensive)
        mtf_components = ['williams_r_mtf', 'atr_mtf', 'rsi_mtf', 'macd_mtf']
        
        for symbol in symbols:
            # Warm up MTF indicators
            for component in mtf_components:
                indicator_type = component if component in self.TTL_CONFIG else 'technical_mtf'
                if indicator_type in compute_funcs or 'technical' in compute_funcs:
                    try:
                        func = compute_funcs.get(indicator_type, {}).get(component) or \
                               compute_funcs.get('technical', {}).get(component)
                        if func:
                            await self.get_indicator(
                                indicator_type=indicator_type,
                                symbol=symbol,
                                component=component,
                                compute_func=func
                            )
                            warmup_count += 1
                    except Exception as e:
                        logger.error(f"Warmup failed for {symbol}:{component}: {e}")
            
            # Warm up regular technical indicators
            if 'technical' in compute_funcs:
                for component in ['rsi', 'macd', 'atr', 'bollinger_bands', 'ema']:
                    try:
                        await self.get_indicator(
                            indicator_type='technical',
                            symbol=symbol,
                            component=component,
                            compute_func=compute_funcs['technical'].get(component)
                        )
                        warmup_count += 1
                    except Exception as e:
                        logger.error(f"Warmup failed for {symbol}:{component}: {e}")
        
        logger.info(f"Cache warmup complete: {warmup_count} indicators pre-computed")
        return warmup_count
    
    def _get_frequent_indicators(self) -> list:
        """Get list of frequently accessed indicators from access patterns"""
        frequent = []
        current_hour = datetime.now().strftime("%Y%m%d_%H")
        
        if current_hour in self.access_patterns:
            # Get indicators accessed more than 5 times in current hour
            for key, pattern in self.access_patterns[current_hour].items():
                if pattern['count'] > 5:
                    frequent.append({
                        'key': key,
                        'type': pattern['type'],
                        'count': pattern['count']
                    })
        
        return sorted(frequent, key=lambda x: x['count'], reverse=True)
    
    def get_cache_recommendations(self) -> Dict:
        """
        Analyze access patterns and provide caching recommendations
        """
        recommendations = []
        
        # Find frequently accessed indicators
        current_hour = datetime.now().strftime("%Y%m%d_%H")
        if current_hour in self.access_patterns:
            sorted_patterns = sorted(
                self.access_patterns[current_hour].items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )
            
            # Top 10 most accessed
            top_accessed = sorted_patterns[:10]
            
            for key, pattern in top_accessed:
                if pattern['count'] > 10:  # More than 10 accesses per hour
                    recommendations.append({
                        'key': key,
                        'type': pattern['type'],
                        'access_count': pattern['count'],
                        'recommendation': 'Consider longer TTL or pre-warming'
                    })
        
        return {
            'recommendations': recommendations,
            'total_unique_keys': len(self.access_patterns.get(current_hour, {})),
            'analysis_period': current_hour
        }

# Global instance for easy access
_indicator_cache = None

def get_indicator_cache() -> IndicatorCache:
    """Get or create global indicator cache instance"""
    global _indicator_cache
    if _indicator_cache is None:
        _indicator_cache = IndicatorCache()
    return _indicator_cache