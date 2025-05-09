# CCXT Integration Guide

## Overview

Virtuoso includes a powerful integration with the CCXT (CryptoCurrency eXchange Trading) library, 
allowing you to access data from 100+ cryptocurrency exchanges through a unified API.

This guide explains how to use the CCXT integration in your Virtuoso trading strategies and analytics.

## Features

- **Unified API**: Access data from any CCXT-supported exchange using a consistent interface
- **Auto-fallback**: If an exchange-specific method is unavailable, the system attempts alternative approaches
- **100+ Exchanges**: Support for all major crypto exchanges including Binance, Bybit, Coinbase, Kraken, KuCoin, and many more
- **Complete Market Data**: Fetch order books, trades, OHLCV data, funding rates, open interest, and more
- **Rate-limiting**: Built-in rate limiting and request retry logic to ensure reliable operation
- **Error Handling**: Comprehensive error handling with informative logging

## Setup and Configuration

### Installation

The CCXT library is included in Virtuoso's requirements. If you need to install it separately:

```bash
pip install ccxt
```

### Configuration

To use a CCXT-supported exchange, create a configuration with the `use_ccxt` flag:

```python
config = {
    "use_ccxt": True,  # Enable CCXT integration
    "exchange_id": "binance",  # Specify the exchange to use
    "ccxt_options": {
        "enableRateLimit": True,
        "timeout": 30000
    },
    # Optional API credentials for authenticated endpoints
    "api_credentials": {
        "api_key": "YOUR_API_KEY",
        "api_secret": "YOUR_API_SECRET"
    }
}

# Create and initialize the exchange
exchange = await ExchangeFactory.create_exchange("ccxt", config)
```

## Basic Usage

### Fetching Market Data

```python
# Fetch ticker data
ticker = await exchange.fetch_ticker("BTC/USDT")

# Fetch order book
orderbook = await exchange.fetch_order_book("BTC/USDT", 20)  # Depth of 20

# Fetch recent trades
trades = await exchange.fetch_trades("BTC/USDT", limit=50)

# Fetch OHLCV data
ohlcv = await exchange.fetch_historical_klines(
    "BTC/USDT", 
    "1h",  # 1 hour timeframe
    limit=100
)

# Fetch funding rate (for futures exchanges)
funding = await exchange.fetch_funding_rate("BTC/USDT")

# Fetch open interest (for futures exchanges)
open_interest = await exchange.fetch_open_interest("BTC/USDT")

# Fetch all market data at once
market_data = await exchange.fetch_market_data("BTC/USDT")
```

### Account and Trading (for authenticated sessions)

```python
# Fetch account balance
balance = await exchange.fetch_balance()

# Fetch open positions
positions = await exchange.fetch_positions()

# Fetch open orders
orders = await exchange.fetch_open_orders("BTC/USDT")
```

## Supported Exchanges

The CCXT integration supports all exchanges available in the CCXT library, including but not limited to:

- Binance, Binance US, Binance Futures
- Bybit
- Coinbase Pro
- Kraken
- KuCoin
- FTX
- Huobi
- OKX
- Bitfinex
- Gate.io
- And many more...

For a complete list, refer to the [CCXT documentation](https://github.com/ccxt/ccxt#supported-cryptocurrency-exchange-markets).

## Symbol Format

CCXT uses a standardized symbol format with a forward slash separating the base and quote currencies:

```
BTC/USDT    # Bitcoin quoted in USDT
ETH/BTC     # Ethereum quoted in Bitcoin
XRP/USD     # XRP quoted in USD
```

The CCXTExchange class will automatically handle the conversion between CCXT's format and exchange-specific formats (like BTCUSDT on Binance).

## Example Code

See the [CCXT demo script](../../examples/demo/ccxt_demo.py) for a complete example of how to use the CCXT integration.

## Limitations

- WebSocket subscriptions are currently handled by CCXT internally and can't be manually controlled
- Some exchange-specific features may not be available through the unified API
- Authenticated endpoints require valid API credentials with appropriate permissions

## Troubleshooting

If you encounter issues with the CCXT integration:

1. Check that your exchange_id is valid and supported by CCXT
2. Verify that your API credentials have the correct permissions
3. Look for detailed error messages in the logs
4. Consider using an exchange-specific adapter if you need special features

## Reference

For more detailed information on CCXT's capabilities, refer to the [official CCXT documentation](https://github.com/ccxt/ccxt/wiki). 