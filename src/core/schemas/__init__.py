"""
Unified Cache Schemas
=====================

This module defines the data contracts between the monitoring service
and web service for all cache keys. All services MUST use these schemas
when reading/writing cache data.

Benefits:
- Type safety: Catch schema errors at development time
- Single source of truth: One place to update schemas
- Validation: Automatic data validation on read/write
- Documentation: Self-documenting cache structure
- Evolution: Versioned schemas for migrations

Usage Example:
    from src.core.schemas import MarketOverviewSchema

    # Writing to cache (monitoring service)
    schema = MarketOverviewSchema(
        total_symbols=15,
        trend_strength=75.0,
        btc_dominance=58.5,
        total_volume_24h=45000000000
    )
    await cache.set(schema.CACHE_KEY, schema.to_dict())

    # Reading from cache (web service)
    data = await cache.get('market:overview')
    schema = MarketOverviewSchema.from_dict(data)
    if schema.validate():
        print(f"Symbols: {schema.total_symbols}")
        print(f"Trend: {schema.trend_strength}")
"""

from .base import CacheSchema, SchemaVersion
from .market_overview import MarketOverviewSchema
from .signals import SignalsSchema, SignalSchema, SignalComponentsSchema
from .market_breadth import MarketBreadthSchema
from .market_movers import MarketMoversSchema

__version__ = "1.0.0"

__all__ = [
    # Base classes
    'CacheSchema',
    'SchemaVersion',

    # Schema classes
    'MarketOverviewSchema',
    'SignalsSchema',
    'SignalSchema',
    'SignalComponentsSchema',
    'MarketBreadthSchema',
    'MarketMoversSchema',
]
