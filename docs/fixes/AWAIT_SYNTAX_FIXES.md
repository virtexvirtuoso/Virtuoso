# Await Syntax Error Fixes

## Problem
The application failed to start with:
```
SyntaxError: 'await' outside async function
```

This occurred because `await` statements were used in the `__init__` method of MarketMonitor, which is not an async function.

## Root Cause
Python's `__init__` methods cannot be async, so you cannot use `await` inside them. Any asynchronous initialization must be deferred to an async method like `start()` or `initialize()`.

## Fixes Applied

### 1. MarketMonitor WebSocket Initialization (Line 1937)
**File**: `/src/monitoring/monitor.py`

**Before**:
```python
# In __init__ method
if self.websocket_config.get('enabled', True) and self.symbol_str:
    await self._initialize_websocket()
```

**After**:
```python
# In __init__ method
# Note: WebSocket initialization is deferred to start() method since __init__ is not async
self._websocket_pending_init = self.websocket_config.get('enabled', True) and self.symbol_str
```

### 2. MarketMonitor WebSocket Config Check (Line 1968)
**File**: `/src/monitoring/monitor.py`

**Before**:
```python
# In __init__ method
if self.config.get('exchanges', {}).get('bybit', {}).get('websocket', {}).get('enabled', False):
    self.logger.info("WebSocket is enabled in config, initializing WebSocket connection...")
    await self._initialize_websocket()
```

**After**:
```python
# In __init__ method
if self.config.get('exchanges', {}).get('bybit', {}).get('websocket', {}).get('enabled', False):
    self.logger.info("WebSocket is enabled in config, will initialize after startup")
    self._websocket_pending_init = True
else:
    self.logger.info("WebSocket is disabled in config or not configured")
    self._websocket_pending_init = False
```

### 3. Added Deferred Initialization in start() Method
**File**: `/src/monitoring/monitor.py`

**Added in `start()` method after exchange initialization**:
```python
# Initialize WebSocket if it was deferred from __init__
if hasattr(self, '_websocket_pending_init') and self._websocket_pending_init:
    self.logger.info("Initializing WebSocket connection...")
    await self._initialize_websocket()
```

## Pattern for Async Initialization

When you need async initialization in a class:

```python
class MyClass:
    def __init__(self):
        # Store configuration but don't do async work
        self._needs_async_init = True
        
    async def initialize(self):
        # Do async initialization here
        if self._needs_async_init:
            await self._do_async_setup()
            
    async def start(self):
        # Or do it in start method
        await self.initialize()
```

## Verification

All syntax errors have been resolved:
- `src/monitoring/monitor.py` - ✅ OK
- `src/main.py` - ✅ OK  
- `src/monitoring/market_reporter.py` - ✅ OK
- `src/core/market/market_data_manager.py` - ✅ OK

## Prevention

To prevent this issue in the future:
1. Never use `await` in `__init__` methods
2. Create an async `initialize()` or use existing `start()` method for async setup
3. Use Python linters that can catch these syntax errors before runtime