# WebSocket API

The WebSocket API provides real-time updates for market data, order status changes, and system events. WebSockets offer a more efficient way to receive updates compared to polling the REST API.

## Connection

Connect to the WebSocket API at:

```
ws://[hostname]:[port]/ws
```

The WebSocket connection requires authentication using the same API keys as the REST API. Authentication is performed by sending an `authenticate` message after establishing the connection.

## Authentication

After connecting to the WebSocket, you must authenticate:

```json
{
  "action": "authenticate",
  "api_key": "your_api_key",
  "timestamp": 1647356789123,
  "signature": "your_signature"
}
```

The server will respond with:

```json
{
  "event": "authenticated",
  "success": true,
  "timestamp": 1647356789124
}
```

If authentication fails:

```json
{
  "event": "error",
  "message": "Authentication failed",
  "code": 401,
  "timestamp": 1647356789124
}
```

## Subscribing to Channels

After successful authentication, you can subscribe to various data channels:

```json
{
  "action": "subscribe",
  "channels": ["market_data", "orders", "positions"],
  "params": {
    "exchange": "binance",
    "symbols": ["BTCUSDT", "ETHUSDT"]
  }
}
```

The server will respond with:

```json
{
  "event": "subscribed",
  "channels": ["market_data", "orders", "positions"],
  "params": {
    "exchange": "binance",
    "symbols": ["BTCUSDT", "ETHUSDT"]
  },
  "timestamp": 1647356789125
}
```

## Unsubscribing from Channels

To unsubscribe from channels:

```json
{
  "action": "unsubscribe",
  "channels": ["positions"],
  "params": {
    "exchange": "binance",
    "symbols": ["BTCUSDT"]
  }
}
```

The server will respond with:

```json
{
  "event": "unsubscribed",
  "channels": ["positions"],
  "params": {
    "exchange": "binance",
    "symbols": ["BTCUSDT"]
  },
  "timestamp": 1647356789126
}
```

## Available Channels

### Market Data Channel

Provides real-time market data updates.

**Subscription:**
```json
{
  "action": "subscribe",
  "channels": ["market_data"],
  "params": {
    "exchange": "binance",
    "symbols": ["BTCUSDT"],
    "type": "ticker"
  }
}
```

**Data Messages:**
```json
{
  "channel": "market_data",
  "type": "ticker",
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "data": {
    "price": 42650.5,
    "volume": 2541.34,
    "timestamp": 1647356789123,
    "bid": 42650.0,
    "ask": 42651.0,
    "high": 43100.0,
    "low": 42500.0
  },
  "timestamp": 1647356789123
}
```

### Orderbook Channel

Provides real-time order book updates.

**Subscription:**
```json
{
  "action": "subscribe",
  "channels": ["orderbook"],
  "params": {
    "exchange": "binance",
    "symbols": ["BTCUSDT"],
    "depth": 10
  }
}
```

**Data Messages:**
```json
{
  "channel": "orderbook",
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "data": {
    "bids": [
      [42650.0, 1.5],
      [42649.5, 2.3]
    ],
    "asks": [
      [42651.0, 0.8],
      [42652.5, 1.2]
    ],
    "timestamp": 1647356789123
  },
  "timestamp": 1647356789123
}
```

### Trades Channel

Provides real-time trade updates.

**Subscription:**
```json
{
  "action": "subscribe",
  "channels": ["trades"],
  "params": {
    "exchange": "binance",
    "symbols": ["BTCUSDT"]
  }
}
```

**Data Messages:**
```json
{
  "channel": "trades",
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "data": {
    "id": "123456789",
    "price": 42650.5,
    "amount": 0.1,
    "side": "buy",
    "timestamp": 1647356789123
  },
  "timestamp": 1647356789123
}
```

### Orders Channel

Provides real-time updates for your orders.

**Subscription:**
```json
{
  "action": "subscribe",
  "channels": ["orders"],
  "params": {
    "exchange": "binance",
    "symbols": ["BTCUSDT"]
  }
}
```

**Data Messages:**
```json
{
  "channel": "orders",
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "event": "update",
  "data": {
    "id": "123456789",
    "symbol": "BTCUSDT",
    "exchange": "binance",
    "timestamp": 1647356789123,
    "type": "limit",
    "side": "buy",
    "amount": 0.1,
    "price": 42500.0,
    "cost": 4250.0,
    "filled": 0.05,
    "remaining": 0.05,
    "status": "partially_filled",
    "fee": {
      "cost": 2.125,
      "currency": "USDT",
      "rate": 0.001
    }
  },
  "timestamp": 1647356789123
}
```

### Positions Channel

Provides real-time updates for your positions.

**Subscription:**
```json
{
  "action": "subscribe",
  "channels": ["positions"],
  "params": {
    "exchange": "binance",
    "symbols": ["BTCUSDT"]
  }
}
```

**Data Messages:**
```json
{
  "channel": "positions",
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "event": "update",
  "data": {
    "symbol": "BTCUSDT",
    "exchange": "binance",
    "timestamp": 1647356789123,
    "type": "spot",
    "side": "long",
    "amount": 0.5,
    "cost": 21325.0,
    "average_price": 42650.0,
    "unrealized_pnl": 125.0,
    "unrealized_pnl_percentage": 0.58,
    "liquidation_price": null,
    "stop_loss": 41000.0,
    "take_profit": 45000.0,
    "trailing_stop": 2.5
  },
  "timestamp": 1647356789123
}
```

### System Events Channel

Provides real-time system event updates.

**Subscription:**
```json
{
  "action": "subscribe",
  "channels": ["system_events"]
}
```

**Data Messages:**
```json
{
  "channel": "system_events",
  "event": "exchange_connection_status",
  "data": {
    "exchange": "binance",
    "status": "connected",
    "timestamp": 1647356789123
  },
  "timestamp": 1647356789123
}
```

## Error Handling

If an error occurs, the server will send an error message:

```json
{
  "event": "error",
  "message": "Invalid symbol format",
  "code": 400,
  "timestamp": 1647356789125
}
```

Common error codes:
- 400: Bad request
- 401: Unauthorized
- 403: Forbidden
- 404: Not found
- 429: Too many requests
- 500: Internal server error

## Ping/Pong Heartbeat

To keep the connection alive, the client should respond to ping messages with pong messages:

**Server ping:**
```json
{
  "event": "ping",
  "timestamp": 1647356789125
}
```

**Client response:**
```json
{
  "action": "pong",
  "timestamp": 1647356789126
}
```

If no messages are exchanged for 30 seconds, the server will send a ping message. If the client does not respond with a pong message within 10 seconds, the connection will be closed.

## Connection Close

The server may close the connection with a close message:

```json
{
  "event": "close",
  "message": "Session timeout",
  "code": 1000,
  "timestamp": 1647356789125
}
```

Common close codes:
- 1000: Normal closure
- 1001: Going away
- 1008: Policy violation
- 1011: Internal error 