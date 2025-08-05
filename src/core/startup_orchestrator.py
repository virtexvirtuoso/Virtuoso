"""
Startup orchestrator for controlled component initialization.
Ensures components are initialized in the correct order with proper timeouts.
"""

import asyncio
import logging
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime


class StartupOrchestrator:
    """Orchestrates system startup with proper initialization order and timeouts."""
    
    def __init__(self):
        self.logger = logging.getLogger("src.core.StartupOrchestrator")
        self.components: Dict[str, Any] = {}
        self.initialization_times: Dict[str, float] = {}
        self.initialization_errors: Dict[str, str] = {}
        
    def register_component(self, name: str, component: Any) -> None:
        """Register a component for initialization."""
        self.components[name] = component
        self.logger.debug(f"Registered component: {name}")
    
    async def initialize_all(self, initialization_order: Optional[List[Tuple[str, float]]] = None) -> bool:
        """
        Initialize all components in the specified order.
        
        Args:
            initialization_order: List of (component_name, timeout) tuples
            
        Returns:
            bool: True if all components initialized successfully
        """
        if initialization_order is None:
            # Default initialization order
            initialization_order = [
                ("config_manager", 5.0),
                ("database_client", 10.0),
                ("exchange_manager", 30.0),
                ("market_data_manager", 20.0),
                ("confluence_analyzer", 10.0),
                ("alert_manager", 10.0),
                ("market_monitor", 15.0),
                ("dashboard_integration", 10.0),
            ]
        
        self.logger.info(f"Starting system initialization with {len(initialization_order)} components")
        start_time = datetime.now()
        success_count = 0
        
        for component_name, timeout in initialization_order:
            if component_name not in self.components:
                self.logger.warning(f"Component {component_name} not registered, skipping")
                continue
            
            component = self.components[component_name]
            component_start = datetime.now()
            
            try:
                self.logger.info(f"Initializing {component_name} with {timeout}s timeout...")
                
                # Check if component has our new initialize method
                if hasattr(component, 'initialize') and hasattr(component, 'initialization_state'):
                    # Use new initialization pattern
                    success = await component.initialize(timeout=timeout)
                else:
                    # Fallback for legacy components
                    async with asyncio.timeout(timeout):
                        if hasattr(component, 'initialize'):
                            success = await component.initialize()
                        else:
                            self.logger.warning(f"Component {component_name} has no initialize method")
                            success = True
                
                duration = (datetime.now() - component_start).total_seconds()
                self.initialization_times[component_name] = duration
                
                if success:
                    self.logger.info(f"✅ {component_name} initialized in {duration:.2f}s")
                    success_count += 1
                else:
                    error_msg = f"{component_name} initialization returned False"
                    self.logger.error(f"❌ {error_msg}")
                    self.initialization_errors[component_name] = error_msg
                    
            except asyncio.TimeoutError:
                duration = (datetime.now() - component_start).total_seconds()
                error_msg = f"Timeout after {timeout}s"
                self.logger.error(f"❌ {component_name} initialization timed out after {duration:.2f}s")
                self.initialization_errors[component_name] = error_msg
                
            except Exception as e:
                duration = (datetime.now() - component_start).total_seconds()
                error_msg = str(e)
                self.logger.error(f"❌ {component_name} initialization failed: {error_msg}")
                self.initialization_errors[component_name] = error_msg
        
        total_duration = (datetime.now() - start_time).total_seconds()
        self.logger.info(
            f"System initialization completed in {total_duration:.2f}s: "
            f"{success_count}/{len(initialization_order)} components successful"
        )
        
        # Log summary
        self._log_initialization_summary()
        
        return len(self.initialization_errors) == 0
    
    def _log_initialization_summary(self) -> None:
        """Log a summary of the initialization process."""
        self.logger.info("=" * 60)
        self.logger.info("Initialization Summary:")
        self.logger.info("=" * 60)
        
        # Successful initializations
        for name, duration in self.initialization_times.items():
            if name not in self.initialization_errors:
                self.logger.info(f"✅ {name:25} {duration:6.2f}s")
        
        # Failed initializations
        for name, error in self.initialization_errors.items():
            duration = self.initialization_times.get(name, 0.0)
            self.logger.error(f"❌ {name:25} {duration:6.2f}s - {error}")
        
        self.logger.info("=" * 60)
    
    def get_initialization_report(self) -> Dict[str, Any]:
        """Get a detailed initialization report."""
        return {
            "components": list(self.components.keys()),
            "successful": [
                name for name in self.initialization_times.keys()
                if name not in self.initialization_errors
            ],
            "failed": list(self.initialization_errors.keys()),
            "initialization_times": self.initialization_times,
            "errors": self.initialization_errors,
            "total_components": len(self.components),
            "successful_count": len(self.initialization_times) - len(self.initialization_errors),
            "failed_count": len(self.initialization_errors),
        }
    
    async def shutdown_all(self) -> None:
        """Shutdown all components in reverse order."""
        self.logger.info("Starting system shutdown...")
        
        # Shutdown in reverse order
        for name in reversed(list(self.components.keys())):
            component = self.components[name]
            
            try:
                if hasattr(component, 'close'):
                    self.logger.info(f"Closing {name}...")
                    await component.close()
                elif hasattr(component, 'stop'):
                    self.logger.info(f"Stopping {name}...")
                    await component.stop()
                    
            except Exception as e:
                self.logger.error(f"Error closing {name}: {str(e)}")
        
        self.logger.info("System shutdown complete")
