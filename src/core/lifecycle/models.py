"""Lifecycle-related data models."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set, Callable
from enum import Enum
from datetime import datetime

from .states import ComponentState, StateTransition

class LifecycleStage(Enum):
    """Lifecycle stages for hooks and events."""
    PRE_INIT = "pre_init"
    POST_INIT = "post_init"
    PRE_START = "pre_start"
    POST_START = "post_start"
    PRE_STOP = "pre_stop"
    POST_STOP = "post_stop"
    PRE_CLEANUP = "pre_cleanup"
    POST_CLEANUP = "post_cleanup"

@dataclass
class LifecycleHook:
    """Hook for lifecycle events."""
    stage: LifecycleStage
    callback: Callable
    priority: int = 0
    timeout: float = 30.0

@dataclass
class LifecycleConfig:
    """Configuration for component lifecycle."""
    initialization_timeout: float = 30.0
    startup_timeout: float = 30.0
    shutdown_timeout: float = 30.0
    cleanup_timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 5.0
    required_dependencies: Set[str] = field(default_factory=set)
    optional_dependencies: Set[str] = field(default_factory=set)

@dataclass
class ComponentLifecycle:
    """Manages component lifecycle and state transitions."""
    
    name: str
    config: LifecycleConfig = field(default_factory=LifecycleConfig)
    current_state: ComponentState = ComponentState.UNINITIALIZED
    last_transition: Optional[StateTransition] = None
    state_history: List[StateTransition] = field(default_factory=list)
    hooks: Dict[LifecycleStage, List[LifecycleHook]] = field(default_factory=lambda: {
        stage: [] for stage in LifecycleStage
    })
    
    # Timestamps for tracking
    created_at: datetime = field(default_factory=datetime.now)
    initialized_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    terminated_at: Optional[datetime] = None
    
    def add_hook(self, hook: LifecycleHook) -> None:
        """Add a lifecycle hook."""
        self.hooks[hook.stage].append(hook)
        # Sort hooks by priority (higher priority first)
        self.hooks[hook.stage].sort(key=lambda h: h.priority, reverse=True)
        
    def remove_hook(self, stage: LifecycleStage, callback: Callable) -> bool:
        """Remove a lifecycle hook."""
        stage_hooks = self.hooks[stage]
        for hook in stage_hooks[:]:
            if hook.callback == callback:
                stage_hooks.remove(hook)
                return True
        return False
        
    def record_transition(self, transition: StateTransition) -> None:
        """Record a state transition."""
        self.last_transition = transition
        self.state_history.append(transition)
        self.current_state = transition.to_state
        
        # Update timestamps
        now = datetime.now()
        if transition.to_state == ComponentState.RUNNING:
            self.started_at = now
        elif transition.to_state == ComponentState.STOPPED:
            self.stopped_at = now
        elif transition.to_state == ComponentState.TERMINATED:
            self.terminated_at = now
            
    @property
    def uptime(self) -> Optional[float]:
        """Get component uptime in seconds."""
        if not self.started_at:
            return None
            
        end_time = self.stopped_at or datetime.now()
        return (end_time - self.started_at).total_seconds()
        
    @property
    def can_initialize(self) -> bool:
        """Check if component can be initialized."""
        return self.current_state in {
            ComponentState.UNINITIALIZED,
            ComponentState.ERROR
        }
        
    @property
    def can_start(self) -> bool:
        """Check if component can be started."""
        return self.current_state in {
            ComponentState.INITIALIZING,
            ComponentState.STOPPED
        }
        
    @property
    def can_stop(self) -> bool:
        """Check if component can be stopped."""
        return self.current_state in {
            ComponentState.RUNNING,
            ComponentState.PAUSED
        }
        
    @property
    def can_cleanup(self) -> bool:
        """Check if component can be cleaned up."""
        return self.current_state in {
            ComponentState.STOPPED,
            ComponentState.ERROR
        }
        
    def get_hooks_for_stage(self, stage: LifecycleStage) -> List[LifecycleHook]:
        """Get all hooks for a specific lifecycle stage."""
        return self.hooks[stage] 