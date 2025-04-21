# Technical Momentum Indicators

## Overview

The `TechnicalIndicators` class provides comprehensive technical analysis tools for analyzing market momentum, trends, and generating trading signals. The indicators help identify trend direction, strength, and potential reversal points through a weighted scoring system.

## Component Weights

The technical analysis uses the following weighted components:

| Component | Weight | Description |
|-----------|--------|-------------|
| RSI | 20% | Relative Strength Index |
| AO | 20% | Awesome Oscillator |
| MACD | 15% | Moving Average Convergence Divergence |
| Williams %R | 15% | Williams Percent Range |
| ATR | 15% | Average True Range |
| CCI | 15% | Commodity Channel Index |

## Available Indicators

### 1. Relative Strength Index (RSI)
```python
def calculate_rsi_score(
    df: pd.DataFrame,
    timeframe: str = 'base'
) -> float:
    """Calculate RSI score.
    
    Args:
        df: OHLCV DataFrame
        timeframe: Analysis timeframe
        
    Returns:
        Score 0-100 where:
        - 0-30: Oversold (bullish)
        - 30-70: Neutral
        - 70-100: Overbought (bearish)
        
    Calculation:
    1. Calculate RSI using 14-period lookback
    2. Convert RSI to score:
       - RSI > 70: Score decreases as RSI increases (bearish)
       - RSI < 30: Score increases as RSI decreases (bullish)
       - RSI 30-70: Linear mapping around 50
    """
```

### 2. Moving Average Convergence Divergence (MACD)
```python
def calculate_macd_score(
    df: pd.DataFrame,
    timeframe: str = 'base'
) -> float:
    """Calculate MACD score.
    
    Args:
        df: OHLCV DataFrame
        timeframe: Analysis timeframe
        
    Returns:
        Score 0-100 based on:
        - MACD vs Signal line crossovers
        - MACD histogram strength
        - Zero line crossovers
        
    Parameters:
        - Fast Period: 12
        - Slow Period: 26
        - Signal Period: 9
        
    Calculation:
    1. Calculate MACD line = EMA(12) - EMA(26)
    2. Calculate Signal line = EMA(9) of MACD
    3. Calculate Histogram = MACD - Signal
    4. Score based on:
       - MACD/Signal crossovers (+/-15 points)
       - Zero line crossovers (+/-20 points)
       - Histogram strength and direction
    """
```

### 3. Awesome Oscillator (AO)
```python
def calculate_ao_score(
    df: pd.DataFrame,
    timeframe: str = 'base'
) -> float:
    """Calculate Awesome Oscillator score.
    
    Args:
        df: OHLCV DataFrame
        timeframe: Analysis timeframe
        
    Returns:
        Score 0-100 based on:
        - AO value and direction
        - Zero line crossovers
        - Saucer patterns
        
    Calculation:
    1. Calculate median price = (High + Low) / 2
    2. AO = SMA(5) - SMA(34) of median price
    3. Score based on:
       - AO direction and strength
       - Zero line crossovers (+/-20 points)
       - Recent momentum changes
    """
```

### 4. Williams %R
```python
def calculate_williams_r_score(
    df: pd.DataFrame,
    timeframe: str = 'base'
) -> float:
    """Calculate Williams %R score.
    
    Args:
        df: OHLCV DataFrame
        timeframe: Analysis timeframe
        
    Returns:
        Score 0-100 where:
        - 0-20: Oversold (bullish)
        - 20-80: Neutral
        - 80-100: Overbought (bearish)
        
    Calculation:
    1. Calculate highest high and lowest low over period
    2. Williams %R = (Highest High - Close) / (Highest High - Lowest Low) * -100
    3. Convert to 0-100 score
    """
```

### 5. Average True Range (ATR)
```python
def calculate_atr_score(
    df: pd.DataFrame,
    timeframe: str = 'base'
) -> float:
    """Calculate ATR score.
    
    Args:
        df: OHLCV DataFrame
        timeframe: Analysis timeframe
        
    Returns:
        Score 0-100 based on:
        - ATR value relative to recent history
        - ATR trend direction
        
    Calculation:
    1. Calculate True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
    2. ATR = EMA(14) of True Range
    3. Score based on:
       - ATR level vs recent average
       - ATR trend direction
       - Volatility expansion/contraction
    """
```

### 6. Commodity Channel Index (CCI)
```python
def calculate_cci_score(
    df: pd.DataFrame,
    timeframe: str = 'base'
) -> float:
    """Calculate CCI score.
    
    Args:
        df: OHLCV DataFrame
        timeframe: Analysis timeframe
        
    Returns:
        Score 0-100 where:
        - 0-30: Oversold (bullish)
        - 30-70: Neutral
        - 70-100: Overbought (bearish)
        
    Calculation:
    1. Calculate Typical Price = (High + Low + Close) / 3
    2. Calculate Mean Deviation
    3. CCI = (Typical Price - SMA(20)) / (0.015 * Mean Deviation)
    4. Convert CCI to normalized score
    """
```

## Timeframe Analysis

The indicator analyzes momentum across multiple timeframes with the following weights:

| Timeframe | Weight | Description |
|-----------|--------|-------------|
| Base (1m) | 40% | Primary analysis timeframe |
| LTF (5m) | 30% | Lower timeframe for short-term signals |
| MTF (30m) | 20% | Medium timeframe for trend confirmation |
| HTF (4h) | 10% | Higher timeframe for overall context |

## Divergence Analysis

### Timeframe Divergence Detection
```python
def analyze_timeframe_divergences(
    base_ohlcv: pd.DataFrame,
    ltf_ohlcv: pd.DataFrame,
    mtf_ohlcv: pd.DataFrame,
    htf_ohlcv: pd.DataFrame,
    indicators_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Analyze divergences between timeframes.
    
    Detects:
    1. MACD divergences (+/-10 points)
    2. AO divergences (+/-10 points)
    3. RSI divergences (+/-10 points)
    4. CCI divergences (+/-10 points)
    5. Williams %R divergences (+/-10 points)
    6. ATR divergences (+/-5 points)
    
    Returns:
        Dictionary containing:
        - Bullish divergences
        - Bearish divergences
        - Score adjustments
    """
```

## Configuration Parameters

```python
params = {
    # RSI parameters
    'rsi_period': 14,
    
    # MACD parameters
    'macd_fast_period': 12,
    'macd_slow_period': 26,
    'macd_signal_period': 9,
    
    # AO parameters
    'ao_fast': 5,
    'ao_slow': 34,
    
    # Williams %R parameters
    'williams_period': 14,
    
    # ATR parameters
    'atr_period': 14,
    
    # CCI parameters
    'cci_period': 20,
    
    # Divergence parameters
    'divergence_impact': 0.2,
    'divergence_lookback': 14
}
```

## Signal Generation

### Component Signals
```python
def calculate_component_scores(
    data: Dict[str, Any]
) -> Dict[str, float]:
    """Calculate component scores from timeframe scores.
    
    Process:
    1. Calculate individual indicator scores
    2. Apply timeframe weights
    3. Detect divergences
    4. Apply divergence adjustments
    5. Calculate final weighted score
    
    Returns:
        Dictionary with final component scores
    """
```

### Divergence Signals
```python
def apply_divergence_adjustments(
    component_scores: Dict[str, float],
    divergence_data: Dict[str, Any]
) -> Dict[str, float]:
    """Apply divergence adjustments to scores.
    
    Process:
    1. Identify divergences between timeframes
    2. Calculate adjustment magnitudes
    3. Apply adjustments to base scores
    4. Ensure scores remain in valid range
    
    Returns:
        Adjusted component scores
    """
```

## Integration Examples

### 1. With Position Sizing
```python
# Calculate technical scores
tech_scores = technical.calculate_batch(
    market_data,
    indicators=['rsi', 'macd', 'ao']
)

# Calculate position size
position_size = position.calculate_size(
    base_size=1.0,
    tech_scores=tech_scores,
    risk_factor=0.1
)
```

### 2. With Risk Management
```python
# Monitor technical conditions
tech_state = technical.get_market_state()

# Update risk limits
risk_limits = risk.update_limits(
    base_limits=default_limits,
    tech_state=tech_state,
    market_data=market_data
)
```

### 3. With Order Flow
```python
# Combine technical and flow analysis
tech_score = technical.calculate_score(market_data)
flow_score = orderflow.calculate_score(market_data)

# Generate combined signal
signal = {
    'score': 0.6 * tech_score + 0.4 * flow_score,
    'tech_confidence': technical.get_confidence(),
    'flow_confidence': flow.get_confidence()
}
```

## Best Practices

1. **Data Quality**
   ```python
   # Validate input data
   if not technical.validate_input(market_data):
       logger.warning("Insufficient data quality")
       return default_values
   ```

2. **Timeframe Analysis**
   ```python
   # Analyze across timeframes
   scores = {}
   for tf in ['base', 'ltf', 'mtf', 'htf']:
       scores[tf] = technical.calculate_score(data[tf])
       
   # Apply timeframe weights
   final_score = sum(
       score * technical.timeframe_weights[tf]
       for tf, score in scores.items()
   )
   ```

3. **Performance Monitoring**
   ```python
   # Track calculation time
   with technical.timer('technical_analysis'):
       score = technical.calculate_score(market_data)
   
   # Log performance metrics
   stats = technical.get_performance_stats()
   logger.info(f"Average calculation time: {stats['avg_time']}")
   ```

4. **Component Analysis**
   ```python
   # Get detailed component breakdown
   components = technical.get_component_scores(market_data)
   
   # Log significant components
   for component, score in components.items():
       if abs(score - 50) > 20:  # Significant deviation
           logger.info(f"{component} showing strong signal: {score}")
   ``` 