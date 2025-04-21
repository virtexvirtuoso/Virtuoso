# Position Indicators

## Overview

The `PositionIndicators` class provides sophisticated tools for analyzing and managing trading positions, risk metrics, and portfolio performance. These indicators help optimize position sizing, manage risk exposure, and track performance metrics across multiple positions through a weighted scoring system.

## Component Weights

The position analysis uses the following weighted components:

| Component | Weight | Description |
|-----------|--------|-------------|
| Risk Metrics | 30% | Position-level risk measurements |
| Exposure Analysis | 25% | Portfolio exposure and concentration |
| Performance Metrics | 25% | Historical and current performance |
| Position Health | 20% | Overall position quality indicators |

## Available Indicators

### 1. Position Risk Metrics
```python
def calculate_position_risk(
    position: pd.Series,
    prices: pd.Series,
    volatility: pd.Series,
    risk_free_rate: float = 0.02
) -> pd.DataFrame:
    """Calculate comprehensive position risk metrics.
    
    Args:
        position: Series with position sizes
        prices: Price series
        volatility: Volatility series
        risk_free_rate: Annual risk-free rate
        
    Returns:
        DataFrame with risk metrics including:
        - Value at Risk (VaR)
        - Expected Shortfall (ES)
        - Beta
        - Position Delta
        - Position Gamma
        - Position Vega
        - Position Theta
        
    Calculation Methods:
    1. VaR: Historical simulation and parametric methods
    2. ES: Average of losses beyond VaR
    3. Greeks: First and second-order sensitivities
    4. Beta: Rolling regression against market
    """
```

### 2. Portfolio Exposure Analysis
```python
def calculate_exposure(
    positions: pd.DataFrame,
    prices: pd.DataFrame,
    group_by: str = None
) -> pd.DataFrame:
    """Calculate detailed portfolio exposure metrics.
    
    Args:
        positions: DataFrame with positions
        prices: Price data for positions
        group_by: Group exposure by category
        
    Returns:
        DataFrame with exposure metrics including:
        - Gross Exposure
        - Net Exposure
        - Long/Short Ratio
        - Concentration Metrics
        - Sector/Asset Exposures
        
    Calculation Methods:
    1. Gross Exposure = Sum of absolute position values
    2. Net Exposure = Sum of signed position values
    3. Concentration = Herfindahl-Hirschman Index
    4. Category Exposure = Grouped position sums
    """
```

### 3. Position Performance Analysis
```python
def calculate_performance(
    positions: pd.DataFrame,
    prices: pd.DataFrame,
    include_fees: bool = True
) -> pd.DataFrame:
    """Calculate comprehensive position performance metrics.
    
    Args:
        positions: DataFrame with positions
        prices: Price data for positions
        include_fees: Whether to include trading fees
        
    Returns:
        DataFrame with performance metrics including:
        - Realized P&L
        - Unrealized P&L
        - Sharpe Ratio
        - Sortino Ratio
        - Max Drawdown
        - Win Rate
        
    Calculation Methods:
    1. P&L = Sum(Position * Price Change)
    2. Sharpe = (Return - Risk Free) / Volatility
    3. Sortino = (Return - Risk Free) / Downside Vol
    4. Max Drawdown = Max(Peak - Trough) / Peak
    """
```

## Configuration Parameters

```python
params = {
    # Risk parameters
    'var_confidence': 0.99,        # VaR confidence level
    'es_confidence': 0.975,        # ES confidence level
    'lookback_window': 252,        # Risk calculation window
    'decay_factor': 0.94,         # EWMA decay factor
    
    # Exposure parameters
    'max_gross_exposure': 3.0,     # Maximum gross exposure
    'max_net_exposure': 2.0,       # Maximum net exposure
    'concentration_limit': 0.2,    # Single position limit
    
    # Performance parameters
    'performance_window': 252,     # Performance calculation window
    'min_trades': 30,             # Minimum trades for statistics
    
    # Position sizing parameters
    'position_limit': 0.1,        # Maximum position size
    'risk_limit': 0.02,          # Maximum position risk
    
    # Other parameters
    'min_history': 100,           # Minimum price history
    'correlation_window': 63,     # Correlation calculation window
    'rebalance_threshold': 0.1    # Rebalancing trigger threshold
}
```

## Risk Management Framework

### 1. Position-Level Risk Controls
```python
def check_position_limits(
    position: pd.Series,
    risk_metrics: pd.DataFrame
) -> Dict[str, bool]:
    """Check position against risk limits.
    
    Checks:
    1. Position Size vs Limits
    2. Risk Metrics vs Thresholds
    3. Concentration Limits
    4. Drawdown Limits
    """
```

### 2. Portfolio-Level Risk Controls
```python
def check_portfolio_limits(
    positions: pd.DataFrame,
    risk_metrics: pd.DataFrame
) -> Dict[str, bool]:
    """Check portfolio against risk limits.
    
    Checks:
    1. Gross/Net Exposure
    2. Portfolio VaR
    3. Sector Exposure
    4. Portfolio Beta
    """
```

## Position Sizing Framework

### 1. Risk-Based Sizing
```python
def calculate_risk_based_size(
    price: float,
    volatility: float,
    portfolio_value: float,
    risk_target: float = 0.02
) -> float:
    """Calculate position size based on risk.
    
    Method:
    1. Size = Risk Target / (Price * Volatility)
    2. Apply portfolio value scaling
    3. Apply concentration limits
    """
```

### 2. Kelly Criterion Sizing
```python
def calculate_kelly_size(
    win_rate: float,
    win_loss_ratio: float,
    kelly_fraction: float = 0.5
) -> float:
    """Calculate Kelly Criterion position size.
    
    Method:
    1. Kelly = (p*b - q) / b
    where:
    - p = win probability
    - q = loss probability
    - b = win/loss ratio
    2. Apply fractional Kelly
    """
```

## Performance Monitoring

### 1. Position Monitoring
```python
def monitor_positions(
    positions: pd.DataFrame,
    risk_metrics: pd.DataFrame,
    thresholds: Dict[str, float]
) -> pd.DataFrame:
    """Monitor individual position health.
    
    Metrics:
    1. Profit Factor
    2. Risk-Adjusted Return
    3. Information Ratio
    4. Position Drift
    """
```

### 2. Portfolio Monitoring
```python
def monitor_portfolio(
    positions: pd.DataFrame,
    risk_metrics: pd.DataFrame
) -> Dict[str, float]:
    """Monitor overall portfolio health.
    
    Metrics:
    1. Portfolio Sharpe
    2. Diversification Score
    3. Risk Contribution
    4. Style Exposure
    """
```

## Integration Examples

### 1. With Order Management
```python
# Calculate position size
risk_metrics = position.calculate_position_risk(
    current_position,
    prices,
    volatility
)

# Generate order size
order_size = order_manager.calculate_order_size(
    risk_metrics=risk_metrics,
    portfolio_value=portfolio_value,
    risk_target=0.02
)
```

### 2. With Risk Management
```python
# Monitor position risk
risk_metrics = position.calculate_position_risk(
    positions,
    prices,
    volatility
)

# Update risk limits
risk_limits = risk.update_limits(
    risk_metrics=risk_metrics,
    market_state=market_state,
    portfolio_value=portfolio_value
)
```

### 3. With Portfolio Optimization
```python
# Calculate position metrics
performance = position.calculate_performance(positions, prices)
risk = position.calculate_position_risk(positions, prices, vol)

# Optimize weights
weights = optimizer.optimize_weights(
    performance_metrics=performance,
    risk_metrics=risk,
    constraints={'max_weight': 0.2}
)
```

## Best Practices

1. **Risk Management**
   ```python
   # Regular risk checks
   risk_metrics = position.calculate_position_risk(pos, prices, vol)
   if not position.check_risk_limits(risk_metrics):
       position.reduce_risk_exposure(pos, risk_metrics)
   ```

2. **Position Monitoring**
   ```python
   # Monitor position health
   health = position.monitor_positions(positions, risk_metrics)
   for pos_id, metrics in health.items():
       if metrics['health_score'] < threshold:
           logger.warning(f"Position {pos_id} requires attention")
   ```

3. **Portfolio Balance**
   ```python
   # Check portfolio balance
   exposure = position.calculate_exposure(positions, prices)
   if exposure['concentration'] > limits['concentration']:
       position.rebalance_portfolio(positions, target_weights)
   ```

4. **Performance Analysis**
   ```python
   # Track performance metrics
   performance = position.calculate_performance(positions, prices)
   position.log_performance_metrics(
       performance,
       frequency='daily',
       include_risk=True
   )
   ```

# Price Structure Indicators

## Overview

The `PriceStructureIndicators` class provides sophisticated tools for analyzing market structure and price action to identify key levels, trends, and potential reversal points. The analysis is based on the Market Prism Concept, focusing on market structure and price action rather than actual trading positions.

## Component Weights

The price structure analysis uses the following weighted components:

| Component | Weight | Description |
|-----------|--------|-------------|
| Order Block | 15% | Significant supply/demand zones and institutional blocks |
| Volume Profile | 25% | Volume distribution and price acceptance/rejection |
| VWAP | 20% | Volume-Weighted Average Price analysis |
| Composite Value | 15% | Price relative to key value indicators |
| Support/Resistance | 10% | Key price reaction levels |
| Market Structure | 15% | Swing points and structural patterns |

## Available Indicators

### 1. Support/Resistance Levels
```python
def analyze_sr_levels(
    ohlcv_data: Dict[str, pd.DataFrame]
) -> float:
    """Analyze support/resistance levels.
    
    Args:
        ohlcv_data: Dictionary of OHLCV DataFrames by timeframe
        
    Returns:
        Score 0-100 based on:
        - Proximity to key levels
        - Level strength
        - Level alignment
        
    Calculation Methods:
    1. Find swing points using zigzag algorithm
    2. Group levels within 0.5% range
    3. Filter levels within 20% of current price
    4. Score based on:
       - Distance to nearest level
       - Level strength (volume/time)
       - Level alignment across timeframes
    """
```

### 2. Order Block Analysis
```python
def analyze_orderblock_zones(
    ohlcv_data: Dict[str, pd.DataFrame]
) -> float:
    """Analyze order block zones.
    
    Args:
        ohlcv_data: Dictionary of OHLCV DataFrames by timeframe
        
    Returns:
        Score 0-100 based on:
        - Proximity to order blocks
        - Block strength
        - Block type (bullish/bearish)
        
    Calculation Methods:
    1. Identify strong moves with preceding consolidation
    2. Calculate block strength based on:
       - Volume expansion
       - Price range expansion
       - Time in consolidation
    3. Score based on:
       - Distance to nearest blocks
       - Block strength
       - Block type alignment
    """
```

### 3. Volume Profile Analysis
```python
def calculate_volume_profile_score(
    df: pd.DataFrame
) -> float:
    """Calculate volume profile score.
    
    Args:
        df: OHLCV DataFrame
        
    Returns:
        Score 0-100 based on:
        - Position relative to POC
        - Value area location
        - Volume node strength
        
    Calculation Methods:
    1. Calculate adaptive bin size based on volatility
    2. Create volume profile using TPO-style analysis
    3. Identify POC and value area (70% of volume)
    4. Score based on:
       - Price position in value area
       - Distance from POC
       - Volume node strength
    """
```

### 4. Market Structure Analysis
```python
def analyze_market_structure(
    ohlcv_data: Dict[str, pd.DataFrame]
) -> float:
    """Analyze market structure patterns.
    
    Args:
        ohlcv_data: Dictionary of OHLCV DataFrames by timeframe
        
    Returns:
        Score 0-100 based on:
        - Higher highs/lower lows
        - Swing point patterns
        - Structure breaks
        
    Calculation Methods:
    1. Identify swing points using adaptive window
    2. Analyze recent swing patterns (last 3)
    3. Calculate trend strength using EMAs
    4. Score based on:
       - Structure type (bullish/bearish)
       - Structure strength
       - EMA alignment
    """
```

### 5. Composite Value Analysis
```python
def calculate_composite_value(
    df: pd.DataFrame
) -> Dict[str, Any]:
    """Calculate composite value score.
    
    Args:
        df: OHLCV DataFrame
        
    Returns:
        Dictionary containing:
        - Score (0-100)
        - Component scores
        - Raw metrics
        
    Calculation Methods:
    1. Calculate VWAP
    2. Calculate moving averages (20, 50)
    3. Score based on:
       - Price vs VWAP (40% weight)
       - Price vs MAs (30% each)
       - Recent price action
    """
```

## Configuration Parameters

```python
params = {
    # Order block parameters
    'order_block_lookback': 20,
    
    # Volume profile parameters
    'volume_profile_bins': 100,
    'value_area_volume': 0.7,
    
    # Market structure parameters
    'swing_point_threshold': 0.003,
    'structure_lookback': 20,
    
    # Timeframe weights
    'timeframe_weights': {
        'base': 0.4,  # 1-minute
        'ltf': 0.3,   # 5-minute
        'mtf': 0.2,   # 30-minute
        'htf': 0.1    # 4-hour
    },
    
    # Validation requirements
    'min_base_candles': 100,
    'min_ltf_candles': 50,
    'min_mtf_candles': 50,
    'min_htf_candles': 50
}
```

## Market Structure Analysis

### 1. Swing Point Detection
```python
def _identify_swing_points(
    df: pd.DataFrame
) -> Dict[str, float]:
    """Identify swing points with divergence confirmation.
    
    Process:
    1. Calculate base swing levels
    2. Calculate divergence confirmation
    3. Apply divergence bonus
    4. Return swing points and scores
    """
```

### 2. Structure Type Analysis
```python
def _calculate_structural_score(
    df: pd.DataFrame
) -> float:
    """Calculate structural score based on price action.
    
    Process:
    1. Analyze local structure (highs/lows)
    2. Detect structure breaks
    3. Calculate break strength
    4. Score based on pattern type and strength
    """
```

## Volume Analysis

### 1. Volume Node Analysis
```python
def _calculate_volume_node_score(
    df: pd.DataFrame
) -> float:
    """Calculate score based on volume nodes.
    
    Process:
    1. Calculate volume profile with granular bins
    2. Identify high/low volume nodes
    3. Calculate node strength and proximity
    4. Score based on:
       - Node type (HVN/LVN)
       - Node strength
       - Price position
    """
```

### 2. Value Area Analysis
```python
def _calculate_value_area_score(
    df: pd.DataFrame
) -> float:
    """Calculate value area score.
    
    Process:
    1. Calculate value area levels
    2. Analyze price alignment
    3. Score based on:
       - Position in value area
       - Level alignment
       - Volume concentration
    """
```

## Integration Examples

### 1. With Order Flow Analysis
```python
# Combine structure and flow analysis
structure = price_structure.calculate_score(market_data)
flow = orderflow.calculate_score(market_data)

# Generate combined signal
signal = {
    'score': 0.7 * structure + 0.3 * flow,
    'structure_confidence': structure.get_confidence(),
    'flow_confidence': flow.get_confidence()
}
```

### 2. With Position Sizing
```python
# Use structure analysis for position sizing
structure_metrics = price_structure.calculate_batch(
    market_data,
    indicators=['order_blocks', 'market_structure']
)

# Calculate position size
position_size = position.calculate_size(
    base_size=1.0,
    structure_metrics=structure_metrics,
    risk_factor=0.1
)
```

### 3. With Risk Management
```python
# Monitor market structure
structure_state = price_structure.get_market_state()

# Update risk limits
risk_limits = risk.update_limits(
    base_limits=default_limits,
    structure_state=structure_state,
    market_data=market_data
)
```

## Best Practices

1. **Data Quality**
   ```python
   # Validate input data
   if not price_structure.validate_input(market_data):
       logger.warning("Insufficient data quality")
       return default_values
   ```

2. **Timeframe Analysis**
   ```python
   # Analyze across timeframes
   scores = {}
   for tf in ['base', 'ltf', 'mtf', 'htf']:
       scores[tf] = price_structure.calculate_score(data[tf])
       
   # Apply timeframe weights
   final_score = sum(
       score * price_structure.timeframe_weights[tf]
       for tf, score in scores.items()
   )
   ```

3. **Performance Monitoring**
   ```python
   # Track calculation time
   with price_structure.timer('structure_analysis'):
       score = price_structure.calculate_score(market_data)
   
   # Log performance metrics
   stats = price_structure.get_performance_stats()
   logger.info(f"Average calculation time: {stats['avg_time']}")
   ```

4. **Component Analysis**
   ```python
   # Get detailed component breakdown
   components = price_structure.get_component_scores(market_data)
   
   # Log significant components
   for component, score in components.items():
       if abs(score - 50) > 20:  # Significant deviation
           logger.info(f"{component} showing strong signal: {score}")
   ``` 