from typing import Dict, Set, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StateTransitionError(Exception):
    """Raised when a state transition is invalid."""
    pass

class ComponentState(Enum):
    """Possible states for components."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"

@dataclass
class StateTransition:
    """Represents a state transition event."""
    from_state: ComponentState
    to_state: ComponentState
    timestamp: datetime
    reason: Optional[str] = None
    error: Optional[Exception] = None

class StateManager:
    """Manages component states and transitions."""
    
    def __init__(self):
        self._states: Dict[str, ComponentState] = {}
        self._history: Dict[str, List[StateTransition]] = {}
        self._state_handlers: Dict[ComponentState, List[Callable]] = {}
        self._transition_validators: Dict[tuple[ComponentState, ComponentState], List[Callable]] = {}
        self._state_conditions: Dict[str, asyncio.Condition] = {}
        
    async def set_state(
        self,
        component_name: str,
        new_state: ComponentState,
        reason: Optional[str] = None,
        error: Optional[Exception] = None
    ) -> None:
        """Set component state with validation."""
        current_state = self._states.get(component_name, ComponentState.UNINITIALIZED)
        
        # Validate transition
        if not await self._validate_transition(component_name, current_state, new_state):
            raise StateTransitionError(
                f"Invalid transition from {current_state} to {new_state} for {component_name}"
            )
            
        # Record transition
        transition = StateTransition(
            from_state=current_state,
            to_state=new_state,
            timestamp=datetime.now(),
            reason=reason,
            error=error
        )
        
        self._states[component_name] = new_state
        self._history.setdefault(component_name, []).append(transition)
        
        # Notify state change
        if component_name in self._state_conditions:
            async with self._state_conditions[component_name]:
                self._state_conditions[component_name].notify_all()
                
        # Execute state handlers
        await self._execute_state_handlers(new_state, component_name, transition)
        
    async def get_state(self, component_name: str) -> ComponentState:
        """Get current state of a component."""
        return self._states.get(component_name, ComponentState.UNINITIALIZED)
        
    async def wait_for_state(
        self,
        component_name: str,
        target_state: ComponentState,
        timeout: Optional[float] = None
    ) -> bool:
        """Wait for component to reach target state."""
        if component_name not in self._state_conditions:
            self._state_conditions[component_name] = asyncio.Condition()
            
        async with self._state_conditions[component_name]:
            try:
                start_time = datetime.now()
                while self._states.get(component_name) != target_state:
                    if timeout is not None:
                        remaining = timeout - (datetime.now() - start_time).total_seconds()
                        if remaining <= 0:
                            return False
                        await asyncio.wait_for(
                            self._state_conditions[component_name].wait(),
                            timeout=remaining
                        )
                    else:
                        await self._state_conditions[component_name].wait()
                return True
            except asyncio.TimeoutError:
                return False
                
    def register_state_handler(
        self,
        state: ComponentState,
        handler: Callable[[str, StateTransition], Any]
    ) -> None:
        """Register handler for state changes."""
        self._state_handlers.setdefault(state, []).append(handler)
        
    def register_transition_validator(
        self,
        from_state: ComponentState,
        to_state: ComponentState,
        validator: Callable[[str], bool]
    ) -> None:
        """Register validator for state transitions."""
        key = (from_state, to_state)
        self._transition_validators.setdefault(key, []).append(validator)
        
    def get_state_history(
        self,
        component_name: str,
        since: Optional[datetime] = None
    ) -> List[StateTransition]:
        """Get state transition history for a component."""
        history = self._history.get(component_name, [])
        if since is not None:
            history = [t for t in history if t.timestamp >= since]
        return history
        
    async def _validate_transition(
        self,
        component_name: str,
        from_state: ComponentState,
        to_state: ComponentState
    ) -> bool:
        """Validate state transition using registered validators."""
        validators = self._transition_validators.get((from_state, to_state), [])
        return all(validator(component_name) for validator in validators)
        
    async def _execute_state_handlers(
        self,
        state: ComponentState,
        component_name: str,
        transition: StateTransition
    ) -> None:
        """Execute handlers for state change."""
        handlers = self._state_handlers.get(state, [])
        for handler in handlers:
            try:
                await handler(component_name, transition)
            except Exception as e:
                logger.error(f"Error in state handler: {str(e)}") 