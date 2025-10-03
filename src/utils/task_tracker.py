"""Asyncio task tracking utility for proper resource management.

This module provides centralized task tracking to prevent resource leaks
and ensure proper cleanup during application shutdown.
"""

import asyncio
import logging
from typing import Set

logger = logging.getLogger(__name__)

# Global set to track all background tasks
background_tasks: Set[asyncio.Task] = set()


def create_tracked_task(coro, name=None):
    """Create a task with proper tracking for cleanup.

    Args:
        coro: The coroutine to run as a task
        name: Optional name for the task (for debugging)

    Returns:
        The created asyncio.Task with tracking enabled
    """
    global background_tasks

    task = asyncio.create_task(coro)
    if name and hasattr(task, 'set_name'):
        task.set_name(name)

    # Add to tracking set
    background_tasks.add(task)

    # Remove from set when done (success or failure)
    def task_done_callback(task):
        background_tasks.discard(task)
        task_name = getattr(task, 'get_name', lambda: str(task))()
        if task.cancelled():
            logger.debug(f"Task {task_name} was cancelled")
        elif task.exception():
            logger.error(f"Task {task_name} failed: {task.exception()}")

    task.add_done_callback(task_done_callback)
    return task


async def cleanup_background_tasks():
    """Gracefully cleanup all background tasks."""
    global background_tasks

    if not background_tasks:
        return

    logger.info(f"Cleaning up {len(background_tasks)} background tasks...")

    # Cancel all tasks
    for task in background_tasks:
        if not task.done():
            task.cancel()

    # Wait for all tasks to complete or be cancelled
    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)

    # Clear the set
    background_tasks.clear()
    logger.info("✅ All background tasks cleaned up")


def get_task_count() -> int:
    """Get the current number of tracked tasks."""
    return len(background_tasks)


def get_task_info() -> dict:
    """Get information about currently tracked tasks."""
    return {
        'total_tasks': len(background_tasks),
        'running_tasks': len([t for t in background_tasks if not t.done()]),
        'completed_tasks': len([t for t in background_tasks if t.done() and not t.cancelled()]),
        'cancelled_tasks': len([t for t in background_tasks if t.cancelled()]),
        'failed_tasks': len([t for t in background_tasks if t.done() and t.exception()]),
    }