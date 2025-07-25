"""
Optimization script for the root endpoint (/) to improve performance.

This script demonstrates how to optimize the root endpoint by:
1. Parallelizing health checks
2. Adding caching
3. Implementing timeouts
4. Graceful degradation
"""

import asyncio
from datetime import timedelta
from typing import Dict, Any, Optional
import time
import logging

logger = logging.getLogger(__name__)

# Simulated optimized root endpoint
async def optimized_root_endpoint(
    exchange_manager,
    database_client,
    market_monitor,
    top_symbols_manager,
    cache_manager=None
) -> Dict[str, Any]:
    """
    Optimized root endpoint with parallel health checks and caching.
    
    Improvements:
    - Parallel health checks using asyncio.gather
    - Timeout controls on each check
    - Caching of results
    - Graceful degradation on failures
    """
    
    # Check cache first
    if cache_manager:
        cached_result = cache_manager.get("root_status")
        if cached_result:
            logger.debug("Returning cached root status")
            return cached_result
    
    start_time = time.time()
    
    # Initialize base status
    status = {
        "status": "ok",
        "timestamp": int(time.time() * 1000),
        "components": {}
    }
    
    # Define health check functions with timeouts
    async def check_exchange_health():
        try:
            return await asyncio.wait_for(
                exchange_manager.is_healthy(),
                timeout=2.0  # 2 second timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Exchange health check timed out")
            return None
        except Exception as e:
            logger.error(f"Exchange health check failed: {e}")
            return None
    
    async def check_database_health():
        try:
            return await asyncio.wait_for(
                database_client.is_healthy(),
                timeout=2.0
            )
        except asyncio.TimeoutError:
            logger.warning("Database health check timed out")
            return None
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return None
    
    async def check_monitor_health():
        try:
            return await asyncio.wait_for(
                market_monitor.is_healthy(),
                timeout=2.0
            )
        except asyncio.TimeoutError:
            logger.warning("Monitor health check timed out")
            return None
        except Exception as e:
            logger.error(f"Monitor health check failed: {e}")
            return None
    
    async def get_top_symbols_count():
        try:
            if hasattr(top_symbols_manager, 'get_top_symbols'):
                symbols = await asyncio.wait_for(
                    top_symbols_manager.get_top_symbols(limit=5),
                    timeout=1.0
                )
                return len(symbols) if symbols else 0
            return 0
        except asyncio.TimeoutError:
            logger.warning("Top symbols check timed out")
            return 0
        except Exception as e:
            logger.error(f"Top symbols check failed: {e}")
            return 0
    
    # Execute all health checks in parallel
    logger.debug("Starting parallel health checks")
    results = await asyncio.gather(
        check_exchange_health(),
        check_database_health(),
        check_monitor_health(),
        get_top_symbols_count(),
        return_exceptions=True
    )
    
    # Process results
    exchange_health, db_health, monitor_health, symbols_count = results
    
    # Update status based on results
    status["components"]["exchange_manager"] = {
        "status": "active" if exchange_health else "degraded",
        "healthy": bool(exchange_health),
        "error": None if exchange_health is not None else "Health check failed"
    }
    
    status["components"]["database"] = {
        "status": "connected" if db_health else "disconnected",
        "healthy": bool(db_health),
        "error": None if db_health is not None else "Health check failed"
    }
    
    status["components"]["market_monitor"] = {
        "status": "active" if monitor_health else "inactive",
        "healthy": bool(monitor_health),
        "error": None if monitor_health is not None else "Health check failed"
    }
    
    status["components"]["top_symbols"] = {
        "count": symbols_count,
        "status": "active" if symbols_count > 0 else "inactive"
    }
    
    # Calculate overall status
    healthy_components = sum(1 for comp in status["components"].values() 
                           if comp.get("healthy", False) or comp.get("status") == "active")
    total_components = len(status["components"])
    
    if healthy_components == total_components:
        status["status"] = "healthy"
    elif healthy_components > 0:
        status["status"] = "degraded"
    else:
        status["status"] = "unhealthy"
    
    # Add performance metrics
    elapsed_time = (time.time() - start_time) * 1000  # Convert to ms
    status["performance"] = {
        "response_time_ms": round(elapsed_time, 2),
        "optimized": True,
        "parallel_checks": True
    }
    
    # Cache the result
    if cache_manager and status["status"] != "unhealthy":
        cache_manager.set("root_status", status, timedelta(seconds=30))
        logger.debug("Cached root status for 30 seconds")
    
    logger.info(f"Root endpoint completed in {elapsed_time:.2f}ms")
    return status


# Comparison function to show improvement
async def compare_implementations():
    """Compare sequential vs parallel implementation performance."""
    
    # Mock objects for testing
    class MockComponent:
        async def is_healthy(self):
            await asyncio.sleep(1.5)  # Simulate network delay
            return True
    
    class MockTopSymbols:
        async def get_top_symbols(self, limit=50):
            await asyncio.sleep(0.5)
            return [{"symbol": f"SYM{i}"} for i in range(limit)]
    
    # Sequential implementation (OLD)
    async def sequential_health_checks():
        start = time.time()
        mock = MockComponent()
        
        exchange_health = await mock.is_healthy()
        db_health = await mock.is_healthy()
        monitor_health = await mock.is_healthy()
        symbols = await MockTopSymbols().get_top_symbols(5)
        
        return time.time() - start
    
    # Parallel implementation (NEW)
    async def parallel_health_checks():
        start = time.time()
        mock = MockComponent()
        symbols_mgr = MockTopSymbols()
        
        results = await asyncio.gather(
            mock.is_healthy(),
            mock.is_healthy(),
            mock.is_healthy(),
            symbols_mgr.get_top_symbols(5)
        )
        
        return time.time() - start
    
    print("Performance Comparison:")
    print("-" * 50)
    
    sequential_time = await sequential_health_checks()
    print(f"Sequential execution: {sequential_time:.2f} seconds")
    
    parallel_time = await parallel_health_checks()
    print(f"Parallel execution: {parallel_time:.2f} seconds")
    
    improvement = ((sequential_time - parallel_time) / sequential_time) * 100
    print(f"\nImprovement: {improvement:.1f}% faster")
    print(f"Time saved: {sequential_time - parallel_time:.2f} seconds")


# Example usage
if __name__ == "__main__":
    import asyncio
    
    print("Root Endpoint Optimization Demo")
    print("=" * 50)
    
    # Run comparison
    asyncio.run(compare_implementations())
    
    print("\n" + "=" * 50)
    print("Key Optimizations Applied:")
    print("1. Parallel execution of health checks")
    print("2. Timeout controls (2s per check)")
    print("3. Result caching (30s TTL)")
    print("4. Graceful degradation on failures")
    print("5. Performance metrics in response")