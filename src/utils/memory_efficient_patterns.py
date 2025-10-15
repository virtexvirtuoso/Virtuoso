
# Memory-efficient patterns for the trading system

# 1. Use __slots__ to reduce memory overhead
class MemoryEfficientTicker:
    __slots__ = ['symbol', 'price', 'volume', 'timestamp']

    def __init__(self, symbol: str, price: float, volume: float, timestamp: int):
        self.symbol = symbol
        self.price = price
        self.volume = volume
        self.timestamp = timestamp

# 2. Use weak references for caches
import weakref

class WeakCache:
    def __init__(self):
        self._cache = weakref.WeakValueDictionary()

    def get(self, key):
        return self._cache.get(key)

    def set(self, key, value):
        self._cache[key] = value

# 3. Use generators for large datasets
def memory_efficient_data_processor(data_source):
    """Process data using generators to minimize memory usage."""
    for batch in data_source.iter_batches(size=1000):
        yield process_batch(batch)

# 4. Implement memory-bounded LRU cache
from functools import lru_cache

@lru_cache(maxsize=128)  # Limit cache size
def expensive_calculation(symbol: str) -> dict:
    # Expensive calculation here
    pass

# 5. Use context managers for resource cleanup
class MemoryManagedResource:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup resources
        self.cleanup()

    def cleanup(self):
        # Free memory explicitly
        pass
