"""
API Request Queue Manager

Implements a priority queue system for API requests to prevent connection pool 
exhaustion and manage rate limits effectively.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from queue import PriorityQueue
import logging
from enum import IntEnum
import hashlib
import json

logger = logging.getLogger(__name__)


class RequestPriority(IntEnum):
    """Request priority levels."""
    CRITICAL = 1  # Market data for active trades
    HIGH = 2      # Order book, ticker updates
    NORMAL = 3    # Historical data, analytics
    LOW = 4       # Background updates, non-critical data


@dataclass
class QueuedRequest:
    """Represents a queued API request."""
    priority: RequestPriority
    timestamp: float
    endpoint: str
    method: str
    params: Dict[str, Any]
    callback: Callable
    retry_count: int = 0
    request_id: str = field(default_factory=lambda: str(time.time()))
    
    def __lt__(self, other):
        """Priority queue ordering: lower priority value = higher priority."""
        if self.priority != other.priority:
            return self.priority < other.priority
        # If same priority, older requests first (FIFO)
        return self.timestamp < other.timestamp


class APIRequestQueue:
    """
    Manages API request queuing with priority, rate limiting, and caching.
    """
    
    def __init__(
        self, 
        max_concurrent: int = 10,
        rate_limit: int = 10,  # requests per second
        cache_ttl: int = 30,   # cache TTL in seconds
        max_retries: int = 3
    ):
        self.max_concurrent = max_concurrent
        self.rate_limit = rate_limit
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        
        # Request queue
        self.queue = asyncio.PriorityQueue()
        self.active_requests = 0
        self.request_times = []  # Track request timestamps for rate limiting
        
        # Response cache
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Statistics
        self.total_requests = 0
        self.failed_requests = 0
        self.queued_requests = 0
        
        # Control
        self.running = False
        self._workers = []
        
    def _generate_cache_key(self, endpoint: str, method: str, params: Dict) -> str:
        """Generate a unique cache key for the request."""
        # Sort params for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True)
        key_string = f"{method}:{endpoint}:{sorted_params}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _check_cache(self, cache_key: str) -> Optional[Any]:
        """Check if response is in cache and still valid."""
        if cache_key in self.cache:
            response, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                self.cache_hits += 1
                logger.debug(f"Cache hit for key: {cache_key}")
                return response
            else:
                # Expired, remove from cache
                del self.cache[cache_key]
        
        self.cache_misses += 1
        return None
    
    def _update_cache(self, cache_key: str, response: Any):
        """Update cache with new response."""
        self.cache[cache_key] = (response, time.time())
        
        # Clean old entries if cache is getting large
        if len(self.cache) > 1000:
            self._clean_cache()
    
    def _clean_cache(self):
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp > self.cache_ttl
        ]
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned {len(expired_keys)} expired cache entries")
    
    async def _check_rate_limit(self):
        """Ensure we don't exceed rate limit."""
        current_time = time.time()
        
        # Remove timestamps older than 1 second
        self.request_times = [t for t in self.request_times if current_time - t < 1.0]
        
        # If at rate limit, wait
        if len(self.request_times) >= self.rate_limit:
            wait_time = 1.0 - (current_time - self.request_times[0])
            if wait_time > 0:
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                # Recursive call to recheck
                await self._check_rate_limit()
        
        # Add current request timestamp
        self.request_times.append(current_time)
    
    async def enqueue(
        self,
        endpoint: str,
        method: str,
        params: Dict[str, Any],
        callback: Callable,
        priority: RequestPriority = RequestPriority.NORMAL,
        use_cache: bool = True
    ) -> str:
        """
        Add request to queue.
        
        Returns:
            Request ID for tracking
        """
        # Check cache first if enabled
        if use_cache and method.upper() == 'GET':
            cache_key = self._generate_cache_key(endpoint, method, params)
            cached_response = self._check_cache(cache_key)
            if cached_response is not None:
                # Call callback with cached response immediately
                try:
                    # For cached responses, return the response directly
                    # The callback expects to be called with endpoint, method, params
                    # but for cached responses, we already have the result
                    return f"cached_{cache_key}"
                except Exception as e:
                    logger.error(f"Error in callback with cached response: {e}")
        
        # Create queued request
        request = QueuedRequest(
            priority=priority,
            timestamp=time.time(),
            endpoint=endpoint,
            method=method,
            params=params,
            callback=callback
        )
        
        await self.queue.put((request.priority, request))
        self.queued_requests += 1
        
        logger.debug(
            f"Enqueued request: {endpoint} (priority: {priority.name}, "
            f"queue size: {self.queue.qsize()})"
        )
        
        return request.request_id
    
    async def _process_request(self, request: QueuedRequest) -> bool:
        """
        Process a single request.
        
        Returns:
            True if successful, False if failed
        """
        try:
            # Check rate limit
            await self._check_rate_limit()
            
            # Execute the callback (which should make the actual API call)
            response = await request.callback(
                request.endpoint,
                request.method,
                request.params
            )
            
            # Cache successful GET responses
            if request.method.upper() == 'GET' and response:
                cache_key = self._generate_cache_key(
                    request.endpoint,
                    request.method,
                    request.params
                )
                self._update_cache(cache_key, response)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing request to {request.endpoint}: {e}")
            
            # Retry logic
            if request.retry_count < self.max_retries:
                request.retry_count += 1
                wait_time = 2 ** request.retry_count  # Exponential backoff
                logger.info(
                    f"Retrying request to {request.endpoint} "
                    f"(attempt {request.retry_count}/{self.max_retries}) "
                    f"after {wait_time}s"
                )
                await asyncio.sleep(wait_time)
                # Re-queue with same priority
                await self.queue.put((request.priority, request))
                return False
            else:
                logger.error(
                    f"Request to {request.endpoint} failed after "
                    f"{self.max_retries} retries"
                )
                self.failed_requests += 1
                return False
    
    async def _worker(self, worker_id: int):
        """Worker coroutine that processes requests from the queue."""
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # Wait for request with timeout to allow checking running flag
                priority, request = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )
                
                self.active_requests += 1
                self.total_requests += 1
                
                logger.debug(
                    f"Worker {worker_id} processing request to {request.endpoint}"
                )
                
                # Process the request
                success = await self._process_request(request)
                
                self.active_requests -= 1
                
                # Log statistics periodically
                if self.total_requests % 100 == 0:
                    self._log_statistics()
                    
            except asyncio.TimeoutError:
                # No requests in queue, continue
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                self.active_requests = max(0, self.active_requests - 1)
    
    def _log_statistics(self):
        """Log queue statistics."""
        cache_hit_rate = (
            self.cache_hits / (self.cache_hits + self.cache_misses) * 100
            if (self.cache_hits + self.cache_misses) > 0
            else 0
        )
        
        logger.info(
            f"Queue Stats - Total: {self.total_requests}, "
            f"Failed: {self.failed_requests}, "
            f"Active: {self.active_requests}, "
            f"Queued: {self.queue.qsize()}, "
            f"Cache Hit Rate: {cache_hit_rate:.1f}%"
        )
    
    async def start(self):
        """Start the request queue workers."""
        self.running = True
        
        # Start worker tasks
        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)
        
        logger.info(
            f"Request queue started with {self.max_concurrent} workers, "
            f"rate limit: {self.rate_limit} req/s"
        )
    
    async def stop(self):
        """Stop the request queue and wait for workers to finish."""
        logger.info("Stopping request queue...")
        self.running = False
        
        # Wait for workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        
        # Log final statistics
        self._log_statistics()
        logger.info("Request queue stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current queue statistics."""
        return {
            'total_requests': self.total_requests,
            'failed_requests': self.failed_requests,
            'active_requests': self.active_requests,
            'queued_requests': self.queue.qsize(),
            'cache_size': len(self.cache),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': (
                self.cache_hits / (self.cache_hits + self.cache_misses)
                if (self.cache_hits + self.cache_misses) > 0
                else 0
            )
        }


# Example usage for Bybit integration
class BybitQueuedClient:
    """Example of how to integrate the queue with Bybit client."""
    
    def __init__(self, bybit_exchange, queue_config: Optional[Dict] = None):
        self.exchange = bybit_exchange
        
        # Initialize queue with config
        config = queue_config or {}
        self.request_queue = APIRequestQueue(
            max_concurrent=config.get('max_concurrent', 10),
            rate_limit=config.get('rate_limit', 10),
            cache_ttl=config.get('cache_ttl', 30),
            max_retries=config.get('max_retries', 3)
        )
    
    async def start(self):
        """Start the queued client."""
        await self.request_queue.start()
    
    async def stop(self):
        """Stop the queued client."""
        await self.request_queue.stop()
    
    async def get_ticker(self, symbol: str, priority: RequestPriority = RequestPriority.HIGH):
        """Get ticker with queuing."""
        endpoint = '/v5/market/tickers'
        params = {'category': 'linear', 'symbol': symbol}
        
        async def make_request(endpoint, method, params):
            # This calls the actual Bybit API
            return await self.exchange._make_request('GET', endpoint, params)
        
        request_id = await self.request_queue.enqueue(
            endpoint=endpoint,
            method='GET',
            params=params,
            callback=make_request,
            priority=priority,
            use_cache=True
        )
        
        return request_id
    
    async def get_orderbook(self, symbol: str, priority: RequestPriority = RequestPriority.HIGH):
        """Get orderbook with queuing."""
        endpoint = '/v5/market/orderbook'
        params = {'category': 'linear', 'symbol': symbol, 'limit': 100}
        
        async def make_request(endpoint, method, params):
            return await self.exchange._make_request('GET', endpoint, params)
        
        request_id = await self.request_queue.enqueue(
            endpoint=endpoint,
            method='GET',
            params=params,
            callback=make_request,
            priority=priority,
            use_cache=True
        )
        
        return request_id