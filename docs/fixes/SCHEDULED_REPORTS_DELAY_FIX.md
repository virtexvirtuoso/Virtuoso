# Scheduled Reports Startup Delay Fix

## Problem
The warning `Symbol FARTCOINUSDT not in cache, initializing` appears early during application startup because scheduled reports try to generate market summaries before the cache has been populated.

## Root Cause
1. MarketReporter starts scheduled reports immediately on startup
2. Scheduled reports check for symbols like FARTCOINUSDT
3. Cache is empty at startup, causing cache miss warnings
4. This is normal behavior but creates unnecessary warning noise

## Solution Implemented

### 1. Added Startup Delay to Scheduled Reports
**File**: `/src/monitoring/market_reporter.py`

**Changes**:
- Added `startup_delay_minutes = 2` configuration
- Track startup time with `_startup_time`
- Delay first scheduled report by 2 minutes to allow cache population

```python
# In __init__ method:
self.startup_delay_minutes = 2  # Wait 2 minutes before first scheduled report
self._startup_time = datetime.utcnow()
self.logger.info(f"Scheduled reports will start after {self.startup_delay_minutes} minute startup delay")

# In run_scheduled_reports method:
if hasattr(self, '_startup_time'):
    elapsed = (datetime.utcnow() - self._startup_time).total_seconds() / 60
    if elapsed < self.startup_delay_minutes:
        remaining = self.startup_delay_minutes - elapsed
        self.logger.info(f"Waiting {remaining:.1f} more minutes before starting scheduled reports (cache population)")
        await asyncio.sleep(remaining * 60)
        self.logger.info("Startup delay complete, beginning scheduled reports")
```

### 2. Changed Cache Warning Level During Startup
**File**: `/src/core/market/market_data_manager.py`

**Changes**:
- Track initialization time with `_init_time`
- Use INFO level instead of WARNING for first 2 minutes
- Helps reduce log noise during normal startup

```python
# In __init__ method:
self._init_time = time.time()  # Track initialization time

# In get_market_data method:
if symbol not in self.data_cache:
    # Use info level for first 2 minutes to reduce startup noise
    if hasattr(self, '_init_time') and (time.time() - self._init_time) < 120:
        self.logger.info(f"Symbol {symbol} not in cache, initializing (startup phase)")
    else:
        self.logger.warning(f"Symbol {symbol} not in cache, initializing")
```

## Benefits

1. **Reduced Log Noise**: Cache miss messages are INFO level during startup instead of WARNING
2. **Better Cache Utilization**: Reports run after cache has been populated
3. **Cleaner Startup**: No unnecessary warnings for expected behavior
4. **Improved Performance**: Avoids redundant data fetches during startup

## Expected Behavior After Fix

1. **On Startup**:
   - You'll see: `"Scheduled reports will start after 2 minute startup delay"`
   - Cache messages will be INFO level: `"Symbol FARTCOINUSDT not in cache, initializing (startup phase)"`
   
2. **After 2 Minutes**:
   - You'll see: `"Startup delay complete, beginning scheduled reports"`
   - Normal scheduled report generation begins
   - Cache should be populated with commonly accessed symbols

3. **After Startup Period**:
   - Cache misses will show as WARNING again (normal behavior)
   - Most symbols should be cached, reducing warnings

## Configuration Options

You can adjust the delays if needed:

1. **Scheduled Reports Delay**: Change `self.startup_delay_minutes` in MarketReporter.__init__
2. **Cache Warning Grace Period**: Change the `120` (seconds) in market_data_manager.py

## Verification

To verify the fix is working:

```bash
# Check for startup delay message
grep "Scheduled reports will start after" logs/app.log

# Check for startup phase cache messages
grep "startup phase" logs/app.log | head -10

# Verify delay completion
grep "Startup delay complete" logs/app.log
```

## Note

The FARTCOINUSDT warning was not an error - it's normal behavior when a symbol is accessed for the first time. This fix simply delays scheduled reports to allow the cache to populate naturally during startup, reducing unnecessary warnings.