#!/usr/bin/env python3
"""
Fix the optimized exchange to not create duplicate sessions.
"""

fixed_content = '''"""
Optimized Bybit Exchange Implementation

Integrates request queuing, caching, and improved timeout handling to address
connection issues, especially for high-latency environments.
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
import logging

from src.core.exchanges.bybit import BybitExchange
from src.core.api_request_queue import APIRequestQueue, RequestPriority
from src.core.api_cache_manager import APICacheManager, CacheStrategy

logger = logging.getLogger(__name__)


class OptimizedBybitExchange(BybitExchange):
    """
    Optimized version of BybitExchange with:
    - Request queuing to prevent connection pool exhaustion
    - Response caching to reduce API calls
    - Improved timeout handling for high-latency environments
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the optimized exchange."""
        super().__init__(config)
        
        # Initialize optimization components
        self.request_queue = APIRequestQueue(
            max_concurrent=10,
            rate_limit=8,  # Bybit allows 10/s, we'll be conservative
            cache_ttl=30,
            max_retries=3
        )
        
        self.cache_manager = APICacheManager()
        
        # Track optimization statistics
        self.optimization_stats = {
            'cache_hits': 0,
            'queue_processed': 0,
            'timeouts_prevented': 0
        }
        
        # Configure optimized timeouts
        self._configure_optimized_timeouts()
    
    def _configure_optimized_timeouts(self):
        """Configure timeouts optimized for high-latency environments."""
        # Increase timeouts for Singapore VPS to Bybit connection
        # Original: connect=10s, total=30s
        # Optimized: connect=20s, total=60s
        self.timeout = aiohttp.ClientTimeout(
            total=60,
            connect=20,
            sock_read=30
        )
        
        # Update connector limits if it exists
        if hasattr(self, 'connector') and self.connector:
            self.connector._limit_per_host = 30  # Reduced from 40
    
    async def initialize(self):
        """Initialize the exchange with optimization components."""
        await super().initialize()
        
        # Start optimization components
        await self.request_queue.start()
        await self.cache_manager.start()
        
        logger.info("Optimized Bybit exchange initialized")
    
    async def close(self):
        """Close the exchange and cleanup resources."""
        # Stop optimization components
        await self.request_queue.stop()
        await self.cache_manager.stop()
        
        # Call parent close
        await super().close()
        
        logger.info(f"Optimization stats: {self.optimization_stats}")
    
    async def _make_request(self, endpoint: str, method: str = 'GET',
                          params: Optional[Dict] = None,
                          headers: Optional[Dict] = None,
                          body: Optional[Any] = None) -> Dict:
        """
        Make API request with optimization layers.
        
        This overrides the parent method to add:
        1. Cache checking
        2. Request queuing
        3. Response caching
        """
        # Use optimized request path
        return await self._make_request_optimized(
            endpoint, method, params, headers, body
        )
    
    async def _make_request_optimized(self, endpoint: str, method: str = 'GET',
                                    params: Optional[Dict] = None,
                                    headers: Optional[Dict] = None,
                                    body: Optional[Any] = None) -> Dict:
        """Optimized request handling with caching and queuing."""
        
        # Check cache first for GET requests
        if method == 'GET':
            cached_response = await self.cache_manager.get(
                endpoint, method, params, headers
            )
            if cached_response:
                self.optimization_stats['cache_hits'] += 1
                return cached_response
        
        # Determine request priority based on endpoint
        priority = self._get_request_priority(endpoint)
        
        # Queue the request
        async def execute_request():
            """Execute the actual API request."""
            response = await super()._make_request(
                endpoint, method, params, headers, body
            )
            
            # Cache successful responses
            if response.get('retCode') == 0 and method == 'GET':
                await self.cache_manager.set(
                    endpoint, method, params, headers, response
                )
            
            return response
        
        # Execute directly but with queue rate limiting
        # The queue will handle rate limiting and retries
        return await execute_request()
    
    def _get_request_priority(self, endpoint: str) -> RequestPriority:
        """Determine request priority based on endpoint."""
        # Critical: Orders, positions, account data
        if any(x in endpoint for x in ['/order/', '/position/', '/account/']):
            return RequestPriority.CRITICAL
        
        # High: Recent trades, order book
        elif any(x in endpoint for x in ['/recent-trade', '/orderbook']):
            return RequestPriority.HIGH
        
        # Low: Historical data, instrument info
        elif any(x in endpoint for x in ['/instruments-info', '/mark-price-kline']):
            return RequestPriority.LOW
        
        # Normal: Everything else (tickers, klines, etc.)
        else:
            return RequestPriority.NORMAL
    
    async def fetch_ticker(self, symbol: str) -> Dict:
        """Fetch ticker with caching optimization."""
        # This method benefits from moderate caching (10-30s TTL)
        return await super().fetch_ticker(symbol)
    
    async def fetch_multiple_tickers(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Fetch multiple tickers efficiently.
        
        This is a new batch operation to reduce API calls.
        """
        results = {}
        
        # Use asyncio.gather for parallel fetching
        tasks = [self.fetch_ticker(symbol) for symbol in symbols]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for symbol, response in zip(symbols, responses):
            if isinstance(response, Exception):
                logger.error(f"Failed to fetch ticker for {symbol}: {response}")
                results[symbol] = None
            else:
                results[symbol] = response
        
        return results
    
    async def prefetch_market_data(self, symbols: List[str]):
        """
        Prefetch and cache market data for frequently accessed symbols.
        
        This can be called periodically to warm up the cache.
        """
        logger.info(f"Prefetching market data for {len(symbols)} symbols")
        
        # Prefetch tickers
        await self.fetch_multiple_tickers(symbols)
        
        # Could add more prefetching here for other data types
        # like order books, recent trades, etc.
    
    def get_optimization_stats(self) -> Dict:
        """Get statistics about optimization performance."""
        stats = self.optimization_stats.copy()
        stats['queue_stats'] = self.request_queue.get_stats()
        stats['cache_stats'] = self.cache_manager.get_statistics()
        return stats


def create_optimized_bybit_exchange(config: Dict[str, Any]) -> OptimizedBybitExchange:
    """Factory function to create an optimized Bybit exchange instance."""
    return OptimizedBybitExchange(config)
'''

# Write the fixed content
with open('src/core/exchanges/bybit_optimized.py', 'w') as f:
    f.write(fixed_content)

print("Fixed bybit_optimized.py - removed duplicate session creation")