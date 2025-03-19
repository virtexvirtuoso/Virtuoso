"""Core component protocols."""

from typing import Protocol, Dict, Any

class Component(Protocol):
    """Basic component interface."""
    
    async def initialize(self) -> None:
        """Initialize the component."""
        ...
        
    async def cleanup(self) -> None:
        """Clean up component resources."""
        ...
        
    async def is_healthy(self) -> bool:
        """Check if component is healthy."""
        return True

class DataProcessor(Component, Protocol):
    """Data processing component interface."""
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data."""
        ...

class EventHandler(Component, Protocol):
    """Event handling component interface."""
    
    async def handle_event(self, event_type: str, data: Any) -> None:
        """Handle an event."""
        ... 