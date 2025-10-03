from src.utils.task_tracker import create_tracked_task
"""
Health Check Service for Virtuoso CCXT Trading System.

Provides comprehensive health monitoring with:
- Service dependency mapping and health checks
- Cascading health status evaluation
- Configurable health check intervals and timeouts
- Integration with circuit breakers and connection pools
- Health check endpoints and metrics
- Automated alerting on health degradation
- Support for custom health check implementations
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List, Callable, Set, Awaitable, Union
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import threading
from collections import defaultdict
import weakref

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service health status levels."""
    HEALTHY = "healthy"          # Service is fully operational
    DEGRADED = "degraded"        # Service has minor issues but functional
    UNHEALTHY = "unhealthy"      # Service has major issues
    CRITICAL = "critical"        # Service is non-functional
    UNKNOWN = "unknown"          # Health status cannot be determined


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    
    status: ServiceStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0  # Time taken to perform check
    error: Optional[Exception] = None
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp == 0:
            self.timestamp = time.time()
    
    @property
    def is_healthy(self) -> bool:
        """Check if result indicates healthy status."""
        return self.status in (ServiceStatus.HEALTHY, ServiceStatus.DEGRADED)
    
    @property
    def is_critical(self) -> bool:
        """Check if result indicates critical status."""
        return self.status == ServiceStatus.CRITICAL


@dataclass
class HealthCheckConfig:
    """Configuration for health checks."""
    
    # Check timing
    interval: float = 30.0          # Check interval in seconds
    timeout: float = 10.0           # Check timeout in seconds
    initial_delay: float = 0.0      # Initial delay before first check
    
    # Failure handling
    consecutive_failures: int = 3   # Failures before marking unhealthy
    consecutive_successes: int = 2  # Successes needed to recover
    
    # Status thresholds
    degraded_threshold: float = 0.8  # Success ratio for degraded status
    critical_threshold: float = 0.2  # Success ratio for critical status
    
    # Dependencies
    required_dependencies: Set[str] = field(default_factory=set)  # Services that must be healthy
    optional_dependencies: Set[str] = field(default_factory=set)  # Services that affect status but don't fail check
    
    # Monitoring
    name: str = "health_check"
    enable_metrics: bool = True
    alert_on_status_change: bool = True
    
    def __post_init__(self):
        """Validate configuration."""
        if self.interval <= 0:
            raise ValueError("interval must be positive")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.consecutive_failures <= 0:
            raise ValueError("consecutive_failures must be positive")


class HealthCheck(ABC):
    """Base class for health check implementations."""
    
    def __init__(self, name: str, config: HealthCheckConfig):
        self.name = name
        self.config = config
        self._last_result: Optional[HealthCheckResult] = None
        self._check_history: List[HealthCheckResult] = []
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._lock = threading.RLock()
    
    @abstractmethod
    async def perform_check(self) -> HealthCheckResult:
        """Perform the actual health check. Must be implemented by subclasses."""
        pass
    
    async def check_health(self) -> HealthCheckResult:
        """Perform health check with timeout and error handling."""
        start_time = time.time()
        
        try:
            # Perform check with timeout
            result = await asyncio.wait_for(
                self.perform_check(),
                timeout=self.config.timeout
            )
            
            # Set duration
            result.duration = time.time() - start_time
            
            # Update consecutive counters
            with self._lock:
                if result.is_healthy:
                    self._consecutive_successes += 1
                    self._consecutive_failures = 0
                else:
                    self._consecutive_failures += 1
                    self._consecutive_successes = 0
                
                # Store result
                self._last_result = result
                self._check_history.append(result)
                
                # Keep only recent history (last 100 checks)
                if len(self._check_history) > 100:
                    self._check_history = self._check_history[-100:]
            
            logger.debug(f"Health check '{self.name}' completed: {result.status.value}")
            return result
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            result = HealthCheckResult(
                status=ServiceStatus.CRITICAL,
                message=f"Health check timed out after {self.config.timeout}s",
                duration=duration,
                error=asyncio.TimeoutError("Health check timeout")
            )
            
        except Exception as e:
            duration = time.time() - start_time
            result = HealthCheckResult(
                status=ServiceStatus.CRITICAL,
                message=f"Health check failed: {str(e)}",
                duration=duration,
                error=e
            )
            
            logger.error(f"Health check '{self.name}' failed: {e}")
        
        # Update counters for failed checks
        with self._lock:
            self._consecutive_failures += 1
            self._consecutive_successes = 0
            self._last_result = result
            self._check_history.append(result)
            
            if len(self._check_history) > 100:
                self._check_history = self._check_history[-100:]
        
        return result
    
    def get_current_status(self) -> Optional[HealthCheckResult]:
        """Get the most recent health check result."""
        with self._lock:
            return self._last_result
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get health check metrics."""
        with self._lock:
            if not self._check_history:
                return {
                    'name': self.name,
                    'total_checks': 0,
                    'success_rate': 1.0,
                    'current_status': 'unknown',
                    'consecutive_failures': 0,
                    'consecutive_successes': 0
                }
            
            successful_checks = sum(1 for r in self._check_history if r.is_healthy)
            total_checks = len(self._check_history)
            avg_duration = sum(r.duration for r in self._check_history) / total_checks
            
            return {
                'name': self.name,
                'total_checks': total_checks,
                'successful_checks': successful_checks,
                'failed_checks': total_checks - successful_checks,
                'success_rate': successful_checks / total_checks,
                'average_duration': avg_duration,
                'current_status': self._last_result.status.value if self._last_result else 'unknown',
                'last_check_time': self._last_result.timestamp if self._last_result else None,
                'consecutive_failures': self._consecutive_failures,
                'consecutive_successes': self._consecutive_successes,
                'config': {
                    'interval': self.config.interval,
                    'timeout': self.config.timeout,
                    'consecutive_failures': self.config.consecutive_failures,
                    'consecutive_successes': self.config.consecutive_successes
                }
            }


class SimpleHealthCheck(HealthCheck):
    """Simple health check implementation using a callable."""
    
    def __init__(self, name: str, check_func: Callable[[], Awaitable[bool]], config: HealthCheckConfig, message: str = ""):
        super().__init__(name, config)
        self.check_func = check_func
        self.success_message = message or f"{name} is healthy"
        self.failure_message = f"{name} is unhealthy"
    
    async def perform_check(self) -> HealthCheckResult:
        """Perform simple boolean health check."""
        try:
            is_healthy = await self.check_func()
            return HealthCheckResult(
                status=ServiceStatus.HEALTHY if is_healthy else ServiceStatus.UNHEALTHY,
                message=self.success_message if is_healthy else self.failure_message
            )
        except Exception as e:
            return HealthCheckResult(
                status=ServiceStatus.CRITICAL,
                message=f"Health check error: {str(e)}",
                error=e
            )


class ConnectionPoolHealthCheck(HealthCheck):
    """Health check for connection pools."""
    
    def __init__(self, name: str, pool_name: str, config: HealthCheckConfig):
        super().__init__(name, config)
        self.pool_name = pool_name
    
    async def perform_check(self) -> HealthCheckResult:
        """Check connection pool health."""
        try:
            from .connection_pool import get_connection_pool_manager
            
            manager = get_connection_pool_manager()
            pools = manager.get_all_pools()
            
            if self.pool_name not in pools:
                return HealthCheckResult(
                    status=ServiceStatus.CRITICAL,
                    message=f"Connection pool '{self.pool_name}' not found"
                )
            
            pool = pools[self.pool_name]
            metrics = pool.get_metrics()
            
            # Determine status based on pool metrics
            success_rate = metrics['metrics']['success_rate']
            pool_status = metrics['status']
            
            if pool_status == 'healthy' and success_rate > self.config.degraded_threshold:
                status = ServiceStatus.HEALTHY
                message = f"Connection pool '{self.pool_name}' is healthy"
            elif pool_status == 'degraded' or success_rate > self.config.critical_threshold:
                status = ServiceStatus.DEGRADED
                message = f"Connection pool '{self.pool_name}' is degraded"
            elif pool_status == 'unhealthy':
                status = ServiceStatus.UNHEALTHY
                message = f"Connection pool '{self.pool_name}' is unhealthy"
            else:
                status = ServiceStatus.CRITICAL
                message = f"Connection pool '{self.pool_name}' is critical"
            
            return HealthCheckResult(
                status=status,
                message=message,
                details=metrics
            )
            
        except Exception as e:
            return HealthCheckResult(
                status=ServiceStatus.CRITICAL,
                message=f"Failed to check connection pool '{self.pool_name}': {str(e)}",
                error=e
            )


class CircuitBreakerHealthCheck(HealthCheck):
    """Health check for circuit breakers."""
    
    def __init__(self, name: str, circuit_breaker_name: str, config: HealthCheckConfig):
        super().__init__(name, config)
        self.circuit_breaker_name = circuit_breaker_name
    
    async def perform_check(self) -> HealthCheckResult:
        """Check circuit breaker health."""
        try:
            from .circuit_breaker import get_circuit_breaker_metrics
            
            all_metrics = get_circuit_breaker_metrics()
            
            if self.circuit_breaker_name not in all_metrics:
                return HealthCheckResult(
                    status=ServiceStatus.CRITICAL,
                    message=f"Circuit breaker '{self.circuit_breaker_name}' not found"
                )
            
            metrics = all_metrics[self.circuit_breaker_name]
            cb_state = metrics['state']
            success_rate = metrics['metrics']['success_rate']
            
            # Determine status based on circuit breaker state and metrics
            if cb_state == 'closed' and success_rate > self.config.degraded_threshold:
                status = ServiceStatus.HEALTHY
                message = f"Circuit breaker '{self.circuit_breaker_name}' is closed and healthy"
            elif cb_state == 'half_open':
                status = ServiceStatus.DEGRADED
                message = f"Circuit breaker '{self.circuit_breaker_name}' is testing recovery"
            elif cb_state == 'open':
                status = ServiceStatus.UNHEALTHY
                message = f"Circuit breaker '{self.circuit_breaker_name}' is open"
            else:
                status = ServiceStatus.UNKNOWN
                message = f"Circuit breaker '{self.circuit_breaker_name}' has unknown state"
            
            return HealthCheckResult(
                status=status,
                message=message,
                details=metrics
            )
            
        except Exception as e:
            return HealthCheckResult(
                status=ServiceStatus.CRITICAL,
                message=f"Failed to check circuit breaker '{self.circuit_breaker_name}': {str(e)}",
                error=e
            )


class HealthCheckService:
    """
    Comprehensive health check service with dependency management.
    
    Features:
    - Service dependency mapping
    - Cascading health evaluation
    - Automated health monitoring
    - Health check scheduling and execution
    - Metrics collection and reporting
    - Alert integration
    """
    
    def __init__(self):
        self._health_checks: Dict[str, HealthCheck] = {}
        self._dependencies: Dict[str, Set[str]] = defaultdict(set)
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._status_cache: Dict[str, HealthCheckResult] = {}
        self._lock = threading.RLock()
        self._shutdown = False
        
        # Global health status
        self._overall_status = ServiceStatus.UNKNOWN
        self._status_listeners: List[Callable[[ServiceStatus], Awaitable[None]]] = []
        
        logger.info("Health Check Service initialized")
    
    def register_health_check(self, health_check: HealthCheck, dependencies: Optional[Set[str]] = None):
        """Register a health check with optional dependencies."""
        with self._lock:
            if self._shutdown:
                raise RuntimeError("Health Check Service is shut down")
            
            name = health_check.name
            self._health_checks[name] = health_check
            
            if dependencies:
                self._dependencies[name] = dependencies.copy()
            
            # Start monitoring if interval is configured
            if health_check.config.interval > 0:
                self._start_monitoring(name)
            
            logger.info(f"Registered health check: {name}")
    
    def unregister_health_check(self, name: str):
        """Unregister a health check."""
        with self._lock:
            if name in self._health_checks:
                self._stop_monitoring(name)
                del self._health_checks[name]
                
                # Remove from dependencies
                if name in self._dependencies:
                    del self._dependencies[name]
                
                # Remove from status cache
                if name in self._status_cache:
                    del self._status_cache[name]
                
                logger.info(f"Unregistered health check: {name}")
    
    def _start_monitoring(self, name: str):
        """Start monitoring task for a health check."""
        if name in self._monitoring_tasks:
            return  # Already monitoring
        
        health_check = self._health_checks[name]
        task = create_tracked_task(self._monitoring_loop, name="_monitoring_loop_task")
        self._monitoring_tasks[name] = task
        
        logger.info(f"Started monitoring for health check: {name}")
    
    def _stop_monitoring(self, name: str):
        """Stop monitoring task for a health check."""
        if name in self._monitoring_tasks:
            task = self._monitoring_tasks.pop(name)
            task.cancel()
            logger.info(f"Stopped monitoring for health check: {name}")
    
    async def _monitoring_loop(self, name: str, health_check: HealthCheck):
        """Background monitoring loop for a health check."""
        try:
            # Initial delay
            if health_check.config.initial_delay > 0:
                await asyncio.sleep(health_check.config.initial_delay)
            
            while not self._shutdown:
                try:
                    # Perform health check
                    result = await health_check.check_health()
                    
                    # Update status cache
                    with self._lock:
                        old_status = self._status_cache.get(name)
                        self._status_cache[name] = result
                        
                        # Check for status changes
                        if old_status is None or old_status.status != result.status:
                            if health_check.config.alert_on_status_change:
                                await self._handle_status_change(name, old_status, result)
                    
                    # Update overall status
                    await self._update_overall_status()
                    
                    # Wait for next check
                    await asyncio.sleep(health_check.config.interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in monitoring loop for '{name}': {e}")
                    await asyncio.sleep(health_check.config.interval)
                    
        except asyncio.CancelledError:
            pass
        finally:
            logger.debug(f"Monitoring loop ended for health check: {name}")
    
    async def _handle_status_change(self, name: str, old_result: Optional[HealthCheckResult], new_result: HealthCheckResult):
        """Handle health status changes."""
        old_status = old_result.status if old_result else ServiceStatus.UNKNOWN
        new_status = new_result.status
        
        logger.info(f"Health status changed for '{name}': {old_status.value} -> {new_status.value}")
        
        # Here you could integrate with alerting systems
        # For example, send notifications for critical status changes
        if new_status == ServiceStatus.CRITICAL:
            logger.critical(f"Health check '{name}' is now CRITICAL: {new_result.message}")
    
    async def _update_overall_status(self):
        """Update overall system health status."""
        with self._lock:
            if not self._status_cache:
                new_status = ServiceStatus.UNKNOWN
            else:
                statuses = [result.status for result in self._status_cache.values()]
                
                # Determine overall status based on individual statuses
                if ServiceStatus.CRITICAL in statuses:
                    new_status = ServiceStatus.CRITICAL
                elif ServiceStatus.UNHEALTHY in statuses:
                    new_status = ServiceStatus.UNHEALTHY
                elif ServiceStatus.DEGRADED in statuses:
                    new_status = ServiceStatus.DEGRADED
                elif all(status == ServiceStatus.HEALTHY for status in statuses):
                    new_status = ServiceStatus.HEALTHY
                else:
                    new_status = ServiceStatus.UNKNOWN
            
            old_status = self._overall_status
            self._overall_status = new_status
        
        # Notify listeners if status changed
        if old_status != new_status:
            logger.info(f"Overall health status changed: {old_status.value} -> {new_status.value}")
            await self._notify_status_listeners(new_status)
    
    async def _notify_status_listeners(self, status: ServiceStatus):
        """Notify all status change listeners."""
        for listener in self._status_listeners:
            try:
                await listener(status)
            except Exception as e:
                logger.error(f"Error notifying status listener: {e}")
    
    def add_status_listener(self, listener: Callable[[ServiceStatus], Awaitable[None]]):
        """Add a listener for overall status changes."""
        self._status_listeners.append(listener)
    
    async def check_health(self, name: str) -> HealthCheckResult:
        """Perform immediate health check for a specific service."""
        with self._lock:
            if name not in self._health_checks:
                raise ValueError(f"Health check '{name}' not found")
            
            health_check = self._health_checks[name]
        
        return await health_check.check_health()
    
    async def check_all_health(self) -> Dict[str, HealthCheckResult]:
        """Perform immediate health checks for all registered services."""
        with self._lock:
            health_checks = self._health_checks.copy()
        
        results = {}
        for name, health_check in health_checks.items():
            try:
                results[name] = await health_check.check_health()
            except Exception as e:
                results[name] = HealthCheckResult(
                    status=ServiceStatus.CRITICAL,
                    message=f"Failed to check health: {str(e)}",
                    error=e
                )
        
        return results
    
    def get_current_status(self, name: str) -> Optional[HealthCheckResult]:
        """Get current cached status for a service."""
        with self._lock:
            return self._status_cache.get(name)
    
    def get_all_current_status(self) -> Dict[str, HealthCheckResult]:
        """Get current cached status for all services."""
        with self._lock:
            return self._status_cache.copy()
    
    def get_overall_status(self) -> ServiceStatus:
        """Get overall system health status."""
        return self._overall_status
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive health metrics."""
        with self._lock:
            health_checks = self._health_checks.copy()
            status_cache = self._status_cache.copy()
        
        metrics = {}
        for name, health_check in health_checks.items():
            metrics[name] = health_check.get_metrics()
        
        # Add overall metrics
        total_checks = len(health_checks)
        healthy_checks = sum(1 for result in status_cache.values() if result.is_healthy)
        
        return {
            'overall_status': self._overall_status.value,
            'total_health_checks': total_checks,
            'healthy_checks': healthy_checks,
            'health_ratio': healthy_checks / total_checks if total_checks > 0 else 1.0,
            'individual_checks': metrics,
            'dependencies': dict(self._dependencies)
        }
    
    async def shutdown(self):
        """Shutdown the health check service."""
        with self._lock:
            if self._shutdown:
                return
            
            self._shutdown = True
            tasks = list(self._monitoring_tasks.values())
            self._monitoring_tasks.clear()
        
        # Cancel all monitoring tasks
        for task in tasks:
            task.cancel()
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("Health Check Service shut down")


# Global health check service instance
_health_service: Optional[HealthCheckService] = None
_service_lock = threading.RLock()


def get_health_service() -> HealthCheckService:
    """Get the global health check service."""
    global _health_service
    
    with _service_lock:
        if _health_service is None:
            _health_service = HealthCheckService()
        return _health_service


async def shutdown_health_service():
    """Shutdown the global health check service."""
    global _health_service
    
    with _service_lock:
        if _health_service is not None:
            await _health_service.shutdown()
            _health_service = None