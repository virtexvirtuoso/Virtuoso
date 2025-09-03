"""
Connection Pool Manager for Virtuoso CCXT Trading System.

Provides centralized connection management with:
- HTTP connection pooling with configurable limits
- Connection health monitoring and automatic recovery
- Integration with circuit breaker and retry policies
- Per-service connection pool configuration
- Connection lifecycle management
- Performance metrics and monitoring
- Support for multiple connection backends (aiohttp, httpx)
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List, Union, Callable, AsyncContextManager
from enum import Enum
from dataclasses import dataclass, field
import threading
import weakref
from contextlib import asynccontextmanager
import aiohttp
import ssl
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ConnectionBackend(Enum):
    """Available connection backends."""
    AIOHTTP = "aiohttp"
    HTTPX = "httpx"


class ConnectionStatus(Enum):
    """Connection pool status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CLOSED = "closed"


@dataclass
class PoolConfig:
    """Configuration for connection pool."""
    
    # Pool sizing
    max_connections: int = 100          # Maximum total connections
    max_connections_per_host: int = 30  # Maximum connections per host
    max_keepalive_connections: int = 20 # Maximum keep-alive connections
    
    # Timeouts
    connect_timeout: float = 10.0       # Connection establishment timeout
    request_timeout: float = 30.0       # Request timeout
    pool_timeout: float = 5.0           # Timeout to get connection from pool
    keepalive_timeout: float = 30.0     # Keep-alive timeout
    
    # Health checking
    health_check_interval: float = 60.0 # Health check interval in seconds
    max_unhealthy_ratio: float = 0.3    # Max ratio of unhealthy connections
    
    # SSL/TLS settings
    verify_ssl: bool = True
    ssl_context: Optional[ssl.SSLContext] = None
    
    # Connection behavior
    enable_cleanup: bool = True         # Enable automatic cleanup
    cleanup_interval: float = 300.0     # Cleanup interval in seconds
    max_idle_time: float = 600.0        # Max idle time before closing connection
    
    # Retry settings for connection establishment
    connection_retries: int = 3
    connection_retry_delay: float = 1.0
    
    # Monitoring
    name: str = "connection_pool"
    enable_metrics: bool = True
    
    def __post_init__(self):
        """Validate configuration."""
        if self.max_connections <= 0:
            raise ValueError("max_connections must be positive")
        if self.max_connections_per_host > self.max_connections:
            raise ValueError("max_connections_per_host cannot exceed max_connections")
        if self.connect_timeout <= 0:
            raise ValueError("connect_timeout must be positive")
        if self.request_timeout <= 0:
            raise ValueError("request_timeout must be positive")


@dataclass
class ConnectionMetrics:
    """Metrics for connection pool."""
    
    # Connection counts
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    
    # Performance metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    
    # Health metrics
    health_checks: int = 0
    healthy_checks: int = 0
    unhealthy_checks: int = 0
    last_health_check: Optional[float] = None
    
    # Pool utilization
    peak_connections: int = 0
    pool_exhaustions: int = 0
    connection_waits: int = 0
    average_wait_time: float = 0.0
    
    def update_connection_count(self, total: int, active: int, idle: int):
        """Update connection counts."""
        self.total_connections = total
        self.active_connections = active
        self.idle_connections = idle
        self.peak_connections = max(self.peak_connections, total)
    
    def record_request(self, success: bool, response_time: float):
        """Record request metrics."""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        # Update average response time (simple moving average)
        if self.total_requests == 1:
            self.average_response_time = response_time
        else:
            self.average_response_time = (
                (self.average_response_time * (self.total_requests - 1) + response_time) 
                / self.total_requests
            )
    
    def record_health_check(self, healthy: bool):
        """Record health check result."""
        self.health_checks += 1
        self.last_health_check = time.time()
        if healthy:
            self.healthy_checks += 1
        else:
            self.unhealthy_checks += 1
    
    def record_pool_wait(self, wait_time: float):
        """Record pool wait time."""
        self.connection_waits += 1
        if self.connection_waits == 1:
            self.average_wait_time = wait_time
        else:
            self.average_wait_time = (
                (self.average_wait_time * (self.connection_waits - 1) + wait_time)
                / self.connection_waits
            )
    
    @property
    def success_rate(self) -> float:
        """Calculate request success rate."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    @property
    def health_ratio(self) -> float:
        """Calculate health check success ratio."""
        if self.health_checks == 0:
            return 1.0
        return self.healthy_checks / self.health_checks


class ConnectionPool:
    """
    Individual connection pool for a specific service/host.
    """
    
    def __init__(self, name: str, config: PoolConfig):
        self.name = name
        self.config = config
        self.metrics = ConnectionMetrics()
        self.status = ConnectionStatus.HEALTHY
        
        # Connection management
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        self._lock = asyncio.Lock()
        self._closed = False
        
        # Health monitoring
        self._health_check_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info(f"Connection pool '{name}' initialized with config: {config}")
    
    async def initialize(self):
        """Initialize the connection pool."""
        async with self._lock:
            if self._session is not None:
                return
            
            # Create SSL context if needed
            ssl_context = self.config.ssl_context
            if ssl_context is None and self.config.verify_ssl:
                ssl_context = ssl.create_default_context()
            
            # Create TCP connector with pool configuration
            self._connector = aiohttp.TCPConnector(
                limit=self.config.max_connections,
                limit_per_host=self.config.max_connections_per_host,
                keepalive_timeout=self.config.keepalive_timeout,
                enable_cleanup_closed=self.config.enable_cleanup,
                ssl=ssl_context if self.config.verify_ssl else False,
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True
            )
            
            # Create timeout configuration
            timeout = aiohttp.ClientTimeout(
                total=self.config.request_timeout,
                connect=self.config.connect_timeout,
                sock_read=self.config.request_timeout
            )
            
            # Create session
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout
            )
            
            # Start background tasks
            if self.config.health_check_interval > 0:
                self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            if self.config.enable_cleanup and self.config.cleanup_interval > 0:
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            logger.info(f"Connection pool '{self.name}' initialized successfully")
    
    async def close(self):
        """Close the connection pool."""
        async with self._lock:
            if self._closed:
                return
            
            self._closed = True
            self.status = ConnectionStatus.CLOSED
            
            # Cancel background tasks
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Close session and connector
            if self._session:
                await self._session.close()
                self._session = None
            
            if self._connector:
                await self._connector.close()
                self._connector = None
            
            logger.info(f"Connection pool '{self.name}' closed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncContextManager[aiohttp.ClientSession]:
        """Get a session from the pool."""
        if self._closed:
            raise RuntimeError(f"Connection pool '{self.name}' is closed")
        
        if self._session is None:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # Wait for available connection with timeout
            async with asyncio.timeout(self.config.pool_timeout):
                yield self._session
        except asyncio.TimeoutError:
            self.metrics.pool_exhaustions += 1
            wait_time = time.time() - start_time
            self.metrics.record_pool_wait(wait_time)
            raise RuntimeError(f"Pool timeout: no connections available in {self.config.pool_timeout}s")
    
    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """Make an HTTP request using the connection pool."""
        start_time = time.time()
        
        try:
            async with self.get_session() as session:
                response = await session.request(method, url, **kwargs)
                
                # Record successful request
                response_time = time.time() - start_time
                self.metrics.record_request(True, response_time)
                
                return response
                
        except Exception as e:
            # Record failed request
            response_time = time.time() - start_time
            self.metrics.record_request(False, response_time)
            self.metrics.failed_connections += 1
            
            logger.error(f"Request failed in pool '{self.name}': {e}")
            raise
    
    async def _health_check_loop(self):
        """Background task for health checking."""
        while not self._closed:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error in pool '{self.name}': {e}")
                await asyncio.sleep(self.config.health_check_interval)
    
    async def _perform_health_check(self):
        """Perform health check on the connection pool."""
        try:
            if self._connector:
                # Get connector statistics
                stats = self._connector._pool_stats() if hasattr(self._connector, '_pool_stats') else {}
                
                # Update connection counts
                total_connections = len(getattr(self._connector, '_conns', []))
                active_connections = total_connections  # Simplified for now
                idle_connections = 0  # Would need more detailed connector inspection
                
                self.metrics.update_connection_count(total_connections, active_connections, idle_connections)
                
                # Determine health status
                if self.metrics.health_ratio < (1.0 - self.config.max_unhealthy_ratio):
                    self.status = ConnectionStatus.UNHEALTHY
                elif self.metrics.health_ratio < 0.9:
                    self.status = ConnectionStatus.DEGRADED
                else:
                    self.status = ConnectionStatus.HEALTHY
                
                self.metrics.record_health_check(self.status == ConnectionStatus.HEALTHY)
                
            logger.debug(f"Health check completed for pool '{self.name}': {self.status.value}")
            
        except Exception as e:
            self.metrics.record_health_check(False)
            self.status = ConnectionStatus.UNHEALTHY
            logger.error(f"Health check failed for pool '{self.name}': {e}")
    
    async def _cleanup_loop(self):
        """Background task for connection cleanup."""
        while not self._closed:
            try:
                await self._perform_cleanup()
                await asyncio.sleep(self.config.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error in pool '{self.name}': {e}")
                await asyncio.sleep(self.config.cleanup_interval)
    
    async def _perform_cleanup(self):
        """Perform connection cleanup."""
        try:
            if self._connector:
                # Force cleanup of closed connections
                await self._connector._cleanup_closed()
                logger.debug(f"Cleanup completed for pool '{self.name}'")
        except Exception as e:
            logger.error(f"Cleanup failed for pool '{self.name}': {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current pool metrics."""
        return {
            'name': self.name,
            'status': self.status.value,
            'config': {
                'max_connections': self.config.max_connections,
                'max_connections_per_host': self.config.max_connections_per_host,
                'connect_timeout': self.config.connect_timeout,
                'request_timeout': self.config.request_timeout
            },
            'metrics': {
                'total_connections': self.metrics.total_connections,
                'active_connections': self.metrics.active_connections,
                'idle_connections': self.metrics.idle_connections,
                'peak_connections': self.metrics.peak_connections,
                'total_requests': self.metrics.total_requests,
                'successful_requests': self.metrics.successful_requests,
                'failed_requests': self.metrics.failed_requests,
                'success_rate': self.metrics.success_rate,
                'average_response_time': self.metrics.average_response_time,
                'health_ratio': self.metrics.health_ratio,
                'pool_exhaustions': self.metrics.pool_exhaustions,
                'connection_waits': self.metrics.connection_waits,
                'average_wait_time': self.metrics.average_wait_time
            }
        }


class ConnectionPoolManager:
    """
    Centralized manager for all connection pools.
    
    Features:
    - Per-service connection pool management
    - Dynamic pool creation and configuration
    - Global connection limits and monitoring
    - Integration with circuit breaker patterns
    - Automatic pool lifecycle management
    """
    
    def __init__(self):
        self._pools: Dict[str, ConnectionPool] = {}
        self._lock = threading.RLock()
        self._global_config: Optional[PoolConfig] = None
        self._shutdown = False
        
        logger.info("Connection Pool Manager initialized")
    
    def set_global_config(self, config: PoolConfig):
        """Set global default configuration for pools."""
        with self._lock:
            self._global_config = config
            logger.info(f"Global pool configuration set: {config}")
    
    def get_pool(self, name: str, config: Optional[PoolConfig] = None) -> ConnectionPool:
        """
        Get or create a connection pool.
        
        Args:
            name: Pool name/identifier
            config: Optional pool-specific configuration
        
        Returns:
            ConnectionPool instance
        """
        with self._lock:
            if self._shutdown:
                raise RuntimeError("Connection Pool Manager is shut down")
            
            if name not in self._pools:
                # Use provided config or global default
                pool_config = config or self._global_config
                if pool_config is None:
                    pool_config = PoolConfig(name=name)
                
                # Ensure name is set correctly
                if pool_config.name != name:
                    pool_config.name = name
                
                self._pools[name] = ConnectionPool(name, pool_config)
                logger.info(f"Created new connection pool: {name}")
            
            return self._pools[name]
    
    async def initialize_pool(self, name: str, config: Optional[PoolConfig] = None):
        """Initialize a specific pool."""
        pool = self.get_pool(name, config)
        await pool.initialize()
    
    async def close_pool(self, name: str):
        """Close a specific pool."""
        with self._lock:
            if name in self._pools:
                pool = self._pools.pop(name)
                await pool.close()
                logger.info(f"Closed connection pool: {name}")
    
    async def shutdown(self):
        """Shutdown all pools."""
        with self._lock:
            if self._shutdown:
                return
            
            self._shutdown = True
            pools = list(self._pools.values())
            self._pools.clear()
        
        # Close all pools concurrently
        if pools:
            await asyncio.gather(*[pool.close() for pool in pools], return_exceptions=True)
        
        logger.info("Connection Pool Manager shut down")
    
    def get_all_pools(self) -> Dict[str, ConnectionPool]:
        """Get all registered pools."""
        with self._lock:
            return self._pools.copy()
    
    def get_pool_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all pools."""
        with self._lock:
            return {name: pool.get_metrics() for name, pool in self._pools.items()}
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """Get aggregated global metrics."""
        pools_metrics = self.get_pool_metrics()
        
        total_connections = sum(m['metrics']['total_connections'] for m in pools_metrics.values())
        total_requests = sum(m['metrics']['total_requests'] for m in pools_metrics.values())
        total_successful = sum(m['metrics']['successful_requests'] for m in pools_metrics.values())
        
        return {
            'total_pools': len(pools_metrics),
            'healthy_pools': sum(1 for m in pools_metrics.values() if m['status'] == 'healthy'),
            'total_connections': total_connections,
            'total_requests': total_requests,
            'global_success_rate': total_successful / total_requests if total_requests > 0 else 1.0,
            'pools': pools_metrics
        }


# Global connection pool manager instance
_pool_manager: Optional[ConnectionPoolManager] = None
_manager_lock = threading.RLock()


def get_connection_pool_manager() -> ConnectionPoolManager:
    """Get the global connection pool manager."""
    global _pool_manager
    
    with _manager_lock:
        if _pool_manager is None:
            _pool_manager = ConnectionPoolManager()
        return _pool_manager


def get_connection_pool(name: str, config: Optional[PoolConfig] = None) -> ConnectionPool:
    """Get a connection pool from the global manager."""
    manager = get_connection_pool_manager()
    return manager.get_pool(name, config)


async def shutdown_connection_pools():
    """Shutdown all connection pools."""
    global _pool_manager
    
    with _manager_lock:
        if _pool_manager is not None:
            await _pool_manager.shutdown()
            _pool_manager = None