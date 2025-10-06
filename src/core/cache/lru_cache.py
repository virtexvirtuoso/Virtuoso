"""
High-Performance LRU Cache Implementation for L1 Memory Cache

Implements a doubly-linked list with hashmap for O(1) operations.
Target: 1500 items capacity with <1ms access time.
"""

import time
import logging
from typing import Any, Optional, Dict, Tuple
from dataclasses import dataclass
from threading import RLock

logger = logging.getLogger(__name__)


@dataclass
class LRUNode:
    """Node in the LRU doubly-linked list"""
    key: str
    value: Any
    timestamp: float
    ttl: int
    access_count: int = 0
    prev: Optional['LRUNode'] = None
    next: Optional['LRUNode'] = None

    def is_expired(self) -> bool:
        """Check if the node is expired"""
        return time.time() - self.timestamp > self.ttl

    def touch(self):
        """Update access statistics"""
        self.access_count += 1


class HighPerformanceLRUCache:
    """
    High-performance LRU cache with O(1) operations.

    Uses a doubly-linked list with hashmap for optimal performance.
    Designed for <1ms access times with 1500 item capacity.
    """

    def __init__(self, max_size: int = 1500, default_ttl: int = 30):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of items (default: 1500)
            default_ttl: Default TTL in seconds (default: 30)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl

        # Use RLock for thread safety in async environment
        self._lock = RLock()

        # Hash map for O(1) lookups
        self._cache: Dict[str, LRUNode] = {}

        # Doubly-linked list for O(1) LRU operations
        # head -> most recently used
        # tail -> least recently used
        self._head = LRUNode("HEAD", None, 0, 0)
        self._tail = LRUNode("TAIL", None, 0, 0)
        self._head.next = self._tail
        self._tail.prev = self._head

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expired_removals = 0

        logger.info(f"High-performance LRU cache initialized: {max_size} items, {default_ttl}s TTL")

    def _add_to_head(self, node: LRUNode):
        """Add node right after head (most recently used)"""
        node.prev = self._head
        node.next = self._head.next
        self._head.next.prev = node
        self._head.next = node

    def _remove_node(self, node: LRUNode):
        """Remove an existing node from the linked list"""
        node.prev.next = node.next
        node.next.prev = node.prev

    def _move_to_head(self, node: LRUNode):
        """Move node to head (mark as most recently used)"""
        self._remove_node(node)
        self._add_to_head(node)

    def _pop_tail(self) -> LRUNode:
        """Remove and return the least recently used node"""
        last_node = self._tail.prev
        self._remove_node(last_node)
        return last_node

    def get(self, key: str) -> Optional[Any]:
        """
        Get value by key with O(1) complexity.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            start_time = time.perf_counter()

            node = self._cache.get(key)
            if node is None:
                self._misses += 1
                return None

            # Check if expired
            if node.is_expired():
                # Remove expired node
                self._remove_node(node)
                del self._cache[key]
                self._expired_removals += 1
                self._misses += 1
                return None

            # Move to head (mark as recently used)
            self._move_to_head(node)
            node.touch()
            self._hits += 1

            elapsed = (time.perf_counter() - start_time) * 1000  # Convert to ms
            if elapsed > 1.0:  # Log if operation takes > 1ms
                logger.warning(f"LRU get operation took {elapsed:.2f}ms for key: {key}")

            return node.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value with key with O(1) complexity.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)

        Returns:
            True if successfully set
        """
        with self._lock:
            start_time = time.perf_counter()

            if ttl is None:
                ttl = self.default_ttl

            current_time = time.time()
            node = self._cache.get(key)

            if node is not None:
                # Update existing node
                node.value = value
                node.timestamp = current_time
                node.ttl = ttl
                node.access_count = 0
                self._move_to_head(node)
            else:
                # Create new node
                new_node = LRUNode(key, value, current_time, ttl)

                # Check if we need to evict
                if len(self._cache) >= self.max_size:
                    # Remove LRU node
                    tail = self._pop_tail()
                    del self._cache[tail.key]
                    self._evictions += 1

                # Add new node
                self._cache[key] = new_node
                self._add_to_head(new_node)

            elapsed = (time.perf_counter() - start_time) * 1000  # Convert to ms
            if elapsed > 1.0:  # Log if operation takes > 1ms
                logger.warning(f"LRU set operation took {elapsed:.2f}ms for key: {key}")

            return True

    def delete(self, key: str) -> bool:
        """
        Delete value by key with O(1) complexity.

        Args:
            key: Cache key

        Returns:
            True if key existed and was deleted
        """
        with self._lock:
            node = self._cache.get(key)
            if node is None:
                return False

            self._remove_node(node)
            del self._cache[key]
            return True

    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._head.next = self._tail
            self._tail.prev = self._head

            # Reset statistics
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            self._expired_removals = 0

    def size(self) -> int:
        """Get current cache size"""
        return len(self._cache)

    def is_full(self) -> bool:
        """Check if cache is at capacity"""
        return len(self._cache) >= self.max_size

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of expired entries removed
        """
        with self._lock:
            current_time = time.time()
            expired_keys = []

            # Find expired keys
            for key, node in self._cache.items():
                if current_time - node.timestamp > node.ttl:
                    expired_keys.append(key)

            # Remove expired entries
            for key in expired_keys:
                node = self._cache[key]
                self._remove_node(node)
                del self._cache[key]
                self._expired_removals += 1

            return len(expired_keys)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache stats
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "capacity_usage": len(self._cache) / self.max_size * 100,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "evictions": self._evictions,
            "expired_removals": self._expired_removals,
            "total_requests": total_requests
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get detailed performance metrics for monitoring.

        Returns:
            Dictionary with performance metrics
        """
        stats = self.get_statistics()

        # Test access time
        test_key = f"__perf_test_{time.time()}"
        test_value = {"test": True}

        # Measure set performance
        start_time = time.perf_counter()
        self.set(test_key, test_value, 1)  # 1 second TTL
        set_time = (time.perf_counter() - start_time) * 1000

        # Measure get performance
        start_time = time.perf_counter()
        retrieved = self.get(test_key)
        get_time = (time.perf_counter() - start_time) * 1000

        # Cleanup test entry
        self.delete(test_key)

        stats.update({
            "avg_set_time_ms": set_time,
            "avg_get_time_ms": get_time,
            "performance_target_met": get_time < 1.0 and set_time < 1.0,
            "memory_efficiency": len(self._cache) > 0  # Simple check
        })

        return stats

    def __len__(self) -> int:
        """Get cache size"""
        return len(self._cache)

    def __contains__(self, key: str) -> bool:
        """Check if key exists (without affecting LRU order)"""
        return key in self._cache

    def __repr__(self) -> str:
        """String representation"""
        return f"HighPerformanceLRUCache(size={len(self._cache)}, max_size={self.max_size})"


# Alias for backward compatibility
LRUCache = HighPerformanceLRUCache