"""
Optimized Cache Configuration
Addresses critical cache inefficiency issues with improved TTL settings
to achieve 45%+ cache hit ratio and reduce CPU usage.
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import aiomcache
from enum import Enum

logger = logging.getLogger(__name__)

class CacheLevel(Enum):
    """Cache levels with different TTL strategies"""
    HOT = "hot"          # Most frequently accessed, longer TTL
    WARM = "warm"        # Moderately accessed, medium TTL  
    COLD = "cold"        # Less frequently accessed, shorter TTL

@dataclass
class OptimizedCacheConfig:
    """Optimized cache configuration with targeted TTL settings"""
    
    # Optimized TTL settings for better hit ratios
    TTL_SETTINGS = {
        # Hot cache - frequently accessed data (longer TTL)
        'market_overview': 120,      # 2 minutes (was 30s)
        'top_symbols': 300,          # 5 minutes (was 60s) 
        'market_regime': 180,        # 3 minutes (was 60s)
        'btc_dominance': 240,        # 4 minutes (was 60s)
        
        # Warm cache - moderately accessed data (medium TTL)
        'confluence_scores': 60,     # 1 minute (was 30s)
        'technical_indicators': 60,  # 1 minute (was 30s)
        'signal_analysis': 90,       # 1.5 minutes (was 30s)
        'dashboard_data': 45,        # 45 seconds (was 30s)
        'market_tickers': 30,        # 30 seconds (optimized)
        
        # Cold cache - less frequently accessed (shorter TTL)
        'market_movers': 90,         # 1.5 minutes (was 60s)
        'market_breadth': 75,        # 1.25 minutes (was 60s)
        'system_alerts': 120,        # 2 minutes (was 60s)
        'health_status': 45,         # 45 seconds (was 30s)
        
        # Real-time data - minimal caching but still optimized
        'orderbook_data': 5,         # 5 seconds (was 2s)
        'recent_trades': 10,         # 10 seconds (was 5s)
        'price_updates': 15,         # 15 seconds (was 10s)
        
        # Symbol-specific breakdown data
        'confluence_breakdown': 45,  # 45 seconds (new)
        'technical_breakdown': 60,   # 1 minute (new)
    }
    
    # Priority symbols for cache warming
    PRIORITY_SYMBOLS = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'XRPUSDT',
        'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'MATICUSDT', 'ATOMUSDT'
    ]
    
    # Cache warming intervals
    WARM_UP_INTERVALS = {
        'market_overview': 30,       # Warm every 30 seconds
        'top_symbols': 60,           # Warm every minute  
        'confluence_scores': 20,     # Warm every 20 seconds
        'priority_symbols': 15,      # Warm priority symbols every 15s
    }
    
    @classmethod
    def get_ttl(cls, cache_key: str, default: int = 30) -> int:
        """Get optimized TTL for cache key"""
        return cls.TTL_SETTINGS.get(cache_key, default)
    
    @classmethod
    def get_cache_level(cls, cache_key: str) -> CacheLevel:
        """Determine cache level for key"""
        if cache_key in ['market_overview', 'top_symbols', 'market_regime', 'btc_dominance']:
            return CacheLevel.HOT
        elif cache_key in ['confluence_scores', 'technical_indicators', 'signal_analysis', 'dashboard_data']:
            return CacheLevel.WARM
        else:
            return CacheLevel.COLD

@dataclass
class CacheWarmingStrategy:
    """Cache warming strategy to pre-populate frequently accessed data"""
    
    def __init__(self, cache_adapter):
        self.cache_adapter = cache_adapter
        self.warming_tasks: Set[asyncio.Task] = set()
        self.is_warming = False
        self.config = OptimizedCacheConfig()
    
    async def start_warming(self):
        """Start cache warming background tasks"""
        if self.is_warming:
            return
            
        self.is_warming = True
        logger.info("Starting optimized cache warming strategy")
        
        # Start warming tasks for different data types
        warming_coroutines = [
            self._warm_market_overview(),
            self._warm_priority_symbols(),
            self._warm_confluence_scores(),
            self._warm_system_data(),
        ]
        
        for coro in warming_coroutines:
            task = asyncio.create_task(coro)
            self.warming_tasks.add(task)
            task.add_done_callback(self.warming_tasks.discard)
    
    async def stop_warming(self):
        """Stop all warming tasks"""
        self.is_warming = False
        
        for task in self.warming_tasks.copy():
            task.cancel()
        
        if self.warming_tasks:
            await asyncio.gather(*self.warming_tasks, return_exceptions=True)
        
        logger.info("Cache warming stopped")
    
    async def _warm_market_overview(self):
        """Warm market overview data"""
        while self.is_warming:
            try:
                await asyncio.sleep(self.config.WARM_UP_INTERVALS['market_overview'])
                
                # Pre-populate market overview cache
                if hasattr(self.cache_adapter, '_warm_cache_key'):
                    await self.cache_adapter._warm_cache_key('market_overview')
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error warming market overview: {e}")
                await asyncio.sleep(10)  # Brief pause on error
    
    async def _warm_priority_symbols(self):
        """Warm priority symbol data"""
        while self.is_warming:
            try:
                await asyncio.sleep(self.config.WARM_UP_INTERVALS['priority_symbols'])
                
                # Warm confluence data for priority symbols
                for symbol in self.config.PRIORITY_SYMBOLS[:5]:  # Top 5 symbols
                    if hasattr(self.cache_adapter, '_warm_symbol_data'):
                        await self.cache_adapter._warm_symbol_data(symbol)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error warming priority symbols: {e}")
                await asyncio.sleep(15)
    
    async def _warm_confluence_scores(self):
        """Warm confluence score data"""
        while self.is_warming:
            try:
                await asyncio.sleep(self.config.WARM_UP_INTERVALS['confluence_scores'])
                
                # Pre-populate confluence scores
                if hasattr(self.cache_adapter, '_warm_cache_key'):
                    await self.cache_adapter._warm_cache_key('confluence_scores')
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error warming confluence scores: {e}")
                await asyncio.sleep(20)
    
    async def _warm_system_data(self):
        """Warm system and health data"""
        while self.is_warming:
            try:
                await asyncio.sleep(60)  # Every minute
                
                # Warm system data
                system_keys = ['health_status', 'system_alerts', 'market_regime']
                for key in system_keys:
                    if hasattr(self.cache_adapter, '_warm_cache_key'):
                        await self.cache_adapter._warm_cache_key(key)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error warming system data: {e}")
                await asyncio.sleep(30)

class EnhancedConnectionPool:
    """Enhanced connection pool with better resource management"""
    
    def __init__(self, host: str = 'localhost', port: int = 11211, 
                 pool_size: int = 15, max_retries: int = 3):
        self.host = host
        self.port = port
        self.pool_size = pool_size
        self.max_retries = max_retries
        self.connections: List[aiomcache.Client] = []
        self.available_connections = asyncio.Queue()
        self.connection_lock = asyncio.Lock()
        self.initialized = False
        self.active_connections = 0
        self.max_active_connections = pool_size * 2  # Allow burst capacity
        
    async def initialize(self):
        """Initialize enhanced connection pool"""
        async with self.connection_lock:
            if self.initialized:
                return
            
            logger.info(f"Initializing enhanced connection pool (size: {self.pool_size})")
            
            # Create initial connections
            for i in range(self.pool_size):
                conn = await self._create_verified_connection()
                if conn:
                    self.connections.append(conn)
                    await self.available_connections.put(conn)
            
            if not self.connections:
                raise ConnectionError("Failed to create any cache connections")
            
            self.initialized = True
            logger.info(f"Connection pool ready with {len(self.connections)} connections")
    
    async def _create_verified_connection(self) -> Optional[aiomcache.Client]:
        """Create and verify connection with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                conn = aiomcache.Client(self.host, self.port)
                
                # Verify connection with quick test
                test_key = f"pool_test_{int(time.time() * 1000)}_{attempt}"
                await asyncio.wait_for(
                    conn.set(test_key.encode(), b'1', exptime=1),
                    timeout=1.5
                )
                await conn.delete(test_key.encode())
                
                return conn
                
            except Exception as e:
                backoff_time = 0.5 * (2 ** attempt)
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(backoff_time)
        
        return None
    
    @asynccontextmanager
    async def get_connection(self, timeout: float = 3.0):
        """Get connection with timeout and connection limits"""
        if not self.initialized:
            await self.initialize()
        
        if self.active_connections >= self.max_active_connections:
            raise ConnectionError("Connection pool exhausted")
        
        conn = None
        try:
            # Get connection with timeout
            conn = await asyncio.wait_for(
                self.available_connections.get(),
                timeout=timeout
            )
            self.active_connections += 1
            yield conn
            
        except asyncio.TimeoutError:
            # Try to create new connection if under pool limit
            if len(self.connections) < self.pool_size * 1.5:
                conn = await self._create_verified_connection()
                if conn:
                    self.connections.append(conn)
                    self.active_connections += 1
                    yield conn
                else:
                    raise ConnectionError("Unable to create new connection")
            else:
                raise ConnectionError(f"Connection timeout after {timeout}s")
        
        finally:
            if conn:
                self.active_connections -= 1
                try:
                    await self.available_connections.put(conn)
                except asyncio.QueueFull:
                    # Queue full, connection will be lost but that's OK
                    pass

class SmartCacheKeyManager:
    """Smart cache key management with optimization features"""
    
    OPTIMIZED_KEYS = {
        # Core dashboard data
        'market:overview:v2': 'market_overview',
        'market:tickers:all': 'market_tickers', 
        'market:movers:top': 'market_movers',
        'market:regime:current': 'market_regime',
        
        # Analysis data
        'analysis:confluence:scores': 'confluence_scores',
        'analysis:signals:active': 'signal_analysis',
        'analysis:technical:indicators': 'technical_indicators',
        
        # System data
        'system:health:status': 'health_status',
        'system:alerts:active': 'system_alerts',
        'market:btc:dominance': 'btc_dominance',
    }
    
    @classmethod
    def get_standardized_key(cls, key: str) -> str:
        """Get standardized cache key"""
        return cls.OPTIMIZED_KEYS.get(key, key)
    
    @classmethod
    def get_breakdown_key(cls, symbol: str, analysis_type: str = 'confluence') -> str:
        """Get breakdown key for symbol analysis"""
        return f'breakdown:{analysis_type}:{symbol}'
    
    @classmethod
    def is_priority_key(cls, key: str) -> bool:
        """Check if key is high priority for caching"""
        priority_prefixes = ['market:overview', 'confluence:scores', 'breakdown:']
        return any(key.startswith(prefix) for prefix in priority_prefixes)

# Export optimized configuration
def get_optimized_cache_config() -> Dict[str, Any]:
    """Get optimized cache configuration dictionary"""
    return {
        'ttl_settings': OptimizedCacheConfig.TTL_SETTINGS,
        'priority_symbols': OptimizedCacheConfig.PRIORITY_SYMBOLS,
        'warm_up_intervals': OptimizedCacheConfig.WARM_UP_INTERVALS,
        'cache_levels': {
            'hot': ['market_overview', 'top_symbols', 'market_regime', 'btc_dominance'],
            'warm': ['confluence_scores', 'technical_indicators', 'signal_analysis', 'dashboard_data'],
            'cold': ['market_movers', 'market_breadth', 'system_alerts', 'health_status']
        }
    }

logger.info("Optimized cache configuration loaded")
