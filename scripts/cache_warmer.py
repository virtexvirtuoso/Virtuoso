#!/usr/bin/env python3
"""
Cache Warmer for Virtuoso Trading System
Pre-loads frequently accessed data into cache layers
"""
import os
import sys
import time
import json
import asyncio
import aiohttp
import redis
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cache_warmer')

class CacheWarmer:
    def __init__(self):
        self.base_url = os.getenv('BASE_URL', 'http://localhost:8003')
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_client = redis.Redis(host=self.redis_host, port=6379, db=0)
        self.warm_interval = int(os.getenv('CACHE_WARM_INTERVAL', '300'))  # 5 minutes

        # Critical endpoints to warm
        self.critical_endpoints = [
            '/api/market/prices',
            '/api/signals/overview',
            '/api/dashboard/data',
            '/api/liquidation/latest',
            '/api/bitcoin-beta/correlation',
            '/api/monitoring/status'
        ]

        # Trading pairs to warm
        self.trading_pairs = [
            'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT',
            'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'MATIC/USDT'
        ]

        # Timeframes to warm
        self.timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']

    async def warm_endpoint(self, session: aiohttp.ClientSession, endpoint: str, params: Dict = None) -> bool:
        """Warm a single endpoint"""
        try:
            url = f"{self.base_url}{endpoint}"
            start_time = time.time()

            async with session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    elapsed = time.time() - start_time

                    # Store response time metrics
                    self.redis_client.zadd(
                        'cache_warm_times',
                        {f"{endpoint}:{datetime.utcnow().isoformat()}": elapsed}
                    )

                    logger.info(f"✅ Warmed {endpoint} in {elapsed:.2f}s")
                    return True
                else:
                    logger.warning(f"⚠️ Failed to warm {endpoint}: Status {response.status}")
                    return False

        except Exception as e:
            logger.error(f"❌ Error warming {endpoint}: {str(e)}")
            return False

    async def warm_market_data(self, session: aiohttp.ClientSession):
        """Warm market data for all trading pairs and timeframes"""
        tasks = []

        for pair in self.trading_pairs:
            for timeframe in self.timeframes:
                endpoint = f"/api/market/ohlcv"
                params = {'symbol': pair, 'timeframe': timeframe, 'limit': 100}
                tasks.append(self.warm_endpoint(session, endpoint, params))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if r is True)
        logger.info(f"Market data warming: {success_count}/{len(tasks)} successful")

    async def warm_signals(self, session: aiohttp.ClientSession):
        """Warm trading signals for all pairs"""
        tasks = []

        for pair in self.trading_pairs:
            endpoint = f"/api/signals/generate"
            params = {'symbol': pair}
            tasks.append(self.warm_endpoint(session, endpoint, params))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if r is True)
        logger.info(f"Signals warming: {success_count}/{len(tasks)} successful")

    async def warm_critical_endpoints(self, session: aiohttp.ClientSession):
        """Warm all critical endpoints"""
        tasks = [self.warm_endpoint(session, ep) for ep in self.critical_endpoints]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if r is True)
        logger.info(f"Critical endpoints warming: {success_count}/{len(tasks)} successful")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            info = self.redis_client.info()
            return {
                'used_memory_mb': round(info['used_memory'] / 1024 / 1024, 2),
                'hit_ratio': round(
                    info.get('keyspace_hits', 0) /
                    max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1), 1) * 100, 2
                ),
                'connected_clients': info['connected_clients'],
                'total_keys': sum(info.get(f'db{i}', {}).get('keys', 0) for i in range(16))
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}")
            return {}

    async def run_warming_cycle(self):
        """Run a complete warming cycle"""
        logger.info("🔥 Starting cache warming cycle...")
        start_time = time.time()

        # Get initial cache stats
        initial_stats = self.get_cache_stats()
        logger.info(f"Initial cache stats: {json.dumps(initial_stats, indent=2)}")

        async with aiohttp.ClientSession() as session:
            # Run all warming tasks
            await asyncio.gather(
                self.warm_critical_endpoints(session),
                self.warm_market_data(session),
                self.warm_signals(session),
                return_exceptions=True
            )

        # Get final cache stats
        final_stats = self.get_cache_stats()
        logger.info(f"Final cache stats: {json.dumps(final_stats, indent=2)}")

        elapsed = time.time() - start_time
        logger.info(f"✅ Cache warming completed in {elapsed:.2f}s")

        # Store warming history
        self.redis_client.rpush(
            'cache_warm_history',
            json.dumps({
                'timestamp': datetime.utcnow().isoformat(),
                'duration': elapsed,
                'initial_stats': initial_stats,
                'final_stats': final_stats
            })
        )

        # Keep only last 100 warming records
        self.redis_client.ltrim('cache_warm_history', -100, -1)

    async def run_continuous(self):
        """Run continuous cache warming"""
        logger.info(f"Starting continuous cache warming (interval: {self.warm_interval}s)")

        while True:
            try:
                await self.run_warming_cycle()
            except Exception as e:
                logger.error(f"Error in warming cycle: {str(e)}")

            # Wait for next cycle
            logger.info(f"Sleeping for {self.warm_interval}s until next warming cycle...")
            await asyncio.sleep(self.warm_interval)

def main():
    """Main entry point"""
    warmer = CacheWarmer()

    # Check if running in continuous mode
    if os.getenv('CACHE_WARMER_MODE') == 'true':
        asyncio.run(warmer.run_continuous())
    else:
        # Run single warming cycle
        asyncio.run(warmer.run_warming_cycle())

if __name__ == '__main__':
    main()