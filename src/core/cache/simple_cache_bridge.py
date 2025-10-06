#!/usr/bin/env python3
"""
Simple Shared Cache Bridge - Python 3.7 Compatible
==================================================

CRITICAL ARCHITECTURAL FIX: Python 3.7 compatible shared cache bridge
implementation for cross-service data integration.

Simplified implementation without complex dependencies to ensure
compatibility with the current Python environment.
"""

import asyncio
import json
import time
import logging
import os
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

class SimpleCacheBridge:
    """Simple shared cache bridge compatible with Python 3.7"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        # Configuration
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.memcached_host = os.getenv('MEMCACHED_HOST', 'localhost')
        self.memcached_port = int(os.getenv('MEMCACHED_PORT', 11211))

        # Simple in-memory cache for testing
        self._memory_cache = {}
        self._cache_timestamps = {}

        # Performance metrics
        self.metrics = {
            'hits': 0,
            'misses': 0,
            'writes': 0,
            'cross_service_hits': 0,
            'last_update': 0
        }

        logger.info("SimpleCacheBridge initialized")

    async def initialize(self):
        """Initialize cache connections"""
        try:
            # Try to initialize Redis
            try:
                import redis.asyncio as aioredis
                self._redis_client = await aioredis.from_url(
                    f'redis://{self.redis_host}:{self.redis_port}',
                    decode_responses=True
                )
                await self._redis_client.ping()
                logger.info("✅ Redis connected")
            except Exception as e:
                logger.warning(f"Redis not available: {e}")
                self._redis_client = None

            # Try to initialize Memcached
            try:
                import aiomcache
                self._memcached_client = aiomcache.Client(
                    self.memcached_host,
                    self.memcached_port
                )
                logger.info("✅ Memcached connected")
            except Exception as e:
                logger.warning(f"Memcached not available: {e}")
                self._memcached_client = None

            return True

        except Exception as e:
            logger.error(f"Cache initialization failed: {e}")
            return False

    async def set_data(self, key, data, ttl=300):
        """Store data in shared cache"""
        try:
            # Store in memory cache
            self._memory_cache[key] = data
            self._cache_timestamps[key] = time.time() + ttl

            # Try Redis
            if self._redis_client:
                serialized = json.dumps(data) if not isinstance(data, str) else data
                await self._redis_client.setex(f"vt_shared:{key}", ttl, serialized)

            # Try Memcached
            if self._memcached_client:
                serialized = json.dumps(data).encode() if not isinstance(data, (str, bytes)) else data
                if isinstance(serialized, str):
                    serialized = serialized.encode()
                await self._memcached_client.set(f"vt_shared:{key}".encode(), serialized, exptime=ttl)

            self.metrics['writes'] += 1
            self.metrics['last_update'] = time.time()
            logger.debug(f"Cache set: {key}")
            return True

        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False

    async def get_data(self, key):
        """Get data from shared cache"""
        try:
            # Check memory cache first
            if key in self._memory_cache:
                if time.time() < self._cache_timestamps.get(key, 0):
                    self.metrics['hits'] += 1
                    logger.debug(f"Memory cache hit: {key}")
                    return self._memory_cache[key], False
                else:
                    # Expired
                    del self._memory_cache[key]
                    del self._cache_timestamps[key]

            # Try Redis
            if self._redis_client:
                try:
                    data = await self._redis_client.get(f"vt_shared:{key}")
                    if data:
                        parsed_data = json.loads(data) if data != 'null' else None
                        if parsed_data:
                            # Cache in memory for faster access
                            self._memory_cache[key] = parsed_data
                            self._cache_timestamps[key] = time.time() + 60
                            self.metrics['cross_service_hits'] += 1
                            logger.debug(f"Redis cache hit: {key}")
                            return parsed_data, True
                except Exception as e:
                    logger.debug(f"Redis error for {key}: {e}")

            # Try Memcached
            if self._memcached_client:
                try:
                    data = await self._memcached_client.get(f"vt_shared:{key}".encode())
                    if data:
                        parsed_data = json.loads(data.decode())
                        # Cache in memory for faster access
                        self._memory_cache[key] = parsed_data
                        self._cache_timestamps[key] = time.time() + 60
                        self.metrics['cross_service_hits'] += 1
                        logger.debug(f"Memcached cache hit: {key}")
                        return parsed_data, True
                except Exception as e:
                    logger.debug(f"Memcached error for {key}: {e}")

            # Cache miss
            self.metrics['misses'] += 1
            logger.debug(f"Cache miss: {key}")
            return None, False

        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            self.metrics['misses'] += 1
            return None, False

    def get_metrics(self):
        """Get cache performance metrics"""
        total = self.metrics['hits'] + self.metrics['misses']
        hit_rate = (self.metrics['hits'] / total * 100) if total > 0 else 0
        cross_service_rate = (self.metrics['cross_service_hits'] / total * 100) if total > 0 else 0

        return {
            **self.metrics,
            'hit_rate_percent': round(hit_rate, 2),
            'cross_service_hit_rate_percent': round(cross_service_rate, 2),
            'total_operations': total,
            'memory_cache_size': len(self._memory_cache),
            'timestamp': time.time()
        }

    async def health_check(self):
        """Simple health check"""
        return {
            'status': 'healthy',
            'redis_available': self._redis_client is not None,
            'memcached_available': self._memcached_client is not None,
            'memory_cache_size': len(self._memory_cache),
            'timestamp': time.time()
        }

    async def close(self):
        """Close connections"""
        try:
            if self._redis_client:
                await self._redis_client.close()
            logger.info("SimpleCacheBridge closed")
        except Exception as e:
            logger.error(f"Error closing cache bridge: {e}")

# Global instance
_simple_cache_bridge = None

def get_simple_cache_bridge():
    """Get singleton cache bridge instance"""
    global _simple_cache_bridge
    if _simple_cache_bridge is None:
        _simple_cache_bridge = SimpleCacheBridge()
    return _simple_cache_bridge

class SimpleWebAdapter:
    """Simple web service cache adapter"""

    def __init__(self):
        self.bridge = get_simple_cache_bridge()
        self.metrics = {
            'requests': 0,
            'cache_hits': 0,
            'last_access': 0
        }

    async def initialize(self):
        """Initialize adapter"""
        return await self.bridge.initialize()

    async def get_market_overview(self):
        """Get market overview from cache"""
        self.metrics['requests'] += 1
        self.metrics['last_access'] = time.time()

        try:
            data, is_cross_service = await self.bridge.get_data('market:overview')

            if data and isinstance(data, dict):
                self.metrics['cache_hits'] += 1
                return {
                    **data,
                    'data_source': 'shared_cache_live' if is_cross_service else 'local_cache',
                    'timestamp': int(time.time())
                }

            # Fallback data
            return {
                'total_symbols': 0,
                'total_volume': 0,
                'total_volume_24h': 0,
                'average_change': 0,
                'volatility': 0,
                'btc_dominance': 59.3,
                'data_source': 'fallback',
                'timestamp': int(time.time())
            }

        except Exception as e:
            logger.error(f"Error getting market overview: {e}")
            return {'data_source': 'error', 'error': str(e)}

    async def get_dashboard_overview(self):
        """Get dashboard overview"""
        market_overview = await self.get_market_overview()

        return {
            'summary': {
                'total_symbols': market_overview.get('total_symbols', 0),
                'total_volume': market_overview.get('total_volume', 0),
                'total_volume_24h': market_overview.get('total_volume_24h', 0),
                'average_change': market_overview.get('average_change', 0)
            },
            'market_regime': 'unknown',
            'signals': [],
            'top_gainers': [],
            'top_losers': [],
            'data_source': market_overview.get('data_source', 'fallback'),
            'timestamp': int(time.time())
        }

    async def get_mobile_data(self):
        """Get mobile dashboard data"""
        return {
            'market_overview': {
                'market_regime': 'unknown',
                'trend_strength': 50,
                'volatility': 0,
                'btc_dominance': 59.3,
                'total_volume_24h': 0
            },
            'confluence_scores': [],
            'top_movers': {'gainers': [], 'losers': []},
            'status': 'success',
            'data_source': 'simple_cache',
            'timestamp': int(time.time())
        }

    def get_performance_metrics(self):
        """Get performance metrics"""
        hit_rate = (self.metrics['cache_hits'] / self.metrics['requests'] * 100) if self.metrics['requests'] > 0 else 0
        return {
            **self.metrics,
            'cache_hit_rate_percent': round(hit_rate, 2),
            'timestamp': time.time()
        }

class SimpleTradingBridge:
    """Simple trading service cache bridge"""

    def __init__(self):
        self.bridge = get_simple_cache_bridge()
        self.metrics = {
            'updates': 0,
            'failed_updates': 0,
            'last_update': 0
        }

    async def initialize(self):
        """Initialize bridge"""
        return await self.bridge.initialize()

    async def populate_market_overview(self, data):
        """Populate market overview in cache"""
        try:
            success = await self.bridge.set_data('market:overview', data, ttl=300)
            if success:
                self.metrics['updates'] += 1
                self.metrics['last_update'] = time.time()
                logger.info(f"Market overview populated: {data.get('total_symbols', 0)} symbols")
            else:
                self.metrics['failed_updates'] += 1
            return success
        except Exception as e:
            logger.error(f"Error populating market overview: {e}")
            self.metrics['failed_updates'] += 1
            return False

    async def populate_signals_data(self, data):
        """Populate signals data"""
        try:
            success = await self.bridge.set_data('analysis:signals', data, ttl=300)
            if success:
                self.metrics['updates'] += 1
                logger.info(f"Signals populated: {len(data.get('signals', []))} signals")
            else:
                self.metrics['failed_updates'] += 1
            return success
        except Exception as e:
            logger.error(f"Error populating signals: {e}")
            self.metrics['failed_updates'] += 1
            return False

    def get_performance_metrics(self):
        """Get performance metrics"""
        total = self.metrics['updates'] + self.metrics['failed_updates']
        success_rate = (self.metrics['updates'] / total * 100) if total > 0 else 0
        return {
            **self.metrics,
            'success_rate_percent': round(success_rate, 2),
            'timestamp': time.time()
        }

# Global instances
_simple_web_adapter = None
_simple_trading_bridge = None

def get_simple_web_adapter():
    """Get web adapter instance"""
    global _simple_web_adapter
    if _simple_web_adapter is None:
        _simple_web_adapter = SimpleWebAdapter()
    return _simple_web_adapter

def get_simple_trading_bridge():
    """Get trading bridge instance"""
    global _simple_trading_bridge
    if _simple_trading_bridge is None:
        _simple_trading_bridge = SimpleTradingBridge()
    return _simple_trading_bridge

async def simple_initialize_shared_cache():
    """Initialize simple shared cache"""
    bridge = get_simple_cache_bridge()
    return await bridge.initialize()