from typing import Dict, Set, Optional, NamedTuple
import asyncio
import logging
import psutil
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class ResourceLimits:
    """System resource limits."""
    max_memory_percent: float = 80.0
    max_cpu_percent: float = 90.0
    max_tasks: int = 100
    max_connections: int = 50
    task_memory_limit: int = 500 * 1024 * 1024  # 500MB per task

class ResourceStats(NamedTuple):
    """Current resource statistics."""
    memory_percent: float
    cpu_percent: float
    active_tasks: int
    active_connections: int
    timestamp: datetime

class ResourceAllocationError(Exception):
    """Raised when resource allocation fails."""
    pass

class ResourceManager:
    """Manages system resources and enforces limits."""
    
    def __init__(
        self,
        limits: Optional[ResourceLimits] = None,
        monitor_interval: float = 5.0
    ):
        self._limits = limits or ResourceLimits()
        self._monitor_interval = monitor_interval
        self._active_tasks: Dict[str, int] = {}  # task_id -> memory usage
        self._active_connections: Set[str] = set()
        self._monitor_task: Optional[asyncio.Task] = None
        self._last_stats: Optional[ResourceStats] = None
        self._lock = asyncio.Lock()
        
    async def start_monitoring(self) -> None:
        """Start resource monitoring."""
        if self._monitor_task is not None:
            return
            
        async def monitor_resources():
            while True:
                try:
                    await self._update_resource_stats()
                    await self._check_resource_limits()
                    await asyncio.sleep(self._monitor_interval)
                except Exception as e:
                    logger.error(f"Error in resource monitoring: {str(e)}")
                    await asyncio.sleep(1.0)
                    
        self._monitor_task = asyncio.create_task(monitor_resources())
        
    async def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
            
    async def allocate_task(
        self,
        task_id: str,
        memory_requirement: Optional[int] = None
    ) -> bool:
        """Allocate resources for a new task."""
        async with self._lock:
            # Check task limit
            if len(self._active_tasks) >= self._limits.max_tasks:
                raise ResourceAllocationError("Maximum number of tasks reached")
                
            # Check memory requirement
            if memory_requirement is not None:
                if memory_requirement > self._limits.task_memory_limit:
                    raise ResourceAllocationError("Task memory requirement exceeds limit")
                    
                stats = await self.get_resource_stats()
                available_memory = psutil.virtual_memory().available
                if memory_requirement > available_memory:
                    raise ResourceAllocationError("Insufficient memory available")
                    
            self._active_tasks[task_id] = memory_requirement or 0
            return True
            
    async def release_task(self, task_id: str) -> None:
        """Release resources allocated to a task."""
        async with self._lock:
            self._active_tasks.pop(task_id, None)
            
    async def register_connection(self, connection_id: str) -> bool:
        """Register a new connection."""
        async with self._lock:
            if len(self._active_connections) >= self._limits.max_connections:
                raise ResourceAllocationError("Maximum number of connections reached")
                
            self._active_connections.add(connection_id)
            return True
            
    async def unregister_connection(self, connection_id: str) -> None:
        """Unregister a connection."""
        async with self._lock:
            self._active_connections.discard(connection_id)
            
    async def get_resource_stats(self) -> ResourceStats:
        """Get current resource statistics."""
        if self._last_stats is None:
            await self._update_resource_stats()
        return self._last_stats
        
    async def _update_resource_stats(self) -> None:
        """Update resource statistics."""
        try:
            self._last_stats = ResourceStats(
                memory_percent=psutil.virtual_memory().percent,
                cpu_percent=psutil.cpu_percent(),
                active_tasks=len(self._active_tasks),
                active_connections=len(self._active_connections),
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Error updating resource stats: {str(e)}")
            
    async def _check_resource_limits(self) -> None:
        """Check if resource usage exceeds limits."""
        if self._last_stats is None:
            return
            
        if self._last_stats.memory_percent > self._limits.max_memory_percent:
            logger.warning("Memory usage exceeds limit")
            # Implement memory pressure handling
            
        if self._last_stats.cpu_percent > self._limits.max_cpu_percent:
            logger.warning("CPU usage exceeds limit")
            # Implement CPU pressure handling 