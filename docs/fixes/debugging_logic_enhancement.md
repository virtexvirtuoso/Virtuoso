# Debugging Logic Enhancement for System Issues

## Overview

Based on the error logs provided, I've added comprehensive debugging logic to help identify the root causes of several system issues:

1. **System webhook timeout errors**
2. **Memory usage alerts**
3. **WebSocket connection issues**
4. **API timeout warnings**

## Issues Identified

### 1. System Webhook Timeout Error
```
2025-07-18 09:08:48.454 [ERROR] src.monitoring.alert_manager - ❌ ERROR: System webhook alert timed out after 10 seconds
```

**Root Cause**: The system webhook is timing out after 10 seconds, likely due to:
- Network connectivity issues
- Discord server problems
- Incorrect webhook URL format
- DNS resolution issues

### 2. Memory Usage Alerts
```
2025-07-18 09:08:26.433 [INFO] src.monitoring.alert_manager - Routing memory alert to system webhook only
```

**Root Cause**: Memory alerts are being triggered despite having thresholds set to 98%. This suggests:
- Configuration conflicts between different memory tracking systems
- Multiple memory monitoring components with different thresholds
- Memory usage actually reaching high levels

### 3. WebSocket Connection Issues
```
2025-07-18 09:08:34.783 [INFO] src.core.exchanges.websocket_manager - Attempting to reconnect conn_9 in 1s...
2025-07-18 09:08:36.772 [INFO] src.core.exchanges.websocket_manager - Attempting to reconnect conn_2 in 1s...
2025-07-18 09:08:38.927 [INFO] src.core.exchanges.websocket_manager - Attempting to reconnect conn_7 in 1s...
```

**Root Cause**: Multiple WebSocket connections are failing simultaneously, indicating:
- Network connectivity issues
- Exchange server problems
- Connection pool exhaustion
- Rate limiting from the exchange

### 4. API Timeout Warnings
```
2025-07-18 09:08:27.552 [WARNING] src.core.exchanges.manager - ⚠️  WARNING: Timeout fetching ticker for XLMUSDT (attempt 1/3)
2025-07-18 09:08:43.182 [WARNING] src.core.exchanges.manager - ⚠️  WARNING: Timeout fetching ticker for XLMUSDT (attempt 2/3)
```

**Root Cause**: API calls are timing out, suggesting:
- Network latency issues
- Exchange server overload
- Rate limiting
- Symbol-specific issues (XLMUSDT)

## Debugging Logic Added

### 1. Enhanced System Webhook Debugging

**File**: `src/monitoring/alert_manager.py`
**Method**: `_send_system_webhook_alert`

**Added Debugging**:
- Webhook URL validation and format checking
- Request timing and response status logging
- Detailed error categorization (timeout, client error, general error)
- Network diagnostics for common issues
- Full traceback logging for unexpected errors

**Debug Output Example**:
```
=== SYSTEM WEBHOOK ALERT DEBUG ===
System webhook URL configured: True
Webhook URL length: 121
Webhook URL starts with https: True
Webhook URL contains discord.com: True
Creating system webhook payload for message: High memory_usage...
Payload created with 1 base fields
Added 0 detail fields to payload
Creating aiohttp session with timeout: 10 seconds
Preparing POST request to system webhook
Payload size: 1234 characters
Executing POST request to system webhook
Request completed in 10.5 seconds
Response status: 408
Response headers: {...}
System webhook failed with status 408: Request Timeout
```

### 2. Enhanced Memory Threshold Debugging

**File**: `src/monitoring/components/health_monitor.py`
**Method**: `_check_threshold_violations`

**Added Debugging**:
- Current memory usage logging
- Configuration validation
- Threshold comparison logging
- Alert trigger decision tracking
- Process details when available

**Debug Output Example**:
```
=== MEMORY THRESHOLD CHECK DEBUG ===
Current memory usage: 95.2% (8192MB)
Total memory: 16384MB
Available memory: 819MB
Memory warning threshold: 98%
Memory critical threshold: 98%
Min warning size MB: 2048
Suppress repeated warnings: True
Disable memory warnings: False
Include process details: True
Memory metric warning threshold: 98%
Memory metric critical threshold: 98%
Current memory MB: 8192 >= Min warning size MB: 2048 = True
Current memory percent: 95.2% >= Warning threshold: 98% = False
Current memory percent: 95.2% >= Critical threshold: 98% = False
Memory usage above minimum size threshold - proceeding with alert checks
No memory alert triggered - usage 95.2% below thresholds
```

### 3. Enhanced WebSocket Reconnection Debugging

**File**: `src/core/exchanges/websocket_manager.py`
**Method**: `_reconnect`

**Added Debugging**:
- Connection state tracking
- Reconnection attempt logging
- Session cleanup verification
- Backoff timing details
- Success/failure tracking

**Debug Output Example**:
```
=== WEBSOCKET RECONNECT DEBUG ===
Connection ID: conn_9
Topics to resubscribe: ['orderbook.50.BTCUSDT', 'orderbook.50.ETHUSDT']
Session closed: False
Active connections before reconnect: 5
Reconnect tasks running: 3
Closing existing session for conn_9
Session closed successfully for conn_9
Removing conn_9 from active connections
Active connections after removal: 4
Starting reconnection process for conn_9
Max retries: 10, Max backoff: 60s
Attempting to reconnect conn_9 in 1s... (attempt 1/10)
Creating new connection for conn_9
Successfully reconnected conn_9
Active connections after successful reconnect: 5
```

### 4. Enhanced API Timeout Debugging

**File**: `src/core/exchanges/manager.py`
**Method**: `fetch_ticker`

**Added Debugging**:
- Symbol and exchange details
- Request timing
- Exchange initialization status
- Error categorization
- Retry attempt tracking

**Debug Output Example**:
```
=== FETCH TICKER DEBUG ===
Symbol: XLMUSDT
Exchange ID: bybit
Current time: 1749879600.123
Fetch ticker attempt 1/3 for XLMUSDT
Using exchange: BybitExchange
Exchange initialized: True
Formatted API symbol: XLMUSDT
Using timeout: 5 seconds
Timeout fetching ticker for XLMUSDT (attempt 1/3) after 5.0s
Timeout occurred while fetching from exchange: BybitExchange
API symbol used: XLMUSDT
Waiting 2s before retry 2
```

## Recommendations for Fixing Issues

### 1. System Webhook Issues

**Immediate Actions**:
1. **Verify Webhook URL**: Check that `SYSTEM_ALERTS_WEBHOOK_URL` environment variable is correctly set
2. **Test Connectivity**: Manually test the webhook URL with a simple curl command
3. **Increase Timeout**: Consider increasing the timeout from 10 to 30 seconds
4. **Add Retry Logic**: Implement exponential backoff for webhook failures

**Configuration Check**:
```yaml
monitoring:
  alerts:
    system_alerts:
      use_system_webhook: true
      webhook_timeout: 30  # Increase from 10
      max_retries: 3
```

### 2. Memory Alert Issues

**Immediate Actions**:
1. **Check Memory Usage**: Monitor actual system memory usage
2. **Verify Configuration**: Ensure all memory thresholds are consistently set to 98%
3. **Disable Redundant Alerts**: Temporarily disable memory warnings if they're too frequent
4. **Memory Optimization**: Review memory-intensive operations

**Configuration Check**:
```yaml
monitoring:
  memory_tracking:
    warning_threshold_percent: 98
    critical_threshold_percent: 98
    disable_memory_warnings: false  # Set to true if too frequent
    suppress_repeated_warnings: true
```

### 3. WebSocket Connection Issues

**Immediate Actions**:
1. **Reduce Connection Count**: Limit the number of simultaneous WebSocket connections
2. **Implement Connection Pooling**: Reuse connections instead of creating new ones
3. **Add Circuit Breaker**: Prevent cascading failures
4. **Monitor Network**: Check for network connectivity issues

**Configuration Check**:
```yaml
exchanges:
  bybit:
    websocket:
      max_connections: 5  # Reduce from current value
      reconnect_attempts: 5  # Reduce from 10
      reconnect_delay: 2  # Increase from 1
```

### 4. API Timeout Issues

**Immediate Actions**:
1. **Increase Timeouts**: Extend timeout values for API calls
2. **Implement Rate Limiting**: Add proper rate limiting to prevent API overload
3. **Add Circuit Breaker**: Prevent repeated failures from overwhelming the system
4. **Symbol-Specific Handling**: Add special handling for problematic symbols like XLMUSDT

**Configuration Check**:
```yaml
exchanges:
  bybit:
    api:
      timeout: 10  # Increase from 5
      max_retries: 3
      rate_limit: 100  # requests per minute
```

## Monitoring and Alerting Improvements

### 1. Enhanced Error Tracking
- Track error patterns by type and frequency
- Implement alerting for repeated failures
- Add circuit breaker patterns for failing components

### 2. Performance Monitoring
- Monitor API response times
- Track WebSocket connection health
- Monitor memory usage trends

### 3. Automated Recovery
- Implement automatic restart for failing components
- Add health checks for critical services
- Implement graceful degradation

## Next Steps

1. **Enable Debug Logging**: Set log level to DEBUG to see the enhanced debugging output
2. **Monitor the Debug Output**: Watch for patterns in the debug logs
3. **Implement Fixes**: Apply the configuration changes recommended above
4. **Test Changes**: Verify that the fixes resolve the issues
5. **Monitor Results**: Continue monitoring to ensure stability

## Debug Output Analysis

To analyze the debug output effectively:

1. **Look for Patterns**: Identify recurring issues across different components
2. **Check Timing**: Note when issues occur (time of day, system load, etc.)
3. **Correlate Events**: Connect related issues (e.g., memory alerts and webhook timeouts)
4. **Track Metrics**: Monitor system performance during issue periods

The enhanced debugging logic will provide detailed information to help identify and resolve these system issues quickly and effectively. 