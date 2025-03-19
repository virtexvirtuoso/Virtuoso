# API Authentication

The Virtuoso Trading System API uses API keys and HMAC signatures to secure access to the API endpoints. This document explains how to properly authenticate your API requests.

## API Keys

To use the Virtuoso Trading System API, you need to generate an API key pair consisting of:

1. **API Key**: A public identifier for your API client
2. **API Secret**: A private key used to sign requests

You can generate API keys from the Virtuoso Trading System web interface under Settings > API Keys.

## Authentication Headers

All authenticated API requests must include the following headers:

| Header | Description |
|--------|-------------|
| X-API-Key | Your API key |
| X-API-Timestamp | Current Unix timestamp in milliseconds |
| X-API-Signature | HMAC-SHA256 signature of the request |

## Creating the Signature

The signature is created using the HMAC-SHA256 algorithm with your API secret as the key. The signature is based on a string created from:

1. The HTTP method (GET, POST, PUT, DELETE)
2. The request path (including query parameters)
3. The request timestamp
4. The request body (for POST, PUT requests)

### Signature String Format

```
{METHOD}\n{PATH}\n{TIMESTAMP}\n{BODY}
```

Where:
- `{METHOD}` is the HTTP method in uppercase (e.g., "GET", "POST")
- `{PATH}` is the full request path including query parameters
- `{TIMESTAMP}` is the Unix timestamp in milliseconds (same as in the X-API-Timestamp header)
- `{BODY}` is the request body as a JSON string (for POST, PUT requests) or empty string for GET requests

### Signature Calculation

Here's an example of how to calculate the signature in Python:

```python
import hmac
import hashlib
import time
import json

def generate_signature(api_secret, method, path, timestamp, body=None):
    # Convert body to JSON string if it exists
    body_str = json.dumps(body) if body else ""
    
    # Create the string to sign
    string_to_sign = f"{method}\n{path}\n{timestamp}\n{body_str}"
    
    # Create the HMAC signature using SHA256
    signature = hmac.new(
        api_secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature

# Example usage
api_key = "your_api_key"
api_secret = "your_api_secret"
method = "POST"
path = "/api/v1/binance/order"
timestamp = int(time.time() * 1000)
body = {
    "symbol": "BTC/USDT",
    "type": "limit",
    "side": "buy",
    "amount": 0.1,
    "price": 42500.0
}

signature = generate_signature(api_secret, method, path, timestamp, body)

# Create headers
headers = {
    "X-API-Key": api_key,
    "X-API-Timestamp": str(timestamp),
    "X-API-Signature": signature,
    "Content-Type": "application/json"
}
```

## Example API Request

Here's a complete example of making an authenticated API request in Python:

```python
import requests
import hmac
import hashlib
import time
import json

def make_request(api_key, api_secret, method, path, body=None):
    # Base URL
    base_url = "http://your-virtuoso-instance.com"
    
    # Get current timestamp
    timestamp = int(time.time() * 1000)
    
    # Generate signature
    signature = generate_signature(api_secret, method, path, timestamp, body)
    
    # Create headers
    headers = {
        "X-API-Key": api_key,
        "X-API-Timestamp": str(timestamp),
        "X-API-Signature": signature,
        "Content-Type": "application/json"
    }
    
    # Make the request
    url = base_url + path
    
    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=body)
    elif method == "PUT":
        response = requests.put(url, headers=headers, json=body)
    elif method == "DELETE":
        response = requests.delete(url, headers=headers)
    
    return response.json()

def generate_signature(api_secret, method, path, timestamp, body=None):
    # Convert body to JSON string if it exists
    body_str = json.dumps(body) if body else ""
    
    # Create the string to sign
    string_to_sign = f"{method}\n{path}\n{timestamp}\n{body_str}"
    
    # Create the HMAC signature using SHA256
    signature = hmac.new(
        api_secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature

# Example usage
api_key = "your_api_key"
api_secret = "your_api_secret"

# Get market data
result = make_request(
    api_key,
    api_secret,
    "GET",
    "/api/v1/binance/BTC/USDT/data"
)
print(result)

# Place an order
order_result = make_request(
    api_key,
    api_secret,
    "POST",
    "/api/v1/binance/order",
    {
        "symbol": "BTC/USDT",
        "type": "limit",
        "side": "buy",
        "amount": 0.1,
        "price": 42500.0
    }
)
print(order_result)
```

## API Key Permissions

When creating API keys, you can specify the following permissions:

1. **Read Only**: Can only access market data and read-only endpoints
2. **Trading**: Can place and manage orders
3. **Withdrawal**: Can withdraw funds (not recommended for most applications)

It's recommended to use the least privileged permission level needed for your application.

## IP Restrictions

You can enhance security by restricting API key usage to specific IP addresses. When generating an API key, you can specify allowed IP addresses or CIDR ranges.

## Rate Limits

API requests are subject to rate limits. The rate limits vary depending on the endpoint and your API key permission level. If you exceed the rate limits, your requests will be rejected with a 429 status code.

Rate limit information is included in the response headers:

| Header | Description |
|--------|-------------|
| X-RateLimit-Limit | The maximum number of requests you can make per minute |
| X-RateLimit-Remaining | The number of requests remaining in the current rate limit window |
| X-RateLimit-Reset | The time at which the current rate limit window resets in UTC epoch seconds |

## Best Practices

1. **Never share your API secret**: Keep your API secret secure and never expose it in client-side code
2. **Use appropriate permissions**: Only request the permissions your application needs
3. **Implement IP restrictions**: Restrict API key usage to your application's IP addresses
4. **Handle rate limits gracefully**: Implement exponential backoff when rate limited
5. **Validate server responses**: Always verify that the response contains the expected data
6. **Rotate API keys periodically**: Regularly generate new API keys and deactivate old ones 