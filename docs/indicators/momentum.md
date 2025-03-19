# Momentum Indicators

## Overview

The `MomentumIndicators` class provides tools for analyzing price momentum and trend strength. These indicators help identify trend direction, strength, and potential reversal points.

## Available Indicators

### 1. Relative Strength Index (RSI)
```python
def calculate_rsi(
    prices: pd.Series,
    period: int = 14,
    smoothing: str = 'sma'
) -> pd.Series:
    """Calculate Relative Strength Index.
    
    Args:
        prices: Price series
        period: Calculation period
        smoothing: Smoothing method ('sma' or 'ema')
        
    Returns:
        Series containing RSI values (0-100)
    """
```

### 2. Moving Average Convergence Divergence (MACD)
```python
def calculate_macd(
    prices: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD line, signal line, and histogram.
    
    Args:
        prices: Price series
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line period
        
    Returns:
        Tuple of (MACD line, signal line, histogram)
    """
```

### 3. Stochastic Oscillator
```python
def calculate_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3
) -> Tuple[pd.Series, pd.Series]:
    """Calculate Stochastic Oscillator.
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        k_period: %K period
        d_period: %D period
        
    Returns:
        Tuple of (%K line, %D line)
    """
```

## Usage Examples

### Basic Usage
```python
from src.indicators import MomentumIndicators

# Initialize
momentum = MomentumIndicators()

# Calculate RSI
rsi = momentum.calculate_rsi(prices)

# Calculate MACD
macd_line, signal_line, histogram = momentum.calculate_macd(prices)

# Calculate Stochastic
k_line, d_line = momentum.calculate_stochastic(high, low, close)
```

### Advanced Usage
```python
# Custom configuration
momentum = MomentumIndicators(
    config={
        'rsi': {
            'overbought': 70,
            'oversold': 30
        },
        'macd': {
            'fast_ema_alpha': 0.15,
            'slow_ema_alpha': 0.075
        }
    }
)

# Batch calculation
results = momentum.calculate_batch(
    prices,
    indicators=['rsi', 'macd'],
    periods={'rsi': 14, 'macd': (12, 26, 9)}
)
```

## Signal Generation

### RSI Signals
```python
def generate_rsi_signals(
    prices: pd.Series,
    overbought: float = 70,
    oversold: float = 30
) -> pd.Series:
    """Generate trading signals based on RSI.
    
    Returns:
        Series with values:
        1: Buy signal (oversold)
        -1: Sell signal (overbought)
        0: No signal
    """
```

### MACD Signals
```python
def generate_macd_signals(
    prices: pd.Series
) -> pd.Series:
    """Generate trading signals based on MACD.
    
    Returns:
        Series with values:
        1: Buy signal (MACD crosses above signal)
        -1: Sell signal (MACD crosses below signal)
        0: No signal
    """
```

## Performance Optimization

### Caching
```python
# Enable caching for repeated calculations
momentum.enable_cache()

# Cache with custom TTL
momentum.enable_cache(ttl=600)  # 10 minutes

# Clear cache
momentum.clear_cache()
```

### Batch Processing
```python
# Process multiple symbols
symbols = ['BTC-USD', 'ETH-USD']
results = {}

for symbol in symbols:
    results[symbol] = momentum.calculate_batch(
        prices[symbol],
        indicators=['rsi', 'macd', 'stoch']
    )
```

## Configuration Options

```python
config = {
    'rsi': {
        'period': 14,
        'overbought': 70,
        'oversold': 30,
        'smoothing': 'sma'  # or 'ema'
    },
    'macd': {
        'fast_period': 12,
        'slow_period': 26,
        'signal_period': 9,
        'histogram_scaling': 1.0
    },
    'stochastic': {
        'k_period': 14,
        'd_period': 3,
        'smoothing': 'sma'
    }
}
```

## Error Handling

```python
try:
    rsi = momentum.calculate_rsi(prices)
except ValidationError as e:
    logger.error(f"Invalid input data: {e}")
except CalculationError as e:
    logger.error(f"Calculation failed: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

## Best Practices

1. **Data Preparation**
   ```python
   # Remove NaN values
   prices = prices.dropna()
   
   # Ensure correct frequency
   prices = prices.asfreq('1min')
   
   # Handle outliers
   prices = momentum.remove_outliers(prices)
   ```

2. **Parameter Selection**
   ```python
   # Adjust periods based on timeframe
   if timeframe == '1h':
       rsi_period = 14
   elif timeframe == '1d':
       rsi_period = 21
   
   rsi = momentum.calculate_rsi(prices, period=rsi_period)
   ```

3. **Signal Validation**
   ```python
   # Combine multiple indicators
   rsi_signal = momentum.generate_rsi_signals(prices)
   macd_signal = momentum.generate_macd_signals(prices)
   
   # Generate combined signal
   combined_signal = momentum.combine_signals([
       (rsi_signal, 0.5),
       (macd_signal, 0.5)
   ])
   ```

4. **Performance Monitoring**
   ```python
   # Track calculation time
   with momentum.timer('rsi_calculation'):
       rsi = momentum.calculate_rsi(prices)
   
   # Get performance stats
   stats = momentum.get_performance_stats()
   print(f"Average RSI calculation time: {stats['rsi_avg_time']}")
   ``` 