"""Base component implementation."""

import logging
from typing import Optional

class BaseComponent:
    """Base class for system components."""
    
    def __init__(self, name: Optional[str] = None):
        """Initialize base component.
        
        Args:
            name: Optional component name
        """
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(self.name)
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the component."""
        if self._initialized:
            return
            
        try:
            await self._do_initialize()
            self._initialized = True
            self.logger.info(f"Initialized {self.name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name}: {str(e)}")
            raise
            
    async def cleanup(self) -> None:
        """Clean up component resources."""
        if not self._initialized:
            return
            
        try:
            await self._do_cleanup()
            self._initialized = False
            self.logger.info(f"Cleaned up {self.name}")
        except Exception as e:
            self.logger.error(f"Failed to clean up {self.name}: {str(e)}")
            raise
            
    async def is_healthy(self) -> bool:
        """Check if component is healthy."""
        return self._initialized
        
    async def _do_initialize(self) -> None:
        """Implement component-specific initialization."""
        pass
        
    async def _do_cleanup(self) -> None:
        """Implement component-specific cleanup."""
        pass 