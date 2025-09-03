"""
Batch Cache Operations Manager
High-performance batch operations to reduce cache overhead and improve throughput.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from collections import defaultdict
from .key_generator import CacheKeyGenerator

logger = logging.getLogger(__name__)

@dataclass
class BatchOperation:
    """Represents a single cache operation in a batch"""
    operation: str  # 'get', 'set', 'delete'
    key: str
    value: Any = None
    ttl: Optional[int] = None
    callback: Optional[callable] = None

@dataclass
class BatchResult:
    """Result of a batch operation"""
    success: bool
    results: Dict[str, Any]
    errors: List[str]
    execution_time_ms: float
    operations_count: int

class BatchCacheManager:
    """Efficient batch operations to reduce cache overhead"""
    
    def __init__(self, cache_adapter):
        self.cache_adapter = cache_adapter
        self.logger = logger
        self._batch_queue = defaultdict(list)
        self._processing = False
        self._stats = {
            'total_batches': 0,
            'total_operations': 0,
            'avg_batch_size': 0,
            'avg_execution_time': 0,
            'success_rate': 0
        }
    
    async def multi_get(self, keys: List[str], timeout: float = 1.0) -> Dict[str, Any]:
        """Batch get operation for multiple keys"""
        if not keys:
            return {}
            
        start_time = time.time()
        
        try:
            # Use the existing multi_get from cache adapter
            results = await asyncio.wait_for(
                self.cache_adapter.get_multiple(keys),
                timeout=timeout
            )
            
            execution_time = (time.time() - start_time) * 1000
            self.logger.debug(f"Batch get completed: {len(keys)} keys in {execution_time:.2f}ms")
            
            # Update stats
            self._update_stats(len(keys), execution_time, True)
            
            return results
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Batch get timeout for {len(keys)} keys")
            return {}
        except Exception as e:
            self.logger.error(f"Batch get error: {e}")
            return {}
    
    async def multi_set(self, data: Dict[str, Any], ttl: Optional[int] = None, timeout: float = 2.0) -> Dict[str, bool]:
        """Batch set operation for multiple key-value pairs"""
        if not data:
            return {}
            
        start_time = time.time()
        results = {}
        
        try:
            # Determine TTL for each key if not provided
            tasks = []
            for key, value in data.items():
                key_ttl = ttl if ttl else CacheKeyGenerator.get_ttl_for_key(key)
                task = self.cache_adapter.set(key, value, key_ttl)
                tasks.append((key, task))
            
            # Execute all sets in parallel
            set_results = await asyncio.wait_for(
                asyncio.gather(*[task for _, task in tasks], return_exceptions=True),
                timeout=timeout
            )
            
            # Map results back to keys
            for i, (key, _) in enumerate(tasks):
                result = set_results[i]
                if isinstance(result, Exception):
                    self.logger.error(f"Error setting {key}: {result}")
                    results[key] = False
                else:
                    results[key] = result
            
            execution_time = (time.time() - start_time) * 1000
            success_count = sum(1 for r in results.values() if r)
            
            self.logger.debug(f"Batch set completed: {success_count}/{len(data)} keys in {execution_time:.2f}ms")
            
            # Update stats
            self._update_stats(len(data), execution_time, success_count == len(data))
            
            return results
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Batch set timeout for {len(data)} keys")
            return {key: False for key in data.keys()}
        except Exception as e:
            self.logger.error(f"Batch set error: {e}")
            return {key: False for key in data.keys()}
    
    async def multi_delete(self, keys: List[str], timeout: float = 1.0) -> Dict[str, bool]:
        """Batch delete operation for multiple keys"""
        if not keys:
            return {}
            
        start_time = time.time()
        results = {}
        
        try:
            # Execute all deletes in parallel
            tasks = [(key, self.cache_adapter.delete(key)) for key in keys]
            
            delete_results = await asyncio.wait_for(
                asyncio.gather(*[task for _, task in tasks], return_exceptions=True),
                timeout=timeout
            )
            
            # Map results back to keys
            for i, (key, _) in enumerate(tasks):
                result = delete_results[i]
                if isinstance(result, Exception):
                    self.logger.error(f"Error deleting {key}: {result}")
                    results[key] = False
                else:
                    results[key] = result
            
            execution_time = (time.time() - start_time) * 1000
            success_count = sum(1 for r in results.values() if r)
            
            self.logger.debug(f"Batch delete completed: {success_count}/{len(keys)} keys in {execution_time:.2f}ms")
            
            return results
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Batch delete timeout for {len(keys)} keys")
            return {key: False for key in keys}
        except Exception as e:
            self.logger.error(f"Batch delete error: {e}")
            return {key: False for key in keys}
    
    async def execute_batch(self, operations: List[BatchOperation]) -> BatchResult:
        """Execute a batch of mixed cache operations"""
        if not operations:
            return BatchResult(True, {}, [], 0.0, 0)
        
        start_time = time.time()
        results = {}
        errors = []
        
        try:
            # Group operations by type for efficiency
            get_keys = [op.key for op in operations if op.operation == 'get']
            set_data = {op.key: op.value for op in operations if op.operation == 'set'}
            delete_keys = [op.key for op in operations if op.operation == 'delete']
            
            # Execute operation groups in parallel
            tasks = []
            if get_keys:
                tasks.append(('get', self.multi_get(get_keys)))
            if set_data:
                tasks.append(('set', self.multi_set(set_data)))
            if delete_keys:
                tasks.append(('delete', self.multi_delete(delete_keys)))
            
            # Wait for all operations
            if tasks:
                task_results = await asyncio.gather(
                    *[task for _, task in tasks], 
                    return_exceptions=True
                )
                
                # Combine results
                for i, (op_type, _) in enumerate(tasks):
                    result = task_results[i]
                    if isinstance(result, Exception):
                        errors.append(f"{op_type} operation failed: {result}")
                    else:
                        results.update(result)
            
            execution_time = (time.time() - start_time) * 1000
            success = len(errors) == 0
            
            self.logger.info(f"Batch execution: {len(operations)} ops in {execution_time:.2f}ms")
            
            return BatchResult(
                success=success,
                results=results,
                errors=errors,
                execution_time_ms=execution_time,
                operations_count=len(operations)
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"Batch execution failed: {e}"
            self.logger.error(error_msg)
            
            return BatchResult(
                success=False,
                results={},
                errors=[error_msg],
                execution_time_ms=execution_time,
                operations_count=len(operations)
            )
    
    async def warm_cache(self, warm_data: Dict[str, Any]) -> Dict[str, bool]:
        """Warm cache with pre-calculated data"""
        self.logger.info(f"Warming cache with {len(warm_data)} items")
        
        # Use batch set with optimized TTLs
        return await self.multi_set(warm_data)
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern (prefix-based)"""
        # Note: This is a simplified implementation
        # In production, you might want to maintain a pattern index
        invalidated = 0
        
        try:
            # For now, we'll implement dependency-based invalidation
            if ":" in pattern:
                dependencies = CacheKeyGenerator.get_dependencies(pattern)
                if dependencies:
                    delete_keys = [pattern] + dependencies
                    results = await self.multi_delete(delete_keys)
                    invalidated = sum(1 for success in results.values() if success)
            
            self.logger.info(f"Invalidated {invalidated} keys matching pattern: {pattern}")
            return invalidated
            
        except Exception as e:
            self.logger.error(f"Pattern invalidation failed: {e}")
            return 0
    
    async def get_or_compute(self, key: str, compute_func: callable, ttl: Optional[int] = None) -> Any:
        """Get from cache or compute and cache the result"""
        try:
            # Try to get from cache first
            cached_result = await self.cache_adapter.get(key)
            if cached_result is not None:
                return cached_result
            
            # Compute the result
            result = await compute_func()
            if result is not None:
                # Cache the computed result
                cache_ttl = ttl if ttl else CacheKeyGenerator.get_ttl_for_key(key)
                await self.cache_adapter.set(key, result, cache_ttl)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Get or compute failed for {key}: {e}")
            return None
    
    async def refresh_cache(self, keys: List[str], compute_functions: Dict[str, callable]) -> Dict[str, bool]:
        """Refresh multiple cache entries with new data"""
        refresh_data = {}
        
        for key in keys:
            if key in compute_functions:
                try:
                    new_value = await compute_functions[key]()
                    if new_value is not None:
                        refresh_data[key] = new_value
                except Exception as e:
                    self.logger.error(f"Failed to compute refresh data for {key}: {e}")
        
        if refresh_data:
            return await self.multi_set(refresh_data)
        return {}
    
    def _update_stats(self, operation_count: int, execution_time: float, success: bool):
        """Update internal statistics"""
        self._stats['total_batches'] += 1
        self._stats['total_operations'] += operation_count
        
        # Update averages
        total_batches = self._stats['total_batches']
        self._stats['avg_batch_size'] = self._stats['total_operations'] / total_batches
        
        current_avg_time = self._stats['avg_execution_time']
        self._stats['avg_execution_time'] = ((current_avg_time * (total_batches - 1)) + execution_time) / total_batches
        
        # Update success rate
        if success:
            current_success_rate = self._stats['success_rate']
            self._stats['success_rate'] = ((current_success_rate * (total_batches - 1)) + 100) / total_batches
        else:
            current_success_rate = self._stats['success_rate']
            self._stats['success_rate'] = (current_success_rate * (total_batches - 1)) / total_batches
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batch operation statistics"""
        return {
            **self._stats,
            'cache_stats': self.cache_adapter.get_stats() if hasattr(self.cache_adapter, 'get_stats') else {}
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on batch cache operations"""
        try:
            # Test basic operations
            test_key = "batch:health:test"
            test_value = {"test": True, "timestamp": time.time()}
            
            start_time = time.time()
            
            # Test set
            set_result = await self.cache_adapter.set(test_key, test_value, 10)
            
            # Test get
            get_result = await self.cache_adapter.get(test_key)
            
            # Test delete
            delete_result = await self.cache_adapter.delete(test_key)
            
            execution_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy" if all([set_result, get_result, delete_result]) else "degraded",
                "set_success": set_result,
                "get_success": get_result is not None,
                "delete_success": delete_result,
                "response_time_ms": round(execution_time, 2),
                "stats": self.get_stats()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "stats": self.get_stats()
            }