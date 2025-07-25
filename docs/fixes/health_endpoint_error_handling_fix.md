# Health Endpoint Error Handling Fix

## Issue
The `/health` endpoint was returning HTTP 500 errors when certain components were not initialized or when async operations failed.

## Root Cause
1. The health check was using `await` operations on potentially `None` objects
2. No proper null checks before calling async methods like `is_healthy()`
3. Exception handling was catching and re-raising HTTPException but converting other exceptions to 500 errors

## Solution Implemented

### 1. Main Health Endpoint (`/health` in main.py)
- Added individual try-except blocks for each component check
- Proper null checks before calling async methods
- Returns degraded status (200) instead of 500 for non-critical failures
- Only returns 503 when all components are unhealthy
- Provides detailed component status and unhealthy component list

### 2. Alpha Scanner Health Endpoint (`/api/alpha/health`)
- Removed dependency injection that could fail
- Added graceful handling when exchange manager is not available
- Returns degraded status instead of throwing exceptions
- Provides meaningful error messages

## Key Changes

### Before:
```python
required_components = {
    "exchange_manager": bool(exchange_manager and await exchange_manager.is_healthy()),
    # This would throw AttributeError if exchange_manager is None
}
```

### After:
```python
# Check exchange_manager
try:
    if exchange_manager:
        required_components["exchange_manager"] = await exchange_manager.is_healthy()
    else:
        required_components["exchange_manager"] = False
except Exception as e:
    logger.debug(f"Error checking exchange_manager health: {e}")
    required_components["exchange_manager"] = False
```

## Response Status Codes
- **200 OK**: System is healthy or degraded but operational
- **503 Service Unavailable**: All components are unhealthy (critical failure)
- **No more 500 errors**: All exceptions are handled gracefully

## Testing
Use the provided test script:
```bash
python tests/test_health_endpoint.py [port]
```

This will test the health endpoint and display the status and any unhealthy components.

## Benefits
1. Load balancers won't remove instances due to transient 500 errors
2. Better visibility into which components are failing
3. Graceful degradation - system can operate with some components down
4. Proper logging at debug level for troubleshooting
5. No uncaught exceptions reaching the user