"""Event handling system."""

import logging
from typing import Dict, Any, Callable, List
from .base import BaseComponent

EventHandler = Callable[[str, Any], None]

class EventBus(BaseComponent):
    """Simple event bus for system-wide events."""
    
    def __init__(self):
        """Initialize event bus."""
        super().__init__("EventBus")
        self._handlers: Dict[str, List[EventHandler]] = {}
        
    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Event handler function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        self.logger.info(f"Subscribed handler to {event_type}")
        
    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            handler: Event handler function
        """
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
            self.logger.info(f"Unsubscribed handler from {event_type}")
            
    async def publish(self, event_type: str, data: Any = None) -> None:
        """Publish an event.
        
        Args:
            event_type: Type of event to publish
            data: Optional event data
        """
        if event_type not in self._handlers:
            return
            
        for handler in self._handlers[event_type]:
            try:
                await handler(event_type, data)
            except Exception as e:
                self.logger.error(f"Event handler failed for {event_type}: {str(e)}")
                
    async def _do_cleanup(self) -> None:
        """Clean up event handlers."""
        self._handlers.clear() 