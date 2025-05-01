# Virtuoso Trading System API Documentation

The Virtuoso Trading System provides a powerful REST API that allows you to interact with cryptocurrency exchanges, analyze market data, and execute trades programmatically.

## API Base URL

```
http://[hostname]:[port]/api/v1
```

## Authentication

Authentication is required for endpoints that perform actions (trading, accessing private data). The API uses API keys for authentication.

Include the following headers with your requests:
- `X-API-Key`: Your API key
- `X-API-Timestamp`: Current timestamp in milliseconds
- `X-API-Signature`: HMAC SHA256 signature

## API Sections

The API is organized into the following sections:

1. [Market Data](./market.md) - Access market data, order books, and technical analysis
2. [Trading](./trading.md) - Place and manage orders, track positions
3. [System](./system.md) - System status, performance metrics, and configuration
4. [Signals](./signals.md) - Access trading signals and signal reports

## Response Format

All API responses are in JSON format and follow a consistent structure:

```json
{
  "success": true,
  "data": { ... },
  "timestamp": 1647356789123
}
```

In case of an error:

```json
{
  "success": false,
  "error": {
    "code": 400,
    "message": "Invalid parameters"
  },
  "timestamp": 1647356789123
}
```

## Rate Limits

The API implements rate limiting to ensure system stability:

- Public endpoints: 60 requests per minute
- Private endpoints: 20 requests per minute
- Trading endpoints: 10 requests per minute
- Signals endpoints: 60 requests per minute

Rate limit headers are included in each response:
- `X-RateLimit-Limit`: Total requests allowed in the time window
- `X-RateLimit-Remaining`: Remaining requests in the current window
- `X-RateLimit-Reset`: Time (Unix timestamp) when the rate limit resets

## Common Parameters

Many endpoints support the following common parameters:

- `exchange_id`: The ID of the exchange to query or interact with
- `symbol`: Trading pair in exchange format (e.g., "BTC/USDT")
- `timeframe`: Time interval for candle data (e.g., "1m", "5m", "1h", "1d") 