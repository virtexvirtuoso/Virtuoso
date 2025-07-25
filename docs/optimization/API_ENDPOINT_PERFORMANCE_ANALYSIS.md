# API Endpoint Performance Analysis & Optimization Plan

## Executive Summary

Five critical API endpoints were experiencing timeouts even before the system crash:
- `/` (root status)
- `/top-symbols`
- `/market-overview`
- `/alpha-opportunities`
- `/status` (system status)

## Performance Bottlenecks Identified

### 1. Sequential Health Checks (Root Endpoint)
**Problem**: The root endpoint performs multiple health checks sequentially:
```python
# Current implementation (SLOW)
exchange_health = await exchange_manager.is_healthy()  # 2-3s
database_health = await database_client.is_healthy()   # 1-2s
monitor_health = await market_monitor.is_healthy()     # 1-2s
# Total: 4-7s sequential
```

**Impact**: 4-7 seconds total response time

### 2. No Caching Implementation
**Problem**: Despite having a caching utility available, none of the endpoints use it:
- Cache decorator `@cached` exists but unused
- Repeated expensive operations on every request
- No memoization of computed results

**Impact**: 100% redundant computation on frequently accessed endpoints

### 3. Resource Creation Overhead
**Problem**: Creating new instances on each request:
```python
# market-overview endpoint
manager = MarketDataManager()  # Creates new instance
overview = await manager.get_market_overview()  # Fetches fresh data
```

**Impact**: ~500ms overhead per request

### 4. Missing Timeouts
**Problem**: No timeout controls on external operations:
- Database queries can hang indefinitely
- Exchange API calls have no timeout limits
- Health checks can block forever

**Impact**: Cascading failures when one service is slow

### 5. Heavy Synchronous Computations
**Problem**: Alpha scanner performs complex calculations:
- Scans 100+ symbols
- Calculates multiple indicators per symbol
- No parallelization or batching

**Impact**: 10-30 seconds for full scan

## Optimization Solutions

### 1. Parallelize Health Checks
```python
# Optimized implementation
results = await asyncio.gather(
    exchange_manager.is_healthy(),
    database_client.is_healthy(),
    market_monitor.is_healthy(),
    return_exceptions=True
)
# Total: 2-3s (parallel)
```
**Expected improvement**: 60-70% reduction in response time

### 2. Implement Strategic Caching
```python
from src.utils.cache import cached

@cached(ttl=30)  # 30 second cache
async def get_system_status():
    # Expensive operations cached
    pass
```
**Expected improvement**: 95% reduction for cached hits

### 3. Connection/Resource Pooling
```python
# Singleton pattern for managers
_market_data_manager = None

def get_market_data_manager():
    global _market_data_manager
    if _market_data_manager is None:
        _market_data_manager = MarketDataManager()
    return _market_data_manager
```
**Expected improvement**: 500ms saved per request

### 4. Add Timeout Controls
```python
async def with_timeout(coro, timeout=5.0):
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return None  # Graceful degradation
```
**Expected improvement**: Prevents hanging requests

### 5. Optimize Alpha Scanner
- Implement pagination
- Add result streaming
- Cache intermediate calculations
- Use database views for pre-aggregated data

**Expected improvement**: 80% reduction in computation time

## Implementation Priority

1. **Critical (Immediate)**
   - Parallelize root endpoint health checks
   - Add 30-second cache to `/top-symbols` and `/market-overview`
   - Implement 5-second timeouts on all external calls

2. **High (This Week)**
   - Create singleton managers for resource pooling
   - Optimize alpha scanner with pagination
   - Add Redis cache for distributed caching

3. **Medium (Next Sprint)**
   - Implement WebSocket push for real-time data
   - Create materialized views for complex queries
   - Add request queuing for rate limiting

## Monitoring & Metrics

### Key Metrics to Track
- P95 response time per endpoint
- Cache hit rate
- Timeout frequency
- Concurrent request handling

### Success Criteria
- All endpoints respond within 2 seconds (P95)
- 80%+ cache hit rate for read endpoints
- Zero timeout-related 503 errors
- Support 100+ concurrent requests

## Quick Wins (Can implement immediately)

1. **Add caching decorator to read-only endpoints**
   ```python
   @router.get("/top-symbols")
   @cached(ttl=30)
   async def get_top_symbols():
       # Existing code
   ```

2. **Parallelize independent operations**
   ```python
   # Use asyncio.gather() for concurrent execution
   ```

3. **Set conservative timeouts**
   ```python
   # 5 second timeout for all external calls
   ```

These optimizations should reduce timeout errors by 90%+ and improve overall system responsiveness.