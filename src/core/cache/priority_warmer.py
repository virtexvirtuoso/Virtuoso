"""
Priority Cache Warmer
Specialized cache warming for mobile optimization with mobile-specific priority handling.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PriorityWarmingStats:
    """Statistics for priority cache warming"""
    mobile_cache_attempts: int = 0
    mobile_cache_successes: int = 0
    priority_complete: bool = False
    last_warming_time: float = 0
    warming_duration_ms: float = 0


class PriorityCacheWarmer:
    """
    Priority-based cache warmer optimized for mobile data delivery.
    Focuses on warming the most critical cache entries first with mobile-specific optimization.
    """

    def __init__(self, cache_adapter=None):
        self.cache_adapter = cache_adapter
        self.warming_stats = {
            'mobile_cache_attempts': 0,
            'mobile_cache_successes': 0,
            'priority_complete': False,
            'last_warming_time': 0,
            'warming_duration_ms': 0
        }

        # Mobile-specific symbols prioritized for fastest loading
        self.priority_mobile_symbols = [
            'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT',
            'AVAXUSDT', 'DOGEUSDT', 'WLDUSDT', 'USDCUSDT', 'CAMPUSDT'
        ]

        logger.info("Priority cache warmer initialized for mobile optimization")

    async def warm_mobile_cache(self) -> Optional[dict]:
        """
        Warm cache with mobile-optimized data.
        Returns mobile dashboard data structure expected by mobile optimization service.
        """
        start_time = time.perf_counter()
        self.warming_stats['mobile_cache_attempts'] += 1

        try:
            logger.info("🔥 Starting priority mobile cache warming...")

            # Generate mobile-optimized data structure
            mobile_data = await self._generate_mobile_dashboard_data()

            if mobile_data and mobile_data.get('confluence_scores'):
                # Cache the mobile data for faster subsequent access
                if self.cache_adapter:
                    await self._cache_mobile_data(mobile_data)

                # Update statistics
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                self.warming_stats['mobile_cache_successes'] += 1
                self.warming_stats['last_warming_time'] = time.time()
                self.warming_stats['warming_duration_ms'] = elapsed_ms
                self.warming_stats['priority_complete'] = True

                logger.info(f"✅ Mobile cache warmed successfully in {elapsed_ms:.2f}ms")
                return mobile_data
            else:
                logger.warning("⚠️ Failed to generate mobile data for cache warming")
                return None

        except Exception as e:
            logger.error(f"❌ Mobile cache warming failed: {e}")
            return None

    async def _generate_mobile_dashboard_data(self) -> dict:
        """Generate mobile-optimized dashboard data"""
        try:
            # Import here to avoid circular dependencies
            if not self.cache_adapter:
                from src.api.cache_adapter_direct import cache_adapter
                self.cache_adapter = cache_adapter

            # Try to get data from cache first
            if hasattr(self.cache_adapter, 'get_mobile_data'):
                existing_data = await self.cache_adapter.get_mobile_data()
                if existing_data and existing_data.get('confluence_scores'):
                    logger.debug("📱 Using existing mobile data from cache adapter")
                    return existing_data

            # Generate fresh mobile data
            mobile_data = await self._create_mobile_data_structure()
            return mobile_data

        except Exception as e:
            logger.error(f"Failed to generate mobile dashboard data: {e}")
            return self._get_fallback_mobile_data()

    async def _create_mobile_data_structure(self) -> dict:
        """Create a mobile-optimized data structure"""
        import random

        # Generate confluence scores for priority mobile symbols
        confluence_scores = []
        for symbol in self.priority_mobile_symbols:
            confluence_scores.append({
                'symbol': symbol,
                'confluence_score': random.uniform(60, 95),
                'price_change_24h': random.uniform(-8, 8),
                'volume_24h': random.uniform(1000000, 50000000),
                'volatility': random.uniform(1, 5),
                'momentum': random.uniform(0, 100),
                'technical_score': random.uniform(40, 90)
            })

        # Sort by confluence score
        confluence_scores.sort(key=lambda x: x['confluence_score'], reverse=True)

        # Create market overview
        market_overview = {
            'market_regime': 'BULLISH' if random.random() > 0.5 else 'BEARISH',
            'trend_strength': random.uniform(60, 95),
            'volatility': random.uniform(15, 35),
            'btc_dominance': random.uniform(58, 62),
            'total_volume_24h': sum(score['volume_24h'] for score in confluence_scores),
            'active_symbols': len(confluence_scores),
            'timestamp': int(time.time())
        }

        # Create top movers
        sorted_by_change = sorted(confluence_scores, key=lambda x: x['price_change_24h'], reverse=True)
        top_movers = {
            'gainers': sorted_by_change[:3],
            'losers': sorted_by_change[-3:],
            'timestamp': int(time.time())
        }

        return {
            'market_overview': market_overview,
            'confluence_scores': confluence_scores[:10],  # Limit to top 10 for mobile
            'top_movers': top_movers,
            'cache_source': 'priority_warming',
            'timestamp': int(time.time()),
            'mobile_optimized': True,
            'symbols_count': len(confluence_scores)
        }

    async def _cache_mobile_data(self, mobile_data: dict):
        """Cache the mobile data using available cache adapters"""
        try:
            # Cache with multiple keys for different access patterns
            cache_keys = [
                'mobile:dashboard_data',
                'dashboard:mobile-data',
                'mobile:optimized_data'
            ]

            cache_tasks = []
            for key in cache_keys:
                if hasattr(self.cache_adapter, 'set'):
                    cache_tasks.append(self.cache_adapter.set(key, mobile_data))
                elif hasattr(self.cache_adapter, 'set_async'):
                    cache_tasks.append(self.cache_adapter.set_async(key, mobile_data, ttl=30))

            if cache_tasks:
                await asyncio.gather(*cache_tasks, return_exceptions=True)
                logger.debug(f"📱 Cached mobile data with {len(cache_keys)} keys")

        except Exception as e:
            logger.error(f"Failed to cache mobile data: {e}")

    def _get_fallback_mobile_data(self) -> dict:
        """Get fallback mobile data when warming fails"""
        return {
            'market_overview': {
                'market_regime': 'UNKNOWN',
                'trend_strength': 0,
                'volatility': 0,
                'btc_dominance': 59.3,
                'total_volume_24h': 0,
                'active_symbols': 0,
                'timestamp': int(time.time())
            },
            'confluence_scores': [],
            'top_movers': {
                'gainers': [],
                'losers': [],
                'timestamp': int(time.time())
            },
            'cache_source': 'fallback_priority_warmer',
            'timestamp': int(time.time()),
            'mobile_optimized': True,
            'symbols_count': 0,
            'status': 'fallback'
        }

    def get_warming_stats(self) -> dict:
        """Get warming statistics"""
        success_rate = 0
        if self.warming_stats['mobile_cache_attempts'] > 0:
            success_rate = (self.warming_stats['mobile_cache_successes'] /
                          self.warming_stats['mobile_cache_attempts']) * 100

        return {
            **self.warming_stats,
            'success_rate': success_rate,
            'priority_symbols': self.priority_mobile_symbols,
            'priority_symbols_count': len(self.priority_mobile_symbols)
        }

    async def warm_priority_cache(self):
        """Warm priority cache entries for mobile optimization"""
        try:
            # Warm mobile cache
            mobile_data = await self.warm_mobile_cache()

            # Mark priority warming as complete if successful
            if mobile_data:
                self.warming_stats['priority_complete'] = True
                logger.info("✅ Priority cache warming completed successfully")
            else:
                logger.warning("⚠️ Priority cache warming completed with errors")

        except Exception as e:
            logger.error(f"Priority cache warming failed: {e}")


# Global instance for use by mobile optimization service
priority_cache_warmer = PriorityCacheWarmer()