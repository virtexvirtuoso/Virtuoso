# WebSocket Initialization Race Condition Fix

## Issue
The WebSocket initialization in `main.py` had a race condition where it tried to get top symbols immediately after creating the `TopSymbolsManager`, but the manager hadn't fetched any data yet.

## Root Cause
1. `top_symbols_manager.get_top_symbols()` was called without `await` (line 435)
2. This returned a coroutine object instead of actual data
3. Even if it was awaited, the manager might not have fetched initial data yet

## Fix Applied
Updated the initialization sequence in `src/main.py` (lines 430-452):

### Before:
```python
top_symbols = top_symbols_manager.get_top_symbols()  # Missing await!
if top_symbols:
    symbol_names = [s['symbol'].replace('/', '') for s in top_symbols[:20]]
```

### After:
```python
# First ensure top symbols manager has data
logger.info("Ensuring top symbols manager has fetched initial data...")
await top_symbols_manager.update_top_symbols()

# Get top symbols for WebSocket monitoring (now using await for async method)
top_symbols = await top_symbols_manager.get_top_symbols(limit=20)
if top_symbols:
    symbol_names = [s['symbol'].replace('/', '') for s in top_symbols]
```

## Key Changes:
1. Added `await top_symbols_manager.update_top_symbols()` to ensure data is fetched first
2. Changed to `await top_symbols_manager.get_top_symbols(limit=20)` to properly await the async method
3. Added fallback to initialize with empty array if no symbols available
4. Improved error handling and logging

## Benefits:
- Eliminates race condition during startup
- Ensures WebSocket has valid symbols to subscribe to
- Provides better error messages for debugging
- Allows graceful degradation if symbol fetching fails

## Testing:
To verify the fix works:
1. Enable WebSocket in config: `exchanges.bybit.websocket.enabled: true`
2. Run the application: `python src/main.py`
3. Check logs for "Market data manager initialized with WebSocket connections"
4. Verify no errors about coroutine objects or missing symbols