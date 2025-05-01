"""Component lifecycle states."""

from enum import Enum, auto
from typing import Optional, Dict, Set, Tuple
from datetime import datetime

class ComponentState(Enum):
    """States a component can be in."""
    
    UNINITIALIZED = auto()   # Initial state before registration
    REGISTERED = auto()      # Component is registered but not initialized
    INITIALIZING = auto()    # Component is being initialized
    RUNNING = auto()         # Component is running normally
    PAUSED = auto()          # Component is paused but still active
    STOPPING = auto()        # Component is being stopped
    STOPPED = auto()         # Component is being stopped
    SHUTTING_DOWN = auto()   # Component is shutting down
    TERMINATED = auto()      # Component has been terminated
    ERROR = auto()           # Component is in error state
    RECOVERING = auto()      # Component is recovering from error

class StateTransition:
    """Represents a transition from one state to another."""
    
    def __init__(
        self,
        from_state: ComponentState,
        to_state: ComponentState,
        reason: str,
        timestamp: Optional[datetime] = None,
        error: Optional[Exception] = None,
        is_valid: bool = True,
        validation_error: Optional[str] = None
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        self.timestamp = timestamp or datetime.now()
        self.error = error
        self.is_valid = is_valid
        self.validation_error = validation_error

class StateValidator:
    """Validates state transitions based on rules."""
    
    def __init__(self):
        # Define valid state transitions
        self._valid_transitions: Dict[ComponentState, Set[ComponentState]] = {
            ComponentState.UNINITIALIZED: {
                ComponentState.REGISTERED, ComponentState.ERROR
            },
            ComponentState.REGISTERED: {
                ComponentState.INITIALIZING, ComponentState.ERROR
            },
            ComponentState.INITIALIZING: {
                ComponentState.RUNNING, ComponentState.ERROR, ComponentState.RECOVERING
            },
            ComponentState.RUNNING: {
                ComponentState.STOPPING, ComponentState.ERROR, 
                ComponentState.SHUTTING_DOWN, ComponentState.PAUSED
            },
            ComponentState.PAUSED: {
                ComponentState.RUNNING, ComponentState.STOPPING, 
                ComponentState.ERROR, ComponentState.SHUTTING_DOWN
            },
            ComponentState.STOPPING: {
                ComponentState.STOPPED, ComponentState.ERROR, 
                ComponentState.RUNNING
            },
            ComponentState.STOPPED: {
                ComponentState.INITIALIZING, ComponentState.SHUTTING_DOWN
            },
            ComponentState.SHUTTING_DOWN: {
                ComponentState.TERMINATED, ComponentState.ERROR
            },
            ComponentState.ERROR: {
                ComponentState.RECOVERING, ComponentState.TERMINATED, 
                ComponentState.SHUTTING_DOWN
            },
            ComponentState.RECOVERING: {
                ComponentState.RUNNING, ComponentState.ERROR, 
                ComponentState.SHUTTING_DOWN
            },
            ComponentState.TERMINATED: set()  # Terminal state
        }
    
    def validate_transition(
        self,
        from_state: ComponentState,
        to_state: ComponentState,
        reason: str,
        error: Optional[Exception] = None
    ) -> StateTransition:
        """Validate a state transition based on defined rules."""
        if to_state in self._valid_transitions.get(from_state, set()):
            return StateTransition(
                from_state=from_state,
                to_state=to_state,
                reason=reason,
                error=error,
                is_valid=True
            )
        else:
            return StateTransition(
                from_state=from_state,
                to_state=to_state,
                reason=reason,
                error=error,
                is_valid=False,
                validation_error=f"Invalid transition from {from_state} to {to_state}"
            ) 