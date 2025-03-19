"""Lifecycle context objects.

This module provides context objects for managing component lifecycle operations:
- InitializationContext: Manages component initialization
- CleanupContext: Manages component cleanup

These context objects maintain state and provide utilities for their respective
lifecycle operations, ensuring proper tracking and management of the process.

Example:
    ```python
    # Create initialization context
    init_context = InitializationContext(
        name="data_processor",
        config={"timeout": 30.0},
        required_dependencies={"database"},
        optional_dependencies={"cache"}
    )

    # Track initialization attempts
    try:
        # Attempt initialization
        pass
    except Exception as e:
        init_context.record_attempt(error=e)
        if init_context.should_retry:
            # Retry after delay
            await asyncio.sleep(init_context.next_retry_delay)
    ```
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set
from datetime import datetime

@dataclass
class InitializationContext:
    """Context for component initialization.
    
    Manages the initialization process for a component, including configuration,
    dependencies, timing, and state tracking.
    
    Attributes:
        name: Component name
        config: Component configuration
        required_dependencies: Set of required dependency names
        optional_dependencies: Set of optional dependency names
        resolved_dependencies: Map of resolved dependency instances
        timeout: Maximum time allowed for initialization
        retry_count: Maximum number of retry attempts
        retry_delay: Base delay between retries
        attempt: Current attempt number
        start_time: When initialization started
        last_attempt_time: When last attempt was made
        error_history: List of errors from failed attempts
    
    Methods:
        record_attempt: Record an initialization attempt
        elapsed_time: Get time elapsed since start
        should_retry: Check if another retry is allowed
        next_retry_delay: Get delay for next retry
    """
    
    # Component information
    name: str
    config: Dict[str, Any]
    
    # Dependencies
    required_dependencies: Set[str] = field(default_factory=set)
    optional_dependencies: Set[str] = field(default_factory=set)
    resolved_dependencies: Dict[str, Any] = field(default_factory=dict)
    
    # Timing configuration
    timeout: float = 30.0
    retry_count: int = 3
    retry_delay: float = 5.0
    
    # State tracking
    attempt: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    last_attempt_time: Optional[datetime] = None
    error_history: List[Exception] = field(default_factory=list)
    
    def record_attempt(self, error: Optional[Exception] = None) -> None:
        """Record an initialization attempt.
        
        Args:
            error: Optional exception if attempt failed
        """
        self.attempt += 1
        self.last_attempt_time = datetime.now()
        if error:
            self.error_history.append(error)
            
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since initialization started.
        
        Returns:
            float: Seconds elapsed since start
        """
        return (datetime.now() - self.start_time).total_seconds()
        
    @property
    def should_retry(self) -> bool:
        """Check if another retry attempt should be made.
        
        Returns:
            bool: True if retry is allowed, False otherwise
        """
        return (
            self.attempt < self.retry_count and
            self.elapsed_time < self.timeout
        )
        
    @property
    def next_retry_delay(self) -> float:
        """Get delay for next retry attempt with exponential backoff.
        
        Returns:
            float: Seconds to wait before next attempt
        """
        return min(self.retry_delay * (2 ** (self.attempt - 1)), 30.0)

@dataclass
class CleanupContext:
    """Context for component cleanup.
    
    Manages the cleanup process for a component, tracking progress and errors.
    
    Attributes:
        name: Component name
        config: Component configuration
        dependencies: List of dependencies to clean up
        timeout: Maximum time allowed for cleanup
        start_time: When cleanup started
        completed_steps: List of completed cleanup steps
        errors: Map of step names to errors
    
    Methods:
        record_step: Record a cleanup step completion
        elapsed_time: Get time elapsed since start
        is_complete: Check if cleanup is complete
        remaining_steps: Get list of remaining steps
        has_errors: Check if any errors occurred
    """
    
    # Component information
    name: str
    config: Dict[str, Any]
    
    # Dependencies to clean up
    dependencies: List[str] = field(default_factory=list)
    
    # Timing configuration
    timeout: float = 30.0
    
    # State tracking
    start_time: datetime = field(default_factory=datetime.now)
    completed_steps: List[str] = field(default_factory=list)
    errors: Dict[str, Exception] = field(default_factory=dict)
    
    def record_step(self, step: str, error: Optional[Exception] = None) -> None:
        """Record a cleanup step.
        
        Args:
            step: Name of the step completed
            error: Optional exception if step failed
        """
        if error:
            self.errors[step] = error
        else:
            self.completed_steps.append(step)
            
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since cleanup started.
        
        Returns:
            float: Seconds elapsed since start
        """
        return (datetime.now() - self.start_time).total_seconds()
        
    @property
    def is_complete(self) -> bool:
        """Check if cleanup is complete.
        
        Returns:
            bool: True if all steps are complete
        """
        return len(self.completed_steps) == len(set(self.dependencies))
        
    @property
    def remaining_steps(self) -> List[str]:
        """Get list of remaining cleanup steps.
        
        Returns:
            List[str]: Names of incomplete steps
        """
        completed = set(self.completed_steps)
        return [dep for dep in self.dependencies if dep not in completed]
        
    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred during cleanup.
        
        Returns:
            bool: True if any steps had errors
        """
        return len(self.errors) > 0 