# System Webhook Alert Error - Root Cause Analysis and Fix

## Error Description

The system was logging the following error:
```
2025-07-17 09:43:05.044 [ERROR] src.monitoring.alert_manager - ❌ ERROR: Error sending system webhook alert:  (alert_manager.py:4407)
```

The error message was empty after the colon, indicating an issue with exception handling and the underlying webhook request.

## Root Cause Analysis

### Investigation Steps

1. **Error Location**: The error was occurring in the `_send_system_webhook_alert` method in `src/monitoring/alert_manager.py` at line 4407.

2. **Environment Check**: Verified that the `SYSTEM_ALERTS_WEBHOOK_URL` environment variable was properly configured:
   - URL was set and valid Discord webhook format
   - Length: 121 characters
   - Starts with `https://discord.com/`
   - No whitespace or formatting issues

3. **Payload Format Analysis**: Compared the failing method with working Discord webhook implementations in the codebase.

### Root Cause

The `_send_system_webhook_alert` method was using an **incorrect payload format** for Discord webhooks:

**❌ Incorrect Format (causing the error):**
```python
payload = {
    "text": message,           # Discord expects "content", not "text"
    "details": details or {},  # Discord doesn't understand this field
    "timestamp": time.time(),  # Discord doesn't understand this field
    "source": "virtuoso_trading" # Discord doesn't understand this field
}
```

**✅ Correct Discord Webhook Format:**
```python
payload = {
    "content": message,  # Discord expects "content"
    "embeds": [{          # Proper Discord embed structure
        "title": "System Alert",
        "description": message,
        "color": 0xf39c12,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fields": [...],
        "footer": {"text": "Virtuoso System Monitoring"}
    }]
}
```

### Why the Error Message Was Empty

When Discord received the malformed payload, it returned an HTTP error response (likely 400 Bad Request), but the exception handling only captured `str(e)` which didn't contain the full HTTP response details.

## Fix Implementation

### 1. Fixed Payload Format

Updated the `_send_system_webhook_alert` method to use proper Discord webhook format:

```python
async def _send_system_webhook_alert(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Send alert to system webhook for monitoring."""
    if not self.system_webhook_url:
        return
        
    try:
        # Create proper Discord webhook payload format
        payload = {
            "content": message,  # Discord expects "content", not "text"
            "embeds": [{
                "title": "System Alert",
                "description": message,
                "color": 0xf39c12,  # Orange color
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "fields": [
                    {
                        "name": "Source",
                        "value": "virtuoso_trading",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "Virtuoso System Monitoring"
                }
            }]
        }
        
        # Add details as embed fields if provided
        if details:
            embed_fields = payload["embeds"][0]["fields"]
            for key, value in details.items():
                # Skip complex objects and limit field count
                if len(embed_fields) >= 25:  # Discord limit
                    break
                if isinstance(value, (str, int, float, bool)):
                    embed_fields.append({
                        "name": str(key)[:256],  # Discord field name limit
                        "value": str(value)[:1024],  # Discord field value limit
                        "inline": True
                    })
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.system_webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status in [200, 204]:  # Both 200 and 204 are success codes for Discord webhooks
                    self.logger.debug("System webhook alert sent successfully")
                else:
                    # Get response text for better error diagnostics
                    response_text = await response.text()
                    self.logger.warning(f"System webhook failed with status {response.status}: {response_text[:200]}")
                    
    except asyncio.TimeoutError:
        self.logger.error("System webhook alert timed out after 10 seconds")
    except aiohttp.ClientError as e:
        self.logger.error(f"System webhook client error: {type(e).__name__}: {str(e)}")
    except Exception as e:
        self.logger.error(f"Error sending system webhook alert: {type(e).__name__}: {str(e)}")
        # Add traceback for debugging
        import traceback
        self.logger.debug(f"System webhook error traceback: {traceback.format_exc()}")
```

### 2. Improved Error Handling

- Added specific exception types for better error categorization
- Included HTTP response text in error messages
- Added traceback logging for debugging
- Handle Discord's 204 (No Content) success response

### 3. Discord Webhook Standards Compliance

- Use `"content"` field instead of `"text"`
- Proper embed structure with Discord-compatible fields
- Respect Discord field limits (25 fields max, 256 char names, 1024 char values)
- Include proper timestamp formatting
- Add footer for identification

## Testing

Verified the fix works correctly:

```bash
System webhook URL configured: True
✅ System webhook test completed successfully!
```

No more error messages or warnings in the logs.

## Impact

This fix resolves:
- ❌ Empty error messages in logs
- ❌ Failed system webhook alerts
- ❌ Malformed Discord webhook payloads
- ✅ Proper system alert routing
- ✅ Clear error diagnostics
- ✅ Discord webhook compliance

## Prevention

To prevent similar issues:
1. Always use proper Discord webhook payload format
2. Test webhook implementations against Discord's API documentation
3. Include comprehensive error handling with response details
4. Use existing working webhook implementations as templates
5. Validate webhook payloads before sending

## Related Files

- `src/monitoring/alert_manager.py` - Main fix location
- `config/config.yaml` - System webhook configuration
- Environment variable: `SYSTEM_ALERTS_WEBHOOK_URL` 