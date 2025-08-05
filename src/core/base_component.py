"""
Base component class with proper initialization state management.
Prevents duplicate initialization and provides timeout protection.
"""

import asyncio
import logging
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime


class InitializationState(Enum):
    """Component initialization states."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class BaseComponent:
    """Base class for all async components with proper initialization management."""
    
    def __init__(self, config: Dict[str, Any], component_name: str = None):
        self.config = config
        self.component_name = component_name or self.__class__.__name__
        self.logger = logging.getLogger(f"src.core.{self.component_name}")
        
        # Initialization state management
        self._init_state = InitializationState.NOT_STARTED
        self._init_lock = asyncio.Lock()
        self._init_start_time: Optional[datetime] = None
        self._init_end_time: Optional[datetime] = None
        self._init_error: Optional[str] = None
        
        # Component state
        self.initialized = False
        
    @property
    def initialization_state(self) -> InitializationState:
        """Get current initialization state."""
        return self._init_state
    
    @property
    def initialization_duration(self) -> Optional[float]:
        """Get initialization duration in seconds."""
        if self._init_start_time and self._init_end_time:
            return (self._init_end_time - self._init_start_time).total_seconds()
        return None
    
    async def initialize(self, timeout: float = 30.0) -> bool:
        """
        Initialize the component with proper state management and timeout.
        
        Args:
            timeout: Maximum time allowed for initialization in seconds
            
        Returns:
            bool: True if initialization successful, False otherwise
        """
        async with self._init_lock:
            # Check if already initialized
            if self._init_state == InitializationState.COMPLETED:
                self.logger.debug(f"{self.component_name} already initialized")
                return True
            
            # Check if initialization is in progress
            if self._init_state == InitializationState.IN_PROGRESS:
                self.logger.warning(f"{self.component_name} initialization already in progress")
                return False
            
            # Check if previously failed
            if self._init_state == InitializationState.FAILED:
                self.logger.info(f"{self.component_name} reinitializing after previous failure")
            
            # Start initialization
            self._init_state = InitializationState.IN_PROGRESS
            self._init_start_time = datetime.now()
            self._init_error = None
            
            try:
                self.logger.info(f"Initializing {self.component_name} with {timeout}s timeout...")
                
                # Use asyncio.timeout for Python 3.11+
                async with asyncio.timeout(timeout):
                    success = await self._do_initialize()
                
                if success:
                    self._init_state = InitializationState.COMPLETED
                    self._init_end_time = datetime.now()
                    self.initialized = True
                    self.logger.info(
                        f"{self.component_name} initialized successfully in "
                        f"{self.initialization_duration:.2f}s"
                    )
                    return True
                else:
                    self._init_state = InitializationState.FAILED
                    self._init_end_time = datetime.now()
                    self._init_error = "Initialization returned False"
                    self.logger.error(f"{self.component_name} initialization failed")
                    return False
                    
            except asyncio.TimeoutError:
                self._init_state = InitializationState.FAILED
                self._init_end_time = datetime.now()
                self._init_error = f"Timeout after {timeout}s"
                self.logger.error(f"{self.component_name} initialization timed out after {timeout}s")
                return False
                
            except Exception as e:
                self._init_state = InitializationState.FAILED
                self._init_end_time = datetime.now()
                self._init_error = str(e)
                self.logger.error(f"{self.component_name} initialization failed: {str(e)}")
                return False
    
    async def _do_initialize(self) -> bool:
        """
        Perform actual initialization. Override in subclasses.
        
        Returns:
            bool: True if initialization successful
        """
        raise NotImplementedError("Subclasses must implement _do_initialize")
    
    async def close(self) -> None:
        """Clean up resources. Override in subclasses if needed."""
        self.logger.info(f"Closing {self.component_name}")
        self.initialized = False
        self._init_state = InitializationState.NOT_STARTED
    
    def get_status(self) -> Dict[str, Any]:
        """Get component status information."""
        return {
            "component": self.component_name,
            "initialized": self.initialized,
            "state": self._init_state.value,
            "init_duration": self.initialization_duration,
            "init_error": self._init_error,
            "init_start_time": self._init_start_time.isoformat() if self._init_start_time else None,
            "init_end_time": self._init_end_time.isoformat() if self._init_end_time else None,
        }