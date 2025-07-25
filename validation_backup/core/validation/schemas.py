"""Market data validation schemas.

This module defines JSON schemas for validating market data:
- Kline (candlestick) data
- Trade data
- Orderbook data
- Ticker data
"""

KLINE_SCHEMA = {
    "type": "object",
    "required": [
        "start_time",
        "interval",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ],
    "properties": {
        "start_time": {
            "type": "integer",
            "minimum": 0,
            "description": "Start time in milliseconds"
        },
        "interval": {
            "type": "string",
            "enum": [
                "1m", "3m", "5m", "15m", "30m",
                "1h", "2h", "4h", "6h", "8h", "12h",
                "1d", "3d", "1w", "1M"
            ],
            "description": "Kline interval"
        },
        "open": {
            "type": "number",
            "minimum": 0,
            "description": "Opening price"
        },
        "high": {
            "type": "number",
            "minimum": 0,
            "description": "Highest price"
        },
        "low": {
            "type": "number",
            "minimum": 0,
            "description": "Lowest price"
        },
        "close": {
            "type": "number",
            "minimum": 0,
            "description": "Closing price"
        },
        "volume": {
            "type": "number",
            "minimum": 0,
            "description": "Trading volume"
        }
    },
    "additionalProperties": True
}

TRADE_SCHEMA = {
    "type": "object",
    "required": [
        "price",
        "quantity",
        "timestamp",
        "side"
    ],
    "properties": {
        "price": {
            "type": "number",
            "minimum": 0,
            "description": "Trade price"
        },
        "quantity": {
            "type": "number",
            "minimum": 0,
            "description": "Trade quantity"
        },
        "timestamp": {
            "type": "integer",
            "minimum": 0,
            "description": "Trade timestamp in milliseconds"
        },
        "side": {
            "type": "string",
            "enum": ["buy", "sell", "BUY", "SELL"],
            "description": "Trade side"
        },
        "trade_id": {
            "type": "string",
            "description": "Unique trade identifier"
        }
    },
    "additionalProperties": True
}

ORDERBOOK_SCHEMA = {
    "type": "object",
    "required": [
        "bids",
        "asks",
        "timestamp"
    ],
    "properties": {
        "bids": {
            "type": "array",
            "items": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": [
                    {
                        "type": "number",
                        "minimum": 0,
                        "description": "Bid price"
                    },
                    {
                        "type": "number",
                        "minimum": 0,
                        "description": "Bid quantity"
                    }
                ]
            },
            "description": "List of [price, quantity] pairs for bids"
        },
        "asks": {
            "type": "array",
            "items": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": [
                    {
                        "type": "number",
                        "minimum": 0,
                        "description": "Ask price"
                    },
                    {
                        "type": "number",
                        "minimum": 0,
                        "description": "Ask quantity"
                    }
                ]
            },
            "description": "List of [price, quantity] pairs for asks"
        },
        "timestamp": {
            "type": "integer",
            "minimum": 0,
            "description": "Orderbook timestamp in milliseconds"
        }
    },
    "additionalProperties": True
}

TICKER_SCHEMA = {
    "type": "object",
    "required": [
        "symbol",
        "price",
        "timestamp"
    ],
    "properties": {
        "symbol": {
            "type": "string",
            "description": "Trading symbol"
        },
        "price": {
            "type": "number",
            "minimum": 0,
            "description": "Current price"
        },
        "timestamp": {
            "type": "integer",
            "minimum": 0,
            "description": "Ticker timestamp in milliseconds"
        },
        "volume": {
            "type": "number",
            "minimum": 0,
            "description": "24h trading volume"
        },
        "change": {
            "type": "number",
            "description": "24h price change"
        },
        "change_percent": {
            "type": "number",
            "description": "24h price change percentage"
        }
    },
    "additionalProperties": True
}

# Additional validation rules for price relationships in klines
KLINE_RULES = [
    {
        "name": "price_range",
        "description": "Validate price relationships (high >= low, open/close within range)",
        "level": "error",
        "parameters": {
            "validation_func": lambda data: (
                float(data['low']) <= float(data['high']) and
                float(data['low']) <= float(data['open']) <= float(data['high']) and
                float(data['low']) <= float(data['close']) <= float(data['high'])
            ),
            "error_message": "Invalid price relationships in kline data"
        }
    }
]

# Additional validation rules for orderbook
ORDERBOOK_RULES = [
    {
        "name": "price_ordering",
        "description": "Validate bid/ask price ordering (highest bid < lowest ask)",
        "level": "error",
        "parameters": {
            "validation_func": lambda data: (
                not data['bids'] or
                not data['asks'] or
                float(data['bids'][0][0]) < float(data['asks'][0][0])
            ),
            "error_message": "Invalid bid/ask price ordering"
        }
    }
]

# Map of data types to their schemas
SCHEMAS = {
    "kline": KLINE_SCHEMA,
    "trade": TRADE_SCHEMA,
    "orderbook": ORDERBOOK_SCHEMA,
    "ticker": TICKER_SCHEMA
}

# Map of data types to their additional validation rules
VALIDATION_RULES = {
    "kline": KLINE_RULES,
    "orderbook": ORDERBOOK_RULES
} 