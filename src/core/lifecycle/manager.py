"""Lifecycle management system."""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Set
from datetime import datetime

from ..error.manager import ErrorManager
from ..error.models import ErrorSeverity, ErrorContext
from ..error.exceptions import (
    ComponentInitializationError,
    ComponentCleanupError,
    StateError
)

from .states import ComponentState, StateValidator, StateTransition
from .models import ComponentLifecycle, LifecycleConfig, LifecycleStage, LifecycleHook
from .context import InitializationContext, CleanupContext

logger = logging.getLogger(__name__)

class LifecycleManager:
    """Manages component lifecycles and state transitions."""
    
    def __init__(
        self,
        error_manager: ErrorManager,
        default_config: Optional[LifecycleConfig] = None
    ):
        self._error_manager = error_manager
        self._default_config = default_config or LifecycleConfig()
        self._state_validator = StateValidator()
        self._components: Dict[str, ComponentLifecycle] = {}
        self._initialization_lock = asyncio.Lock()
        
    def register_component(
        self,
        name: str,
        config: Optional[LifecycleConfig] = None
    ) -> ComponentLifecycle:
        """Register a new component."""
        if name in self._components:
            raise ValueError(f"Component {name} already registered")
            
        lifecycle = ComponentLifecycle(
            name=name,
            config=config or self._default_config
        )
        self._components[name] = lifecycle
        return lifecycle
        
    async def initialize_component(
        self,
        name: str,
        context: InitializationContext
    ) -> bool:
        """Initialize a component with retry logic."""
        async with self._initialization_lock:
            lifecycle = self._components.get(name)
            if not lifecycle:
                raise ValueError(f"Component {name} not registered")
                
            if not lifecycle.can_initialize:
                raise StateError(
                    f"Component {name} cannot be initialized in state {lifecycle.current_state}"
                )
                
            while context.should_retry:
                try:
                    # Execute pre-init hooks
                    await self._execute_hooks(lifecycle, LifecycleStage.PRE_INIT)
                    
                    # Transition to initializing state
                    await self._transition_state(
                        lifecycle,
                        ComponentState.INITIALIZING,
                        f"Initializing component (attempt {context.attempt + 1})"
                    )
                    
                    # Check dependencies
                    if not await self._check_dependencies(context):
                        raise ComponentInitializationError(
                            f"Dependencies not ready for {name}"
                        )
                        
                    # Execute post-init hooks
                    await self._execute_hooks(lifecycle, LifecycleStage.POST_INIT)
                    
                    # Transition to running state
                    await self._transition_state(
                        lifecycle,
                        ComponentState.RUNNING,
                        "Component initialized successfully"
                    )
                    
                    logger.info(f"Successfully initialized component {name}")
                    return True
                    
                except Exception as e:
                    context.record_attempt(e)
                    
                    if not context.should_retry:
                        await self._handle_initialization_failure(name, e)
                        return False
                        
                    logger.warning(
                        f"Initialization failed for {name}, "
                        f"retrying in {context.next_retry_delay}s "
                        f"({context.attempt}/{context.retry_count})"
                    )
                    await asyncio.sleep(context.next_retry_delay)
                    
            return False
            
    async def cleanup_component(
        self,
        name: str,
        context: CleanupContext
    ) -> bool:
        """Clean up a component."""
        lifecycle = self._components.get(name)
        if not lifecycle:
            return True  # Already cleaned up
            
        if not lifecycle.can_cleanup:
            raise StateError(
                f"Component {name} cannot be cleaned up in state {lifecycle.current_state}"
            )
            
        try:
            # Execute pre-cleanup hooks
            await self._execute_hooks(lifecycle, LifecycleStage.PRE_CLEANUP)
            
            # Transition to shutting down state
            await self._transition_state(
                lifecycle,
                ComponentState.SHUTTING_DOWN,
                "Starting component cleanup"
            )
            
            # Clean up dependencies
            for dep in context.dependencies:
                try:
                    if await self.cleanup_component(dep, context):
                        context.record_step(dep)
                    else:
                        context.record_step(dep, Exception(f"Failed to clean up {dep}"))
                except Exception as e:
                    context.record_step(dep, e)
                    
            # Execute post-cleanup hooks
            await self._execute_hooks(lifecycle, LifecycleStage.POST_CLEANUP)
            
            # Transition to terminated state
            await self._transition_state(
                lifecycle,
                ComponentState.TERMINATED,
                "Component cleanup successful"
            )
            
            return True
            
        except Exception as e:
            await self._handle_cleanup_failure(name, e)
            return False
            
    async def _transition_state(
        self,
        lifecycle: ComponentLifecycle,
        new_state: ComponentState,
        reason: str,
        error: Optional[Exception] = None
    ) -> None:
        """Transition a component to a new state."""
        transition = self._state_validator.validate_transition(
            lifecycle.current_state,
            new_state,
            reason,
            error
        )
        
        if not transition.is_valid:
            raise StateError(transition.validation_error)
            
        lifecycle.record_transition(transition)
        logger.info(
            f"Component {lifecycle.name} transitioned from "
            f"{transition.from_state.value} to {transition.to_state.value}: {reason}"
        )
        
    async def _execute_hooks(
        self,
        lifecycle: ComponentLifecycle,
        stage: LifecycleStage
    ) -> None:
        """Execute all hooks for a lifecycle stage."""
        hooks = lifecycle.get_hooks_for_stage(stage)
        for hook in hooks:
            try:
                async with asyncio.timeout(hook.timeout):
                    await hook.callback()
            except Exception as e:
                logger.error(
                    f"Error executing {stage.value} hook for {lifecycle.name}: {str(e)}"
                )
                raise
                
    async def _check_dependencies(self, context: InitializationContext) -> bool:
        """Check if all required dependencies are ready."""
        for dep in context.required_dependencies:
            dep_lifecycle = self._components.get(dep)
            if not dep_lifecycle or dep_lifecycle.current_state != ComponentState.RUNNING:
                return False
        return True
        
    async def _handle_initialization_failure(
        self,
        name: str,
        error: Exception
    ) -> None:
        """Handle component initialization failure."""
        lifecycle = self._components[name]
        error_msg = f"Component initialization failed: {str(error)}"
        logger.error(error_msg)
        
        # Register error
        await self._error_manager.handle_error(
            error=error,
            context=ErrorContext(
                component=name,
                operation="initialization"
            ),
            severity=ErrorSeverity.HIGH
        )
        
        # Transition to error state
        await self._transition_state(
            lifecycle,
            ComponentState.ERROR,
            error_msg,
            error
        )
        
    async def _handle_cleanup_failure(
        self,
        name: str,
        error: Exception
    ) -> None:
        """Handle component cleanup failure."""
        lifecycle = self._components[name]
        error_msg = f"Component cleanup failed: {str(error)}"
        logger.error(error_msg)
        
        # Register error
        await self._error_manager.handle_error(
            error=error,
            context=ErrorContext(
                component=name,
                operation="cleanup"
            ),
            severity=ErrorSeverity.HIGH
        )
        
        # Transition to error state
        await self._transition_state(
            lifecycle,
            ComponentState.ERROR,
            error_msg,
            error
        ) 