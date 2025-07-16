# Binance API Analysis Wrapper Integration Guide for Junior Developers

> **For Junior Developers**: This guide assumes you're familiar with Python basics, Git, and REST APIs, but new to the Virtuoso trading system architecture. We'll explain everything step-by-step!

## Table of Contents
1. [Before You Start](#before-you-start)
2. [Understanding Virtuoso Architecture](#understanding-virtuoso-architecture)
3. [Project Goals & Scope](#project-goals--scope)
4. [Configuration Setup](#configuration-setup)
5. [Step-by-Step Implementation](#step-by-step-implementation)
6. [Testing Your Implementation](#testing-your-implementation)
7. [Troubleshooting Guide](#troubleshooting-guide)

---

## Before You Start

### Prerequisites
**Required Knowledge:**
- Python 3.11+ (intermediate level)
- Basic understanding of REST APIs
- Git workflow basics
- YAML configuration files
- Basic async/await concepts

**Required Software:**
```bash
# Python 3.11 or higher
python --version  # Should show 3.11+

# Git (any recent version)
git --version

# A code editor (VSCode recommended)
```

### Environment Setup

**Step 1: Install Dependencies**
```bash
# Install CCXT (our exchange library)
pip install ccxt

# Install required async libraries (if not already installed)
pip install aiohttp asyncio pandas numpy

# Install testing dependencies
pip install pytest pytest-asyncio
```

**Step 2: Get Binance API Credentials (Optional)**
> **Note**: Binance API credentials are optional for this integration. They only increase rate limits. Without them, you get public data access which is sufficient for analysis.

1. Go to [Binance API Management](https://www.binance.com/en/my/settings/api-management)
2. Create a new API key (if you want higher rate limits)
3. **Important**: Only enable "Read Info" permissions (never enable trading!)
4. Save your API key and secret (we'll use them in configuration)

**Step 3: Understand the Codebase Structure**
```
Virtuoso_ccxt/
├── src/
│   ├── core/
│   │   ├── exchanges/          # ← We'll add Binance here
│   │   │   ├── base.py         # ← The interface we must implement
│   │   │   ├── ccxt_exchange.py # ← We'll extend this
│   │   │   └── manager.py      # ← Manages all exchanges
│   │   └── market/             # ← Data flows here
│   ├── data_acquisition/       # ← Alternative location for our code
│   └── ...
├── config/
│   └── config.yaml            # ← We'll add Binance config here
├── tests/
│   └── ...                    # ← We'll add our tests here
└── docs/
    └── ...                    # ← Documentation goes here
```

---

## Understanding Virtuoso Architecture

### What is Virtuoso?
Virtuoso is a **trading analysis system** (not a trading bot) that:
1. **Fetches** market data from exchanges (prices, order books, trades)
2. **Analyzes** the data using technical indicators
3. **Generates** trading signals and reports
4. **Sends** alerts to Discord when interesting patterns are found

### Key Components Explained

#### 1. BaseExchange (The Interface)
Think of `BaseExchange` as a **contract** that says "every exchange must be able to do these things":

```python
# This is what EVERY exchange must implement
class BaseExchange:
    async def fetch_ticker(self, symbol):      # Get current price info
        pass
    
    async def fetch_order_book(self, symbol):  # Get buy/sell orders
        pass
    
    async def fetch_trades(self, symbol):      # Get recent trades
        pass
    
    async def fetch_market_data(self, symbol): # Get everything at once
        pass
```

#### 2. ExchangeManager (The Coordinator)
The `ExchangeManager` is like a **smart dispatcher** that:
- Knows which exchanges are available (Bybit, Binance, etc.)
- Routes requests to the right exchange
- Handles failures by trying backup exchanges
- Combines data from multiple sources

#### 3. Data Flow Diagram
```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Binance   │    │    Bybit     │    │  Other Exchanges│
│     API     │    │     API      │    │                 │
└──────┬──────┘    └──────┬───────┘    └─────────┬───────┘
       │                  │                      │
       │                  │                      │
       ▼                  ▼                      ▼
┌─────────────────────────────────────────────────────────┐
│              ExchangeManager                            │
│  (Decides which exchange to use, handles failover)     │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              MarketDataManager                          │
│  (Processes and caches the data)                       │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Analysis Framework                         │
│  (Technical indicators, signals, confluence scores)    │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Output Systems                             │
│  (Discord alerts, PDF reports, databases)              │
└─────────────────────────────────────────────────────────┘
```

#### 4. Market Data Structure
Every exchange must return data in this standard format:
```python
market_data = {
    'symbol': 'BTCUSDT',                    # Trading pair
    'timestamp': 1634567890000,             # When data was fetched
    'ticker': {                             # Current price info
        'last': 45000.0,                    # Last trade price
        'bid': 44995.0,                     # Highest buy order
        'ask': 45005.0,                     # Lowest sell order
        'volume': 1234.56,                  # 24h volume
        'high': 46000.0,                    # 24h high price
        'low': 44000.0                      # 24h low price
    },
    'orderbook': {                          # Order book data
        'bids': [[44995.0, 1.5], ...],     # Buy orders [price, size]
        'asks': [[45005.0, 0.8], ...],     # Sell orders [price, size]
        'timestamp': 1634567890000
    },
    'trades': [                             # Recent trades
        {
            'timestamp': 1634567890000,
            'price': 45000.0,
            'amount': 0.1,
            'side': 'buy'                   # 'buy' or 'sell'
        },
        # ... more trades
    ],
    'ohlcv': {                             # Candlestick data
        'base': pandas_dataframe,           # 1-minute candles
        'ltf': pandas_dataframe,            # 5-minute candles  
        'mtf': pandas_dataframe,            # 30-minute candles
        'htf': pandas_dataframe             # 4-hour candles
    }
}
```

---

## Project Goals & Scope

### What We're Building
**Goal**: Add Binance as a **secondary data source** for market analysis (not trading).

**What This Means**:
- ✅ Fetch price data from Binance
- ✅ Use Binance data in technical analysis
- ✅ Compare Binance vs Bybit data for validation
- ❌ **NO trading functionality** (analysis only!)
- ❌ **NO account management** (public data only!)

### Success Criteria
When we're done, you should be able to:
1. Enable Binance in configuration
2. See Binance data flowing into analysis
3. Generate trading signals using Binance data
4. Get Discord alerts based on Binance analysis
5. Have automatic failover if Binance API is down

---

## Configuration Setup

### Step 1: Environment Variables
Create or update your `.env` file:

```bash
# .env file - Add these lines

# Binance Configuration (Optional - for higher rate limits)
BINANCE_API_KEY=your_api_key_here_if_you_have_one
BINANCE_API_SECRET=your_secret_here_if_you_have_one

# Feature Toggles
ENABLE_BINANCE_DATA=true        # Set to 'true' to enable Binance
BINANCE_AS_PRIMARY=false        # Keep 'false' - let Bybit stay primary
```

**Line-by-line explanation**:
- `BINANCE_API_KEY`: Your Binance API key (optional, leave empty for public access)
- `BINANCE_API_SECRET`: Your Binance secret (optional, leave empty for public access)  
- `ENABLE_BINANCE_DATA`: Turn Binance integration on/off without code changes
- `BINANCE_AS_PRIMARY`: If true, use Binance as main data source (recommended: false)

### Step 2: Update config.yaml
Add this section to your `config/config.yaml` file in the `exchanges` section:

```yaml
exchanges:
  # Existing Bybit configuration (don't change this)
  bybit:
    enabled: true
    primary: true
    # ... existing bybit config ...

  # NEW: Add Binance configuration
  binance:
    # Basic settings
    enabled: ${ENABLE_BINANCE_DATA:false}     # Use env variable, default false
    primary: ${BINANCE_AS_PRIMARY:false}      # Use env variable, default false
    data_only: true                           # Analysis only, no trading
    use_ccxt: true                           # Use CCXT library for standardization
    
    # API credentials (optional - only for higher rate limits)
    api_credentials:
      api_key: ${BINANCE_API_KEY:}           # From .env file, empty default
      api_secret: ${BINANCE_API_SECRET:}     # From .env file, empty default
    
    # Rate limiting (important to avoid getting banned!)
    rate_limits:
      requests_per_minute: 1200              # Binance allows 1200 requests/minute
      requests_per_second: 10                # Conservative limit
      weight_per_minute: 6000                # Binance uses "weight" system
    
    # API endpoints
    rest_endpoint: https://api.binance.com   # Main Binance API
    testnet_endpoint: https://testnet.binance.vision  # For testing
    testnet: false                           # Use real API (not testnet)
    
    # WebSocket settings (for real-time data)
    websocket:
      public: wss://stream.binance.com:9443/ws        # Real-time data stream
      testnet_public: wss://testnet.binance.vision/ws # Testnet stream
      keep_alive: true                       # Keep connection alive
      ping_interval: 30                      # Send ping every 30 seconds
      reconnect_attempts: 3                  # Try to reconnect 3 times
    
    # Market types to support
    market_types:
      - spot                                 # Regular trading pairs (BTC/USDT)
      - futures                              # Futures contracts (BTCUSDT)
    
    # Data quality filters
    data_preferences:
      preferred_quote_currencies: ["USDT", "BTC", "ETH"]  # Focus on these pairs
      exclude_symbols: []                    # Symbols to ignore (empty for now)
      min_24h_volume: 1000000               # Only symbols with $1M+ daily volume
```

**Configuration explanation**:
- `enabled`: Master switch for Binance integration
- `primary`: Whether to use Binance as the main data source (keep false)
- `data_only`: Confirms this is for analysis, not trading
- `use_ccxt`: Use the CCXT library for standardized API calls
- `rate_limits`: Respect Binance's API limits to avoid getting banned
- `market_types`: Support both spot trading and futures markets
- `data_preferences`: Filter for high-quality, liquid trading pairs

### Step 3: Verify Configuration
Run this test to make sure your configuration is valid:

```python
# test_config.py - Create this file to test your configuration
import yaml
import os
from pathlib import Path

def test_config():
    # Load the configuration
    config_path = Path("config/config.yaml")
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Check if Binance section exists
    assert 'binance' in config['exchanges'], "Binance config not found!"
    
    binance_config = config['exchanges']['binance']
    
    # Verify required fields
    required_fields = ['enabled', 'primary', 'data_only', 'use_ccxt']
    for field in required_fields:
        assert field in binance_config, f"Missing required field: {field}"
    
    print("✅ Configuration is valid!")
    print(f"Binance enabled: {binance_config['enabled']}")
    print(f"Binance primary: {binance_config['primary']}")

if __name__ == "__main__":
    test_config()
```

Run it:
```bash
python test_config.py
```

You should see:
```
✅ Configuration is valid!
Binance enabled: true
Binance primary: false
```

---

## Step-by-Step Implementation

<!-- TODO: Continue with detailed implementation steps --> 