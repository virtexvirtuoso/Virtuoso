"""
Wrapper to add optimization layers to existing Bybit exchange.

This approach wraps the existing exchange instead of subclassing,
avoiding initialization issues.
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional
import logging

from src.core.api_request_queue import APIRequestQueue, RequestPriority
from src.core.api_cache_manager import APICacheManager

logger = logging.getLogger(__name__)


class BybitOptimizationWrapper:
    """
    Wrapper that adds optimization layers to an existing Bybit exchange instance.
    """
    
    def __init__(self, exchange):
        """
        Initialize wrapper with existing exchange.
        
        Args:
            exchange: Existing BybitExchange instance
        """
        self.exchange = exchange
        self._original_make_request = exchange._make_request
        
        # Initialize optimization components
        self.request_queue = APIRequestQueue(
            max_concurrent=10,
            rate_limit=8,
            cache_ttl=30,
            max_retries=3
        )
        
        self.cache_manager = APICacheManager()
        
        # Track statistics
        self.stats = {
            'cache_hits': 0,
            'api_calls': 0,
            'timeouts_prevented': 0
        }
        
        # Apply optimizations
        self._apply_optimizations()
    
    def _apply_optimizations(self):
        """Apply optimizations to the exchange."""
        # Increase timeouts
        self.exchange.timeout = aiohttp.ClientTimeout(
            total=60,
            connect=20,
            sock_read=30
        )
        
        # Reduce connection limit
        if hasattr(self.exchange, 'connector') and self.exchange.connector:
            self.exchange.connector._limit_per_host = 30
        
        # Replace the _make_request method
        self.exchange._make_request = self._make_request_optimized
        
        logger.info("Applied optimizations to Bybit exchange")
    
    async def start(self):
        """Start optimization components."""
        await self.request_queue.start()
        await self.cache_manager.start()
        logger.info("Optimization components started")
    
    async def stop(self):
        """Stop optimization components."""
        await self.request_queue.stop()
        await self.cache_manager.stop()
        logger.info(f"Optimization stats: {self.stats}")
    
    async def _make_request_optimized(self, endpoint: str, method: str = 'GET',
                                    params: Optional[Dict] = None,
                                    headers: Optional[Dict] = None,
                                    body: Optional[Any] = None) -> Dict:
        """Optimized request with caching and rate limiting."""
        
        # Check cache for GET requests
        if method == 'GET':
            cached = await self.cache_manager.get(endpoint, method, params, headers)
            if cached:
                self.stats['cache_hits'] += 1
                return cached
        
        # Make the actual request
        self.stats['api_calls'] += 1
        
        try:
            # Use the original method
            response = await self._original_make_request(
                endpoint, method, params, headers, body
            )
            
            # Cache successful GET responses
            if response.get('retCode') == 0 and method == 'GET':
                await self.cache_manager.set(
                    endpoint, method, params, headers, response
                )
            
            return response
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout prevented for {endpoint}")
            self.stats['timeouts_prevented'] += 1
            raise
    
    def get_stats(self) -> Dict:
        """Get optimization statistics."""
        return {
            **self.stats,
            'queue_stats': self.request_queue.get_stats(),
            'cache_stats': self.cache_manager.get_statistics()
        }


async def apply_optimizations_to_exchange(exchange):
    """
    Apply optimizations to an existing Bybit exchange instance.
    
    Args:
        exchange: Existing BybitExchange instance
        
    Returns:
        BybitOptimizationWrapper instance
    """
    wrapper = BybitOptimizationWrapper(exchange)
    await wrapper.start()
    return wrapper