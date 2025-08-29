# Virtuoso CCXT Trading System - Comprehensive Data Flow Documentation

## Table of Contents
1. [Data Source Analysis](#1-data-source-analysis)
2. [Data Fetching Mechanisms](#2-data-fetching-mechanisms)
3. [Data Transformation Pipeline](#3-data-transformation-pipeline)
4. [Data Flow Architecture](#4-data-flow-architecture)
5. [Data Samples and Formats](#5-data-samples-and-formats)
6. [Performance and Caching](#6-performance-and-caching)
7. [Data Usage Mapping](#7-data-usage-mapping)

---

## 1. Data Source Analysis

### 1.1 External Data Sources

#### Primary Exchange: Bybit
- **REST API Endpoint**: `https://api.bybit.com`
- **WebSocket Endpoints**:
  - Public Spot: `wss://stream.bybit.com/v5/public/spot`
  - Public Linear: `wss://stream.bybit.com/v5/public/linear`
  - Public Inverse: `wss://stream.bybit.com/v5/public/inverse`
  - Private: `wss://stream.bybit.com/v5/private`

**Data Types Provided:**
- OHLCV candle data (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M)
- Order book data (L2 depth)
- Real-time trade data
- Liquidation events
- Open interest data
- Funding rates
- Mark/index prices
- 24h tickers and statistics

**Configuration:**
```yaml
# /Users/ffv_macmini/Desktop/Virtuoso_ccxt/config/config.yaml
exchanges:
  bybit:
    api_credentials:
      api_key: ${BYBIT_API_KEY}
      api_secret: ${BYBIT_API_SECRET}
    enabled: true
    primary: true
    rate_limits:
      requests_per_minute: 1200
      requests_per_second: 20
    rest_endpoint: https://api.bybit.com
    testnet: false
```

#### Secondary Exchange: Binance
- **REST API Endpoint**: `https://api.binance.com`
- **Data Only Mode**: Used primarily for cross-validation and backup data
- **Data Types**: Similar to Bybit but used for comparison and fallback

**Configuration:**
```yaml
exchanges:
  binance:
    api_credentials:
      api_key: ${BINANCE_API_KEY}
      api_secret: ${BINANCE_API_SECRET}
    data_only: false
    data_preferences:
      exclude_symbols: []
      min_24h_volume: 1000000
      preferred_quote_currencies:
      - USDT
      - BTC
```

### 1.2 Internal Data Sources

#### Configuration-Based Data
- **Symbol Lists**: Predefined in `/Users/ffv_macmini/Desktop/Virtuoso_ccxt/config/config.yaml`
- **Timeframe Configurations**: Multi-timeframe analysis settings
- **Analysis Parameters**: Confluence thresholds, indicator settings

#### Derived Data Sources
- **Technical Indicators**: RSI, MACD, EMA, Bollinger Bands (calculated internally)
- **Volume Analysis**: OBV, Volume Delta, Volume Profile
- **Order Flow Metrics**: Buy/sell pressure, imbalance ratios
- **Market Regime Detection**: Trend/range identification
- **Confluence Scores**: 6-dimensional analysis results

### 1.3 Data Refresh Rates

| Data Type | Refresh Rate | Source | Method |
|-----------|-------------|---------|---------|
| OHLCV 1m | 1 second | Bybit WS | Real-time stream |
| OHLCV 5m+ | 5 seconds | Bybit REST | Polling |
| Order Book | Real-time | Bybit WS | Stream updates |
| Trades | Real-time | Bybit WS | Live feed |
| Liquidations | Real-time | Bybit WS | Event stream |
| Technical Indicators | 30 seconds | Internal | Calculation |
| Confluence Scores | 30 seconds | Internal | Analysis |
| Dashboard Data | 30 seconds | Cache | TTL refresh |

---

## 2. Data Fetching Mechanisms

### 2.1 Exchange Integration Layer

#### CCXT-Based Implementation
**File**: `/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/core/exchanges/bybit.py`

```python
class BybitExchange(BaseExchange):
    """Bybit exchange implementation with CCXT standardization"""
    
    RATE_LIMITS = {
        'category': {
            'linear': {'requests': 120, 'per_second': 1},
            'spot': {'requests': 120, 'per_second': 1}
        },
        'endpoints': {
            'kline': {'requests': 120, 'per_second': 1},
            'ticker': {'requests': 120, 'per_second': 1},
            'orderbook': {'requests': 120, 'per_second': 1}
        }
    }
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100):
        """Fetch OHLCV data with rate limiting and error handling"""
        # Implementation with connection pooling and retry logic
```

#### Connection Management
```python
# Connection pool configuration from timeout_fix.yaml
connection_config:
  total_timeout: 60        # Total request timeout
  connect_timeout: 20      # Connection establishment timeout
  socket_read_timeout: 30  # Socket read timeout
  
connection_pool:
  limit: 150              # Total connections
  limit_per_host: 40      # Per-host limit
  keepalive_expiry: 30    # Keep-alive duration
```

### 2.2 WebSocket Data Streaming

#### WebSocket Manager
**File**: `/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/core/exchanges/websocket_manager.py`

```python
class WebSocketManager:
    """WebSocket Manager for real-time data updates"""
    
    WS_ENDPOINTS = {
        'spot': {
            'public': 'wss://stream.bybit.com/v5/public/spot',
            'private': 'wss://stream.bybit.com/v5/private'
        },
        'linear': {
            'public': 'wss://stream.bybit.com/v5/public/linear',
            'private': 'wss://stream.bybit.com/v5/private'
        }
    }
    
    async def subscribe_to_channels(self, channels: List[str]):
        """Subscribe to WebSocket channels for real-time data"""
        # Real-time subscription management
```

#### WebSocket Configuration
```yaml
websocket:
  enabled: true
  reconnect_attempts: 5
  ping_interval: 30
  timeout: 10
  channels:
    ticker: true
    kline: true
    orderbook: true
    trade: true
    liquidation: true
  log_level: INFO
```

### 2.3 API Endpoints and Parameters

#### Market Data Endpoints
```python
# Primary data fetching endpoints used in the system
ENDPOINTS = {
    'kline': '/v5/market/kline',           # OHLCV data
    'tickers': '/v5/market/tickers',       # 24h statistics
    'orderbook': '/v5/market/orderbook',   # Order book depth
    'recent_trades': '/v5/market/recent-trade',  # Recent trades
    'funding_rate': '/v5/market/funding/history', # Funding rates
    'open_interest': '/v5/market/open-interest',  # Open interest
    'liquidations': '/v5/market/liquidations'     # Liquidation events
}

# Example API call with parameters
async def fetch_kline_data(symbol: str, interval: str, limit: int = 200):
    params = {
        'category': 'linear',  # or 'spot'
        'symbol': symbol,
        'interval': interval,  # 1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W, M
        'limit': limit,
        'start': start_timestamp,
        'end': end_timestamp
    }
```

### 2.4 Authentication and Rate Limiting

#### API Authentication
```python
# From bybit.py - HMAC-SHA256 authentication
def _generate_signature(self, timestamp: str, params: str) -> str:
    """Generate HMAC-SHA256 signature for API requests"""
    return hmac.new(
        self.api_secret.encode(),
        f"{timestamp}{self.api_key}{params}".encode(),
        hashlib.sha256
    ).hexdigest()
```

#### Rate Limiting Implementation
```python
from .rate_limiter import BybitRateLimiter

class BybitExchange:
    def __init__(self):
        self.rate_limiter = BybitRateLimiter(
            requests_per_second=20,
            requests_per_minute=1200
        )
    
    async def _make_request(self, endpoint: str, params: dict):
        await self.rate_limiter.acquire()  # Wait for rate limit
        # Make actual API request
```

### 2.5 Error Handling and Fallback

#### Comprehensive Error Handling
```python
class BybitExchangeError(ExchangeError):
    """Bybit-specific exchange error"""
    ERROR_CODES = {
        '10001': 'System error',
        '10002': 'System not available',
        '10003': 'Invalid request',
        '10004': 'Invalid parameter',
        '10005': 'Operation failed',
        '10006': 'Too many requests',
        '10007': 'Authentication required',
        '10008': 'Invalid API key',
        '10009': 'Invalid signature',
    }

@retry_on_error(max_retries=3, backoff_factor=2.0)
async def fetch_with_retry(self, endpoint: str, params: dict):
    """Fetch data with exponential backoff retry logic"""
    # Implementation with circuit breaker pattern
```

---

## 3. Data Transformation Pipeline

### 3.1 Raw Data Processing

#### Data Validation and Normalization
**File**: `/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/core/analysis/data_validator.py`

```python
class DataValidator:
    """Validates and normalizes incoming market data"""
    
    def validate_ohlcv(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate OHLCV data structure and values"""
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        
        # Check data completeness
        if not all(col in data.columns for col in required_columns):
            raise DataValidationError("Missing required OHLCV columns")
        
        # Validate price data consistency (high >= low, etc.)
        invalid_rows = data[data['high'] < data['low']]
        if not invalid_rows.empty:
            logger.warning(f"Found {len(invalid_rows)} invalid price rows")
        
        return self._normalize_timestamps(data)
```

#### Data Structure Conversion
```python
def normalize_exchange_data(raw_data: dict, exchange: str) -> pd.DataFrame:
    """Convert exchange-specific data format to standardized DataFrame"""
    
    if exchange == 'bybit':
        # Bybit returns: [timestamp, open, high, low, close, volume, turnover]
        return pd.DataFrame(raw_data['result']['list'], columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
        ]).astype({
            'timestamp': 'int64',
            'open': 'float64',
            'high': 'float64', 
            'low': 'float64',
            'close': 'float64',
            'volume': 'float64',
            'turnover': 'float64'
        })
```

### 3.2 Technical Indicator Calculation

#### Indicator Processing Pipeline
**File**: `/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/core/analysis/indicator_utils.py`

```python
class TechnicalIndicatorEngine:
    """Calculates technical indicators with TA-Lib optimization"""
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI with pandas optimization"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """Calculate MACD with signal line and histogram"""
        exp1 = prices.ewm(span=fast).mean()
        exp2 = prices.ewm(span=slow).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
```

#### Volume Analysis
```python
def calculate_volume_indicators(data: pd.DataFrame) -> dict:
    """Calculate volume-based indicators"""
    
    # On-Balance Volume (OBV)
    obv = (np.sign(data['close'].diff()) * data['volume']).fillna(0).cumsum()
    
    # Volume-Weighted Average Price (VWAP)
    typical_price = (data['high'] + data['low'] + data['close']) / 3
    vwap = (typical_price * data['volume']).cumsum() / data['volume'].cumsum()
    
    # Volume Delta (Buy/Sell Pressure approximation)
    volume_delta = np.where(
        data['close'] > data['open'], 
        data['volume'], 
        -data['volume']
    )
    
    return {
        'obv': obv,
        'vwap': vwap,
        'volume_delta': volume_delta,
        'avg_volume': data['volume'].rolling(20).mean()
    }
```

### 3.3 6-Dimensional Confluence Analysis

#### Confluence Analysis Engine
**File**: `/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/core/analysis/confluence.py`

```python
class ConfluenceAnalyzer:
    """6-Dimensional Market Analysis System"""
    
    DIMENSIONS = {
        'technical': {
            'weight': 0.25,
            'indicators': ['rsi', 'macd', 'ema_crossover', 'bollinger_bands']
        },
        'volume': {
            'weight': 0.20,
            'indicators': ['obv', 'volume_delta', 'vwap']
        },
        'orderflow': {
            'weight': 0.15,
            'indicators': ['buy_sell_pressure', 'order_imbalance']
        },
        'orderbook': {
            'weight': 0.15,
            'indicators': ['bid_ask_depth', 'liquidity_zones']
        },
        'price_structure': {
            'weight': 0.15,
            'indicators': ['support_resistance', 'trend_analysis']
        },
        'sentiment': {
            'weight': 0.10,
            'indicators': ['funding_rate', 'open_interest_change']
        }
    }
    
    async def analyze(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Perform 6-dimensional confluence analysis"""
        
        results = {}
        total_score = 0.0
        
        for dimension, config in self.DIMENSIONS.items():
            dimension_score = await self._analyze_dimension(
                dimension, 
                market_data, 
                config['indicators']
            )
            
            weighted_score = dimension_score * config['weight']
            total_score += weighted_score
            
            results[dimension] = {
                'score': dimension_score,
                'weight': config['weight'],
                'weighted_score': weighted_score
            }
        
        confluence_score = min(100, max(0, total_score * 100))
        
        return {
            'confluence_score': confluence_score,
            'dimensions': results,
            'signal_strength': self._determine_signal_strength(confluence_score),
            'timestamp': datetime.utcnow().isoformat()
        }
```

### 3.4 Data Aggregation and Normalization

#### Multi-Timeframe Data Aggregation
```python
class MultiTimeframeProcessor:
    """Processes data across multiple timeframes"""
    
    TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
    
    def aggregate_signals(self, timeframe_data: Dict[str, Dict]) -> Dict[str, Any]:
        """Aggregate signals across multiple timeframes"""
        
        aggregated = {
            'overall_signal': 'NEUTRAL',
            'confidence': 0.0,
            'timeframe_breakdown': {},
            'consensus_strength': 0.0
        }
        
        signal_votes = {'BUY': 0, 'SELL': 0, 'NEUTRAL': 0}
        total_confidence = 0.0
        
        for timeframe, analysis in timeframe_data.items():
            signal = analysis.get('signal', 'NEUTRAL')
            confidence = analysis.get('confidence', 0.0)
            
            signal_votes[signal] += confidence
            total_confidence += confidence
            
            aggregated['timeframe_breakdown'][timeframe] = {
                'signal': signal,
                'confidence': confidence,
                'confluence_score': analysis.get('confluence_score', 0)
            }
        
        # Determine consensus
        if signal_votes['BUY'] > signal_votes['SELL'] + signal_votes['NEUTRAL']:
            aggregated['overall_signal'] = 'BUY'
        elif signal_votes['SELL'] > signal_votes['BUY'] + signal_votes['NEUTRAL']:
            aggregated['overall_signal'] = 'SELL'
        
        aggregated['confidence'] = total_confidence / len(timeframe_data)
        aggregated['consensus_strength'] = max(signal_votes.values()) / sum(signal_votes.values())
        
        return aggregated
```

---

## 4. Data Flow Architecture

### 4.1 System Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │    │  Processing Layer │    │  Consumer Layer │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ Bybit REST API  │───▶│  Exchange Manager │───▶│ Dashboard API   │
│ Bybit WebSocket │───▶│  Data Validator   │───▶│ WebSocket API   │
│ Binance API     │───▶│  Indicator Engine │───▶│ Alert System   │
│ Internal Calcs  │───▶│  Confluence Anal. │───▶│ Mobile API      │
└─────────────────┘    │  Cache Layer      │    └─────────────────┘
                       └──────────────────┘
                              │
                       ┌──────────────────┐
                       │  Storage Layer   │
                       ├──────────────────┤
                       │ Memcached Cache  │
                       │ Redis Cache      │
                       │ SQLite Database  │
                       │ File System      │
                       └──────────────────┘
```

### 4.2 Data Flow Sequence

#### Real-time Data Flow
```
1. WebSocket Connection Established
   ├── Bybit: wss://stream.bybit.com/v5/public/linear
   └── Subscribe to channels: [ticker, kline, orderbook, trade, liquidation]

2. Raw Data Reception
   ├── JSON messages received via WebSocket
   ├── Data validation and normalization
   └── Convert to pandas DataFrame format

3. Data Processing Pipeline
   ├── Technical indicator calculation (RSI, MACD, etc.)
   ├── Volume analysis (OBV, VWAP, Volume Delta)
   ├── Order flow analysis (Buy/sell pressure)
   └── 6-dimensional confluence analysis

4. Result Caching
   ├── Cache processed data in Memcached (TTL: 30s)
   ├── Store signals in Redis for persistence
   └── Update dashboard cache for fast retrieval

5. Data Distribution
   ├── WebSocket broadcast to connected clients
   ├── API endpoints serve cached data
   ├── Alert system checks signal thresholds
   └── Mobile API provides optimized data
```

#### Batch Data Flow (REST API)
```
1. Scheduled Data Fetching
   ├── Every 5 seconds for higher timeframes (5m+)
   ├── Rate limited per exchange (20 req/sec)
   └── Connection pool management (40 connections/host)

2. Historical Data Processing
   ├── Fetch OHLCV data for analysis window
   ├── Calculate technical indicators
   ├── Generate confluence scores
   └── Update trend analysis

3. Cache Management
   ├── Store processed results with appropriate TTL
   ├── Invalidate stale cache entries
   └── Maintain cache statistics
```

### 4.3 Component Interaction Diagram

#### Main Application Components
**File**: `/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/main.py`

```python
# Core system initialization and data flow orchestration
async def main():
    """Main application entry point"""
    
    # Initialize core components
    config_manager = ConfigManager()
    
    # Setup exchange connections
    exchange_manager = ExchangeManager(config_manager.config)
    
    # Initialize analysis engine
    confluence_analyzer = ConfluenceAnalyzer(config_manager.config)
    
    # Setup monitoring and alerts
    market_monitor = MarketMonitor(
        exchange_manager=exchange_manager,
        confluence_analyzer=confluence_analyzer,
        alert_manager=alert_manager
    )
    
    # Start data processing pipeline
    await market_monitor.start()
    
    # Launch API servers
    api_tasks = [
        asyncio.create_task(start_main_api(port=8003)),    # Dashboard API
        asyncio.create_task(start_monitoring_api(port=8001))  # Monitoring API
    ]
```

### 4.4 Real-time vs Batch Processing

#### Real-time Processing Path
```python
# WebSocket data handling
class WebSocketDataHandler:
    async def handle_ticker_update(self, message: dict):
        """Process real-time ticker updates"""
        symbol = message['data']['symbol']
        
        # Update cache immediately
        await self.cache.set(f'ticker:{symbol}', message['data'], ttl=60)
        
        # Broadcast to WebSocket clients
        await self.connection_manager.broadcast({
            'type': 'ticker_update',
            'symbol': symbol,
            'data': message['data']
        })
        
        # Trigger analysis if threshold met
        if self._should_analyze(message['data']):
            await self.queue_analysis(symbol)
```

#### Batch Processing Path
```python
# Scheduled batch processing
class BatchProcessor:
    async def process_symbols_batch(self, symbols: List[str]):
        """Process multiple symbols in batch for efficiency"""
        
        # Fetch data concurrently
        tasks = [
            self.exchange.fetch_ohlcv(symbol, '5m', limit=200)
            for symbol in symbols
        ]
        
        ohlcv_data = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process each symbol's data
        for symbol, data in zip(symbols, ohlcv_data):
            if isinstance(data, Exception):
                logger.error(f"Failed to fetch data for {symbol}: {data}")
                continue
                
            # Perform analysis
            analysis_result = await self.analyzer.analyze(symbol, data)
            
            # Cache results
            await self.cache_results(symbol, analysis_result)
```

---

## 5. Data Samples and Formats

### 5.1 Raw Exchange Data Formats

#### Bybit OHLCV Response
```json
{
  "retCode": 0,
  "retMsg": "OK",
  "result": {
    "symbol": "BTCUSDT",
    "category": "linear",
    "list": [
      [
        "1693411200000",  // timestamp (ms)
        "26000.50",       // open price
        "26050.25",       // high price  
        "25980.10",       // low price
        "26025.75",       // close price
        "1500.5",         // volume
        "39075000.125"    // turnover (volume * price)
      ]
    ]
  },
  "retExtInfo": {},
  "time": 1693411234567
}
```

#### Bybit WebSocket Ticker Data
```json
{
  "topic": "tickers.BTCUSDT",
  "type": "snapshot",
  "data": {
    "symbol": "BTCUSDT",
    "tickDirection": "PlusTick",
    "price24hPcnt": "0.0112",
    "lastPrice": "26025.75",
    "prevPrice24h": "25735.50", 
    "highPrice24h": "26100.00",
    "lowPrice24h": "25600.00",
    "prevPrice1h": "25950.25",
    "markPrice": "26023.45",
    "indexPrice": "26024.12",
    "openInterest": "125000.5",
    "openInterestValue": "3250000000.25",
    "turnover24h": "2500000000.50",
    "volume24h": "95000.25",
    "nextFundingTime": "1693440000000",
    "fundingRate": "0.0001",
    "bid1Price": "26024.50",
    "bid1Size": "10.5",
    "ask1Price": "26025.25", 
    "ask1Size": "15.25"
  },
  "cs": 24987956047,
  "ts": 1693411234567
}
```

### 5.2 Processed Data Structures

#### Normalized DataFrame Format
```python
# Standard OHLCV DataFrame structure used throughout the system
columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']
dtypes = {
    'timestamp': 'datetime64[ns]',  # Converted from milliseconds
    'open': 'float64',
    'high': 'float64', 
    'low': 'float64',
    'close': 'float64',
    'volume': 'float64',
    'turnover': 'float64'
}

# Example processed DataFrame
"""
                     timestamp      open      high       low     close    volume      turnover
2023-08-30 12:00:00+00:00    26000.50  26050.25  25980.10  26025.75   1500.5  39075000.125
2023-08-30 12:01:00+00:00    26025.75  26075.00  26010.25  26065.50   1750.2  45590425.750
2023-08-30 12:02:00+00:00    26065.50  26080.75  26055.00  26070.25   1320.8  34425870.500
"""
```

#### Technical Indicator Data
```python
# Technical indicators added to DataFrame
technical_indicators = {
    'rsi_14': pd.Series,      # RSI with 14-period
    'macd': pd.Series,        # MACD line
    'macd_signal': pd.Series, # MACD signal line
    'macd_histogram': pd.Series,  # MACD histogram
    'ema_12': pd.Series,      # 12-period EMA
    'ema_26': pd.Series,      # 26-period EMA
    'bb_upper': pd.Series,    # Bollinger Band upper
    'bb_middle': pd.Series,   # Bollinger Band middle (SMA)
    'bb_lower': pd.Series,    # Bollinger Band lower
    'obv': pd.Series,         # On-Balance Volume
    'vwap': pd.Series,        # Volume Weighted Average Price
    'volume_sma': pd.Series   # Volume Simple Moving Average
}
```

### 5.3 Analysis Result Formats

#### Confluence Analysis Output
```json
{
  "symbol": "BTCUSDT",
  "timeframe": "5m",
  "confluence_score": 72.5,
  "signal": "BUY",
  "confidence": 0.85,
  "dimensions": {
    "technical": {
      "score": 75.0,
      "weight": 0.25,
      "weighted_score": 18.75,
      "components": {
        "rsi": {"value": 65.5, "signal": "NEUTRAL", "weight": 0.3},
        "macd": {"value": 15.2, "signal": "BUY", "weight": 0.4},
        "ema_crossover": {"value": 1, "signal": "BUY", "weight": 0.3}
      }
    },
    "volume": {
      "score": 80.0,
      "weight": 0.20,
      "weighted_score": 16.0,
      "components": {
        "obv": {"value": 125000, "signal": "BUY", "weight": 0.4},
        "volume_delta": {"value": 850.5, "signal": "BUY", "weight": 0.6}
      }
    },
    "orderflow": {
      "score": 65.0,
      "weight": 0.15,
      "weighted_score": 9.75
    },
    "orderbook": {
      "score": 70.0,
      "weight": 0.15,
      "weighted_score": 10.5
    },
    "price_structure": {
      "score": 78.0,
      "weight": 0.15,
      "weighted_score": 11.7
    },
    "sentiment": {
      "score": 60.0,
      "weight": 0.10,
      "weighted_score": 6.0
    }
  },
  "metadata": {
    "processing_time_ms": 85,
    "data_points": 200,
    "last_candle_time": "2023-08-30T12:05:00Z",
    "analysis_time": "2023-08-30T12:05:15Z"
  }
}
```

#### Dashboard Data Format
```json
{
  "market_overview": {
    "active_symbols": 35,
    "total_volume_24h": 2500000000.50,
    "spot_volume_24h": 1200000000.25,
    "linear_volume_24h": 1300000000.25,
    "market_regime": "trending_bullish",
    "trend_strength": 0.75,
    "current_volatility": 0.045,
    "avg_volatility": 0.035,
    "btc_dominance": 0.52,
    "market_breadth": {
      "up": 22,
      "down": 13,
      "flat": 0,
      "breadth_percentage": 62.86
    },
    "timestamp": 1693411515
  },
  "top_signals": [
    {
      "symbol": "BTCUSDT",
      "signal": "BUY",
      "confluence_score": 72.5,
      "confidence": 0.85,
      "timeframe": "5m",
      "timestamp": "2023-08-30T12:05:15Z"
    }
  ],
  "recent_alerts": [
    {
      "id": "alert_1693411515_btcusdt",
      "symbol": "BTCUSDT", 
      "type": "confluence_signal",
      "signal": "BUY",
      "score": 72.5,
      "message": "Strong BUY signal detected on BTCUSDT (5m)",
      "timestamp": "2023-08-30T12:05:15Z"
    }
  ]
}
```

### 5.4 Cache Data Formats

#### Memcached Cache Keys and Values
```python
# Cache key patterns used throughout the system
CACHE_KEYS = {
    'market_overview': 'market:overview',
    'symbol_ticker': 'ticker:{symbol}',
    'ohlcv_data': 'ohlcv:{symbol}:{timeframe}',
    'confluence_score': 'confluence:{symbol}:{timeframe}',
    'technical_indicators': 'indicators:{symbol}:{timeframe}',
    'dashboard_data': 'dashboard:data',
    'mobile_data': 'dashboard:mobile',
    'alert_history': 'alerts:recent',
    'system_metrics': 'metrics:system'
}

# Example cache value for confluence score
cache_value = {
    "score": 72.5,
    "signal": "BUY", 
    "confidence": 0.85,
    "dimensions": {...},  # Full dimension breakdown
    "cached_at": 1693411515,
    "ttl": 30  # seconds
}
```

---

## 6. Performance and Caching

### 6.1 Caching Architecture

#### Multi-Tier Caching Strategy
**File**: `/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/api/cache_adapter_direct.py`

```python
class DirectCacheAdapter:
    """Direct cache adapter with connection pooling"""
    
    def __init__(self):
        self._client = None
    
    async def _get_client(self):
        """Get or create cache client with connection pooling"""
        if self._client is None:
            self._client = aiomcache.Client('localhost', 11211, pool_size=2)
        return self._client
    
    async def _get(self, key: str, default: Any = None) -> Any:
        """Direct cache read with timeout using connection pool"""
        try:
            client = await self._get_client()
            
            # Add timeout wrapper for reliability
            data = await asyncio.wait_for(
                client.get(key.encode()), 
                timeout=2.0  # 2 second timeout
            )
            
            if data:
                try:
                    return json.loads(data.decode())
                except json.JSONDecodeError:
                    return data.decode()  # Return as string if not JSON
            
            return default
            
        except asyncio.TimeoutError:
            logger.warning(f"Cache timeout for {key}")
            return default
        except Exception as e:
            logger.debug(f"Cache read error for {key}: {e}")
            return default
```

#### Cache TTL Configuration
```python
# Time-To-Live settings for different data types
CACHE_TTL = {
    'dashboard_data': 30,        # 30 seconds - frequent updates
    'market_overview': 30,       # 30 seconds - market summary
    'confluence_scores': 30,     # 30 seconds - analysis results
    'technical_indicators': 60,  # 1 minute - calculated indicators
    'ticker_data': 5,           # 5 seconds - real-time prices
    'ohlcv_data': 300,          # 5 minutes - historical candle data
    'system_metrics': 60,       # 1 minute - performance metrics
    'alert_history': 3600       # 1 hour - alert records
}
```

### 6.2 Performance Optimization

#### Connection Pooling
```yaml
# Connection pool configuration from timeout_fix.yaml
connection_pool:
  limit: 150              # Total connection limit
  limit_per_host: 40      # Per-host connection limit
  keepalive_expiry: 30    # Connection keep-alive time
  connection_timeout: 20   # Connection establishment timeout
  socket_read_timeout: 30  # Socket read timeout
  total_timeout: 60        # Total request timeout
```

#### Pandas Optimization
**File**: `/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/core/pandas_optimizer.py`

```python
class PandasOptimizer:
    """Optimizes pandas operations for performance"""
    
    @staticmethod
    def optimize_memory_usage(df: pd.DataFrame) -> pd.DataFrame:
        """Optimize DataFrame memory usage"""
        for col in df.select_dtypes(include=['int64']).columns:
            df[col] = pd.to_numeric(df[col], downcast='integer')
        
        for col in df.select_dtypes(include=['float64']).columns:
            df[col] = pd.to_numeric(df[col], downcast='float')
            
        return df
    
    @staticmethod 
    def efficient_rolling_calculations(df: pd.DataFrame, window: int) -> pd.DataFrame:
        """Perform efficient rolling calculations"""
        # Use numba for JIT compilation if available
        try:
            import numba
            return df.rolling(window, engine='numba').mean()
        except ImportError:
            return df.rolling(window).mean()
```

### 6.3 Performance Metrics

#### System Performance Monitoring
```python
# Performance characteristics from documentation
PERFORMANCE_METRICS = {
    'signal_generation_latency': '<100ms',     # Sub-100ms signal generation
    'symbol_processing': '30+',                # Concurrent symbol processing
    'update_frequency': '1-5s',               # Per symbol update rate
    'memory_usage': '~500MB',                 # For 30 active symbols
    'connection_pool': '20 concurrent',        # Per exchange
    'cache_hit_rate': '>95%',                 # Target cache efficiency
    'api_throughput': '1200 req/min',         # Rate limit compliance
    'websocket_latency': '<50ms',             # Real-time data latency
    'analysis_time_complexity': 'O(n log n)', # For n candles
    'space_complexity': 'O(n)',              # Data storage
}
```

#### Cache Performance Monitoring
```python
class CacheMetrics:
    """Monitor cache performance and efficiency"""
    
    def __init__(self):
        self.stats = {
            'hits': 0,
            'misses': 0, 
            'timeouts': 0,
            'errors': 0,
            'total_requests': 0,
            'avg_response_time': 0.0
        }
    
    def record_hit(self, response_time: float):
        """Record cache hit with response time"""
        self.stats['hits'] += 1
        self.stats['total_requests'] += 1
        self._update_avg_response_time(response_time)
    
    def get_hit_rate(self) -> float:
        """Calculate cache hit rate percentage"""
        total = self.stats['hits'] + self.stats['misses']
        return (self.stats['hits'] / total * 100) if total > 0 else 0.0
```

### 6.4 Rate Limiting and Throttling

#### Exchange Rate Limiting
```python
class BybitRateLimiter:
    """Rate limiter for Bybit API calls"""
    
    def __init__(self, requests_per_second: int = 20, requests_per_minute: int = 1200):
        self.requests_per_second = requests_per_second
        self.requests_per_minute = requests_per_minute
        
        # Token bucket algorithm implementation
        self.second_bucket = requests_per_second
        self.minute_bucket = requests_per_minute
        
        self.last_second_refill = time.time()
        self.last_minute_refill = time.time()
    
    async def acquire(self):
        """Acquire rate limit token before making request"""
        await self._refill_buckets()
        
        if self.second_bucket <= 0 or self.minute_bucket <= 0:
            # Calculate wait time
            wait_time = min(
                1.0 - (time.time() - self.last_second_refill),
                60.0 - (time.time() - self.last_minute_refill)
            )
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                await self._refill_buckets()
        
        self.second_bucket -= 1
        self.minute_bucket -= 1
```

---

## 7. Data Usage Mapping

### 7.1 Component Data Dependencies

#### Dashboard API Data Flow
**File**: `/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/api/routes/dashboard.py`

```python
@router.get("/data")
async def get_dashboard_data():
    """Dashboard data endpoint - comprehensive market overview"""
    
    # Data dependencies:
    # 1. Market Overview (from cache: 'market:overview')
    # 2. Active Symbols (from cache: 'market:tickers') 
    # 3. Recent Signals (from cache: 'dashboard:signals')
    # 4. Alert History (from cache: 'alerts:recent')
    # 5. System Metrics (from cache: 'metrics:system')
    
    dashboard_integration = get_dashboard_integration()
    
    try:
        # Fetch all required data concurrently
        market_data, signals, alerts, metrics = await asyncio.gather(
            dashboard_integration.get_market_overview(),
            dashboard_integration.get_recent_signals(),
            dashboard_integration.get_recent_alerts(),
            dashboard_integration.get_system_metrics(),
            return_exceptions=True
        )
        
        return {
            'market_overview': market_data,
            'top_signals': signals,
            'recent_alerts': alerts,
            'system_metrics': metrics,
            'timestamp': int(time.time())
        }
        
    except Exception as e:
        logger.error(f"Dashboard data error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard data")
```

#### WebSocket Data Consumption
```python
class ConnectionManager:
    """Manages WebSocket connections and data distribution"""
    
    async def broadcast_market_update(self, update_data: dict):
        """Broadcast real-time market updates to WebSocket clients"""
        
        # Data consumed:
        # - Real-time ticker updates
        # - New confluence analysis results  
        # - Signal generation events
        # - Alert notifications
        # - System status changes
        
        message = {
            'type': 'market_update',
            'timestamp': datetime.utcnow().isoformat(),
            'data': update_data
        }
        
        # Broadcast to all connected clients
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"WebSocket broadcast error: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
```

### 7.2 Data Consumer Components

#### Market Monitor Consumer
**File**: `/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/monitoring/monitor.py`

```python
class MarketMonitor:
    """Primary data consumer for market analysis"""
    
    # Data Inputs:
    # - Exchange OHLCV data (via ExchangeManager)
    # - Real-time ticker updates (via WebSocket)
    # - Order book data (via WebSocket)
    # - Trade flow data (via WebSocket)
    
    # Data Outputs:
    # - Confluence analysis results (to cache)
    # - Trading signals (to SignalGenerator)
    # - Performance metrics (to MetricsManager)
    # - Alert triggers (to AlertManager)
    
    async def process_symbol_data(self, symbol: str, timeframe: str):
        """Process individual symbol data through analysis pipeline"""
        
        # Fetch required market data
        ohlcv_data = await self.exchange_manager.get_ohlcv(symbol, timeframe)
        ticker_data = await self.exchange_manager.get_ticker(symbol)
        
        # Perform confluence analysis
        analysis_result = await self.confluence_analyzer.analyze(
            symbol=symbol,
            ohlcv_data=ohlcv_data,
            ticker_data=ticker_data
        )
        
        # Cache analysis results
        await self.cache_manager.set(
            f'confluence:{symbol}:{timeframe}',
            analysis_result,
            ttl=30
        )
        
        # Generate signals if thresholds met
        if analysis_result['confluence_score'] > 70:  # Buy threshold
            await self.signal_generator.generate_buy_signal(symbol, analysis_result)
        elif analysis_result['confluence_score'] < 30:  # Sell threshold
            await self.signal_generator.generate_sell_signal(symbol, analysis_result)
```

#### Alert System Consumer
```python
class AlertManager:
    """Consumes signals and generates alerts"""
    
    # Data Inputs:
    # - Trading signals (from SignalGenerator)
    # - Confluence scores (from MarketMonitor)
    # - Price alerts (from threshold monitors)
    # - System alerts (from health monitors)
    
    # Data Outputs:
    # - Discord webhook messages
    # - Database alert records
    # - WebSocket alert broadcasts
    # - Mobile push notifications
    
    async def process_trading_signal(self, signal: Dict[str, Any]):
        """Process trading signal and generate appropriate alerts"""
        
        # Check alert frequency throttling
        if await self._is_throttled(signal['symbol'], signal['type']):
            logger.debug(f"Alert throttled for {signal['symbol']}")
            return
        
        # Format alert message
        alert_message = self._format_alert_message(signal)
        
        # Distribute alert through configured channels
        await asyncio.gather(
            self._send_discord_alert(alert_message),
            self._save_alert_to_database(signal),
            self._broadcast_websocket_alert(alert_message),
            return_exceptions=True
        )
        
        # Update throttling cache
        await self._update_throttle_cache(signal['symbol'], signal['type'])
```

### 7.3 Data Flow to Display Components

#### Mobile Dashboard Data Mapping
```python
@router.get("/mobile")
async def get_mobile_dashboard_data():
    """Optimized mobile dashboard data endpoint"""
    
    # Mobile-specific data requirements:
    # - Condensed market overview (essential metrics only)
    # - Top 10 signals (instead of full list)
    # - Recent alerts (last 24 hours)
    # - Simplified technical data
    
    try:
        # Get cached mobile-optimized data
        mobile_data = await direct_cache._get('dashboard:mobile', {})
        
        if not mobile_data:
            # Generate mobile data from full dashboard data
            full_data = await dashboard_integration.get_dashboard_data()
            mobile_data = {
                'market_overview': {
                    'active_symbols': full_data.get('market_overview', {}).get('active_symbols', 0),
                    'total_volume_24h': full_data.get('market_overview', {}).get('total_volume_24h', 0),
                    'market_regime': full_data.get('market_overview', {}).get('market_regime', 'unknown'),
                    'btc_dominance': full_data.get('market_overview', {}).get('btc_dominance', 0),
                    'market_breadth': full_data.get('market_overview', {}).get('market_breadth', {})
                },
                'top_signals': full_data.get('top_signals', [])[:10],  # Limit to top 10
                'recent_alerts': full_data.get('recent_alerts', [])[:5],  # Limit to 5 most recent
                'timestamp': int(time.time())
            }
            
            # Cache mobile data for faster access
            await direct_cache._client.set('dashboard:mobile', json.dumps(mobile_data), exptime=30)
        
        return mobile_data
        
    except Exception as e:
        logger.error(f"Mobile dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Mobile dashboard temporarily unavailable")
```

#### Administrative Dashboard Data
```python
@router.get("/admin/system")
async def get_admin_system_data():
    """Administrative system monitoring data"""
    
    # Admin-specific data requirements:
    # - Detailed system metrics (CPU, memory, network)
    # - Cache performance statistics
    # - Exchange connection health
    # - Error rates and logs
    # - Processing queue depths
    # - Rate limit utilization
    
    system_metrics = await get_system_metrics()
    cache_stats = await get_cache_performance()
    exchange_health = await get_exchange_health()
    
    return {
        'system_performance': {
            'cpu_usage': system_metrics.get('cpu_percent', 0),
            'memory_usage': system_metrics.get('memory_percent', 0),
            'disk_usage': system_metrics.get('disk_percent', 0),
            'network_io': system_metrics.get('network_io', {}),
            'uptime': system_metrics.get('uptime', 0)
        },
        'cache_performance': {
            'hit_rate': cache_stats.get('hit_rate', 0),
            'miss_rate': cache_stats.get('miss_rate', 0),
            'avg_response_time': cache_stats.get('avg_response_time', 0),
            'total_operations': cache_stats.get('total_operations', 0)
        },
        'exchange_health': {
            'bybit': exchange_health.get('bybit', {}),
            'binance': exchange_health.get('binance', {})
        },
        'timestamp': int(time.time())
    }
```

### 7.4 Data Flow Summary Diagram

```
Data Sources → Processing Pipeline → Caching Layer → Consumer Applications

┌─────────────────────────┐
│     Data Sources        │
├─────────────────────────┤
│ • Bybit REST API        │──┐
│ • Bybit WebSocket       │  │
│ • Binance API           │  │
│ • Internal Calculations │  │
└─────────────────────────┘  │
                             │
                             ▼
┌─────────────────────────┐  │
│  Processing Pipeline    │  │
├─────────────────────────┤  │
│ • Data Validation       │◀─┘
│ • Technical Indicators  │
│ • Confluence Analysis   │
│ • Signal Generation     │
│ • Metrics Calculation   │
└─────────────────────────┘
             │
             ▼
┌─────────────────────────┐
│    Caching Layer        │
├─────────────────────────┤
│ • Memcached (Primary)   │
│ • Redis (Secondary)     │
│ • Connection Pooling    │
│ • TTL Management        │
└─────────────────────────┘
             │
             ▼
┌─────────────────────────┐
│  Consumer Applications  │
├─────────────────────────┤
│ • Dashboard API (8003)  │
│ • Monitoring API (8001) │
│ • WebSocket Streaming   │
│ • Mobile API            │
│ • Alert System         │
│ • Admin Dashboard       │
└─────────────────────────┘
```

---

## Conclusion

This comprehensive data flow documentation provides developers with a complete understanding of how data moves through the Virtuoso CCXT trading system. The system demonstrates sophisticated architecture with:

- **Multi-source data integration** from Bybit and Binance exchanges
- **Real-time processing** via WebSocket streams and REST APIs  
- **Advanced analysis pipeline** with 6-dimensional confluence analysis
- **High-performance caching** using Memcached with connection pooling
- **Multiple consumer interfaces** for different use cases

The 253x performance optimization is achieved through intelligent caching, connection pooling, and efficient data processing algorithms, enabling sub-100ms signal generation latency while monitoring 30+ cryptocurrency pairs simultaneously.

For developers working with this system:
1. **Data Sources**: All external data comes primarily from Bybit with Binance as fallback
2. **Processing**: Raw data flows through validation, technical analysis, and confluence scoring
3. **Caching**: Processed results are cached with appropriate TTL values for optimal performance  
4. **Consumption**: Multiple APIs serve different client needs (dashboard, mobile, admin, WebSocket)

This documentation should serve as the authoritative reference for understanding, maintaining, and extending the data flow architecture of the Virtuoso CCXT trading system.