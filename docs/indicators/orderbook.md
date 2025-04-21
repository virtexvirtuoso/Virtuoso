# Orderbook Indicators

## Overview

The `OrderbookIndicators` class provides sophisticated tools for analyzing market microstructure through orderbook data. The indicators help identify market depth, liquidity, and potential price pressure points through a weighted scoring system.

## Component Weights

The orderbook analysis uses the following weighted components:

| Component | Weight | Description |
|-----------|--------|-------------|
| Imbalance | 25% | Buy/sell pressure imbalance in orderbook |
| MPI | 20% | Market Pressure Index with price sensitivity |
| Depth | 20% | Liquidity distribution analysis |
| Liquidity | 10% | Overall market liquidity metrics |
| Absorption/Exhaustion | 10% | Supply/demand absorption patterns |
| DOM Momentum | 5% | Depth of Market momentum |
| Spread | 5% | Bid-ask spread analysis |
| OBPS | 5% | Order Book Pressure Score |

## Available Indicators

### 1. Orderbook Imbalance
```python
def _calculate_orderbook_imbalance(
    market_data: Dict[str, Any]
) -> float:
    """Calculate enhanced orderbook imbalance.
    
    Args:
        market_data: Dictionary containing orderbook data
        
    Returns:
        Score 0-100 where:
        0 = extremely bearish (ask-heavy)
        50 = neutral
        100 = extremely bullish (bid-heavy)
        
    Calculation Methods:
    1. Calculate volume-weighted price levels
    2. Apply price sensitivity decay
    3. Compare bid/ask pressure
    4. Normalize using sigmoid transformation
    """
```

### 2. Market Pressure Index (MPI)
```python
def calculate_pressure(
    orderbook: Dict[str, Any]
) -> Dict[str, float]:
    """Calculate Market Pressure Index.
    
    Args:
        orderbook: Dictionary with bids and asks
        
    Returns:
        Dictionary containing:
        - score: Overall MPI score (0-100)
        - pressure: Raw pressure values
        - imbalance: Level imbalances
        
    Calculation Methods:
    1. Calculate price-weighted volume
    2. Analyze order clustering
    3. Measure price impact
    4. Score based on:
       - Volume concentration
       - Price sensitivity
       - Order distribution
    """
```

### 3. Absorption/Exhaustion Analysis
```python
def calculate_absorption_exhaustion(
    bids: np.ndarray,
    asks: np.ndarray
) -> Dict[str, float]:
    """Calculate supply/demand absorption.
    
    Args:
        bids: Numpy array of bid levels
        asks: Numpy array of ask levels
        
    Returns:
        Dictionary containing:
        - score: Overall score (0-100)
        - absorption: Supply/demand metrics
        - exhaustion: Market exhaustion signals
        
    Calculation Methods:
    1. Analyze order replenishment
    2. Track order removal patterns
    3. Detect absorption zones
    4. Score based on:
       - Order flow patterns
       - Volume absorption
       - Price reaction
    """
```

### 4. DOM Momentum
```python
def calculate_dom_momentum(
    current_bids: np.ndarray,
    current_asks: np.ndarray
) -> Dict[str, float]:
    """Calculate Depth of Market momentum.
    
    Args:
        current_bids: Current bid levels
        current_asks: Current ask levels
        
    Returns:
        Dictionary containing:
        - score: Overall momentum score
        - velocity: Order flow metrics
        - acceleration: Change in flow
        
    Calculation Methods:
    1. Track order book changes
    2. Calculate flow velocity
    3. Measure flow acceleration
    4. Score based on:
       - Flow direction
       - Flow strength
       - Flow consistency
    """
```

### 5. Spread Analysis
```python
def calculate_spread_score(
    bids: np.ndarray,
    asks: np.ndarray
) -> Dict[str, float]:
    """Calculate spread-based score.
    
    Args:
        bids: Numpy array of bid levels
        asks: Numpy array of ask levels
        
    Returns:
        Dictionary containing:
        - score: Overall spread score
        - relative_spread: Spread metrics
        - stability: Spread stability
        
    Calculation Methods:
    1. Calculate relative spread
    2. Compare to historical spread
    3. Analyze spread stability
    4. Score based on:
       - Current vs typical spread
       - Spread trend
       - Spread volatility
    """
```

## Configuration Parameters

```python
params = {
    # Depth parameters
    'depth_levels': 10,
    'imbalance_threshold': 1.5,
    'liquidity_threshold': 1.5,
    
    # Spread parameters
    'spread_factor': 2.0,
    'max_spread_bps': 50,
    'min_price_impact': 0.05,
    
    # Sigmoid transformation
    'sigmoid_transformation': {
        'default_sensitivity': 0.12,
        'imbalance_sensitivity': 0.15,
        'pressure_sensitivity': 0.18
    },
    
    # Moving averages
    'spread_ma_period': 20,
    'obps_depth': 10,
    'obps_decay': 0.85,
    
    # Alert thresholds
    'alerts': {
        'large_order_threshold_usd': 100000,
        'aggressive_price_threshold': 0.002,
        'cooldown': 60
    }
}
```

## Order Flow Analysis

### 1. Large Order Detection
```python
def detect_large_aggressive_orders(
    bids: np.ndarray,
    asks: np.ndarray,
    symbol: str
) -> Dict[str, Any]:
    """Detect large aggressive orders.
    
    Process:
    1. Track order size distribution
    2. Identify size anomalies
    3. Analyze price impact
    4. Generate alerts for:
       - Large single orders
       - Aggressive price moves
       - Order clustering
    """
```

### 2. Price Impact Analysis
```python
def _calculate_price_impact(
    orders: List[List[float]],
    size: float
) -> float:
    """Calculate price impact of order.
    
    Process:
    1. Walk the order book
    2. Calculate slippage
    3. Measure market impact
    4. Consider:
       - Order book depth
       - Available liquidity
       - Price sensitivity
    """
```

## Integration Examples

### 1. With Market Making
```python
# Calculate orderbook metrics
ob_metrics = orderbook.calculate_batch(
    market_data,
    indicators=['imbalance', 'pressure']
)

# Generate quotes
quotes = market_maker.generate_quotes(
    base_quotes=quotes,
    ob_metrics=ob_metrics,
    risk_factor=0.1
)
```

### 2. With Position Sizing
```python
# Use orderbook for position sizing
ob_state = orderbook.get_market_state()

# Calculate position size
position_size = position.calculate_size(
    base_size=1.0,
    ob_state=ob_state,
    risk_factor=0.1
)
```

### 3. With Risk Management
```python
# Monitor orderbook conditions
ob_metrics = orderbook.calculate_batch(
    market_data,
    indicators=['liquidity', 'spread']
)

# Update risk limits
risk_limits = risk.update_limits(
    base_limits=default_limits,
    ob_metrics=ob_metrics,
    market_data=market_data
)
```

## Best Practices

1. **Data Quality**
   ```python
   # Validate input data
   if not orderbook.validate_input(market_data):
       logger.warning("Insufficient data quality")
       return default_values
   ```

2. **Historical Context**
   ```python
   # Update historical metrics
   orderbook._update_historical_metrics(
       spread=current_spread,
       depth=current_depth
   )
   
   # Use typical values for comparison
   spread_ratio = current_spread / orderbook.typical_spread
   depth_ratio = current_depth / orderbook.typical_depth
   ```

3. **Performance Monitoring**
   ```python
   # Track calculation time
   with orderbook.timer('ob_analysis'):
       score = orderbook.calculate_score(market_data)
   
   # Log performance metrics
   stats = orderbook.get_performance_stats()
   logger.info(f"Average calculation time: {stats['avg_time']}")
   ```

4. **Component Analysis**
   ```python
   # Get detailed component breakdown
   components = orderbook.get_component_scores(market_data)
   
   # Log significant components
   for component, score in components.items():
       if abs(score - 50) > 20:  # Significant deviation
           logger.info(f"{component} showing strong signal: {score}")
   ```
``` 