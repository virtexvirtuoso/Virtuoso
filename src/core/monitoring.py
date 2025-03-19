import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class HealthStatus:
    """Health status of a component."""
    healthy: bool
    last_check: datetime
    error: Optional[str] = None

class Monitor:
    """Simple system health monitor."""
    
    def __init__(self):
        """Initialize monitor."""
        self.logger = logging.getLogger(__name__)
        self.component_health: Dict[str, HealthStatus] = {}
        
    async def check_health(self, components: Dict[str, Any]) -> Dict[str, bool]:
        """Check health of all components.
        
        Args:
            components: Dictionary of component name to component instance
            
        Returns:
            Dictionary of component name to health status
        """
        results = {}
        for name, component in components.items():
            try:
                is_healthy = await component.is_healthy() if hasattr(component, 'is_healthy') else True
                
                status = HealthStatus(
                    healthy=is_healthy,
                    last_check=datetime.now()
                )
                self.component_health[name] = status
                results[name] = is_healthy
                
                if not is_healthy:
                    self.logger.warning(f"Component {name} is unhealthy")
                    
            except Exception as e:
                error_status = HealthStatus(
                    healthy=False,
                    last_check=datetime.now(),
                    error=str(e)
                )
                self.component_health[name] = error_status
                results[name] = False
                self.logger.error(f"Health check failed for {name}: {str(e)}")
                
        return results
        
    def get_system_health(self) -> Dict[str, Dict[str, Any]]:
        """Get current health status of all components."""
        return {
            name: {
                'healthy': status.healthy,
                'last_check': status.last_check.isoformat(),
                'error': status.error
            }
            for name, status in self.component_health.items()
        } 