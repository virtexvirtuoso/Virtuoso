# Market Data API

The Market Data API provides access to real-time and historical market data, order books, trades, and technical analysis across multiple exchanges.

## Endpoints

### List Exchanges

Retrieves a list of all available exchanges.

```
GET /exchanges
```

#### Response

```json
[
  "binance",
  "bybit",
  "coinbase"
]
```

### Get Market Data

Retrieves market data for a specific symbol from an exchange.

```
GET /{exchange_id}/{symbol}/data
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| exchange_id | string | ID of the exchange |
| symbol | string | Trading pair (e.g., "BTC/USDT") |

#### Response

```json
{
  "symbol": "BTC/USDT",
  "exchange": "binance",
  "price": 42650.5,
  "volume": 2541.34,
  "timestamp": 1647356789123,
  "bid": 42650.0,
  "ask": 42651.0,
  "high": 43100.0,
  "low": 42500.0
}
```

### Get Orderbook Data

Retrieves the current order book for a specific symbol from an exchange.

```
GET /{exchange_id}/{symbol}/orderbook
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| exchange_id | string | ID of the exchange |
| symbol | string | Trading pair (e.g., "BTC/USDT") |
| limit | integer | Number of order book levels to return (default: 50, max: 500) |

#### Response

```json
{
  "symbol": "BTC/USDT",
  "exchange": "binance",
  "timestamp": 1647356789123,
  "bids": [
    {
      "price": 42650.0,
      "amount": 1.5
    },
    {
      "price": 42649.5,
      "amount": 2.3
    }
  ],
  "asks": [
    {
      "price": 42651.0,
      "amount": 0.8
    },
    {
      "price": 42652.5,
      "amount": 1.2
    }
  ]
}
```

### Get Recent Trades

Retrieves the most recent trades for a specific symbol from an exchange.

```
GET /{exchange_id}/{symbol}/trades
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| exchange_id | string | ID of the exchange |
| symbol | string | Trading pair (e.g., "BTC/USDT") |
| limit | integer | Maximum number of trades to return (default: 100, max: 1000) |

#### Response

```json
[
  {
    "symbol": "BTC/USDT",
    "exchange": "binance",
    "timestamp": 1647356789123,
    "price": 42650.5,
    "amount": 0.1,
    "side": "buy",
    "trade_id": "123456789"
  },
  {
    "symbol": "BTC/USDT",
    "exchange": "binance",
    "timestamp": 1647356779000,
    "price": 42649.0,
    "amount": 0.05,
    "side": "sell",
    "trade_id": "123456788"
  }
]
```

### Compare Markets

Compares market data across all available exchanges for a specific symbol.

```
GET /compare/{symbol}
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| symbol | string | Trading pair (e.g., "BTC/USDT") |

#### Response

```json
{
  "symbol": "BTC/USDT",
  "timestamp": 1647356789123,
  "exchanges": {
    "binance": {
      "symbol": "BTC/USDT",
      "exchange": "binance",
      "price": 42650.5,
      "volume": 2541.34,
      "timestamp": 1647356789123,
      "bid": 42650.0,
      "ask": 42651.0,
      "high": 43100.0,
      "low": 42500.0
    },
    "bybit": {
      "symbol": "BTC/USDT",
      "exchange": "bybit",
      "price": 42652.0,
      "volume": 1854.67,
      "timestamp": 1647356788000,
      "bid": 42651.5,
      "ask": 42652.5,
      "high": 43105.0,
      "low": 42498.0
    }
  },
  "price_spread": 1.5,
  "volume_total": 4396.01
}
```

### Get Technical Analysis

Retrieves technical analysis data for a specific symbol from an exchange.

```
GET /{exchange_id}/{symbol}/analysis
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| exchange_id | string | ID of the exchange |
| symbol | string | Trading pair (e.g., "BTC/USDT") |
| timeframe | string | Time interval for analysis (e.g., "1m", "5m", "1h", "1d") |

#### Response

```json
{
  "symbol": "BTC/USDT",
  "exchange": "binance",
  "timestamp": 1647356789123,
  "timeframe": "1h",
  "indicators": {
    "rsi": {
      "name": "RSI",
      "value": 45.67,
      "timestamp": 1647356789123,
      "parameters": {
        "period": 14
      }
    },
    "macd": {
      "name": "MACD",
      "value": {
        "macd": 25.5,
        "signal": 22.3,
        "histogram": 3.2
      },
      "timestamp": 1647356789123,
      "parameters": {
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9
      }
    }
  },
  "signals": {
    "trend": "neutral",
    "momentum": "bullish",
    "volatility": "medium",
    "overall": 60
  }
}
```

## Models

### MarketData

```python
class MarketData(BaseModel):
    symbol: str
    exchange: str
    price: float
    volume: float
    timestamp: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
```

### OrderBookEntry

```python
class OrderBookEntry(BaseModel):
    price: float
    amount: float
```

### OrderBook

```python
class OrderBook(BaseModel):
    symbol: str
    exchange: str
    timestamp: int
    bids: List[OrderBookEntry]
    asks: List[OrderBookEntry]
```

### Trade

```python
class Trade(BaseModel):
    symbol: str
    exchange: str
    timestamp: int
    price: float
    amount: float
    side: str
    trade_id: str
```

### MarketComparison

```python
class MarketComparison(BaseModel):
    symbol: str
    timestamp: int
    exchanges: Dict[str, MarketData]
    price_spread: float
    volume_total: float
```

### TechnicalIndicator

```python
class TechnicalIndicator(BaseModel):
    name: str
    value: Any
    timestamp: int
    parameters: Dict[str, Any]
```

### TechnicalAnalysis

```python
class TechnicalAnalysis(BaseModel):
    symbol: str
    exchange: str
    timestamp: int
    timeframe: str
    indicators: Dict[str, TechnicalIndicator]
    signals: Dict[str, Any]
``` 