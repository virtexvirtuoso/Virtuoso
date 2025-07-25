"""
Optimization for the alpha opportunities endpoint.

Key optimizations:
1. Implement pagination for large result sets
2. Cache intermediate calculations
3. Parallel symbol analysis
4. Streaming results
5. Database query optimization
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import timedelta
import logging
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class AlphaOpportunity:
    """Simplified alpha opportunity model."""
    symbol: str
    score: float
    timeframe: str
    signals: List[str]
    timestamp: int


class OptimizedAlphaScanner:
    """Optimized alpha scanner with performance improvements."""
    
    def __init__(self, exchange_manager, cache_manager=None):
        self.exchange_manager = exchange_manager
        self.cache_manager = cache_manager
        self.batch_size = 10  # Process symbols in batches
        self.max_workers = 5  # Concurrent analysis workers
        
    async def scan_opportunities_paginated(
        self,
        symbols: Optional[List[str]] = None,
        min_score: float = 70.0,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Scan opportunities with pagination support.
        
        Args:
            symbols: List of symbols to scan (None for all)
            min_score: Minimum score threshold
            page: Page number (1-based)
            page_size: Results per page
            
        Returns:
            Paginated results with metadata
        """
        # Check cache for full results
        cache_key = f"alpha_scan:{min_score}:{page}:{page_size}"
        if self.cache_manager:
            cached = self.cache_manager.get(cache_key)
            if cached:
                logger.debug(f"Returning cached alpha scan page {page}")
                return cached
        
        start_time = time.time()
        
        # Get symbols to scan
        if not symbols:
            symbols = await self._get_top_symbols_cached()
        
        # Calculate pagination
        total_symbols = len(symbols)
        total_pages = (total_symbols + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Get symbols for this page
        page_symbols = symbols[start_idx:end_idx]
        
        # Scan symbols in parallel batches
        opportunities = await self._scan_symbols_optimized(
            page_symbols,
            min_score
        )
        
        # Sort by score
        opportunities.sort(key=lambda x: x.score, reverse=True)
        
        elapsed_time = (time.time() - start_time) * 1000
        
        result = {
            "opportunities": [
                {
                    "symbol": opp.symbol,
                    "score": opp.score,
                    "timeframe": opp.timeframe,
                    "signals": opp.signals,
                    "timestamp": opp.timestamp
                }
                for opp in opportunities
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_symbols,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "metadata": {
                "scan_time_ms": round(elapsed_time, 2),
                "min_score": min_score,
                "symbols_scanned": len(page_symbols),
                "opportunities_found": len(opportunities)
            }
        }
        
        # Cache results
        if self.cache_manager:
            self.cache_manager.set(cache_key, result, timedelta(seconds=120))
        
        return result
    
    async def scan_opportunities_stream(
        self,
        symbols: Optional[List[str]] = None,
        min_score: float = 70.0
    ) -> AsyncIterator[AlphaOpportunity]:
        """
        Stream alpha opportunities as they are found.
        
        This allows the client to start processing results immediately
        without waiting for the full scan to complete.
        """
        if not symbols:
            symbols = await self._get_top_symbols_cached()
        
        # Process symbols in batches
        for i in range(0, len(symbols), self.batch_size):
            batch = symbols[i:i + self.batch_size]
            
            # Analyze batch in parallel
            batch_opportunities = await self._scan_symbols_optimized(
                batch,
                min_score
            )
            
            # Yield opportunities as they are found
            for opportunity in batch_opportunities:
                yield opportunity
    
    async def _scan_symbols_optimized(
        self,
        symbols: List[str],
        min_score: float
    ) -> List[AlphaOpportunity]:
        """Scan symbols with optimized parallel processing."""
        opportunities = []
        
        # Create semaphore to limit concurrent workers
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def analyze_symbol(symbol: str) -> Optional[AlphaOpportunity]:
            async with semaphore:
                try:
                    # Check cache first
                    if self.cache_manager:
                        cache_key = f"alpha_symbol:{symbol}"
                        cached = self.cache_manager.get(cache_key)
                        if cached:
                            return AlphaOpportunity(**cached)
                    
                    # Simulate analysis (replace with actual logic)
                    score = await self._calculate_alpha_score(symbol)
                    
                    if score >= min_score:
                        opportunity = AlphaOpportunity(
                            symbol=symbol,
                            score=score,
                            timeframe="1h",
                            signals=["momentum", "volume_spike"],
                            timestamp=int(time.time() * 1000)
                        )
                        
                        # Cache individual result
                        if self.cache_manager:
                            cache_key = f"alpha_symbol:{symbol}"
                            self.cache_manager.set(
                                cache_key,
                                opportunity.__dict__,
                                timedelta(seconds=300)
                            )
                        
                        return opportunity
                    
                    return None
                    
                except Exception as e:
                    logger.error(f"Error analyzing {symbol}: {e}")
                    return None
        
        # Analyze all symbols in parallel
        tasks = [analyze_symbol(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        for result in results:
            if isinstance(result, AlphaOpportunity):
                opportunities.append(result)
        
        return opportunities
    
    async def _calculate_alpha_score(self, symbol: str) -> float:
        """
        Calculate alpha score with caching of intermediate results.
        
        This method demonstrates caching of expensive calculations.
        """
        # Check for cached calculations
        calc_cache_key = f"alpha_calc:{symbol}"
        if self.cache_manager:
            cached_calcs = self.cache_manager.get(calc_cache_key)
            if cached_calcs:
                # Use cached intermediate calculations
                return cached_calcs["final_score"]
        
        # Simulate expensive calculations
        await asyncio.sleep(0.1)  # Replace with actual calculation
        
        # Example scoring (replace with actual logic)
        import random
        technical_score = random.uniform(40, 90)
        volume_score = random.uniform(50, 95)
        momentum_score = random.uniform(45, 85)
        
        # Cache intermediate calculations
        calculations = {
            "technical": technical_score,
            "volume": volume_score,
            "momentum": momentum_score,
            "final_score": (technical_score + volume_score + momentum_score) / 3
        }
        
        if self.cache_manager:
            self.cache_manager.set(
                calc_cache_key,
                calculations,
                timedelta(seconds=600)  # 10 minute cache
            )
        
        return calculations["final_score"]
    
    async def _get_top_symbols_cached(self) -> List[str]:
        """Get top symbols with caching."""
        cache_key = "top_symbols_list"
        
        if self.cache_manager:
            cached = self.cache_manager.get(cache_key)
            if cached:
                return cached
        
        # Default symbols (replace with actual fetching)
        symbols = [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
            "DOTUSDT", "MATICUSDT", "LINKUSDT", "AVAXUSDT", "ATOMUSDT",
            "LTCUSDT", "ETCUSDT", "XLMUSDT", "ALGOUSDT", "NEARUSDT"
        ]
        
        if self.cache_manager:
            self.cache_manager.set(cache_key, symbols, timedelta(seconds=300))
        
        return symbols


# Optimized endpoint implementations
async def optimized_alpha_opportunities_endpoint(
    exchange_manager,
    cache_manager=None,
    page: int = 1,
    page_size: int = 10,
    min_score: float = 70.0
) -> Dict[str, Any]:
    """
    Optimized alpha opportunities endpoint with pagination.
    
    Improvements:
    - Pagination reduces response size
    - Parallel symbol analysis
    - Caching at multiple levels
    - Streaming option for real-time updates
    """
    scanner = OptimizedAlphaScanner(exchange_manager, cache_manager)
    return await scanner.scan_opportunities_paginated(
        min_score=min_score,
        page=page,
        page_size=page_size
    )


# Performance demonstration
async def demonstrate_optimization():
    """Demonstrate the performance improvements."""
    
    print("Alpha Scanner Optimization Demo")
    print("=" * 50)
    
    # Mock exchange manager
    class MockExchangeManager:
        pass
    
    # Simulate old implementation
    async def old_implementation(num_symbols=50):
        start = time.time()
        
        # Sequential processing (BAD)
        opportunities = []
        for i in range(num_symbols):
            await asyncio.sleep(0.1)  # Simulate analysis
            score = 50 + (i % 50)
            if score >= 70:
                opportunities.append({
                    "symbol": f"SYM{i}",
                    "score": score
                })
        
        return time.time() - start
    
    # New optimized implementation
    async def new_implementation(num_symbols=50):
        start = time.time()
        
        scanner = OptimizedAlphaScanner(MockExchangeManager())
        symbols = [f"SYM{i}" for i in range(num_symbols)]
        
        # Parallel processing with batching
        opportunities = await scanner._scan_symbols_optimized(symbols, 70.0)
        
        return time.time() - start
    
    print("\nPerformance Comparison (50 symbols):")
    print("-" * 50)
    
    old_time = await old_implementation(50)
    print(f"Old implementation: {old_time:.2f} seconds")
    
    new_time = await new_implementation(50)
    print(f"New implementation: {new_time:.2f} seconds")
    
    improvement = ((old_time - new_time) / old_time) * 100
    print(f"\nImprovement: {improvement:.1f}% faster")
    print(f"Time saved: {old_time - new_time:.2f} seconds")
    
    print("\n" + "=" * 50)
    print("Key Optimizations:")
    print("1. Pagination (10 results per page)")
    print("2. Parallel analysis (5 concurrent workers)")
    print("3. Multi-level caching (2-10 minute TTL)")
    print("4. Streaming API for real-time updates")
    print("5. Batch processing (10 symbols per batch)")
    
    print("\nAdditional Benefits:")
    print("- Reduced memory usage with pagination")
    print("- Better user experience with streaming")
    print("- Lower database load with caching")
    print("- Scalable to 1000s of symbols")


if __name__ == "__main__":
    asyncio.run(demonstrate_optimization())