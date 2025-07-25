#!/usr/bin/env python3
"""
Fix async/sync issues in the codebase.

This script identifies and provides fixes for:
1. Blocking operations in async contexts
2. Synchronous methods that should be async
3. Missing await statements
"""

import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Issues found and their fixes
ISSUES_FOUND = [
    {
        "file": "src/utils/error_handling.py",
        "issue": "time.sleep() in retry_on_error decorator (blocking)",
        "line": 136,
        "fix": "Create async version of retry decorator using asyncio.sleep"
    },
    {
        "file": "src/core/resource_monitor.py",
        "issue": "psutil operations in check_resources() (blocking I/O)",
        "lines": [22, 23, 36, 37],
        "fix": "Run psutil calls in thread pool executor"
    },
    {
        "file": "src/monitoring/metrics_manager.py",
        "issue": "_get_memory_usage() called in async context without await",
        "line": 773,
        "fix": "Use _get_memory_usage_async() or run in executor"
    },
    {
        "file": "src/core/analysis/confluence.py",
        "issue": "_validate_market_data() is sync but should be async",
        "line": "multiple",
        "fix": "Make _validate_market_data async or run heavy operations in executor"
    },
    {
        "file": "src/core/exchanges/websocket_manager.py",
        "issue": "Sequential processing of WebSocket messages",
        "line": 381,
        "fix": "Already fixed - using asyncio.create_task() for concurrent processing"
    },
    {
        "file": "src/monitoring/monitor.py",
        "issue": "Orderbook sorting blocking event loop",
        "lines": [2238-2243],
        "fix": "Already fixed - using run_in_executor for sorting"
    }
]

# Code templates for fixes
ASYNC_RETRY_DECORATOR = '''
import asyncio
from typing import TypeVar, Callable, Any, cast
import functools

F = TypeVar('F', bound=Callable[..., Any])

def async_retry_on_error(max_attempts: int = 3, delay: float = 1.0) -> Callable[[F], F]:
    """Async decorator to retry function on error.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between retries in seconds
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempts = 0
            while attempts < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts == max_attempts:
                        logger.error(f"Max retry attempts ({max_attempts}) reached for {func.__name__}")
                        raise
                    logger.warning(f"Attempt {attempts} failed for {func.__name__}: {str(e)}")
                    await asyncio.sleep(delay)  # Non-blocking sleep
            return None
        return cast(F, wrapper)
    return decorator
'''

ASYNC_RESOURCE_MONITOR = '''
import asyncio
import psutil
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class AsyncSystemResources:
    """Async system resource monitoring."""
    
    warning_memory_percent: float = 80.0
    warning_cpu_percent: float = 90.0
    
    async def check_resources(self) -> Dict[str, Any]:
        """Check current system resource usage asynchronously.
        
        Returns:
            Dictionary containing resource usage metrics
        """
        try:
            loop = asyncio.get_event_loop()
            
            # Run blocking psutil calls in thread pool
            memory_percent = await loop.run_in_executor(
                None, lambda: psutil.virtual_memory().percent
            )
            cpu_percent = await loop.run_in_executor(
                None, lambda: psutil.cpu_percent(interval=1)
            )
            
            healthy = await self._is_healthy_async()
            
            return {
                'memory_percent': memory_percent,
                'cpu_percent': cpu_percent,
                'healthy': healthy
            }
        except Exception:
            return {'healthy': False}
            
    async def _is_healthy_async(self) -> bool:
        """Check if resource usage is within acceptable limits asynchronously.
        
        Returns:
            bool: True if resource usage is acceptable
        """
        try:
            loop = asyncio.get_event_loop()
            
            # Run blocking calls in thread pool
            mem = await loop.run_in_executor(
                None, lambda: psutil.virtual_memory().percent
            )
            cpu = await loop.run_in_executor(
                None, lambda: psutil.cpu_percent(interval=1)
            )
            
            return (mem < self.warning_memory_percent and 
                   cpu < self.warning_cpu_percent)
        except Exception:
            return False
'''

ASYNC_JSON_OPERATIONS = '''
import aiofiles
import json
from typing import Any, Dict

async def async_json_dump(filepath: str, data: Dict[str, Any], **kwargs) -> None:
    """Asynchronously write JSON data to file."""
    async with aiofiles.open(filepath, 'w') as f:
        content = json.dumps(data, **kwargs)
        await f.write(content)

async def async_json_load(filepath: str) -> Dict[str, Any]:
    """Asynchronously read JSON data from file."""
    async with aiofiles.open(filepath, 'r') as f:
        content = await f.read()
        return json.loads(content)
'''

def print_summary():
    """Print summary of issues found."""
    print("=" * 80)
    print("ASYNC/SYNC ISSUES FOUND AND FIXES")
    print("=" * 80)
    print()
    
    for i, issue in enumerate(ISSUES_FOUND, 1):
        print(f"{i}. {issue['file']}")
        print(f"   Issue: {issue['issue']}")
        print(f"   Line(s): {issue['line']}")
        print(f"   Fix: {issue['fix']}")
        print()
    
    print("=" * 80)
    print("RECOMMENDED ACTIONS:")
    print("=" * 80)
    print()
    print("1. Add async retry decorator to src/utils/error_handling.py")
    print("2. Create AsyncSystemResources class in src/core/resource_monitor.py")
    print("3. Use async JSON operations for file I/O in async contexts")
    print("4. Ensure all blocking operations use run_in_executor")
    print("5. Review and test all async code paths")
    print()
    print("Code templates have been provided above for reference.")

if __name__ == "__main__":
    print_summary()
    
    # Create example fixes
    fixes_dir = Path(__file__).parent / "async_fixes"
    fixes_dir.mkdir(exist_ok=True)
    
    # Write async retry decorator
    with open(fixes_dir / "async_retry_decorator.py", "w") as f:
        f.write(ASYNC_RETRY_DECORATOR)
    
    # Write async resource monitor
    with open(fixes_dir / "async_resource_monitor.py", "w") as f:
        f.write(ASYNC_RESOURCE_MONITOR)
    
    # Write async JSON operations
    with open(fixes_dir / "async_json_operations.py", "w") as f:
        f.write(ASYNC_JSON_OPERATIONS)
    
    print(f"\nExample fix files created in: {fixes_dir}")
    print("\nIMPORTANT: Review and test all changes before applying to production!")