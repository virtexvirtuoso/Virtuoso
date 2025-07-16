# Trading API

The Trading API allows you to place orders, manage positions, and retrieve portfolio information across multiple exchanges.

## Endpoints

### Place Order

Places a new order on the specified exchange.

```
POST /{exchange_id}/order
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| exchange_id | string | ID of the exchange |

#### Request Body

```json
{
  "symbol": "BTC/USDT",
  "type": "limit",
  "side": "buy",
  "amount": 0.1,
  "price": 42500.0,
  "params": {
    "timeInForce": "GTC"
  }
}
```

#### Response

```json
{
  "id": "123456789",
  "symbol": "BTC/USDT",
  "exchange": "binance",
  "timestamp": 1647356789123,
  "type": "limit",
  "side": "buy",
  "amount": 0.1,
  "price": 42500.0,
  "cost": 4250.0,
  "filled": 0.0,
  "remaining": 0.1,
  "status": "open",
  "fee": null
}
```

### Get Orders

Retrieves orders for a specific symbol from an exchange.

```
GET /{exchange_id}/orders
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| exchange_id | string | ID of the exchange |
| symbol | string | Trading pair (e.g., "BTC/USDT") |
| status | string | Optional filter for order status ("open", "closed", "all") |
| limit | integer | Maximum number of orders to return (default: 50, max: 500) |
| since | integer | Timestamp in milliseconds to fetch orders from |

#### Response

```json
[
  {
    "id": "123456789",
    "symbol": "BTC/USDT",
    "exchange": "binance",
    "timestamp": 1647356789123,
    "type": "limit",
    "side": "buy",
    "amount": 0.1,
    "price": 42500.0,
    "cost": 4250.0,
    "filled": 0.0,
    "remaining": 0.1,
    "status": "open",
    "fee": null
  },
  {
    "id": "123456788",
    "symbol": "BTC/USDT",
    "exchange": "binance",
    "timestamp": 1647356689000,
    "type": "market",
    "side": "sell",
    "amount": 0.05,
    "price": 42600.0,
    "cost": 2130.0,
    "filled": 0.05,
    "remaining": 0.0,
    "status": "closed",
    "fee": {
      "cost": 2.13,
      "currency": "USDT",
      "rate": 0.001
    }
  }
]
```

### Get Order

Retrieves a specific order by ID.

```
GET /{exchange_id}/order/{order_id}
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| exchange_id | string | ID of the exchange |
| order_id | string | ID of the order |
| symbol | string | Trading pair (e.g., "BTC/USDT") |

#### Response

```json
{
  "id": "123456789",
  "symbol": "BTC/USDT",
  "exchange": "binance",
  "timestamp": 1647356789123,
  "type": "limit",
  "side": "buy",
  "amount": 0.1,
  "price": 42500.0,
  "cost": 4250.0,
  "filled": 0.0,
  "remaining": 0.1,
  "status": "open",
  "fee": null
}
```

### Cancel Order

Cancels an existing order.

```
DELETE /{exchange_id}/order/{order_id}
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| exchange_id | string | ID of the exchange |
| order_id | string | ID of the order |
| symbol | string | Trading pair (e.g., "BTC/USDT") |

#### Response

```json
{
  "id": "123456789",
  "symbol": "BTC/USDT",
  "exchange": "binance",
  "timestamp": 1647356789123,
  "type": "limit",
  "side": "buy",
  "amount": 0.1,
  "price": 42500.0,
  "cost": 4250.0,
  "filled": 0.0,
  "remaining": 0.1,
  "status": "canceled",
  "fee": null
}
```

### Get Positions

Retrieves current positions from the exchange.

```
GET /{exchange_id}/positions
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| exchange_id | string | ID of the exchange |
| symbol | string | Optional trading pair to filter positions (e.g., "BTC/USDT") |

#### Response

```json
[
  {
    "symbol": "BTC/USDT",
    "exchange": "binance",
    "timestamp": 1647356789123,
    "type": "spot",
    "side": "long",
    "amount": 0.5,
    "cost": 21325.0,
    "average_price": 42650.0,
    "unrealized_pnl": 125.0,
    "unrealized_pnl_percentage": 0.58,
    "liquidation_price": null
  },
  {
    "symbol": "ETHUSDT",
    "exchange": "binance",
    "timestamp": 1647356789123,
    "type": "spot",
    "side": "long",
    "amount": 2.0,
    "cost": 6000.0,
    "average_price": 3000.0,
    "unrealized_pnl": 200.0,
    "unrealized_pnl_percentage": 3.33,
    "liquidation_price": null
  }
]
```

### Update Position Parameters

Updates parameters for an existing position.

```
PUT /{exchange_id}/position/{symbol}
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| exchange_id | string | ID of the exchange |
| symbol | string | Trading pair (e.g., "BTC/USDT") |

#### Request Body

```json
{
  "stop_loss": 41000.0,
  "take_profit": 45000.0,
  "trailing_stop": 2.5
}
```

#### Response

```json
{
  "symbol": "BTC/USDT",
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
}
```

### Get Portfolio Summary

Retrieves a summary of the portfolio across all exchanges.

```
GET /portfolio
```

#### Response

```json
{
  "timestamp": 1647356789123,
  "total_value_usd": 54325.78,
  "daily_pnl": 1250.5,
  "daily_pnl_percentage": 2.35,
  "allocations": {
    "BTC": {
      "amount": 0.5,
      "value_usd": 21325.0,
      "percentage": 39.25
    },
    "ETH": {
      "amount": 2.0,
      "value_usd": 6100.0,
      "percentage": 11.23
    },
    "USDT": {
      "amount": 26900.78,
      "value_usd": 26900.78,
      "percentage": 49.52
    }
  },
  "exchanges": {
    "binance": {
      "value_usd": 35425.78,
      "percentage": 65.21
    },
    "bybit": {
      "value_usd": 18900.0,
      "percentage": 34.79
    }
  }
}
```

## Models

### Order

```python
class Order(BaseModel):
    id: str
    symbol: str
    exchange: str
    timestamp: int
    type: str
    side: str
    amount: float
    price: float
    cost: Optional[float] = None
    filled: Optional[float] = None
    remaining: Optional[float] = None
    status: str
    fee: Optional[Dict[str, Any]] = None
```

### Position

```python
class Position(BaseModel):
    symbol: str
    exchange: str
    timestamp: int
    type: str
    side: str
    amount: float
    cost: float
    average_price: float
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_percentage: Optional[float] = None
    liquidation_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: Optional[float] = None
```

### AssetAllocation

```python
class AssetAllocation(BaseModel):
    amount: float
    value_usd: float
    percentage: float
```

### ExchangeAllocation

```python
class ExchangeAllocation(BaseModel):
    value_usd: float
    percentage: float
```

### PortfolioSummary

```python
class PortfolioSummary(BaseModel):
    timestamp: int
    total_value_usd: float
    daily_pnl: float
    daily_pnl_percentage: float
    allocations: Dict[str, AssetAllocation]
    exchanges: Dict[str, ExchangeAllocation]
``` 