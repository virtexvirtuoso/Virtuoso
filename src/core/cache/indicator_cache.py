#!/usr/bin/env python3
"""
Indicator Cache Module
Provides specialized caching for trading indicators with optimized TTLs and storage strategies.
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass
from enum import Enum

from .multi_tier_cache import MultiTierCacheAdapter, CacheItem, CacheLayer

logger = logging.getLogger(__name__)

class IndicatorType(Enum):
    """Indicator types with specific caching strategies"""
    TECHNICAL = "technical"
    VOLUME = "volume"
    ORDERBOOK = "orderbook"
    ORDERFLOW = "orderflow"
    SENTIMENT = "sentiment"
    PRICE_STRUCTURE = "price_structure"
    CONFLUENCE = "confluence"

@dataclass
class IndicatorCacheConfig:
    """Configuration for indicator-specific caching"""
    default_ttl: int = 30
    technical_ttl: int = 30
    orderbook_ttl: int = 2
    orderflow_ttl: int = 5
    volume_ttl: int = 60
    sentiment_ttl: int = 300
    structure_ttl: int = 300
    confluence_ttl: int = 15

    # Memory limits per indicator type
    max_items_per_type: int = 1000
    enable_compression: bool = True

class IndicatorCache:
    """
    Specialized cache for trading indicators with type-aware TTL management
    """

    def __init__(self, config: Optional[IndicatorCacheConfig] = None):
        """Initialize indicator cache with configuration"""
        self.config = config or IndicatorCacheConfig()
        self.multi_tier_cache = None
        self._initialized = False
        self._cache_hits = 0
        self._cache_misses = 0
        self._indicator_stats = {}

        logger.info("IndicatorCache initialized with config")

    async def initialize(self) -> bool:
        """Initialize the underlying multi-tier cache"""
        try:
            # Initialize multi-tier cache if not already done
            if not self.multi_tier_cache:
                self.multi_tier_cache = MultiTierCacheAdapter()
                await self.multi_tier_cache.initialize()

            self._initialized = True
            logger.info("IndicatorCache multi-tier backend initialized successfully")
            return True

        except Exception as e:
            logger.warning(f"Failed to initialize IndicatorCache backend: {e}")
            self._initialized = False
            return False

    def _get_ttl_for_indicator(self, indicator_type: str) -> int:
        """Get TTL based on indicator type"""
        ttl_mapping = {
            IndicatorType.TECHNICAL.value: self.config.technical_ttl,
            IndicatorType.ORDERBOOK.value: self.config.orderbook_ttl,
            IndicatorType.ORDERFLOW.value: self.config.orderflow_ttl,
            IndicatorType.VOLUME.value: self.config.volume_ttl,
            IndicatorType.SENTIMENT.value: self.config.sentiment_ttl,
            IndicatorType.PRICE_STRUCTURE.value: self.config.structure_ttl,
            IndicatorType.CONFLUENCE.value: self.config.confluence_ttl,
        }
        return ttl_mapping.get(indicator_type, self.config.default_ttl)

    def _build_cache_key(self, symbol: str, indicator_type: str, timeframe: str,
                        component: Optional[str] = None) -> str:
        """Build standardized cache key for indicators"""
        key_parts = ["indicator", symbol, indicator_type, timeframe]
        if component:
            key_parts.append(component)
        return ":".join(key_parts)

    async def get(self, symbol: str, indicator_type: str, timeframe: str,
                 component: Optional[str] = None) -> Optional[Any]:
        """Get cached indicator value"""
        if not self._initialized:
            await self.initialize()

        cache_key = self._build_cache_key(symbol, indicator_type, timeframe, component)

        try:
            # Try to get from multi-tier cache
            if self.multi_tier_cache:
                result, cache_layer = await self.multi_tier_cache.get(cache_key)
                if result is not None:
                    self._cache_hits += 1
                    self._update_indicator_stats(indicator_type, 'hit')
                    return result

            self._cache_misses += 1
            self._update_indicator_stats(indicator_type, 'miss')
            return None

        except Exception as e:
            logger.error(f"Error getting indicator cache for {cache_key}: {e}")
            return None

    async def get_indicator(self, indicator_type: str, symbol: str, component: str,
                           params: Dict[str, Any], compute_func) -> Any:
        """Get or compute indicator value with caching"""
        if not self._initialized:
            await self.initialize()

        # Try to get cached value first
        cached_value = await self.get(symbol, indicator_type, 'base', component)
        if cached_value is not None:
            return cached_value

        # Compute the value
        computed_value = await compute_func()

        # Cache the computed value
        await self.set(symbol, indicator_type, 'base', computed_value, component)

        return computed_value

    async def set(self, symbol: str, indicator_type: str, timeframe: str,
                 value: Any, component: Optional[str] = None) -> bool:
        """Set cached indicator value with type-specific TTL"""
        if not self._initialized:
            await self.initialize()

        cache_key = self._build_cache_key(symbol, indicator_type, timeframe, component)
        ttl = self._get_ttl_for_indicator(indicator_type)

        try:
            # Store in multi-tier cache if available
            if self.multi_tier_cache:
                await self.multi_tier_cache.set(cache_key, value, ttl)
                self._update_indicator_stats(indicator_type, 'set')
                return True

            return False

        except Exception as e:
            logger.error(f"Error setting indicator cache for {cache_key}: {e}")
            return False

    async def delete(self, symbol: str, indicator_type: str, timeframe: str,
                    component: Optional[str] = None) -> bool:
        """Delete cached indicator value"""
        if not self._initialized:
            return False

        cache_key = self._build_cache_key(symbol, indicator_type, timeframe, component)

        try:
            if self.multi_tier_cache:
                await self.multi_tier_cache.delete(cache_key)
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting indicator cache for {cache_key}: {e}")
            return False

    async def clear_indicator_type(self, indicator_type: str) -> int:
        """Clear all cached values for a specific indicator type"""
        if not self._initialized:
            return 0

        # For now, we don't have pattern-based deletion in multi-tier cache
        # This would need to be implemented if required
        logger.warning(f"Pattern-based cache clearing not implemented for {indicator_type}")
        return 0

    def _update_indicator_stats(self, indicator_type: str, operation: str):
        """Update statistics for indicator cache operations"""
        if indicator_type not in self._indicator_stats:
            self._indicator_stats[indicator_type] = {
                'hits': 0, 'misses': 0, 'sets': 0
            }

        if operation in self._indicator_stats[indicator_type]:
            self._indicator_stats[indicator_type][operation] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'total_hits': self._cache_hits,
            'total_misses': self._cache_misses,
            'hit_rate_percent': round(hit_rate, 2),
            'initialized': self._initialized,
            'indicator_stats': self._indicator_stats.copy(),
            'config': {
                'technical_ttl': self.config.technical_ttl,
                'orderbook_ttl': self.config.orderbook_ttl,
                'orderflow_ttl': self.config.orderflow_ttl,
                'volume_ttl': self.config.volume_ttl,
                'sentiment_ttl': self.config.sentiment_ttl,
                'structure_ttl': self.config.structure_ttl,
                'confluence_ttl': self.config.confluence_ttl,
            }
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check cache health status"""
        health = {
            'initialized': self._initialized,
            'backend_available': False,
            'total_operations': self._cache_hits + self._cache_misses
        }

        if self.multi_tier_cache:
            try:
                # Try a simple operation to test backend
                test_key = "health_check_test"
                await self.multi_tier_cache.set(test_key, "test", 1)
                await self.multi_tier_cache.delete(test_key)
                health['backend_available'] = True
            except Exception as e:
                health['backend_error'] = str(e)

        return health

# Global indicator cache instance
_indicator_cache_instance = None

async def get_indicator_cache() -> IndicatorCache:
    """Get singleton indicator cache instance"""
    global _indicator_cache_instance
    if _indicator_cache_instance is None:
        _indicator_cache_instance = IndicatorCache()
        await _indicator_cache_instance.initialize()
    return _indicator_cache_instance

def get_indicator_cache_sync() -> IndicatorCache:
    """Get indicator cache instance synchronously (without initialization)"""
    global _indicator_cache_instance
    if _indicator_cache_instance is None:
        _indicator_cache_instance = IndicatorCache()
    return _indicator_cache_instance