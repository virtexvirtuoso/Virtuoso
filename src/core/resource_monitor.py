"""Resource monitoring module."""

import psutil
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class SystemResources:
    """Basic system resource monitoring."""
    
    warning_memory_percent: float = 80.0
    warning_cpu_percent: float = 90.0
    
    def check_resources(self) -> Dict[str, Any]:
        """Check current system resource usage.
        
        Returns:
            Dictionary containing resource usage metrics
        """
        try:
            return {
                'memory_percent': psutil.virtual_memory().percent,
                'cpu_percent': psutil.cpu_percent(interval=1),
                'healthy': self._is_healthy()
            }
        except Exception:
            return {'healthy': False}
            
    def _is_healthy(self) -> bool:
        """Check if resource usage is within acceptable limits.
        
        Returns:
            bool: True if resource usage is acceptable
        """
        try:
            mem = psutil.virtual_memory().percent
            cpu = psutil.cpu_percent(interval=1)
            return (mem < self.warning_memory_percent and 
                   cpu < self.warning_cpu_percent)
        except Exception:
            return False 