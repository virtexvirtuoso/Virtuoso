# System API

The System API provides access to system status, configuration, and performance metrics for the Virtuoso Trading System.

## Endpoints

### Get System Status

Retrieves the current status of the trading system.

```
GET /status
```

#### Response

```json
{
  "status": "running",
  "uptime": 3456789,
  "version": "1.5.2",
  "system_time": 1647356789123,
  "services": {
    "order_manager": "running",
    "market_data": "running",
    "position_manager": "running",
    "risk_manager": "running",
    "database": "running"
  },
  "exchanges": {
    "binance": "connected",
    "bybit": "connected",
    "coinbase": "disconnected"
  },
  "last_error": null
}
```

### Get System Configuration

Retrieves the current system configuration.

```
GET /config
```

#### Response

```json
{
  "global": {
    "debug_mode": false,
    "trading_enabled": true,
    "max_concurrent_orders": 50,
    "default_exchange": "binance",
    "risk_management": {
      "max_position_size_usd": 10000,
      "daily_loss_limit_percentage": 5,
      "max_leverage": 3
    }
  },
  "exchanges": {
    "binance": {
      "api_key_configured": true,
      "trading_enabled": true,
      "margin_trading_enabled": false,
      "futures_trading_enabled": true,
      "maker_fee": 0.001,
      "taker_fee": 0.001
    },
    "bybit": {
      "api_key_configured": true,
      "trading_enabled": true,
      "margin_trading_enabled": true,
      "futures_trading_enabled": true,
      "maker_fee": 0.0006,
      "taker_fee": 0.001
    }
  },
  "data_providers": {
    "ohlcv": ["binance", "bybit"],
    "orderbook": ["binance", "bybit"],
    "trades": ["binance"]
  },
  "technical_analysis": {
    "default_timeframe": "1h",
    "indicators": {
      "rsi": {
        "enabled": true,
        "period": 14
      },
      "macd": {
        "enabled": true,
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9
      }
    }
  }
}
```

### Update System Configuration

Updates the system configuration.

```
PATCH /config
```

#### Request Body

```json
{
  "global": {
    "trading_enabled": false
  },
  "exchanges": {
    "binance": {
      "trading_enabled": false
    }
  },
  "technical_analysis": {
    "indicators": {
      "rsi": {
        "period": 21
      }
    }
  }
}
```

#### Response

```json
{
  "success": true,
  "message": "Configuration updated successfully",
  "config": {
    "global": {
      "debug_mode": false,
      "trading_enabled": false,
      "max_concurrent_orders": 50,
      "default_exchange": "binance",
      "risk_management": {
        "max_position_size_usd": 10000,
        "daily_loss_limit_percentage": 5,
        "max_leverage": 3
      }
    },
    "exchanges": {
      "binance": {
        "api_key_configured": true,
        "trading_enabled": false,
        "margin_trading_enabled": false,
        "futures_trading_enabled": true,
        "maker_fee": 0.001,
        "taker_fee": 0.001
      },
      "bybit": {
        "api_key_configured": true,
        "trading_enabled": true,
        "margin_trading_enabled": true,
        "futures_trading_enabled": true,
        "maker_fee": 0.0006,
        "taker_fee": 0.001
      }
    },
    "data_providers": {
      "ohlcv": ["binance", "bybit"],
      "orderbook": ["binance", "bybit"],
      "trades": ["binance"]
    },
    "technical_analysis": {
      "default_timeframe": "1h",
      "indicators": {
        "rsi": {
          "enabled": true,
          "period": 21
        },
        "macd": {
          "enabled": true,
          "fast_period": 12,
          "slow_period": 26,
          "signal_period": 9
        }
      }
    }
  }
}
```

### Get System Metrics

Retrieves performance metrics for the trading system.

```
GET /metrics
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| period | string | Time period for metrics ("hour", "day", "week", "month", "all") |

#### Response

```json
{
  "timestamp": 1647356789123,
  "period": "day",
  "system": {
    "cpu_usage": 12.5,
    "memory_usage": 512.7,
    "disk_usage": 25.3,
    "network_in": 1024.5,
    "network_out": 512.3,
    "requests_per_minute": 250
  },
  "exchanges": {
    "binance": {
      "api_requests": 15678,
      "average_latency": 85.3,
      "errors": 2,
      "success_rate": 99.99
    },
    "bybit": {
      "api_requests": 8765,
      "average_latency": 102.7,
      "errors": 5,
      "success_rate": 99.94
    }
  },
  "trading": {
    "orders_placed": 45,
    "orders_filled": 42,
    "orders_canceled": 3,
    "trades_executed": 42,
    "average_slippage": 0.05,
    "average_execution_time": 236.7
  }
}
```

### Get System Logs

Retrieves system logs.

```
GET /logs
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| level | string | Log level filter ("info", "warning", "error", "debug") |
| limit | integer | Maximum number of logs to return (default: 100, max: 1000) |
| since | integer | Timestamp in milliseconds to fetch logs from |
| service | string | Filter logs by service name |

#### Response

```json
[
  {
    "timestamp": 1647356789123,
    "level": "info",
    "service": "order_manager",
    "message": "Order 123456789 successfully placed on binance"
  },
  {
    "timestamp": 1647356788000,
    "level": "warning",
    "service": "market_data",
    "message": "Delayed response from bybit API"
  },
  {
    "timestamp": 1647356787000,
    "level": "error",
    "service": "position_manager",
    "message": "Failed to update position stop-loss: API error"
  }
]
```

### Get Exchange Connection Status

Retrieves the connection status for all configured exchanges.

```
GET /exchanges/status
```

#### Response

```json
{
  "timestamp": 1647356789123,
  "exchanges": {
    "binance": {
      "status": "connected",
      "connected_since": 1647356000000,
      "api_key_configured": true,
      "api_key_permissions": {
        "read": true,
        "trade": true,
        "withdraw": false
      },
      "endpoints": {
        "rest": "online",
        "websocket": "online"
      },
      "last_api_request": 1647356780000,
      "last_error": null
    },
    "bybit": {
      "status": "connected",
      "connected_since": 1647356100000,
      "api_key_configured": true,
      "api_key_permissions": {
        "read": true,
        "trade": true,
        "withdraw": false
      },
      "endpoints": {
        "rest": "online",
        "websocket": "online"
      },
      "last_api_request": 1647356785000,
      "last_error": null
    },
    "coinbase": {
      "status": "disconnected",
      "connected_since": null,
      "api_key_configured": true,
      "api_key_permissions": null,
      "endpoints": {
        "rest": "offline",
        "websocket": "offline"
      },
      "last_api_request": null,
      "last_error": {
        "timestamp": 1647356300000,
        "message": "Connection timeout"
      }
    }
  }
}
```

### Reset Exchange Connection

Resets the connection to a specific exchange.

```
POST /exchanges/{exchange_id}/reset
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| exchange_id | string | ID of the exchange |

#### Response

```json
{
  "success": true,
  "message": "Connection to binance successfully reset",
  "status": {
    "status": "connected",
    "connected_since": 1647356789123,
    "api_key_configured": true,
    "api_key_permissions": {
      "read": true,
      "trade": true,
      "withdraw": false
    },
    "endpoints": {
      "rest": "online",
      "websocket": "online"
    },
    "last_api_request": null,
    "last_error": null
  }
}
```

## Models

### SystemStatus

```python
class SystemStatus(BaseModel):
    status: str
    uptime: int
    version: str
    system_time: int
    services: Dict[str, str]
    exchanges: Dict[str, str]
    last_error: Optional[Dict[str, Any]] = None
```

### SystemConfiguration

```python
class SystemConfiguration(BaseModel):
    global_config: Dict[str, Any]
    exchanges: Dict[str, Dict[str, Any]]
    data_providers: Dict[str, List[str]]
    technical_analysis: Dict[str, Any]
```

### SystemMetrics

```python
class SystemMetrics(BaseModel):
    timestamp: int
    period: str
    system: Dict[str, float]
    exchanges: Dict[str, Dict[str, Any]]
    trading: Dict[str, Any]
```

### LogEntry

```python
class LogEntry(BaseModel):
    timestamp: int
    level: str
    service: str
    message: str
```

### ExchangeStatus

```python
class ExchangeStatus(BaseModel):
    status: str
    connected_since: Optional[int] = None
    api_key_configured: bool
    api_key_permissions: Optional[Dict[str, bool]] = None
    endpoints: Dict[str, str]
    last_api_request: Optional[int] = None
    last_error: Optional[Dict[str, Any]] = None
```

### ExchangesStatus

```python
class ExchangesStatus(BaseModel):
    timestamp: int
    exchanges: Dict[str, ExchangeStatus]
``` 