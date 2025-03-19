# Orderflow Indicators

## Overview

The `OrderflowIndicators` class provides tools for analyzing trade flow and market microstructure through time and sales data. These indicators help identify trading patterns, aggressive order flow, and potential price direction through trade-by-trade analysis.

## Available Indicators

### 1. Trade Flow Imbalance
```python
def calculate_flow_imbalance(
    trades: pd.DataFrame,
    window: int = 100,
    volume_weighted: bool = True
) -> pd.Series:
    """Calculate trade flow imbalance.
    
    Args:
        trades: DataFrame with trades (price, size, side)
        window: Number of trades to consider
        volume_weighted: Whether to weight by trade size
        
    Returns:
        Series with flow imbalance values (-1 to 1)
    """
```

### 2. Trade Size Analysis
```python
def analyze_trade_sizes(
    trades: pd.DataFrame,
    size_buckets: List[float] = [0.1, 1.0, 10.0, 100.0]
) -> pd.DataFrame:
    """Analyze distribution of trade sizes.
    
    Args:
        trades: DataFrame with trades
        size_buckets: List of size thresholds
        
    Returns:
        DataFrame with trade size distribution metrics
    """
```

### 3. Aggressive Flow Detection
```python
def detect_aggressive_flow(
    trades: pd.DataFrame,
    threshold: float = 0.8,
    min_size: float = 1.0
) -> pd.Series:
    """Detect aggressive trading flow.
    
    Args:
        trades: DataFrame with trades
        threshold: Aggressiveness threshold
        min_size: Minimum trade size to consider
        
    Returns:
        Series with aggressive flow indicators
    """
```

## Usage Examples

### Basic Usage
```python
from src.indicators import OrderflowIndicators

# Initialize
orderflow = OrderflowIndicators()

# Calculate flow imbalance
imbalance = orderflow.calculate_flow_imbalance(trades)

# Analyze trade sizes
size_analysis = orderflow.analyze_trade_sizes(trades)

# Detect aggressive flow
aggressive = orderflow.detect_aggressive_flow(trades)
```

### Advanced Usage
```python
# Custom configuration
orderflow = OrderflowIndicators(
    config={
        'flow_imbalance': {
            'decay': 'exponential',
            'half_life': 50
        },
        'trade_size': {
            'dynamic_buckets': True,
            'percentiles': [25, 50, 75, 90]
        }
    }
)

# Batch calculation
results = orderflow.calculate_batch(
    trades,
    indicators=['flow_imbalance', 'aggressive_flow'],
    params={'window': 200}
)
```

## Signal Generation

### Flow Signals
```python
def generate_flow_signals(
    trades: pd.DataFrame,
    imbalance_threshold: float = 0.6,
    size_threshold: float = 0.8
) -> pd.Series:
    """Generate trading signals based on order flow.
    
    Returns:
        Series with values:
        1: Buy signal (strong buying flow)
        -1: Sell signal (strong selling flow)
        0: No signal
    """
```

### Size Anomaly Signals
```python
def detect_size_anomalies(
    trades: pd.DataFrame,
    lookback: int = 1000
) -> pd.Series:
    """Detect anomalous trade sizes.
    
    Returns:
        Series with anomaly scores
    """
```

## Performance Optimization

### Caching
```python
# Enable caching for repeated calculations
orderflow.enable_cache()

# Cache with custom TTL
orderflow.enable_cache(ttl=5)  # 5 seconds

# Clear cache
orderflow.clear_cache()
```

### Batch Processing
```python
# Process multiple symbols
symbols = ['BTC-USD', 'ETH-USD']
results = {}

for symbol in symbols:
    results[symbol] = orderflow.calculate_batch(
        trades[symbol],
        indicators=['flow_imbalance', 'size_analysis']
    )
```

## Configuration Options

```python
config = {
    'flow_imbalance': {
        'window': 100,
        'volume_weighted': True,
        'decay': 'exponential',  # or 'linear'
        'half_life': 50,
        'min_trades': 10
    },
    'trade_size': {
        'size_buckets': [0.1, 1.0, 10.0, 100.0],
        'dynamic_buckets': False,
        'percentiles': [25, 50, 75, 90],
        'min_samples': 1000
    },
    'aggressive_flow': {
        'threshold': 0.8,
        'min_size': 1.0,
        'lookback': 100,
        'smoothing': 0.1
    }
}
```

## Error Handling

```python
try:
    imbalance = orderflow.calculate_flow_imbalance(trades)
except ValidationError as e:
    logger.error(f"Invalid trade data: {e}")
except CalculationError as e:
    logger.error(f"Calculation failed: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

## Best Practices

1. **Data Preparation**
   ```python
   # Clean trade data
   trades = orderflow.clean_trades(trades)
   
   # Remove duplicates
   trades = orderflow.remove_duplicate_trades(trades)
   
   # Sort by timestamp
   trades = trades.sort_values('timestamp')
   ```

2. **Real-time Processing**
   ```python
   # Process trades incrementally
   orderflow.process_trade(
       price=100.0,
       size=1.0,
       side='buy',
       timestamp=1234567890
   )
   
   # Get latest metrics
   current_state = orderflow.get_current_state()
   ```

3. **Analysis Integration**
   ```python
   # Combine with orderbook analysis
   flow = orderflow.calculate_flow_imbalance(trades)
   book_imbalance = orderbook.calculate_imbalance(bids, asks)
   
   # Generate combined signal
   signal = orderflow.combine_signals([
       (flow, 0.7),
       (book_imbalance, 0.3)
   ])
   ```

4. **Performance Monitoring**
   ```python
   # Track calculation time
   with orderflow.timer('flow_calculation'):
       flow = orderflow.calculate_flow_imbalance(trades)
   
   # Get performance stats
   stats = orderflow.get_performance_stats()
   print(f"Average flow calculation time: {stats['flow_avg_time']}")
   ```

## Integration Examples

### 1. With Market Making
```python
# Use orderflow for quote adjustment
flow = orderflow.calculate_flow_imbalance(trades)
aggressive = orderflow.detect_aggressive_flow(trades)

# Adjust quotes based on flow
quotes = market_maker.adjust_quotes(
    base_quotes=quotes,
    flow_imbalance=flow,
    aggressive_flow=aggressive
)
```

### 2. With Position Management
```python
# Use orderflow for position sizing
flow = orderflow.calculate_flow_imbalance(trades)
size_stats = orderflow.analyze_trade_sizes(trades)

# Calculate position size
position_size = position.calculate_size(
    flow_imbalance=flow,
    size_metrics=size_stats,
    risk_factor=0.1
)
```

### 3. With Risk Analysis
```python
# Use orderflow for risk assessment
aggressive = orderflow.detect_aggressive_flow(trades)
anomalies = orderflow.detect_size_anomalies(trades)

# Update risk metrics
risk.update_metrics(
    aggressive_flow=aggressive,
    size_anomalies=anomalies,
    window=100
)
```
``` 