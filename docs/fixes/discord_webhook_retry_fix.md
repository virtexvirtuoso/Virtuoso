# Discord Webhook Retry Logic Fix

## Problem

The system was experiencing connection errors when sending Discord webhooks, specifically:

```
2025-05-23 09:04:04.101 [ERROR] src.monitoring.alert_manager - Error sending Discord alert: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

**Root Cause:** The `_send_discord_alert` method lacked robust retry logic and error handling for network connectivity issues. When Discord's servers closed connections or became temporarily unavailable, the system would fail immediately without attempting retries.

## Solution

### 1. Added Configuration Options

Added new configuration section in `config/config.yaml`:

```yaml
monitoring:
  alerts:
    discord_webhook:
      max_retries: 3                # Maximum number of retry attempts
      initial_retry_delay: 2        # Initial retry delay in seconds
      timeout_seconds: 30           # Request timeout in seconds
      exponential_backoff: true     # Use exponential backoff for retries
      fallback_enabled: true        # Enable fallback to direct HTTP requests
      recoverable_status_codes:     # HTTP status codes that should trigger retries
        - 429                       # Rate limited
        - 500                       # Internal server error
        - 502                       # Bad gateway
        - 503                       # Service unavailable
        - 504                       # Gateway timeout
```

### 2. Enhanced Error Handling

Updated both `_send_discord_alert` and `send_discord_webhook_message` methods to include:

- **Retry Logic with Exponential Backoff**: Retries failed requests up to 3 times with delays of 2s, 4s, 8s
- **Connection Error Handling**: Specifically handles `requests.exceptions.ConnectionError`, `RemoteDisconnected`, and similar network issues
- **Recoverable Status Code Handling**: Automatically retries for HTTP status codes 429, 500, 502, 503, 504
- **Fallback Mechanism**: Uses direct `aiohttp` requests if the `discord_webhook` library continues to fail
- **Comprehensive Logging**: Detailed logging with unique alert IDs for tracking retry attempts

### 3. Key Improvements

#### Before (Vulnerable to Connection Issues):
```python
async def _send_discord_alert(self, alert: Dict[str, Any]) -> None:
    # ... setup code ...
    webhook = DiscordWebhook(url=self.discord_webhook_url)
    webhook.add_embed(embed)
    
    # Single attempt - fails on any network issue
    response = webhook.execute()
    
    if response and hasattr(response, 'status_code'):
        # Basic success/failure handling
```

#### After (Robust Retry Logic):
```python
async def _send_discord_alert(self, alert: Dict[str, Any]) -> None:
    # ... setup code ...
    
    # Retry logic with exponential backoff
    max_retries = self.webhook_max_retries
    retry_delay = self.webhook_initial_retry_delay
    
    for attempt in range(max_retries):
        try:
            response = webhook.execute()
            
            if response and hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                # Success - exit retry loop
                return
            else:
                # Check for recoverable errors and retry if appropriate
                if response.status_code in self.webhook_recoverable_status_codes:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                    
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                requests.exceptions.HTTPError) as req_err:
            # Handle network errors with retry
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
    
    # Fallback mechanism using direct HTTP requests
    if self.webhook_fallback_enabled:
        # Use aiohttp for direct webhook call
```

## Verification

### Test Results

Created comprehensive test suite (`tests/discord/test_discord_webhook_retry.py`) that validates:

1. **Configuration Loading**: ✅ All retry settings properly loaded from config
2. **Connection Error Retry**: ✅ System retries 3 times for `RemoteDisconnected` errors with exponential backoff
3. **Recoverable Status Codes**: ✅ HTTP 429 (rate limited) triggers retry attempts
4. **Successful Sends**: ✅ Successful requests don't trigger unnecessary retries

### Log Evidence

Test execution shows proper retry behavior:

```
2025-05-23 11:46:15,871 [WARNING] [ALERT:f0b1288c] Network error sending alert (attempt 1/3): ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
2025-05-23 11:46:15,872 [INFO] [ALERT:f0b1288c] Retrying after 0.5 seconds...
2025-05-23 11:46:16,373 [WARNING] [ALERT:f0b1288c] Network error sending alert (attempt 2/3): ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
2025-05-23 11:46:16,374 [INFO] [ALERT:f0b1288c] Retrying after 1.0 seconds...
2025-05-23 11:46:17,376 [WARNING] [ALERT:f0b1288c] Network error sending alert (attempt 3/3): ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
2025-05-23 11:46:17,376 [INFO] [ALERT:f0b1288c] Attempting fallback using direct HTTP request...
```

## Benefits

1. **Improved Reliability**: System now gracefully handles temporary network issues and Discord API downtime
2. **Configurable Behavior**: Retry attempts, delays, and timeouts can be adjusted via configuration
3. **Better Observability**: Detailed logging with unique alert IDs helps track retry attempts and failures
4. **Fallback Mechanism**: Direct HTTP requests provide alternative path when discord_webhook library fails
5. **Rate Limit Handling**: Automatic retry for Discord API rate limiting (HTTP 429)

## Configuration Recommendations

For production environments, consider:

```yaml
discord_webhook:
  max_retries: 5              # More retries for production
  initial_retry_delay: 1      # Faster initial retry
  timeout_seconds: 45         # Longer timeout for large files
  exponential_backoff: true
  fallback_enabled: true
```

For development/testing:

```yaml
discord_webhook:
  max_retries: 2              # Fewer retries for faster feedback
  initial_retry_delay: 0.5    # Shorter delays for testing
  timeout_seconds: 15
  exponential_backoff: true
  fallback_enabled: false     # Disable fallback to see errors clearly
```

This fix ensures the Discord alerting system is much more resilient to network connectivity issues and temporary API outages. 