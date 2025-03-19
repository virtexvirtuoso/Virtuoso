"""Unified resource management system."""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class ResourceLimits:
    """Resource limits configuration."""
    max_memory_mb: int = 512
    max_concurrent_operations: int = 50
    operation_timeout: float = 30.0

@dataclass
class ResourceManager:
    """Manages system resources and enforces limits."""
    
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("ResourceManager")
    )
    
    # Track resource usage
    _memory_usage: Dict[str, float] = field(default_factory=dict)
    _operation_counts: Dict[str, int] = field(default_factory=dict)
    
    def register_component(self, name: str) -> None:
        """Register a component for resource tracking."""
        self._memory_usage[name] = 0.0
        self._operation_counts[name] = 0
        
    def unregister_component(self, name: str) -> None:
        """Unregister a component from resource tracking."""
        self._memory_usage.pop(name, None)
        self._operation_counts.pop(name, None)
        
    def update_memory_usage(self, component: str, usage_mb: float) -> bool:
        """Update memory usage for a component.
        
        Returns:
            bool: True if within limits, False otherwise
        """
        self._memory_usage[component] = usage_mb
        total_usage = sum(self._memory_usage.values())
        
        if total_usage > self.limits.max_memory_mb:
            self.logger.warning(f"Memory usage exceeded: {total_usage}MB > {self.limits.max_memory_mb}MB")
            return False
        return True
        
    def increment_operations(self, component: str) -> bool:
        """Increment operation count for a component.
        
        Returns:
            bool: True if within limits, False otherwise
        """
        self._operation_counts[component] = self._operation_counts.get(component, 0) + 1
        total_ops = sum(self._operation_counts.values())
        
        if total_ops > self.limits.max_concurrent_operations:
            self.logger.warning(
                f"Operation limit exceeded: {total_ops} > {self.limits.max_concurrent_operations}"
            )
            return False
        return True
        
    def decrement_operations(self, component: str) -> None:
        """Decrement operation count for a component."""
        if component in self._operation_counts and self._operation_counts[component] > 0:
            self._operation_counts[component] -= 1
            
    def get_component_stats(self, component: str) -> Dict[str, Any]:
        """Get resource statistics for a component."""
        return {
            'memory_usage_mb': self._memory_usage.get(component, 0.0),
            'operation_count': self._operation_counts.get(component, 0)
        }
        
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system resource statistics."""
        return {
            'total_memory_usage_mb': sum(self._memory_usage.values()),
            'total_operations': sum(self._operation_counts.values()),
            'component_count': len(self._memory_usage),
            'memory_limit_mb': self.limits.max_memory_mb,
            'operation_limit': self.limits.max_concurrent_operations
        } 