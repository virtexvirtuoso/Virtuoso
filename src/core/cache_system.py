"""
Optimized Dashboard Cache System
Ensures reliable cache reads with intelligent retry logic, warming strategies, and comprehensive monitoring
"""
import asyncio
import logging
import json
import time
from typing import Dict, Any, Optional, List, Tuple
import aiomcache
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class CacheStatus(Enum):
    HIT = "hit"
    MISS = "miss"
    ERROR = "error"
    TIMEOUT = "timeout"
    WARMING = "warming"

@dataclass
class CacheMetrics:
    hits: int = 0
    misses: int = 0
    errors: int = 0
    timeouts: int = 0
    avg_response_time: float = 0.0
    last_update: float = 0.0

class OptimizedCacheSystem:
    """
    High-performance cache system optimized for dashboard data retrieval
    Features:
    - Smart retry logic with exponential backoff
    - Cache warming for critical data
    - Comprehensive monitoring and metrics
    - Circuit breaker pattern for resilience
    - Multi-tier fallback strategies
    """
    
    def __init__(self, cache_host='localhost', cache_port=11211, pool_size=5):
        self.cache_host = cache_host
        self.cache_port = cache_port
        self.pool_size = pool_size
        self._client = None
        
        # Performance monitoring
        self.metrics = CacheMetrics()
        self.key_metrics: Dict[str, CacheMetrics] = {}
        
        # Circuit breaker state
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_reset_time = 60
        self.last_failure_time = 0
        
        # Cache warming state
        self.warming_in_progress = False
        self.critical_keys = [
            'market:overview',
            'analysis:signals', 
            'market:tickers',
            'market:movers',
            'analysis:market_regime'
        ]
        
        # Retry configuration
        self.max_retries = 3
        self.base_retry_delay = 0.1  # 100ms base delay
        self.max_retry_delay = 2.0   # 2s max delay
        
    async def _get_client(self) -> aiomcache.Client:
        """Get or create optimized cache client with connection pooling"""
        if self._client is None:
            self._client = aiomcache.Client(
                self.cache_host, 
                self.cache_port, 
                pool_size=self.pool_size,
                pool_minsize=2
            )
        return self._client
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open (too many failures)"""
        if self.circuit_breaker_failures < self.circuit_breaker_threshold:
            return False
        
        # Reset circuit breaker after timeout
        if time.time() - self.last_failure_time > self.circuit_breaker_reset_time:
            self.circuit_breaker_failures = 0
            logger.info("Circuit breaker reset - resuming cache operations")
            return False
        
        return True
    
    def _record_failure(self):
        """Record a cache failure for circuit breaker"""
        self.circuit_breaker_failures += 1
        self.last_failure_time = time.time()
        
        if self.circuit_breaker_failures >= self.circuit_breaker_threshold:
            logger.warning(f"Circuit breaker opened - too many cache failures ({self.circuit_breaker_failures})")
    
    def _record_success(self):
        """Record a successful operation"""
        if self.circuit_breaker_failures > 0:
            self.circuit_breaker_failures = max(0, self.circuit_breaker_failures - 1)
    
    async def get_with_retry(self, key: str, default: Any = None, timeout: float = 2.0) -> Tuple[Any, CacheStatus]:
        """
        Get data from cache with intelligent retry logic
        Returns: (data, cache_status)
        """
        start_time = time.perf_counter()
        
        # Check circuit breaker
        if self._is_circuit_breaker_open():
            logger.warning(f"Circuit breaker open - returning default for {key}")
            self._update_key_metrics(key, CacheStatus.ERROR, time.perf_counter() - start_time)
            return default, CacheStatus.ERROR
        
        for attempt in range(self.max_retries + 1):
            try:
                client = await self._get_client()
                
                # Apply timeout based on attempt (shorter for retries)
                current_timeout = timeout / (attempt + 1)
                
                data = await asyncio.wait_for(
                    client.get(key.encode()), 
                    timeout=current_timeout
                )
                
                if data:
                    # Parse the data
                    if key == 'analysis:market_regime':
                        result = data.decode()
                    else:
                        try:
                            result = json.loads(data.decode())
                        except json.JSONDecodeError:
                            result = data.decode()
                    
                    # Record successful hit
                    elapsed = time.perf_counter() - start_time
                    self._update_key_metrics(key, CacheStatus.HIT, elapsed)
                    self._record_success()
                    
                    logger.debug(f"Cache HIT for {key} (attempt {attempt + 1}, {elapsed*1000:.1f}ms)")
                    return result, CacheStatus.HIT
                else:
                    # Cache miss on final attempt
                    if attempt == self.max_retries:
                        elapsed = time.perf_counter() - start_time
                        self._update_key_metrics(key, CacheStatus.MISS, elapsed)
                        logger.debug(f"Cache MISS for {key} after {attempt + 1} attempts")
                        return default, CacheStatus.MISS
                    
                    # Retry with exponential backoff for cache misses
                    retry_delay = min(self.base_retry_delay * (2 ** attempt), self.max_retry_delay)
                    logger.debug(f"Cache miss for {key}, retrying in {retry_delay:.3f}s (attempt {attempt + 1})")
                    await asyncio.sleep(retry_delay)
                    
            except asyncio.TimeoutError:
                if attempt == self.max_retries:
                    elapsed = time.perf_counter() - start_time
                    self._update_key_metrics(key, CacheStatus.TIMEOUT, elapsed)
                    self._record_failure()
                    logger.warning(f"Cache TIMEOUT for {key} after {attempt + 1} attempts ({elapsed:.3f}s)")
                    return default, CacheStatus.TIMEOUT
                
                # Exponential backoff for timeouts
                retry_delay = min(self.base_retry_delay * (2 ** attempt), self.max_retry_delay)
                logger.debug(f"Cache timeout for {key}, retrying in {retry_delay:.3f}s")
                await asyncio.sleep(retry_delay)
                
            except Exception as e:
                if attempt == self.max_retries:
                    elapsed = time.perf_counter() - start_time
                    self._update_key_metrics(key, CacheStatus.ERROR, elapsed)
                    self._record_failure()
                    logger.error(f"Cache ERROR for {key} after {attempt + 1} attempts: {e}")
                    return default, CacheStatus.ERROR
                
                # Shorter delay for connection errors
                retry_delay = min(self.base_retry_delay * (2 ** attempt), 1.0)
                logger.debug(f"Cache error for {key}: {e}, retrying in {retry_delay:.3f}s")
                await asyncio.sleep(retry_delay)
        
        # This shouldn't be reached, but just in case
        return default, CacheStatus.ERROR
    
    def _update_key_metrics(self, key: str, status: CacheStatus, elapsed_time: float):
        """Update metrics for a specific key"""
        if key not in self.key_metrics:
            self.key_metrics[key] = CacheMetrics()
        
        key_metric = self.key_metrics[key]
        
        # Update key-specific metrics
        if status == CacheStatus.HIT:
            key_metric.hits += 1
        elif status == CacheStatus.MISS:
            key_metric.misses += 1
        elif status == CacheStatus.ERROR:
            key_metric.errors += 1
        elif status == CacheStatus.TIMEOUT:
            key_metric.timeouts += 1
        
        # Update response time (exponential moving average)
        if key_metric.avg_response_time == 0:
            key_metric.avg_response_time = elapsed_time
        else:
            key_metric.avg_response_time = (
                0.8 * key_metric.avg_response_time + 0.2 * elapsed_time
            )
        
        key_metric.last_update = time.time()
        
        # Update global metrics
        if status == CacheStatus.HIT:
            self.metrics.hits += 1
        elif status == CacheStatus.MISS:
            self.metrics.misses += 1
        elif status == CacheStatus.ERROR:
            self.metrics.errors += 1
        elif status == CacheStatus.TIMEOUT:
            self.metrics.timeouts += 1
        
        # Update global average response time
        if self.metrics.avg_response_time == 0:
            self.metrics.avg_response_time = elapsed_time
        else:
            self.metrics.avg_response_time = (
                0.9 * self.metrics.avg_response_time + 0.1 * elapsed_time
            )
        
        self.metrics.last_update = time.time()
    
    async def warm_cache(self, force: bool = False) -> Dict[str, str]:
        """
        Warm critical cache keys by triggering data population
        This ensures dashboard doesn't get empty data on startup
        """
        if self.warming_in_progress and not force:
            logger.debug("Cache warming already in progress")
            return {"status": "already_warming"}
        
        logger.info("Starting cache warming for critical dashboard keys...")
        self.warming_in_progress = True
        warm_results = {}
        
        try:
            # Check which critical keys are missing or stale
            missing_keys = []
            stale_keys = []
            current_time = time.time()
            
            for key in self.critical_keys:
                data, status = await self.get_with_retry(key, timeout=1.0)
                
                if status == CacheStatus.MISS:
                    missing_keys.append(key)
                elif isinstance(data, dict) and data.get('timestamp'):
                    # Check if data is stale (>90 seconds old)
                    data_age = current_time - data.get('timestamp', 0)
                    if data_age > 90:
                        stale_keys.append(key)
            
            warm_results['missing_keys'] = missing_keys
            warm_results['stale_keys'] = stale_keys
            
            if missing_keys or stale_keys:
                logger.warning(f"Cache warming needed - Missing: {missing_keys}, Stale: {stale_keys}")
                
                # Trigger cache population by calling bridge methods if available
                try:
                    # Try to get the cache bridge if it exists
                    from src.core.cache_data_bridge import cache_data_bridge
                    
                    if hasattr(cache_data_bridge, 'bridge_monitoring_data'):
                        logger.info("Triggering cache bridge to populate missing data...")
                        await cache_data_bridge.bridge_monitoring_data()
                        warm_results['bridge_triggered'] = True
                    else:
                        logger.warning("Cache bridge not available for warming")
                        warm_results['bridge_available'] = False
                        
                except ImportError:
                    logger.warning("Cache bridge not available - archived")
                    warm_results['bridge_available'] = False
                    
                    # Alternative: try to populate with direct API calls
                    await self._populate_critical_data()
                    warm_results['direct_population'] = True
            else:
                logger.info("Cache warming not needed - all critical keys present and fresh")
                warm_results['status'] = 'not_needed'
                
        except Exception as e:
            logger.error(f"Error during cache warming: {e}")
            warm_results['error'] = str(e)
        finally:
            self.warming_in_progress = False
        
        logger.info(f"Cache warming completed: {warm_results}")
        return warm_results
    
    async def _populate_critical_data(self):
        """Populate critical cache data using direct API calls as fallback"""
        try:
            # Try to get real market data if available
            logger.info("Populating critical data using direct fallback methods...")
            
            # Check if we have any data sources available
            empty_data = {
                'market:overview': {
                    'total_symbols': 0,
                    'total_volume': 0,
                    'average_change': 0,
                    'volatility': 0,
                    'timestamp': int(time.time())
                },
                'analysis:signals': {
                    'signals': [],
                    'count': 0,
                    'timestamp': int(time.time()),
                    'status': 'warming'
                },
                'market:movers': {
                    'gainers': [],
                    'losers': [],
                    'timestamp': int(time.time())
                },
                'analysis:market_regime': 'warming'
            }
            
            # Set empty data with warming indicators
            client = await self._get_client()
            for key, data in empty_data.items():
                try:
                    if isinstance(data, dict):
                        value = json.dumps(data).encode()
                    else:
                        value = str(data).encode()
                    await client.set(key.encode(), value, exptime=30)  # Short TTL for warming data
                    logger.debug(f"Set warming data for {key}")
                except Exception as e:
                    logger.error(f"Failed to set warming data for {key}: {e}")
                    
        except Exception as e:
            logger.error(f"Error populating critical data: {e}")
    
    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cache performance metrics"""
        total_operations = self.metrics.hits + self.metrics.misses + self.metrics.errors + self.metrics.timeouts
        
        metrics = {
            'global_metrics': {
                'total_operations': total_operations,
                'hits': self.metrics.hits,
                'misses': self.metrics.misses,
                'errors': self.metrics.errors,
                'timeouts': self.metrics.timeouts,
                'hit_rate': (self.metrics.hits / total_operations * 100) if total_operations > 0 else 0,
                'avg_response_time_ms': self.metrics.avg_response_time * 1000,
                'last_update': self.metrics.last_update,
                'circuit_breaker_failures': self.circuit_breaker_failures,
                'circuit_breaker_open': self._is_circuit_breaker_open()
            },
            'key_metrics': {}
        }
        
        # Add per-key metrics
        for key, key_metric in self.key_metrics.items():
            key_total = key_metric.hits + key_metric.misses + key_metric.errors + key_metric.timeouts
            metrics['key_metrics'][key] = {
                'total_operations': key_total,
                'hits': key_metric.hits,
                'misses': key_metric.misses,
                'errors': key_metric.errors,
                'timeouts': key_metric.timeouts,
                'hit_rate': (key_metric.hits / key_total * 100) if key_total > 0 else 0,
                'avg_response_time_ms': key_metric.avg_response_time * 1000,
                'last_update': key_metric.last_update,
                'data_age_seconds': time.time() - key_metric.last_update if key_metric.last_update > 0 else 0
            }
        
        return metrics
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for cache system"""
        health_data = {
            'status': 'unknown',
            'timestamp': time.time(),
            'checks': {}
        }
        
        try:
            # Test basic connectivity
            start_time = time.perf_counter()
            test_key = f'health_check:{int(time.time())}'
            test_value = 'health_test'
            
            client = await self._get_client()
            await client.set(test_key.encode(), test_value.encode(), exptime=5)
            
            retrieved_value = await client.get(test_key.encode())
            connection_time = (time.perf_counter() - start_time) * 1000
            
            if retrieved_value and retrieved_value.decode() == test_value:
                health_data['checks']['connectivity'] = {
                    'status': 'healthy',
                    'response_time_ms': round(connection_time, 2)
                }
            else:
                health_data['checks']['connectivity'] = {
                    'status': 'unhealthy',
                    'reason': 'data_mismatch'
                }
            
            # Check critical keys availability
            critical_key_status = {}
            for key in self.critical_keys:
                data, status = await self.get_with_retry(key, timeout=1.0)
                critical_key_status[key] = {
                    'status': status.value,
                    'has_data': data is not None and data != {},
                    'data_type': type(data).__name__ if data else 'None'
                }
            
            health_data['checks']['critical_keys'] = critical_key_status
            
            # Overall status
            connectivity_healthy = health_data['checks']['connectivity']['status'] == 'healthy'
            circuit_breaker_ok = not self._is_circuit_breaker_open()
            
            if connectivity_healthy and circuit_breaker_ok:
                health_data['status'] = 'healthy'
            elif connectivity_healthy:
                health_data['status'] = 'degraded'  # Circuit breaker issues
            else:
                health_data['status'] = 'unhealthy'
            
            # Add performance metrics
            health_data['performance'] = self.get_cache_metrics()['global_metrics']
            
        except Exception as e:
            health_data['status'] = 'error'
            health_data['error'] = str(e)
        
        return health_data
    
    async def close(self):
        """Clean shutdown of cache connections"""
        if self._client:
            try:
                await self._client.close()
                self._client = None
                logger.info("Cache system connections closed")
            except Exception as e:
                logger.error(f"Error closing cache connections: {e}")

# Global optimized cache system instance
optimized_cache_system = OptimizedCacheSystem()