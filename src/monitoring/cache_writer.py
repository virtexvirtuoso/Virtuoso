"""
Monitoring Cache Writer - Unified Schema Implementation
========================================================

This module provides a clean interface for the monitoring system to write
data to cache using the unified schema system, replacing the old direct
cache access pattern that caused schema mismatches.

Key Features:
- Uses unified schemas (MarketOverviewSchema, SignalsSchema, etc.)
- Automatic data validation before caching
- Consistent field names across monitoring and web services
- Migration helpers for transforming old monitoring format

Architecture:
    Monitoring → MonitoringCacheWriter → Unified Schemas → Cache

This solves the schema mismatch issue where monitoring wrote:
    {'total_symbols_monitored': 15, 'bullish_signals': 8}
But dashboard expected:
    {'total_symbols': 15, 'trend_strength': 75}
"""

import asyncio
import json
import logging
import time
import statistics
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

# Import unified schemas
from ..core.schemas import (
    MarketOverviewSchema,
    SignalsSchema,
    MarketBreadthSchema,
    MarketMoversSchema
)

logger = logging.getLogger(__name__)


class MonitoringCacheWriter:
    """
    Unified cache writer for monitoring system.

    Uses structured schemas to ensure data compatibility between
    monitoring service and web service consumers.

    Benefits:
    - Type-safe data structures (Python dataclasses)
    - Automatic validation before caching
    - Consistent field names
    - Built-in versioning for future migrations
    - Reduces cache-related bugs
    """

    def __init__(self, cache_adapter, config: Optional[Dict[str, Any]] = None, shared_cache=None):
        """
        Initialize monitoring cache writer.

        Args:
            cache_adapter: Cache adapter instance (DirectCacheAdapter or MultiTierCache)
            config: Optional configuration dictionary
            shared_cache: Optional SharedCacheBridge for cross-process communication
        """
        self.cache_adapter = cache_adapter
        self.config = config or {}
        self.shared_cache = shared_cache

        # Statistics
        self.write_count = 0
        self.write_errors = 0
        self.validation_failures = 0
        self.last_write_time = 0
        self.shared_cache_writes = 0

        if self.shared_cache:
            logger.info("MonitoringCacheWriter initialized with unified schemas + SharedCacheBridge")
        else:
            logger.info("MonitoringCacheWriter initialized with unified schemas (local cache only)")

    async def write_market_overview(
        self,
        monitoring_data: Dict[str, Any],
        ttl: int = 60
    ) -> bool:
        """
        Write market overview data using unified schema.

        Transforms old monitoring format to unified MarketOverviewSchema.

        Args:
            monitoring_data: Data in old monitoring format with fields like:
                - total_symbols_monitored (mapped to total_symbols)
                - bullish_signals, bearish_signals (calculated into trend_strength)
                - avg_confluence_score
                - market_regime
            ttl: Cache TTL in seconds

        Returns:
            bool: True if write succeeded, False otherwise

        Example:
            old_data = {
                'total_symbols_monitored': 15,
                'bullish_signals': 8,
                'bearish_signals': 2,
                'avg_confluence_score': 67.5,
                'market_regime': 'Trending'
            }
            success = await writer.write_market_overview(old_data)
            # Cache now contains unified format with 'total_symbols' and 'trend_strength'
        """
        try:
            # Transform using schema migration helper
            schema = MarketOverviewSchema.from_monitoring_data(monitoring_data)

            # Validate before writing
            if not schema.validate():
                logger.error("Market overview schema validation failed")
                self.validation_failures += 1
                return False

            # Convert to dict and write to cache
            # CRITICAL FIX: Pass dict directly, not JSON string!
            # MultiTierCache handles JSON serialization internally.
            cache_data = schema.to_dict()

            await self.cache_adapter.set(
                schema.CACHE_KEY,  # "market:overview"
                cache_data,  # Pass dict, not JSON string
                ttl=ttl
            )

            # ALSO write to shared cache if available (cross-process communication)
            if self.shared_cache:
                try:
                    from src.core.cache.shared_cache_bridge import DataSource
                    await self.shared_cache.publish_data_update(
                        key=schema.CACHE_KEY,
                        data=cache_data,
                        source=DataSource.TRADING_SERVICE,
                        ttl=ttl
                    )
                    self.shared_cache_writes += 1
                    logger.debug(f"Published market overview to shared cache for web service visibility")
                except Exception as e:
                    logger.warning(f"Failed to publish market overview to shared cache: {e}")

            self.write_count += 1
            self.last_write_time = time.time()

            logger.debug(
                f"Wrote market:overview - {schema.total_symbols} symbols, "
                f"trend_strength={schema.trend_strength:.1f}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to write market overview: {e}", exc_info=True)
            self.write_errors += 1
            return False

    async def write_signals(
        self,
        signals: List[Dict[str, Any]],
        ttl: int = 120
    ) -> bool:
        """
        Write trading signals using unified schema.

        Args:
            signals: List of signal dictionaries with fields:
                - symbol: Trading pair symbol
                - confluence_score: Signal strength (0-100)
                - signal_type: 'BUY' or 'SELL'
                - reliability: Signal reliability (0-100)
                - components: Component scores breakdown
            ttl: Cache TTL in seconds

        Returns:
            bool: True if write succeeded, False otherwise
        """
        try:
            # Create schema instance
            schema = SignalsSchema(signals=signals)

            # Validate before writing
            if not schema.validate():
                logger.error("Signals schema validation failed")
                self.validation_failures += 1
                return False

            # Convert to dict and write
            # CRITICAL FIX: Pass dict directly, not JSON string!
            # MultiTierCache will handle JSON serialization internally.
            # Passing JSON string causes double-encoding.
            cache_data = schema.to_dict()

            await self.cache_adapter.set(
                schema.CACHE_KEY,  # "analysis:signals"
                cache_data,  # Pass dict, not JSON string
                ttl=ttl
            )

            # ALSO write to shared cache if available (cross-process communication)
            if self.shared_cache:
                try:
                    from src.core.cache.shared_cache_bridge import DataSource
                    await self.shared_cache.publish_data_update(
                        key=schema.CACHE_KEY,
                        data=cache_data,
                        source=DataSource.TRADING_SERVICE,
                        ttl=ttl
                    )
                    self.shared_cache_writes += 1
                    logger.debug(f"Published signals to shared cache for web service visibility")
                except Exception as e:
                    logger.warning(f"Failed to publish signals to shared cache: {e}")

            self.write_count += 1
            logger.debug(
                f"Wrote analysis:signals - {schema.total_signals} signals, "
                f"avg_score={schema.avg_confluence_score:.1f}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to write signals: {e}", exc_info=True)
            self.write_errors += 1
            return False

    async def write_market_breadth(
        self,
        up_count: int,
        down_count: int,
        flat_count: int = 0,
        ttl: int = 60
    ) -> bool:
        """
        Write market breadth data using unified schema.

        Args:
            up_count: Number of symbols moving up
            down_count: Number of symbols moving down
            flat_count: Number of symbols unchanged
            ttl: Cache TTL in seconds

        Returns:
            bool: True if write succeeded, False otherwise
        """
        try:
            # Create schema (automatically calculates breadth_percentage and sentiment)
            schema = MarketBreadthSchema(
                up_count=up_count,
                down_count=down_count,
                flat_count=flat_count
            )

            # Validate
            if not schema.validate():
                logger.error("Market breadth schema validation failed")
                self.validation_failures += 1
                return False

            # Write to cache
            # CRITICAL FIX: Pass dict directly, not JSON string!
            # MultiTierCache handles JSON serialization internally.
            cache_data = schema.to_dict()

            await self.cache_adapter.set(
                schema.CACHE_KEY,  # "market:breadth"
                cache_data,  # Pass dict, not JSON string
                ttl=ttl
            )

            self.write_count += 1
            logger.debug(
                f"Wrote market:breadth - {schema.breadth_percentage:.1f}% bullish, "
                f"sentiment={schema.market_sentiment}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to write market breadth: {e}", exc_info=True)
            self.write_errors += 1
            return False

    async def write_market_movers(
        self,
        gainers: List[Dict[str, Any]],
        losers: List[Dict[str, Any]],
        volume_leaders: List[Dict[str, Any]],
        ttl: int = 90
    ) -> bool:
        """
        Write market movers data using unified schema.

        Args:
            gainers: Top gaining symbols with positive price change
            losers: Top losing symbols with negative price change
            volume_leaders: Symbols with highest trading volume
            ttl: Cache TTL in seconds

        Returns:
            bool: True if write succeeded, False otherwise
        """
        try:
            # Create schema
            schema = MarketMoversSchema(
                gainers=gainers,
                losers=losers,
                volume_leaders=volume_leaders
            )

            # Validate
            if not schema.validate():
                logger.error("Market movers schema validation failed")
                self.validation_failures += 1
                return False

            # Write to cache
            # CRITICAL FIX: Pass dict directly, not JSON string!
            # MultiTierCache handles JSON serialization internally.
            cache_data = schema.to_dict()

            await self.cache_adapter.set(
                schema.CACHE_KEY,  # "market:movers"
                cache_data,  # Pass dict, not JSON string
                ttl=ttl
            )

            self.write_count += 1
            logger.debug(
                f"Wrote market:movers - {len(gainers)} gainers, {len(losers)} losers"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to write market movers: {e}", exc_info=True)
            self.write_errors += 1
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache writer statistics.

        Returns:
            dict: Statistics including write counts and error counts
        """
        return {
            'write_count': self.write_count,
            'write_errors': self.write_errors,
            'validation_failures': self.validation_failures,
            'last_write_time': self.last_write_time,
            'success_rate': (
                (self.write_count / (self.write_count + self.write_errors))
                if (self.write_count + self.write_errors) > 0
                else 0.0
            )
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on cache writer.

        Returns:
            dict: Health status with error counts and last write time
        """
        stats = self.get_statistics()

        # Determine health status
        if stats['write_errors'] > 10:
            status = 'unhealthy'
        elif stats['write_errors'] > 5:
            status = 'degraded'
        else:
            status = 'healthy'

        return {
            'status': status,
            'statistics': stats,
            'cache_adapter': str(type(self.cache_adapter).__name__)
        }
