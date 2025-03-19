"""Component lifecycle states."""

from enum import Enum, auto

class ComponentState(Enum):
    """States a component can be in."""
    
    REGISTERED = auto()      # Component is registered but not initialized
    INITIALIZING = auto()    # Component is being initialized
    RUNNING = auto()         # Component is running normally
    STOPPING = auto()        # Component is being stopped
    STOPPED = auto()         # Component has been stopped
    ERROR = auto()           # Component is in error state
    RECOVERING = auto()      # Component is recovering from error 