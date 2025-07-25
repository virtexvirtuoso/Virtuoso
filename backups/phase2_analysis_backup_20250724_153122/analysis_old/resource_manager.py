"""Resource management for analysis components."""

from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
import asyncio
import logging
import psutil
from datetime import datetime, timedelta
import numpy as np
from collections import deque

@dataclass
class ResourceThresholds:
    """Dynamic resource thresholds."""
    
    base_memory_mb: float = 1024  # 1GB base memory limit
    base_cpu_percent: float = 80.0
    max_operations: int = 100
    operation_timeout: float = 30.0
    
    # Adaptive settings
    memory_headroom_percent: float = 20.0
    cpu_headroom_percent: float = 10.0
    scale_factor: float = 1.2
    
    def __post_init__(self):
        """Initialize adaptive thresholds."""
        self.update_thresholds()
    
    def update_thresholds(self) -> None:
        """Update thresholds based on system resources."""
        try:
            # Get system memory info
            system_memory = psutil.virtual_memory()
            available_memory_mb = system_memory.available / (1024 * 1024)
            
            # Calculate memory threshold with headroom
            self.memory_threshold = min(
                self.base_memory_mb,
                available_memory_mb * (1 - self.memory_headroom_percent / 100)
            )
            
            # Get CPU count and adjust base threshold
            cpu_count = psutil.cpu_count()
            self.cpu_threshold = min(
                self.base_cpu_percent,
                100 - self.cpu_headroom_percent
            ) * cpu_count
            
        except Exception as e:
            logging.error(f"Error updating thresholds: {e}")
            # Fall back to base thresholds
            self.memory_threshold = self.base_memory_mb
            self.cpu_threshold = self.base_cpu_percent

@dataclass
class ResourceMetrics:
    """Enhanced resource usage metrics."""
    
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    active_operations: int = 0
    operation_times: deque = field(default_factory=lambda: deque(maxlen=100))
    last_updated: datetime = field(default_factory=datetime.utcnow)
    peak_memory: float = 0.0
    peak_cpu: float = 0.0
    
    def update(self, memory_mb: float, cpu_percent: float) -> None:
        """Update metrics with new values."""
        self.memory_mb = memory_mb
        self.cpu_percent = cpu_percent
        self.last_updated = datetime.utcnow()
        
        # Update peaks
        self.peak_memory = max(self.peak_memory, memory_mb)
        self.peak_cpu = max(self.peak_cpu, cpu_percent)
    
    def add_operation_time(self, duration: float) -> None:
        """Add operation duration to history."""
        self.operation_times.append(duration)
    
    @property
    def avg_operation_time(self) -> float:
        """Calculate average operation time."""
        if not self.operation_times:
            return 0.0
        return sum(self.operation_times) / len(self.operation_times)
    
    @property
    def operation_time_percentile(self, percentile: float = 95) -> float:
        """Calculate operation time percentile."""
        if not self.operation_times:
            return 0.0
        return float(np.percentile(self.operation_times, percentile))

@dataclass
class ResourceManager:
    """Enhanced resource manager with adaptive thresholds."""
    
    thresholds: ResourceThresholds = field(default_factory=ResourceThresholds)
    check_interval: float = 5.0
    cleanup_interval: float = 300.0  # 5 minutes
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("ResourceManager")
    )
    
    _metrics: Dict[str, ResourceMetrics] = field(default_factory=dict)
    _active_components: Set[str] = field(default_factory=set)
    _check_task: Optional[asyncio.Task] = None
    _cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start resource monitoring and cleanup tasks."""
        if not self._check_task:
            self._check_task = asyncio.create_task(self._monitor_resources())
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_resources())
    
    async def stop(self) -> None:
        """Stop resource monitoring and cleanup tasks."""
        for task in [self._check_task, self._cleanup_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._check_task = None
        self._cleanup_task = None
    
    def register_component(self, component_name: str) -> None:
        """Register a component for monitoring."""
        if component_name not in self._metrics:
            self._metrics[component_name] = ResourceMetrics()
            self._active_components.add(component_name)
    
    def unregister_component(self, component_name: str) -> None:
        """Unregister a component from monitoring."""
        self._active_components.discard(component_name)
        if component_name in self._metrics:
            del self._metrics[component_name]
    
    async def check_resources(self, component_name: str) -> bool:
        """Check if component can use more resources."""
        if component_name not in self._active_components:
            return False
            
        metrics = self._metrics.get(component_name)
        if not metrics:
            return True
            
        # Update thresholds based on current system state
        self.thresholds.update_thresholds()
        
        # Check memory usage
        if metrics.memory_mb > self.thresholds.memory_threshold:
            self.logger.warning(
                f"Component {component_name} exceeds memory threshold: "
                f"{metrics.memory_mb:.1f}MB > {self.thresholds.memory_threshold:.1f}MB"
            )
            return False
            
        # Check CPU usage
        if metrics.cpu_percent > self.thresholds.cpu_threshold:
            self.logger.warning(
                f"Component {component_name} exceeds CPU threshold: "
                f"{metrics.cpu_percent:.1f}% > {self.thresholds.cpu_threshold:.1f}%"
            )
            return False
            
        # Check operation count
        if metrics.active_operations >= self.thresholds.max_operations:
            self.logger.warning(
                f"Component {component_name} exceeds operation limit: "
                f"{metrics.active_operations} > {self.thresholds.max_operations}"
            )
            return False
            
        return True
    
    async def allocate_resources(self,
                               component_name: str,
                               resources: Dict[str, Any]) -> bool:
        """Attempt to allocate resources to a component."""
        if not await self.check_resources(component_name):
            return False
            
        metrics = self._metrics.get(component_name)
        if not metrics:
            return False
            
        # Track operation
        metrics.active_operations += 1
        
        # Schedule automatic release
        asyncio.create_task(
            self._auto_release(
                component_name,
                self.thresholds.operation_timeout
            )
        )
        
        return True
    
    async def release_resources(self,
                              component_name: str,
                              operation_duration: Optional[float] = None) -> None:
        """Release resources allocated to a component."""
        metrics = self._metrics.get(component_name)
        if not metrics:
            return
            
        metrics.active_operations = max(0, metrics.active_operations - 1)
        
        if operation_duration is not None:
            metrics.add_operation_time(operation_duration)
    
    async def _auto_release(self,
                          component_name: str,
                          timeout: float) -> None:
        """Automatically release resources after timeout."""
        await asyncio.sleep(timeout)
        await self.release_resources(component_name)
    
    async def _monitor_resources(self) -> None:
        """Monitor system resources."""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self._update_system_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring resources: {e}")
    
    async def _cleanup_resources(self) -> None:
        """Cleanup stale resources."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_stale_components()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error cleaning up resources: {e}")
    
    async def _update_system_metrics(self) -> None:
        """Update system-wide metrics."""
        try:
            process = psutil.Process()
            
            # Get memory info
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            
            # Get CPU usage
            cpu_percent = process.cpu_percent()
            
            # Update metrics for active components
            for component in self._active_components:
                metrics = self._metrics.get(component)
                if metrics:
                    metrics.update(memory_mb, cpu_percent)
                    
        except Exception as e:
            self.logger.error(f"Error updating system metrics: {e}")
    
    async def _cleanup_stale_components(self) -> None:
        """Clean up stale component resources."""
        now = datetime.utcnow()
        stale_threshold = timedelta(minutes=30)
        
        for component in list(self._active_components):
            metrics = self._metrics.get(component)
            if metrics and (now - metrics.last_updated) > stale_threshold:
                self.logger.warning(f"Cleaning up stale component: {component}")
                self.unregister_component(component)
    
    def get_metrics(self, component_name: str) -> Optional[ResourceMetrics]:
        """Get current metrics for a component."""
        return self._metrics.get(component_name)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system resource status."""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            return {
                'memory_available_mb': memory.available / (1024 * 1024),
                'memory_percent': memory.percent,
                'cpu_percent': cpu_percent,
                'active_components': len(self._active_components),
                'total_operations': sum(
                    m.active_operations for m in self._metrics.values()
                ),
                'thresholds': {
                    'memory_mb': self.thresholds.memory_threshold,
                    'cpu_percent': self.thresholds.cpu_threshold,
                    'max_operations': self.thresholds.max_operations
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {} 