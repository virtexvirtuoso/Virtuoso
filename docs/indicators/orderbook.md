# Orderbook Indicators

## Overview

The `OrderbookIndicators` class provides tools for analyzing market microstructure through orderbook data. These indicators help identify market depth, liquidity, and potential price pressure points. The class calculates a composite orderbook score (0-100) based on weighted component indicators, where scores above 50 indicate bullish bias and below 50 indicate bearish bias.

## Component Weights

The orderbook score is calculated using the following weighted components:

| Component | Weight | Description |
|-----------|--------|-------------|
| Imbalance | 25% | Measures the buy/sell pressure imbalance in the orderbook |
| MPI (Market Pressure Index) | 20% | Analyzes buying/selling pressure with price sensitivity |
| Depth | 20% | Analyzes the distribution of liquidity through orderbook depth |
| Liquidity | 10% | Measures overall market liquidity based on depth and spread |
| Absorption/Exhaustion | 10% | Detects supply/demand absorption and market exhaustion |
| DOM Momentum | 5% | Depth of Market momentum analyzing order flow velocity |
| Spread | 5% | Evaluates the bid-ask spread relative to recent price action |
| OBPS | 5% | Order Book Pressure Score capturing overall orderbook bias |

These weights prioritize the most reliable and predictive components while still maintaining a comprehensive view of orderbook dynamics.

## Available Indicators

### 1. Order Book Imbalance
```python
def calculate_imbalance(
    bids: pd.DataFrame,
    asks: pd.DataFrame,
    depth: int = 10
) -> float:
    """Calculate order book imbalance.
    
    Args:
        bids: Bid levels DataFrame (price, size)
        asks: Ask levels DataFrame (price, size)
        depth: Number of levels to consider
        
    Returns:
        Imbalance ratio (-1 to 1)
    """
```

### 2. Market Pressure Index (MPI)
```python
def calculate_pressure(
    orderbook: Dict[str, Any]
) -> Dict[str, float]:
    """Calculate orderbook pressure with enhanced sensitivity.
    
    Args:
        orderbook: Dictionary containing bids and asks
    
    Returns:
        Dictionary with score, pressure metrics and imbalance values
    """
```

### 3. Market Depth Analysis
```python
def calculate_market_depth(
    bids: pd.DataFrame,
    asks: pd.DataFrame,
    price_range: float = 0.01
) -> pd.DataFrame:
    """Calculate cumulative market depth.
    
    Args:
        bids: Bid levels DataFrame
        asks: Ask levels DataFrame
        price_range: Price range as percentage
        
    Returns:
        DataFrame with cumulative depth at each level
    """
```

### 4. Liquidity Analysis
```python
def calculate_liquidity_score(
    bids: pd.DataFrame,
    asks: pd.DataFrame,
    target_size: float
) -> float:
    """Calculate liquidity score based on order book.
    
    Args:
        bids: Bid levels DataFrame
        asks: Ask levels DataFrame
        target_size: Target transaction size
        
    Returns:
        Liquidity score (0-100)
    """
```

### 5. Absorption/Exhaustion
```python
def calculate_absorption_exhaustion(
    bids: np.ndarray,
    asks: np.ndarray
) -> Dict[str, float]:
    """Calculate absorption and exhaustion metrics.
    
    Args:
        bids: Numpy array of bid levels (price, size)
        asks: Numpy array of ask levels (price, size)
        
    Returns:
        Dictionary with absorption, exhaustion and combined scores
    """
```

### 6. DOM Momentum
```python
def calculate_dom_momentum(
    current_bids: np.ndarray,
    current_asks: np.ndarray
) -> Dict[str, float]:
    """Calculate Depth of Market momentum.
    
    Args:
        current_bids: Current snapshot of bid levels
        current_asks: Current snapshot of ask levels
        
    Returns:
        Dictionary with score and flow velocity metrics
    """
```

### 7. Spread Analysis
```python
def calculate_spread_score(
    bids: np.ndarray,
    asks: np.ndarray
) -> Dict[str, float]:
    """Calculate enhanced spread score with stability metrics.
    
    Args:
        bids: Numpy array of bid levels
        asks: Numpy array of ask levels
        
    Returns:
        Dictionary with score, relative spread and stability metrics
    """
```

### 8. Order Book Pressure Score (OBPS)
```python
def calculate_obps(
    bids: np.ndarray,
    asks: np.ndarray
) -> Dict[str, float]:
    """Calculate Order Book Pressure Score (OBPS).
    
    Args:
        bids: Numpy array of bid levels
        asks: Numpy array of ask levels
        
    Returns:
        Dictionary with score and pressure metrics
    """
```

## Usage Examples

### Basic Usage
```python
from src.indicators import OrderbookIndicators

# Initialize with default config
config = {
    'exchange': 'binance',
    'symbol': 'BTC/USDT',
    'timeframes': {'1m': {'interval': 1, 'validation': {'min_candles': 10}}}
}
orderbook = OrderbookIndicators(config)

# Calculate all indicators
result = await orderbook.calculate(market_data)

# Access the overall score and component scores
overall_score = result['score']  # 0-100 scale (>50 bullish, <50 bearish)
component_scores = result['components']

# Access specific components
imbalance_score = component_scores['imbalance']
mpi_score = component_scores['mpi']
liquidity_score = component_scores['liquidity']

# Access raw underlying metrics
raw_metrics = result['metadata']['raw_values']
```

### Advanced Usage with Custom Weights
```python
# Custom configuration with adjusted weights
config = {
    'exchange': 'binance',
    'symbol': 'BTC/USDT',
    'timeframes': {'1m': {'interval': 1, 'validation': {'min_candles': 10}}},
    'analysis': {
        'indicators': {
            'orderbook': {
                'components': {
                    'imbalance': {'weight': 0.30},  # Increase imbalance weight
                    'mpi': {'weight': 0.25},        # Increase MPI weight
                    'depth': {'weight': 0.15},      # Reduce depth weight
                    'liquidity': {'weight': 0.15},  # Increase liquidity weight
                    # Other components will use default weights
                }
            }
        }
    }
}

# Initialize with custom config
orderbook = OrderbookIndicators(config)

# Calculate with the custom weights
result = await orderbook.calculate(market_data)
```

## Signal Generation

### Imbalance Signals
```python
def generate_imbalance_signals(
    bids: pd.DataFrame,
    asks: pd.DataFrame,
    threshold: float = 0.7
) -> int:
    """Generate trading signals based on order book imbalance.
    
    Returns:
        1: Buy signal (strong bid pressure)
        -1: Sell signal (strong ask pressure)
        0: No signal
    """
```

### Liquidity Signals
```python
def generate_liquidity_signals(
    bids: pd.DataFrame,
    asks: pd.DataFrame,
    baseline_liquidity: float
) -> pd.Series:
    """Generate signals based on liquidity changes.
    
    Returns:
        Series with liquidity state signals
    """
```

## Performance Optimization

### Caching
```python
# Enable caching for repeated calculations
orderbook.enable_cache()

# Cache with custom TTL
orderbook.enable_cache(ttl=1)  # 1 second

# Clear cache
orderbook.clear_cache()
```

### Batch Processing
```python
# Process multiple symbols
symbols = ['BTC-USD', 'ETH-USD']
results = {}

for symbol in symbols:
    results[symbol] = orderbook.calculate_batch(
        bids[symbol],
        asks[symbol],
        indicators=['imbalance', 'depth']
    )
```

## Configuration Options

```python
config = {
    'imbalance': {
        'depth': 10,
        'weight_decay': 'linear',  # or 'exponential'
        'normalize': True,
        'price_sensitivity': 1.0
    },
    'depth': {
        'price_range': 0.01,
        'aggregation': 'price_points',  # or 'levels'
        'n_points': 20,
        'min_size': 0.0001
    },
    'liquidity': {
        'size_grid': [0.1, 0.5, 1.0, 5.0, 10.0],
        'price_impact': True,
        'weighted_score': True
    },
    'mpi': {
        'levels_to_use': 20,
        'concentration_factor': True
    },
    'absorption_exhaustion': {
        'concentration_weight': 0.7,
        'replenishment_weight': 0.3
    }
}
```

## Component Reliability

The component weights have been carefully calibrated based on reliability and predictive value:

1. **Highly Reliable Components (65%)**
   - Imbalance (25%): Most reliable due to sophisticated normalization and multi-factor approach
   - MPI (20%): Strong reliability with price/volume weighting and spread adjustment
   - Depth (20%): Reliable with multi-level analysis and volume balance considerations

2. **Moderately Reliable Components (20%)**
   - Liquidity (10%): Good reliability combining depth and spread analysis
   - Absorption/Exhaustion (10%): Valuable for detecting supply/demand imbalances

3. **Supportive Components (15%)**
   - DOM Momentum (5%): Good for detecting flow but more affected by noise
   - Spread (5%): Simple but can be noisy in liquid markets
   - OBPS (5%): Useful for trend but less reliable in choppy markets

## Error Handling

```python
try:
    result = await orderbook.calculate(market_data)
except ValidationError as e:
    logger.error(f"Invalid orderbook data: {e}")
except CalculationError as e:
    logger.error(f"Calculation failed: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

## Best Practices

1. **Data Preparation**
   ```python
   # Clean orderbook data
   bids, asks = orderbook.clean_orderbook(bids, asks)
   
   # Remove crossed orders
   bids, asks = orderbook.remove_crossed_levels(bids, asks)
   
   # Aggregate small orders
   bids = orderbook.aggregate_levels(bids, min_size=0.001)
   asks = orderbook.aggregate_levels(asks, min_size=0.001)
   ```

2. **Real-time Processing**
   ```python
   # Update orderbook incrementally
   orderbook.update_level(
       side='bids',
       price=100.0,
       size=1.0,
       is_delete=False
   )
   
   # Get latest indicators
   current_state = orderbook.get_current_state()
   ```

3. **Analysis Integration**
   ```python
   # Combine with volume analysis
   result = await orderbook.calculate(market_data)
   volume_profile = volume.calculate_volume_profile(prices, volumes)
   
   # Generate combined signal
   signal = indicators.combine_signals([
       (result['score'], 0.6),
       (volume_profile, 0.4)
   ])
   ```

4. **Performance Monitoring**
   ```python
   # Track calculation time
   with timing.measure('orderbook_calculation'):
       result = await orderbook.calculate(market_data)
   
   # Get performance stats
   stats = timing.get_stats()
   print(f"Average calculation time: {stats['orderbook_calculation_avg']}")
   ```

## Integration Examples

### 1. With Order Flow Analysis
```python
# Combine orderbook and order flow
orderbook_result = await orderbook.calculate(market_data)
flow = await orderflow.calculate(trade_data)

# Analyze order pressure
pressure = analysis.combine_metrics(
    orderbook_score=orderbook_result['score'],
    flow_score=flow['score'],
    window=20
)
```

### 2. With Market Making
```python
# Use orderbook analysis for market making
orderbook_result = await orderbook.calculate(market_data)

# Generate quotes based on orderbook state
quotes = market_maker.generate_quotes(
    orderbook_score=orderbook_result['score'],
    components=orderbook_result['components'],
    raw_metrics=orderbook_result['metadata']['raw_values'],
    risk_factor=0.5
)
```

### 3. With Risk Management
```python
# Use orderbook metrics for risk assessment
orderbook_result = await orderbook.calculate(market_data)
liquidity_score = orderbook_result['components']['liquidity']
depth_score = orderbook_result['components']['depth']

# Adjust position size based on orderbook metrics
adjusted_size = risk.adjust_position_size(
    base_size=position_size,
    liquidity_score=liquidity_score,
    depth_score=depth_score
)
```
``` 