# Bybit API Analysis for Sentiment Indicators

## Overview
This document details which sentiment data is available from Bybit's public API and what requires external sources.

## Available Sentiment Data from Bybit

### 1. **Funding Rate** ✅
- **Source**: Ticker endpoint & Funding History endpoint
- **Endpoints**:
  - `GET /v5/market/tickers` - Current funding rate
  - `GET /v5/market/funding/history` - Historical funding rates
- **Data Format**:
  ```json
  {
    "fundingRate": "0.0001",
    "nextFundingTime": "1753286400000"
  }
  ```
- **Usage**: Sentiment indicator can calculate funding rate score and volatility

### 2. **Open Interest** ✅
- **Source**: Ticker endpoint & Open Interest endpoint
- **Endpoints**:
  - `GET /v5/market/tickers` - Current open interest
  - `GET /v5/market/open-interest` - Historical open interest
- **Data Format**:
  ```json
  {
    "openInterest": "56367.581",
    "openInterestValue": "6650309210.72"
  }
  ```
- **Usage**: Used for market activity analysis

### 3. **Trade Volume Sentiment** ✅
- **Source**: Recent trades endpoint
- **Endpoint**: `GET /v5/market/recent-trade`
- **Calculation**: Analyze buy vs sell trades
- **Example Result**: Buy: 9.02%, Sell: 90.98%
- **Usage**: Volume sentiment score calculation

### 4. **Long/Short Ratio** ✅
- **Source**: Account ratio endpoint
- **Endpoint**: `GET /v5/market/account-ratio`
- **Implementation**: Already available in `BybitExchange._fetch_long_short_ratio()`
- **Parameters**:
  - category: 'linear'
  - symbol: Trading symbol
  - period: '5min', '15min', '30min', '1h', '4h', '1d'
  - limit: Number of data points
- **Data Format**:
  ```json
  {
    "buyRatio": "0.6175",
    "sellRatio": "0.3825",
    "timestamp": "1753286400000"
  }
  ```
- **Usage**: Automatically fetched and included in market data sentiment
- **Market Data Location**: `market_data['sentiment']['long_short_ratio']`
- **Processed Format**:
  ```json
  {
    "symbol": "BTCUSDT",
    "long": 61.75,    // Percentage (0-100)
    "short": 38.25,   // Percentage (0-100)
    "timestamp": 1753286400000
  }
  ```

## NOT Available from Bybit Public API

### 1. **Liquidations Data** ❌
- **Required By**: Sentiment indicator's `calculate_liquidation_events()`
- **Expected Format**:
  ```json
  {
    "long": 1000000,
    "short": 500000
  }
  ```
- **Alternatives**:
  - WebSocket subscription (if available)
  - Third-party liquidation feeds
  - External APIs that track liquidations

### 2. **Market Mood / Social Sentiment** ❌
- **Required By**: Sentiment indicator's `calculate_market_mood()`
- **Expected Format**:
  ```json
  {
    "fear_and_greed": 50,
    "social_sentiment": 0.6,
    "search_trends": 45
  }
  ```
- **Alternatives**:
  - Fear & Greed Index APIs
  - Social media sentiment APIs
  - News sentiment analysis services

## Data Collection Strategy

### For Complete Sentiment Analysis:

1. **Use Bybit API for**:
   - Funding rates (current and historical)
   - Open interest data
   - Trade volume analysis
   - Long/Short ratio (account ratio)

2. **Supplement with External Sources**:
   - Liquidations from data aggregators or WebSocket feeds
   - Social sentiment from sentiment APIs

3. **Fallback Behavior**:
   - When data is unavailable, sentiment indicator returns neutral scores (50)
   - System continues to function with reduced accuracy

## Implementation Example

```python
async def collect_sentiment_data(exchange, symbol):
    """Collect sentiment data from available sources."""
    
    # From Bybit API
    ticker = await exchange.fetch_ticker(symbol)
    trades = await exchange.fetch_trades(symbol, limit=1000)
    
    # Calculate volume sentiment from trades
    buy_volume = sum(t['amount'] for t in trades if t['side'] == 'buy')
    sell_volume = sum(t['amount'] for t in trades if t['side'] == 'sell')
    total_volume = buy_volume + sell_volume
    buy_percentage = buy_volume / total_volume if total_volume > 0 else 0.5
    
    # Fetch long/short ratio (now available!)
    lsr_data = await exchange._fetch_long_short_ratio(symbol)
    
    sentiment_data = {
        'funding_rate': ticker.get('fundingRate', 0),
        'open_interest': ticker.get('openInterest', 0),
        'volume_sentiment': {
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'buy_volume_percent': buy_percentage
        },
        'long_short_ratio': lsr_data,  # Now fetched from API!
        # These would need external sources:
        'liquidations': {'long': 0, 'short': 0},        # Default
        'market_mood': {'fear_and_greed': 50}           # Default
    }
    
    return sentiment_data
```

## CURL Commands for Available Data

```bash
# Get funding rate from ticker
curl -X GET "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"

# Get long/short ratio
curl -X GET "https://api.bybit.com/v5/market/account-ratio?category=linear&symbol=BTCUSDT&period=5min&limit=1"

# Get funding rate history
curl -X GET "https://api.bybit.com/v5/market/funding/history?category=linear&symbol=BTCUSDT&limit=20"

# Get open interest history
curl -X GET "https://api.bybit.com/v5/market/open-interest?category=linear&symbol=BTCUSDT&intervalTime=1h&limit=10"

# Get recent trades for volume sentiment
curl -X GET "https://api.bybit.com/v5/market/recent-trade?category=linear&symbol=BTCUSDT&limit=100"
```

## Recommendations

1. **Priority Data**: All core sentiment data is now available:
   - Funding rate (current and historical)
   - Volume sentiment from trades
   - Long/Short ratio from account-ratio endpoint
   - Open interest data
2. **External Integration**: Only needed for:
   - Liquidation events
   - Social sentiment/Fear & Greed metrics
3. **Graceful Degradation**: System handles missing data by returning neutral scores
4. **Future Enhancement**: Add WebSocket support for real-time liquidation data when available

## Conclusion

The sentiment indicator can function well with Bybit's public API data:

**✅ Available Data:**
- Funding Rate (current and historical)
- Open Interest data
- Trade volume analysis for sentiment
- **Long/Short Ratio** (via account-ratio endpoint)

**❌ Still Requiring External Sources:**
- Liquidation events
- Social sentiment metrics

The system is configured to work optimally with available data while gracefully handling missing components by returning neutral scores.