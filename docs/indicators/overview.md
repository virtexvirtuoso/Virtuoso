# Trading Indicators Documentation

## Overview

The indicators module provides a comprehensive suite of technical analysis tools organized into six main categories:

1. **Momentum Indicators** - Trend and momentum analysis
2. **Volume Indicators** - Volume-based analysis
3. **Orderbook Indicators** - Market microstructure analysis
4. **Orderflow Indicators** - Order flow and liquidity analysis
5. **Position Indicators** - Position and risk metrics
6. **Sentiment Indicators** - Market sentiment analysis

## Module Structure

```
src/indicators/
├── __init__.py              # Package initialization
├── momentum_indicators.py   # Trend and momentum analysis
├── volume_indicators.py     # Volume-based analysis
├── orderbook_indicators.py  # Order book analysis
├── orderflow_indicators.py  # Order flow analysis
├── position_indicators.py   # Position metrics
└── sentiment_indicators.py  # Sentiment analysis
```

## Quick Start

```python
from src.indicators import (
    MomentumIndicators,
    VolumeIndicators,
    OrderbookIndicators,
    OrderflowIndicators,
    PositionIndicators,
    SentimentIndicators
)

# Initialize indicators
momentum = MomentumIndicators()
volume = VolumeIndicators()
orderbook = OrderbookIndicators()
orderflow = OrderflowIndicators()
position = PositionIndicators()
sentiment = SentimentIndicators()

# Use indicators
rsi = momentum.calculate_rsi(prices, period=14)
vwap = volume.calculate_vwap(prices, volumes)
imbalance = orderbook.calculate_imbalance(bids, asks)
```

## Common Features

All indicator classes share these common features:

1. **Data Validation**
   - Input validation
   - NaN handling
   - Type checking
   - Range validation

2. **Performance Optimization**
   - Vectorized calculations
   - Efficient memory usage
   - Caching for expensive computations

3. **Error Handling**
   - Graceful error recovery
   - Detailed error messages
   - Warning for edge cases

4. **Configuration**
   - Customizable parameters
   - Default values
   - Parameter validation

## Integration

The indicators module integrates with:

1. **Data Storage**
   - InfluxDB for time series data
   - Cache for frequent calculations
   - Batch processing support

2. **Analysis Engine**
   - Real-time analysis
   - Historical backtesting
   - Strategy development

3. **Trading System**
   - Signal generation
   - Risk management
   - Position sizing

## Best Practices

1. **Initialization**
   ```python
   # Initialize with default settings
   indicator = MomentumIndicators()
   
   # Initialize with custom settings
   indicator = MomentumIndicators(
       cache_enabled=True,
       validation_level='strict'
   )
   ```

2. **Data Preparation**
   ```python
   # Ensure data quality
   prices = prices.dropna()
   volumes = volumes.fillna(0)
   
   # Align timestamps
   prices = prices.asof(volumes.index)
   ```

3. **Error Handling**
   ```python
   try:
       result = indicator.calculate()
   except ValidationError as e:
       logger.error(f"Validation failed: {e}")
   except CalculationError as e:
       logger.error(f"Calculation failed: {e}")
   ```

4. **Performance**
   ```python
   # Use vectorized operations
   indicator.calculate_batch(data)
   
   # Enable caching for repeated calculations
   indicator.enable_cache()
   ```

## Configuration Options

Common configuration options across all indicators:

```python
config = {
    'validation': {
        'enabled': True,
        'level': 'strict',  # or 'loose'
        'nan_handling': 'drop'  # or 'fill' or 'interpolate'
    },
    'performance': {
        'cache_enabled': True,
        'cache_ttl': 300,  # seconds
        'batch_size': 1000
    },
    'logging': {
        'level': 'INFO',
        'format': 'detailed'
    }
}
```

## Error Handling

Common error types:

1. **ValidationError**
   - Invalid input data
   - Parameter range violations
   - Missing required data

2. **CalculationError**
   - Numerical errors
   - Overflow/underflow
   - Division by zero

3. **ConfigurationError**
   - Invalid settings
   - Incompatible parameters
   - Missing dependencies

## Logging and Monitoring

Built-in logging and monitoring:

```python
# Enable detailed logging
indicator.set_log_level('DEBUG')

# Monitor performance
stats = indicator.get_performance_stats()

# Track calculation times
with indicator.timer('rsi_calculation'):
    result = indicator.calculate_rsi()
``` 