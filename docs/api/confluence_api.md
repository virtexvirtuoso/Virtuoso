# Confluence Engine API

## Overview

The Confluence Engine is a proprietary multi-indicator analysis system that combines various market signals to generate high-confidence trading insights. This document describes the public API for using the confluence engine.

## Quick Start

```python
from src.factories.indicator_factory import IndicatorFactory

# Create analyzer
confluence = IndicatorFactory.create_confluence_analyzer(config)

# Analyze market
result = await confluence.analyze(market_data)
```

## API Reference

### ConfluenceAnalyzer

The main class for performing confluence analysis.

#### Methods

##### `analyze(market_data: Dict[str, Any]) -> Dict[str, Any]`

Performs comprehensive market analysis using multiple indicators.

**Parameters:**
- `market_data`: Dictionary containing:
  - `symbol`: Trading symbol (str)
  - `ohlcv_data`: OHLCV data for multiple timeframes (dict)
  - `orderbook`: Current orderbook snapshot (dict)
  - `trades`: Recent trades (list)
  - `sentiment_data`: Market sentiment metrics (dict)

**Returns:**
- Dictionary containing:
  - `confluence_score`: Overall confluence score (0-100)
  - `component_scores`: Individual indicator scores
  - `reliability`: Confidence level of analysis (0-100)
  - `signals`: List of generated trading signals
  - `top_subcomponents`: Most influential sub-indicators

##### `validate_market_data(market_data: Dict[str, Any]) -> bool`

Validates the structure and content of market data.

**Parameters:**
- `market_data`: Market data to validate

**Returns:**
- `bool`: True if data is valid, False otherwise

##### `get_component_weights() -> Dict[str, float]`

Returns the current weights for each component.

**Returns:**
- Dictionary mapping component names to their weights

## Components

The confluence engine analyzes these components:

1. **Technical Indicators** (20% weight)
   - RSI, MACD, Bollinger Bands, etc.
   
2. **Volume Indicators** (15% weight)
   - OBV, Volume Profile, CVD, etc.
   
3. **Orderbook Analysis** (15% weight)
   - Imbalance, Depth, Liquidity
   
4. **Order Flow** (15% weight)
   - Trade flow, Aggression, Delta
   
5. **Price Structure** (20% weight)
   - Support/Resistance, Order Blocks, Trends
   
6. **Market Sentiment** (15% weight)
   - Funding Rate, Long/Short Ratio, Fear & Greed

## Market Data Structure

### OHLCV Data

```python
{
    'base': pd.DataFrame,  # Base timeframe (e.g., 5m)
    'ltf': pd.DataFrame,   # Lower timeframe (e.g., 1m)
    'mtf': pd.DataFrame,   # Medium timeframe (e.g., 15m)
    'htf': pd.DataFrame    # Higher timeframe (e.g., 1h)
}
```

Each DataFrame should contain columns: `timestamp`, `open`, `high`, `low`, `close`, `volume`

### Orderbook Data

```python
{
    'bids': [[price, amount], ...],  # Buy orders
    'asks': [[price, amount], ...],  # Sell orders
    'timestamp': int                  # Unix timestamp
}
```

### Trade Data

```python
[
    {
        'id': str,
        'price': float,
        'amount': float,
        'side': str,  # 'buy' or 'sell'
        'timestamp': int
    },
    ...
]
```

### Sentiment Data

```python
{
    'funding_rate': float,
    'long_short_ratio': float,
    'open_interest': float,
    'fear_greed_index': float
}
```

## Usage Examples

### Basic Analysis

```python
import asyncio
from src.factories.indicator_factory import IndicatorFactory

async def analyze_btc():
    # Create analyzer
    confluence = IndicatorFactory.create_confluence_analyzer(config)
    
    # Prepare data
    market_data = {
        'symbol': 'BTCUSDT',
        'ohlcv_data': ohlcv_data,
        'orderbook': orderbook,
        'trades': trades,
        'sentiment_data': sentiment
    }
    
    # Analyze
    result = await confluence.analyze(market_data)
    
    # Use results
    if result['confluence_score'] > 70:
        print("Strong bullish confluence")
    elif result['confluence_score'] < 30:
        print("Strong bearish confluence")

asyncio.run(analyze_btc())
```

### Individual Indicators

```python
# Create specific indicator
technical = IndicatorFactory.create_technical_indicators(config)

# Calculate
result = await technical.calculate(market_data)

# Access scores
rsi_score = result['components']['rsi']
macd_score = result['components']['macd']
```

## Error Handling

The API uses standard Python exceptions:

```python
try:
    result = await confluence.analyze(market_data)
except ValueError as e:
    # Invalid data structure
    print(f"Data validation error: {e}")
except Exception as e:
    # Other errors
    print(f"Analysis error: {e}")
```

## Performance Considerations

1. **Data Requirements**: Ensure all required data is available before calling
2. **Caching**: Results are cached for 60 seconds by default
3. **Async Operations**: Use async/await for better performance
4. **Batch Analysis**: Process multiple symbols in parallel when possible

## Rate Limits

- Maximum 100 analyses per minute per instance
- Cached results don't count against rate limit
- Use batch operations for efficiency