"""
Phase 2 Cache Architecture Module

Complete cache optimization system providing:
- L1: In-memory (ultra-fast, 10-30s TTL)
- L2: Memcached (fast, 30-90s TTL)  
- L3: Redis (persistent, 300s TTL)
- Intelligent cache warming with market awareness
- Comprehensive performance monitoring and alerting

Expected Performance Impact: +100% through multi-tier architecture and intelligent warming
"""

from .multi_tier_cache import (
    MultiTierCacheAdapter,
    DirectCacheAdapter,
    CacheLayer,
    CacheStats
)

# Intelligent warmer module removed - functionality integrated elsewhere
# from .intelligent_warmer import (
#     IntelligentCacheWarmer,
#     MarketPeriod,
#     VolatilityLevel,
#     start_intelligent_cache_warming
# )

from .cache_monitoring import (
    CachePerformanceMonitor,
    PerformanceAlert,
    AlertLevel,
    MetricType
)

from .indicator_cache import (
    IndicatorCache,
    IndicatorCacheConfig,
    IndicatorType,
    get_indicator_cache,
    get_indicator_cache_sync
)

__all__ = [
    # Multi-tier cache
    'MultiTierCacheAdapter',
    'DirectCacheAdapter',
    'CacheLayer',
    'CacheStats',

    # Intelligent warming - REMOVED (functionality integrated elsewhere)
    # 'IntelligentCacheWarmer',
    # 'MarketPeriod',
    # 'VolatilityLevel',
    # 'start_intelligent_cache_warming',

    # Performance monitoring
    'CachePerformanceMonitor',
    'PerformanceAlert',
    'AlertLevel',
    'MetricType',

    # Indicator cache
    'IndicatorCache',
    'IndicatorCacheConfig',
    'IndicatorType',
    'get_indicator_cache',
    'get_indicator_cache_sync'
]