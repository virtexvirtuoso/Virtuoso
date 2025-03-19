"""Unified lifecycle management system.

This package provides a comprehensive lifecycle management system for handling component
initialization, state transitions, and cleanup in a reliable and consistent manner.

Key Components:
    - LifecycleManager: Central manager for component lifecycle
    - ComponentState: Enumeration of possible component states
    - StateTransition: Represents and validates state transitions
    - InitializationContext: Context for component initialization
    - CleanupContext: Context for component cleanup
    - ComponentLifecycle: Manages individual component lifecycle
    - LifecycleStage: Lifecycle stages for hooks
    - LifecycleHook: Hook for lifecycle events
    - LifecycleConfig: Configuration for lifecycle management

Example:
    ```python
    # Initialize the lifecycle manager
    lifecycle_manager = LifecycleManager(error_manager=error_manager)

    # Register a component
    lifecycle = await lifecycle_manager.register_component(
        "data_processor",
        config=LifecycleConfig(
            initialization_timeout=30.0,
            required_dependencies={"database"}
        )
    )

    # Add lifecycle hooks
    lifecycle.add_hook(LifecycleHook(
        stage=LifecycleStage.PRE_INIT,
        callback=prepare_initialization
    ))

    # Initialize the component
    context = InitializationContext(
        name="data_processor",
        config={"timeout": 30.0}
    )
    success = await lifecycle_manager.initialize_component("data_processor", context)
    ```
"""

from .manager import LifecycleManager
from .states import ComponentState, StateTransition
from .context import InitializationContext, CleanupContext
from .models import (
    ComponentLifecycle,
    LifecycleStage,
    LifecycleHook,
    LifecycleConfig
)

__all__ = [
    'LifecycleManager',
    'ComponentState',
    'StateTransition',
    'InitializationContext',
    'CleanupContext',
    'ComponentLifecycle',
    'LifecycleStage',
    'LifecycleHook',
    'LifecycleConfig'
] 