# Orderflow Indicators

## Overview

The `OrderflowIndicators` class provides comprehensive tools for analyzing trade flow and market microstructure through time and sales data. The indicators help identify trading patterns, aggressive order flow, and potential price direction through a weighted scoring system.

## Component Weights

The orderflow analysis uses the following weighted components:

| Component | Weight | Description |
|-----------|--------|-------------|
| CVD | 25% | Cumulative Volume Delta (buy vs sell volume) |
| Trade Flow | 20% | Buy vs sell trade flow analysis |
| Imbalance | 15% | Orderbook imbalance metrics |
| Open Interest | 15% | Open interest analysis |
| Liquidity | 15% | Liquidity based on trade frequency/volume |
| Order Block | 10% | Order block analysis |

## Available Indicators

### 1. Cumulative Volume Delta (CVD)
```python
def _calculate_cvd(
    market_data: Dict[str, Any]
) -> float:
    """Calculate Cumulative Volume Delta score.
    
    Args:
        market_data: Dictionary containing trades data
        
    Returns:
        Score 0-100 based on:
        - Buy vs sell volume imbalance
        - Volume delta trend
        - Price-CVD divergence
        
    Calculation Methods:
    1. Calculate CVD = Σ(volume * side) where side is:
       - +1 for buys
       - -1 for sells
    2. Normalize by total volume
    3. Calculate trend and momentum
    4. Score based on:
       - CVD direction and strength
       - Recent momentum
       - Divergence with price
    """
```

### 2. Trade Flow Analysis
```python
def _calculate_trade_flow_score(
    market_data: Dict[str, Any]
) -> float:
    """Calculate trade flow score.
    
    Args:
        market_data: Dictionary containing trades data
        
    Returns:
        Score 0-100 based on:
        - Trade frequency
        - Trade size distribution
        - Trade direction
        
    Calculation Methods:
    1. Analyze trade frequency and size
    2. Calculate directional pressure
    3. Score based on:
       - Buy vs sell frequency
       - Large trade impact
       - Trade flow momentum
    """
```

### 3. Orderbook Imbalance
```python
def _calculate_imbalance_score(
    market_data: Dict[str, Any]
) -> float:
    """Calculate orderbook imbalance score.
    
    Args:
        market_data: Dictionary containing orderbook data
        
    Returns:
        Score 0-100 based on:
        - Bid/ask volume imbalance
        - Price level distribution
        - Order book depth
        
    Calculation Methods:
    1. Calculate bid/ask ratio
    2. Analyze price level concentration
    3. Score based on:
       - Volume imbalance
       - Price level distribution
       - Order book depth
    """
```

### 4. Open Interest Analysis
```python
def _calculate_open_interest_score(
    market_data: Dict[str, Any]
) -> float:
    """Calculate open interest score.
    
    Args:
        market_data: Dictionary containing OI data
        
    Returns:
        Score 0-100 based on:
        - OI trend
        - OI-price divergence
        - OI change rate
        
    Calculation Methods:
    1. Calculate OI trend
    2. Analyze OI-price relationship
    3. Score based on:
       - OI direction
       - OI-price alignment
       - Change magnitude
    """
```

### 5. Liquidity Analysis
```python
def _calculate_liquidity_score(
    market_data: Dict[str, Any]
) -> float:
    """Calculate liquidity score.
    
    Args:
        market_data: Dictionary containing market data
        
    Returns:
        Score 0-100 based on:
        - Trade frequency
        - Volume distribution
        - Market depth
        
    Calculation Methods:
    1. Analyze trade frequency
    2. Calculate volume distribution
    3. Score based on:
       - Trade frequency vs average
       - Volume concentration
       - Market depth ratio
    """
```

## Configuration Parameters

```python
params = {
    # CVD parameters
    'cvd_normalization': 'total_volume',
    'volume_threshold': 1.5,
    'flow_window': 20,
    
    # Divergence parameters
    'divergence_lookback': 20,
    'divergence_strength_threshold': 20.0,
    'divergence_impact': 0.2,
    'time_weighting_enabled': True,
    'recency_factor': 1.2,
    
    # Minimum requirements
    'min_trades': 100,
    
    # Timeframe weights
    'timeframe_weights': {
        'base': 0.4,  # 1-minute
        'ltf': 0.3,   # 5-minute
        'mtf': 0.2,   # 30-minute
        'htf': 0.1    # 4-hour
    },
    
    # Interpretation thresholds
    'thresholds': {
        'strong_buy': 70,
        'buy': 60,
        'neutral_high': 55,
        'neutral': 50,
        'neutral_low': 45,
        'sell': 40,
        'strong_sell': 30
    }
}
```

## Divergence Analysis

### Price-CVD Divergence
```python
def _calculate_price_cvd_divergence(
    market_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate price-CVD divergence.
    
    Process:
    1. Calculate price and CVD trends
    2. Identify divergent patterns
    3. Score divergence strength
    4. Apply time weighting
    
    Returns:
        Dictionary containing:
        - Divergence type
        - Strength score
        - Time factor
    """
```

### Price-OI Divergence
```python
def _calculate_price_oi_divergence(
    market_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate price-OI divergence.
    
    Process:
    1. Calculate price and OI trends
    2. Identify divergent patterns
    3. Score divergence strength
    4. Apply time weighting
    
    Returns:
        Dictionary containing:
        - Divergence type
        - Strength score
        - Time factor
    """
```

## Integration Examples

### 1. With Market Making
```python
# Calculate orderflow metrics
flow_metrics = orderflow.calculate_batch(
    market_data,
    indicators=['cvd', 'imbalance']
)

# Generate quotes
quotes = market_maker.generate_quotes(
    base_quotes=quotes,
    flow_metrics=flow_metrics,
    risk_factor=0.1
)
```

### 2. With Position Sizing
```python
# Use orderflow for position sizing
flow_state = orderflow.get_market_state()

# Calculate position size
position_size = position.calculate_size(
    base_size=1.0,
    flow_state=flow_state,
    risk_factor=0.1
)
```

### 3. With Risk Management
```python
# Monitor orderflow conditions
flow_metrics = orderflow.calculate_batch(
    market_data,
    indicators=['liquidity', 'imbalance']
)

# Update risk limits
risk_limits = risk.update_limits(
    base_limits=default_limits,
    flow_metrics=flow_metrics,
    market_data=market_data
)
```

## Best Practices

1. **Data Quality**
   ```python
   # Validate input data
   if not orderflow.validate_input(market_data):
       logger.warning("Insufficient data quality")
       return default_values
   ```

2. **Timeframe Analysis**
   ```python
   # Analyze across timeframes
   scores = {}
   for tf in ['base', 'ltf', 'mtf', 'htf']:
       scores[tf] = orderflow.calculate_score(data[tf])
       
   # Apply timeframe weights
   final_score = sum(
       score * orderflow.timeframe_weights[tf]
       for tf, score in scores.items()
   )
   ```

3. **Performance Monitoring**
   ```python
   # Track calculation time
   with orderflow.timer('flow_analysis'):
       score = orderflow.calculate_score(market_data)
   
   # Log performance metrics
   stats = orderflow.get_performance_stats()
   logger.info(f"Average calculation time: {stats['avg_time']}")
   ```

4. **Component Analysis**
   ```python
   # Get detailed component breakdown
   components = orderflow.get_component_scores(market_data)
   
   # Log significant components
   for component, score in components.items():
       if abs(score - 50) > 20:  # Significant deviation
           logger.info(f"{component} showing strong signal: {score}")
   ```
``` 