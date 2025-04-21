# Volume Indicators

## Overview

The `VolumeIndicators` class provides comprehensive tools for analyzing trading volume patterns and price-volume relationships. The indicators help identify trading activity intensity, buying/selling pressure, and potential trend reversals through a weighted scoring system.

## Component Weights

The volume analysis uses the following weighted components:

| Component | Weight | Description |
|-----------|--------|-------------|
| Volume Delta | 25% | Measures change in volume over time |
| ADL (Accumulation/Distribution Line) | 20% | Tracks buying/selling pressure |
| CMF (Chaikin Money Flow) | 15% | Measures money flow volume |
| Relative Volume | 20% | Compares current volume to historical |
| OBV (On-Balance Volume) | 20% | Cumulative volume flow indicator |

## Available Indicators

### 1. Volume Delta
```python
def calculate_volume_delta(
    trades_df: pd.DataFrame,
    price_df: pd.DataFrame = None,
    window: int = None
) -> Dict[str, float]:
    """Calculate volume delta and divergence.
    
    Args:
        trades_df: DataFrame with trade data
        price_df: Optional price data for divergence
        window: Lookback window (default: 20)
        
    Returns:
        Dictionary with:
        - volume_delta: Normalized volume change (-1 to 1)
        - divergence: Price-volume divergence score
    
    Calculation:
    1. Calculate rolling volume mean
    2. Compare current volume to mean
    3. Normalize using sigmoid function
    4. Calculate price-volume correlation for divergence
    """
```

### 2. Accumulation/Distribution Line (ADL)
```python
def calculate_adl(
    df: pd.DataFrame
) -> pd.Series:
    """Calculate Accumulation/Distribution Line.
    
    Args:
        df: OHLCV DataFrame
        
    Returns:
        Series with ADL values
    
    Calculation:
    1. Money Flow Multiplier = ((Close - Low) - (High - Close)) / (High - Low)
    2. Money Flow Volume = Multiplier * Volume
    3. ADL = Previous ADL + Current Money Flow Volume
    """
```

### 3. Chaikin Money Flow (CMF)
```python
def calculate_cmf(
    df: pd.DataFrame,
    period: int = 20,
    smoothing: float = 0.5
) -> pd.Series:
    """Calculate Chaikin Money Flow.
    
    Args:
        df: OHLCV DataFrame
        period: Calculation period
        smoothing: EMA smoothing factor
        
    Returns:
        Series with CMF values
    
    Calculation:
    1. Money Flow Multiplier = ((Close - Low) - (High - Close)) / (High - Low)
    2. Money Flow Volume = Multiplier * Volume
    3. CMF = SMA(Money Flow Volume) / SMA(Volume)
    4. Optional: Apply EMA smoothing
    """
```

### 4. Relative Volume
```python
def calculate_relative_volume(
    df: pd.DataFrame,
    period: int = 20
) -> pd.Series:
    """Calculate relative volume ratio.
    
    Args:
        df: OHLCV DataFrame
        period: Lookback period
        
    Returns:
        Series with relative volume values
    
    Calculation:
    1. Calculate average volume over period
    2. Ratio = Current Volume / Average Volume
    3. Normalize using log scale for better distribution
    """
```

### 5. On-Balance Volume (OBV)
```python
def calculate_obv(
    df: pd.DataFrame
) -> pd.Series:
    """Calculate On-Balance Volume.
    
    Args:
        df: OHLCV DataFrame
        
    Returns:
        Series with OBV values
    
    Calculation:
    1. If close > prev_close: OBV = prev_OBV + volume
    2. If close < prev_close: OBV = prev_OBV - volume
    3. If close = prev_close: OBV = prev_OBV
    """
```

## Configuration Parameters

```python
params = {
    # Volume delta parameters
    'volume_delta_lookback': 20,      # Lookback period for volume delta
    'volume_delta_threshold': 1.5,    # Threshold for significant volume delta
    'volume_delta_smoothing': 5,      # Smoothing period for volume delta
    
    # CMF parameters
    'cmf_period': 20,                 # Lookback period for CMF
    'cmf_smoothing': 0.5,             # Smoothing factor for CMF
    
    # ADL parameters
    'adl_lookback': 20,               # Lookback period for ADL trend
    
    # OBV parameters
    'obv_lookback': 20,               # Lookback period for OBV
    'obv_smoothing': 5,               # Smoothing period for OBV
    
    # Relative volume parameters
    'rel_vol_period': 20,             # Period for relative volume comparison
    'rel_vol_threshold': 1.5,         # Threshold for significant volume increase
    
    # Minimum data requirements
    'min_base_candles': 100,          # Minimum candles for base timeframe
    'min_ltf_candles': 50,            # Minimum candles for LTF
    'min_mtf_candles': 50,            # Minimum candles for MTF
    'min_htf_candles': 20,            # Minimum candles for HTF
    'min_trades': 1000                # Minimum trades for reliable analysis
}
```

## Timeframe Analysis

The indicator analyzes volume across multiple timeframes with the following weights:

| Timeframe | Weight | Description |
|-----------|--------|-------------|
| Base | 50% | Primary analysis timeframe |
| LTF | 15% | Lower timeframe for short-term volume patterns |
| MTF | 20% | Medium timeframe for trend confirmation |
| HTF | 15% | Higher timeframe for overall context |

## Signal Generation

### Volume-Based Signals
```python
async def get_signals(
    market_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate trading signals based on volume analysis.
    
    Returns:
        Dictionary containing:
        - score: Overall volume score (0-100)
        - signals: Dictionary of component signals
        - confidence: Signal confidence level
        - metadata: Additional analysis data
    """
```

### Divergence Detection
```python
def _calculate_volume_divergence_bonus(
    df: pd.DataFrame
) -> Dict[str, float]:
    """Detect and score volume-price divergences.
    
    Calculation:
    1. Calculate price and volume trends
    2. Identify divergent patterns
    3. Score divergence strength
    4. Apply bonus/penalty to component scores
    """
```

## Performance Optimization

### 1. Data Validation
```python
def validate_input(data: Dict[str, Any]) -> bool:
    """Validate input data completeness and quality.
    
    Checks:
    1. Required timeframes present
    2. Minimum candle requirements
    3. Data quality and consistency
    4. Required fields present
    """
```

### 2. Caching
- Implements smart caching for repeated calculations
- Cache invalidation based on data updates
- Configurable TTL for different components

### 3. Error Handling
```python
@handle_calculation_error(default_value=pd.Series(dtype=float))
def calculate_indicator(df: pd.DataFrame) -> pd.Series:
    """
    Decorator provides:
    1. Graceful error handling
    2. Default values on failure
    3. Error logging and tracking
    4. Performance monitoring
    """
```

## Integration Examples

### 1. With Order Flow Analysis
```python
# Combine volume and order flow analysis
volume_score = await volume.calculate_score(market_data)
flow_score = await orderflow.calculate_score(market_data)

# Generate combined signal
signal = {
    'score': 0.7 * volume_score + 0.3 * flow_score,
    'volume_confidence': volume.get_confidence(),
    'flow_confidence': flow.get_confidence()
}
```

### 2. With Position Sizing
```python
# Use volume analysis for position sizing
volume_metrics = volume.calculate_batch(
    market_data,
    indicators=['relative_volume', 'volume_delta']
)

# Calculate position size
position_size = position.calculate_size(
    base_size=1.0,
    volume_metrics=volume_metrics,
    risk_factor=0.1
)
```

### 3. With Risk Management
```python
# Adjust risk limits based on volume conditions
volume_state = volume.get_market_state()

risk_limits = risk.calculate_limits(
    base_limits=default_limits,
    volume_state=volume_state,
    market_data=market_data
)
```

## Best Practices

1. **Data Quality**
   ```python
   # Clean and validate input data
   data = volume.clean_data(raw_data)
   if not volume.validate_input(data):
       logger.warning("Insufficient data quality")
       return default_values
   ```

2. **Timeframe Analysis**
   ```python
   # Analyze across timeframes
   scores = {}
   for tf in ['base', 'ltf', 'mtf', 'htf']:
       scores[tf] = volume.calculate_score(data[tf])
       
   # Apply timeframe weights
   final_score = sum(
       score * volume.timeframe_weights[tf]
       for tf, score in scores.items()
   )
   ```

3. **Performance Monitoring**
   ```python
   # Track calculation performance
   with volume.timer('volume_analysis'):
       score = volume.calculate_score(market_data)
   
   # Log performance metrics
   stats = volume.get_performance_stats()
   logger.info(f"Average calculation time: {stats['avg_time']}")
   ```

4. **Component Analysis**
   ```python
   # Get detailed component breakdown
   components = volume.get_component_scores(market_data)
   
   # Log significant components
   for component, score in components.items():
       if abs(score - 50) > 20:  # Significant deviation
           logger.info(f"{component} showing strong signal: {score}")
   ``` 