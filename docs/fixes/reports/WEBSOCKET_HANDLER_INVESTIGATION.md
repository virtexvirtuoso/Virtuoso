# WebSocket Handler Timeout Investigation & Fixes

**Date**: 2025-10-29
**Priority**: 🔴 HIGH
**Status**: ANALYSIS COMPLETE → FIXES READY FOR IMPLEMENTATION

---

## Executive Summary

Production logs show repeated WebSocket handler timeouts and network connectivity failures to Bybit API. Root cause analysis reveals **blocking operations in async callbacks** and **inadequate timeout protection** causing the event loop to stall.

**Impact**: Real-time market data streams experiencing interruptions, reduced data quality.

---

## Root Cause Analysis

### 🔴 Critical Issue #1: Blocking Operations in Async Context

**Location**: `src/core/market/market_data_manager.py:936-1500`

**Problem**: The WebSocket message callback `_handle_websocket_message` is async, but calls **synchronous** update methods that perform CPU-intensive operations:

```python
# Line 936 - Async callback
async def _handle_websocket_message(self, symbol: str, topic: str, message: Dict):
    # ...
    if "tickers" in topic:
        self._update_ticker_from_ws(symbol, data)  # ❌ SYNCHRONOUS
    elif "kline" in topic:
        self._update_kline_from_ws(symbol, data)   # ❌ SYNCHRONOUS
    elif "orderbook" in topic:
        self._update_orderbook_from_ws(symbol, data)  # ❌ SYNCHRONOUS
```

**Blocking Operations Identified**:

1. **Pandas DataFrame Operations** (`_update_kline_from_ws:1303-1308`):
   ```python
   # ❌ BLOCKING: DataFrame concat and deduplication
   combined_df = pd.concat([existing_df, df])
   combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
   combined_df = combined_df.sort_index()
   ```

2. **List Sorting Operations** (`_update_orderbook_from_ws:1418-1428`):
   ```python
   # ❌ BLOCKING: Large list sorting
   self.data_cache[symbol]['orderbook']['bids'] = sorted(
       self.data_cache[symbol]['orderbook']['bids'],
       key=lambda x: float(x[0]),
       reverse=True
   )
   ```

**Why This Causes Timeouts**:
- Pandas operations can take 50-200ms on large datasets
- During this time, the event loop is blocked
- Other async operations (like reading WebSocket messages) are starved
- Eventually triggers `asyncio.TimeoutError` at `websocket_manager.py:374`

---

### 🔴 Critical Issue #2: No Timeout Protection on Callback

**Location**: `src/core/exchanges/websocket_manager.py:484`

**Problem**: The message callback has no timeout wrapper:

```python
# Line 484 - NO TIMEOUT PROTECTION
if hasattr(self, 'message_callback') and callable(self.message_callback):
    await self.message_callback(symbol, topic, message)  # ❌ Can hang forever
```

**Effect**: If the callback takes too long (due to blocking ops), the entire handler times out and catches at line 374:

```python
except asyncio.TimeoutError as e:
    self.logger.error(f"[HANDLER_TIMEOUT] WebSocket message handler timeout for {connection_id}")
```

**Current Timeout Behavior**:
- The timeout is coming from `aiohttp` WebSocket's internal timeout mechanism
- Default `receive_timeout=5.0` at line 207
- Not from explicit `asyncio.wait_for()` protection

---

### 🟠 Moderate Issue #3: Network Connectivity Validation

**Location**: `src/core/exchanges/websocket_manager.py:615-638`

**Problem**: Network validation has tight timeouts and no dedicated exponential backoff:

```python
async def _validate_network_connectivity(self) -> bool:
    try:
        timeout = aiohttp.ClientTimeout(total=5, connect=3)  # ❌ Short timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            test_url = "https://api.bybit.com/v5/market/time"
            async with session.get(test_url) as response:
                if response.status == 200:
                    return True
    except Exception as e:
        self.logger.error(f"Network connectivity validation failed: {str(e)}")  # ← Line 637
        return False
```

**Issues**:
1. 5-second timeout is too short for unreliable networks
2. No retry logic within validation itself
3. Called during connection creation which has its own retries
4. VPS network might have occasional slowness to Bybit API

---

### 🟠 Moderate Issue #4: Excessive Reconnection Attempts

**Location**: `src/core/exchanges/websocket_manager.py:397-461`

**Problem**: Reconnection logic has nested retry loops:

```python
async def _reconnect(self, topics, connection_id, session):
    # Outer loop: 10 retries with exponential backoff
    max_retries = 10
    while retries < max_retries:
        # ...
        conn_info = await self._create_connection(topics, connection_id)
        # ↑ Inner loop: 3 retries in _create_connection:165-296
```

**Result**: `10 × 3 = 30 total connection attempts` per reconnection event

This can:
- Overwhelm the Bybit API with connection attempts
- Trigger rate limiting
- Cause connection storms during network instability

---

## Detailed Error Flow

```
1. WebSocket receives message
   ↓
2. Calls message_callback (market_data_manager._handle_websocket_message)
   ↓
3. Callback calls _update_kline_from_ws
   ↓
4. Pandas operations block for 100-200ms
   ↓
5. Event loop starvation
   ↓
6. aiohttp receive_timeout (5s) expires
   ↓
7. Raises asyncio.TimeoutError
   ↓
8. Caught at line 374: [HANDLER_TIMEOUT] error logged
   ↓
9. Connection marked as failed
   ↓
10. Triggers reconnection with 30 retry attempts
    ↓
11. Network validation fails (short timeout)
    ↓
12. [Network connectivity validation failed] error logged
```

---

## Proposed Solutions

### Solution 1: Offload Blocking Operations to Thread Pool

**File**: `src/core/market/market_data_manager.py`

**Change**: Convert synchronous update methods to run in thread pool executor:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class MarketDataManager:
    def __init__(self, ...):
        # Add thread pool for blocking operations
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="market_data")

    async def _handle_websocket_message(self, symbol: str, topic: str, message: Dict):
        """Handle WebSocket messages without blocking event loop"""
        try:
            # Run blocking update operations in thread pool
            loop = asyncio.get_event_loop()

            if "tickers" in topic:
                await loop.run_in_executor(
                    self._executor,
                    self._update_ticker_from_ws,
                    symbol,
                    data
                )
            elif "kline" in topic:
                await loop.run_in_executor(
                    self._executor,
                    self._update_kline_from_ws,
                    symbol,
                    data
                )
            # ... etc for other update methods
        except Exception as e:
            self.logger.error(f"Error in WebSocket handler: {e}")
```

**Benefits**:
- Pandas/sorting operations run in separate threads
- Event loop remains responsive
- Other async operations not blocked

**Trade-offs**:
- Slight overhead from thread context switching
- Need thread-safe access to data_cache (already using dict, should be OK)

---

### Solution 2: Add Timeout Protection to Callback

**File**: `src/core/exchanges/websocket_manager.py`

**Change**: Wrap callback invocation with explicit timeout:

```python
# Line 483-485
if hasattr(self, 'message_callback') and callable(self.message_callback):
    try:
        # Add 2-second timeout for callback execution
        await asyncio.wait_for(
            self.message_callback(symbol, topic, message),
            timeout=2.0
        )
    except asyncio.TimeoutError:
        self.logger.warning(
            f"Message callback timeout for {symbol} on {topic} "
            f"(took >2s, likely blocking operation)"
        )
    except Exception as e:
        self.logger.error(f"Error in message callback: {e}")
```

**Benefits**:
- Prevents single slow callback from hanging entire handler
- Explicit timeout makes debugging easier
- Callback failures don't kill connection

---

### Solution 3: Improve Network Validation

**File**: `src/core/exchanges/websocket_manager.py`

**Changes**:

1. **Increase timeout**:
   ```python
   # Line 623
   timeout = aiohttp.ClientTimeout(total=10, connect=5)  # Was: total=5, connect=3
   ```

2. **Add retry logic with exponential backoff**:
   ```python
   async def _validate_network_connectivity(self, max_retries=3) -> bool:
       """Validate network connectivity with retry logic"""
       for attempt in range(max_retries):
           try:
               timeout = aiohttp.ClientTimeout(total=10, connect=5)
               async with aiohttp.ClientSession(timeout=timeout) as session:
                   test_url = "https://api.bybit.com/v5/market/time"
                   async with session.get(test_url) as response:
                       if response.status == 200:
                           return True

               # If not successful, wait before retry
               if attempt < max_retries - 1:
                   backoff = 2 ** attempt  # 1s, 2s, 4s
                   await asyncio.sleep(backoff)

           except Exception as e:
               if attempt == max_retries - 1:
                   # Only log error on final attempt
                   self.logger.error(f"Network connectivity validation failed after {max_retries} attempts: {e}")
               else:
                   # Debug log for retry attempts
                   self.logger.debug(f"Network check attempt {attempt+1} failed, retrying...")
                   backoff = 2 ** attempt
                   await asyncio.sleep(backoff)

       return False
   ```

3. **Downgrade some errors to warnings**:
   ```python
   # Line 637 - Change ERROR to WARNING for expected failures
   self.logger.warning(f"Network connectivity check failed (using fallback): {str(e)}")
   ```

---

### Solution 4: Reduce Reconnection Attempts

**File**: `src/core/exchanges/websocket_manager.py`

**Change**: Reduce nested retry loops:

```python
async def _reconnect(self, topics, connection_id, session):
    """Reconnect with reduced retry attempts"""
    try:
        # ... existing cleanup code ...

        # CHANGED: Reduce from 10 to 5 retries
        max_retries = 5  # Was: 10
        retries = 0

        while backoff <= max_backoff and retries < max_retries:
            # ... existing retry logic ...

            # CHANGED: Pass flag to _create_connection to use fewer retries
            conn_info = await self._create_connection(
                topics,
                connection_id,
                is_reconnect=True  # Signal to use reduced retries
            )
```

**In `_create_connection`**:
```python
async def _create_connection(self, topics, connection_id, is_reconnect=False):
    """Create connection with adaptive retry count"""
    # Use fewer retries during reconnection (already in retry loop)
    max_retries = 2 if is_reconnect else 3
    retry_delay = 1.0

    for attempt in range(max_retries):
        # ... existing connection logic ...
```

**Result**: `5 reconnect attempts × 2 connection attempts = 10 total` (down from 30)

---

### Solution 5: Add Handler Timeout Configuration

**File**: `src/core/exchanges/websocket_manager.py`

**Change**: Make handler timeout configurable:

```python
async def _handle_messages(self, ws, topics, connection_id, session):
    """Handle messages with configurable timeout"""
    # Get timeout from config, default 30s
    handler_timeout = self.config.get('websocket', {}).get('handler_timeout', 30.0)

    try:
        async for msg in ws:
            # Add timeout to entire message processing
            try:
                await asyncio.wait_for(
                    self._process_single_message(msg, connection_id),
                    timeout=handler_timeout
                )
            except asyncio.TimeoutError:
                self.logger.warning(
                    f"Message processing timeout ({handler_timeout}s) for {connection_id}"
                )
                # Continue processing other messages
```

---

## Implementation Priority

### Phase 1: Critical Fixes (Implement Immediately)
1. ✅ **Solution 1**: Offload blocking operations to thread pool
2. ✅ **Solution 2**: Add timeout protection to callback

**Expected Impact**: 90% reduction in handler timeouts

### Phase 2: Network Resilience (This Week)
3. ✅ **Solution 3**: Improve network validation with retries and longer timeout
4. ✅ **Solution 4**: Reduce nested reconnection attempts

**Expected Impact**: 70% reduction in network connectivity errors

### Phase 3: Configuration (Nice to Have)
5. ⚪ **Solution 5**: Add configurable handler timeout

**Expected Impact**: Better observability and tuning capability

---

## Testing Plan

### Unit Tests
```python
# Test 1: Verify blocking operations don't block event loop
async def test_websocket_callback_non_blocking():
    """Ensure WebSocket callbacks run in thread pool"""
    manager = MarketDataManager(config)

    start = time.time()
    # Simulate 10 concurrent callbacks with blocking pandas ops
    await asyncio.gather(*[
        manager._handle_websocket_message(f"SYM{i}", "kline.1.SYM", mock_kline_data)
        for i in range(10)
    ])
    elapsed = time.time() - start

    # Should complete in < 1s with thread pool (would take 2-3s blocking)
    assert elapsed < 1.5, f"Callbacks took {elapsed}s, likely blocking"
```

### Integration Tests
```python
# Test 2: Verify timeout protection works
async def test_callback_timeout_protection():
    """Ensure slow callbacks don't hang handler"""

    async def slow_callback(symbol, topic, message):
        await asyncio.sleep(5)  # Simulate slow operation

    ws_manager = WebSocketManager(config)
    ws_manager.register_message_callback(slow_callback)

    # Should log warning but not crash
    # Handler should continue processing other messages
```

### VPS Production Tests
1. Deploy fixes to VPS
2. Monitor logs for 2 hours
3. Count timeout errors before/after
4. Verify message processing continues during network issues

---

## Monitoring & Validation

### Success Criteria
- [ ] `[HANDLER_TIMEOUT]` errors reduced by >90%
- [ ] `Network connectivity validation failed` errors reduced by >70%
- [ ] WebSocket connection uptime >99.5%
- [ ] Message processing latency <100ms p99

### Key Metrics to Track
```python
# Add to websocket_manager.py status
self.status['callback_timeouts'] = 0
self.status['callback_avg_duration_ms'] = 0.0
self.status['network_validation_retries'] = 0
self.status['total_reconnection_attempts'] = 0
```

### Log Analysis Commands
```bash
# Before fix (baseline)
ssh vps "sudo journalctl -u virtuoso-trading.service --since '1 hour ago' | grep HANDLER_TIMEOUT | wc -l"

# After fix (validation)
ssh vps "sudo journalctl -u virtuoso-trading.service --since '1 hour ago' | grep HANDLER_TIMEOUT | wc -l"

# Should see 90%+ reduction
```

---

## Rollback Plan

If fixes cause issues:

1. **Immediate Rollback**:
   ```bash
   cd /home/linuxuser/trading/Virtuoso_ccxt
   git stash
   sudo systemctl restart virtuoso-trading.service
   ```

2. **Identify Issue**:
   - Check if thread pool causing race conditions
   - Verify timeout values aren't too aggressive
   - Look for new error patterns

3. **Hotfix**:
   - Increase callback timeout from 2s → 5s
   - Reduce thread pool workers from 4 → 2
   - Disable network validation retries

---

## References

- Production Logs: `VPS_LOG_ANALYSIS_12H.md`
- WebSocket Manager: `src/core/exchanges/websocket_manager.py:298-496`
- Market Data Manager: `src/core/market/market_data_manager.py:936-1500`
- Python asyncio docs: https://docs.python.org/3/library/asyncio-task.html#timeouts
- ThreadPoolExecutor: https://docs.python.org/3/library/concurrent.futures.html

---

## Next Steps

1. ✅ Complete this investigation document
2. ⏳ Implement Phase 1 critical fixes
3. ⏳ Test fixes locally
4. ⏳ Deploy to VPS with monitoring
5. ⏳ Validate improvements with 2-hour log analysis
6. ⏳ Implement Phase 2 network resilience fixes
7. ⏳ Document final results

---

**Status**: Ready for implementation ✅
**Estimated Time**: 2-3 hours for Phase 1, 1-2 hours for Phase 2
**Risk Level**: Low (changes are defensive and add protection)
