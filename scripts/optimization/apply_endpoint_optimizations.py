"""
Script to apply endpoint optimizations to the actual codebase.

This script provides the code changes needed to optimize the slow endpoints.
Run this to see the exact modifications needed in each file.
"""

import os
from datetime import datetime

def generate_optimization_patches():
    """Generate the actual code patches for optimization."""
    
    patches = []
    
    # 1. Root endpoint optimization
    patches.append({
        "file": "src/main.py",
        "description": "Optimize root endpoint with parallel health checks and caching",
        "location": "Line 674 - @app.get('/')",
        "patch": '''
# Add this import at the top
from src.utils.cache import cached

# Replace the root endpoint function with:
@app.get("/")
@cached(ttl=30)  # 30 second cache
async def root():
    """Root endpoint with system status - OPTIMIZED"""
    try:
        logger.debug("Root endpoint called - getting system status")
        
        # Initialize status variables
        status = {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": RUN_DESCRIPTOR,
            "run_number": RUN_NUMBER,
            "run_started": RUN_TIMESTAMP,
            "components": {}
        }
        
        # Define async health check functions with timeouts
        async def check_exchange():
            try:
                if exchange_manager:
                    return await asyncio.wait_for(exchange_manager.is_healthy(), timeout=2.0)
                return False
            except:
                return False
        
        async def check_database():
            try:
                if database_client:
                    return await asyncio.wait_for(database_client.is_healthy(), timeout=2.0)
                return False
            except:
                return False
        
        async def check_monitor():
            try:
                if market_monitor:
                    return await asyncio.wait_for(market_monitor.is_healthy(), timeout=2.0)
                return False
            except:
                return False
        
        async def check_symbols():
            try:
                if top_symbols_manager and hasattr(top_symbols_manager, 'get_top_symbols'):
                    symbols = await asyncio.wait_for(
                        top_symbols_manager.get_top_symbols(limit=5),
                        timeout=1.0
                    )
                    return len(symbols) if symbols else 0
                return 0
            except:
                return 0
        
        # Execute all health checks in PARALLEL
        start_time = time.time()
        results = await asyncio.gather(
            check_exchange(),
            check_database(),
            check_monitor(),
            check_symbols(),
            return_exceptions=True
        )
        
        exchange_health, db_health, monitor_health, symbols_count = results
        
        # Update status based on results
        status["components"]["exchange_manager"] = {
            "status": "active" if exchange_health else "inactive",
            "healthy": bool(exchange_health)
        }
        
        status["components"]["database"] = {
            "status": "connected" if db_health else "disconnected",
            "healthy": bool(db_health)
        }
        
        status["components"]["market_monitor"] = {
            "status": "active" if monitor_health else "inactive",
            "healthy": bool(monitor_health)
        }
        
        status["components"]["top_symbols"] = {
            "count": symbols_count,
            "status": "active" if symbols_count > 0 else "inactive"
        }
        
        # Add performance metrics
        elapsed_ms = (time.time() - start_time) * 1000
        status["performance"] = {
            "response_time_ms": round(elapsed_ms, 2),
            "parallel_checks": True,
            "cached": False  # Will be True when served from cache
        }
        
        logger.info(f"Root endpoint completed in {elapsed_ms:.2f}ms")
        return status
        
    except Exception as e:
        logger.error(f"Root endpoint error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
'''
    })
    
    # 2. Market overview optimization
    patches.append({
        "file": "src/api/routes/market.py",
        "description": "Optimize market-overview with singleton pattern and caching",
        "location": "Line 352 - @router.get('/overview')",
        "patch": '''
# Add at module level (after imports)
_market_data_manager = None
_manager_lock = asyncio.Lock()

async def get_singleton_market_manager():
    """Get or create singleton MarketDataManager."""
    global _market_data_manager
    if _market_data_manager is None:
        async with _manager_lock:
            if _market_data_manager is None:
                from src.core.market.market_data_manager import MarketDataManager
                _market_data_manager = MarketDataManager()
    return _market_data_manager

# Replace the market overview endpoint with:
@router.get("/overview")
@cached(ttl=60)  # 60 second cache
async def get_market_overview() -> Dict[str, Any]:
    """Get general market overview across all exchanges - OPTIMIZED."""
    try:
        # Use singleton manager
        manager = await get_singleton_market_manager()
        
        try:
            # Add timeout to prevent hanging
            overview = await asyncio.wait_for(
                manager.get_market_overview(),
                timeout=3.0
            )
            
            return {
                "status": "active",
                "timestamp": datetime.utcnow().isoformat(),
                "total_symbols": overview.get("total_symbols", 0),
                "active_exchanges": overview.get("active_exchanges", []),
                "total_volume_24h": overview.get("total_volume_24h", 0.0),
                "market_cap": overview.get("market_cap", 0.0),
                "btc_dominance": overview.get("btc_dominance", 0.0),
                "fear_greed_index": overview.get("fear_greed_index", 50),
                "trending_symbols": overview.get("trending_symbols", []),
                "top_gainers": overview.get("top_gainers", []),
                "top_losers": overview.get("top_losers", []),
                "performance": {
                    "optimized": True,
                    "singleton": True,
                    "cached": False  # Will be True when from cache
                }
            }
            
        except asyncio.TimeoutError:
            logger.warning("Market overview timed out after 3s")
            # Return default overview
            return {
                "status": "degraded",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Market overview temporarily slow",
                "total_symbols": 0,
                "active_exchanges": [],
                "total_volume_24h": 0.0,
                "market_cap": 0.0,
                "btc_dominance": 0.0,
                "fear_greed_index": 50,
                "trending_symbols": [],
                "top_gainers": [],
                "top_losers": []
            }
            
    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))
'''
    })
    
    # 3. Alpha opportunities optimization
    patches.append({
        "file": "src/api/routes/alpha.py",
        "description": "Add pagination and caching to alpha opportunities",
        "location": "Line 66 - @router.get('/opportunities')",
        "patch": '''
# Add import at top

# Replace the opportunities endpoint with:
@router.get("/opportunities", response_model=List[AlphaOpportunity])
@cached(ttl=120)  # 2 minute cache
async def get_opportunities(
    limit: int = Query(default=10, ge=1, le=50),
    min_score: float = Query(default=70.0, ge=0, le=100),
    timeframe: Optional[str] = Query(default=None),
    exchange: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),  # Add pagination
    alpha_scanner = Depends(get_alpha_scanner)
) -> List[AlphaOpportunity]:
    """Get alpha opportunities with pagination - OPTIMIZED."""
    
    try:
        start_time = time.time()
        timeframes = [timeframe] if timeframe else ["15m", "1h", "4h"]
        exchanges = [exchange] if exchange else None
        
        # Add timeout to prevent hanging
        opportunities = await asyncio.wait_for(
            alpha_scanner.scan_opportunities(
                exchanges=exchanges,
                timeframes=timeframes,
                min_score=min_score,
                max_results=limit * page,  # Get enough for pagination
                batch_size=10  # Process in batches
            ),
            timeout=5.0  # 5 second timeout
        )
        
        # Implement pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        page_opportunities = opportunities[start_idx:end_idx]
        
        # Add performance metadata
        for opp in page_opportunities:
            if hasattr(opp, 'metadata'):
                opp.metadata['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
                opp.metadata['page'] = page
                opp.metadata['optimized'] = True
        
        return page_opportunities
        
    except asyncio.TimeoutError:
        logger.error("Alpha scan timed out after 5s")
        raise HTTPException(
            status_code=504,
            detail="Alpha scan timed out. Try reducing the limit or using specific symbols."
        )
    except Exception as e:
        logger.error(f"Failed to fetch opportunities: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
'''
    })
    
    # 4. Add caching utility import
    patches.append({
        "file": "src/api/routes/market.py",
        "description": "Add cache import",
        "location": "After other imports",
        "patch": '''
# Add this import
'''
    })
    
    # 5. Add timeout utility
    patches.append({
        "file": "src/utils/async_helpers.py",
        "description": "Create async helper utilities",
        "patch": '''
"""Async helper utilities for optimized operations."""

import asyncio
from typing import Any, Coroutine, Optional, TypeVar, List
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

async def with_timeout(
    coro: Coroutine[Any, Any, T],
    timeout: float,
    default: Optional[T] = None
) -> Optional[T]:
    """
    Execute coroutine with timeout, returning default on timeout.
    
    Args:
        coro: Coroutine to execute
        timeout: Timeout in seconds
        default: Default value to return on timeout
        
    Returns:
        Result of coroutine or default value
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"Operation timed out after {timeout}s")
        return default

async def gather_with_timeout(
    *coros: Coroutine[Any, Any, Any],
    timeout: float,
    return_exceptions: bool = True
) -> List[Any]:
    """
    Gather multiple coroutines with overall timeout.
    
    Args:
        *coros: Coroutines to execute
        timeout: Overall timeout in seconds
        return_exceptions: Whether to return exceptions as results
        
    Returns:
        List of results
    """
    try:
        return await asyncio.wait_for(
            asyncio.gather(*coros, return_exceptions=return_exceptions),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning(f"Gather operation timed out after {timeout}s")
        return [None] * len(coros)
'''
    })
    
    return patches


def print_optimization_guide():
    """Print the optimization guide."""
    
    print("=" * 80)
    print("API ENDPOINT OPTIMIZATION IMPLEMENTATION GUIDE")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    patches = generate_optimization_patches()
    
    for i, patch in enumerate(patches, 1):
        print(f"\n{i}. {patch['description']}")
        print("-" * 60)
        print(f"File: {patch['file']}")
        if 'location' in patch:
            print(f"Location: {patch['location']}")
        print("\nCode to add/modify:")
        print("```python")
        print(patch['patch'].strip())
        print("```")
        print()
    
    print("\n" + "=" * 80)
    print("IMPLEMENTATION STEPS:")
    print("=" * 80)
    print("""
1. BACKUP your current code first:
   cp src/main.py src/main.py.backup
   cp src/api/routes/market.py src/api/routes/market.py.backup
   cp src/api/routes/alpha.py src/api/routes/alpha.py.backup

2. Create the async helpers file:
   touch src/utils/async_helpers.py

3. Apply each patch carefully, testing after each change

4. Run the optimization test scripts:
   python scripts/optimization/optimize_root_endpoint.py
   python scripts/optimization/optimize_market_overview.py
   python scripts/optimization/optimize_alpha_scanner.py

5. Monitor the improvements:
   - Check endpoint response times
   - Monitor cache hit rates
   - Watch for timeout errors

6. Fine-tune cache TTL values based on your needs:
   - Root endpoint: 30s (system status changes slowly)
   - Market overview: 60s (market data updates frequently)
   - Alpha opportunities: 120s (computationally expensive)

7. Consider adding Redis for distributed caching if running multiple instances
""")
    
    print("\n" + "=" * 80)
    print("EXPECTED IMPROVEMENTS:")
    print("=" * 80)
    print("""
- Root endpoint: 60-70% faster (4-7s → 1.5-2s)
- Market overview: 80% faster with cache (1.6s → 0.3s)
- Alpha opportunities: 90% faster with pagination (10s+ → 1s)
- Overall: 90%+ reduction in timeout errors

These optimizations will make your API much more responsive and reliable!
""")


if __name__ == "__main__":
    print_optimization_guide()