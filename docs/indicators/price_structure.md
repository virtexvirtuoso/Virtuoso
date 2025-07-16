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

The Price Structure Indicators provide comprehensive analysis of market structure, support/resistance levels, order blocks, and institutional trading patterns. This system combines traditional technical analysis with Smart Money Concepts (SMC) to identify high-probability trading opportunities.

## Components and Weights

### Traditional Components (75%)

1. **Support/Resistance Levels (15%)**
   - Identifies key price levels where market has shown significant reaction
   - Uses historical price action to map support and resistance zones
   - Incorporates volume profile for level validation

2. **Order Blocks and Supply/Demand Zones (15%)**
   - Maps significant supply and demand areas using ICT methodology
   - Identifies institutional order blocks with enhanced mitigation tracking
   - Tracks zone reaction strength and validity

3. **Trend Position Relative to Key Moving Averages (15%)**
   - Analyzes price position relative to major MAs
   - Tracks MA crossovers and alignments
   - Measures trend strength and momentum

4. **Volume Analysis Including Profile and VWAP (15%)**
   - Volume Profile analysis for price acceptance/rejection
   - VWAP deviation analysis
   - Volume node identification

5. **Swing Structure Including Swing Points (20%)**
   - Tracks higher highs/lows or lower highs/lows
   - Identifies swing points and pivots
   - Analyzes structural breaks and continuations

### Smart Money Concepts (SMC) Components (25%)

6. **Fair Value Gaps (FVG) - 10%**
   - Detects price gaps that represent inefficient price delivery
   - Tracks mitigation when price returns to fill gaps
   - Acts as magnets for future price action

7. **Liquidity Zones - 10%**
   - Identifies areas where multiple swing highs/lows cluster
   - Tracks liquidity sweeps and stop hunt patterns
   - Maps institutional liquidity targeting zones

8. **Break of Structure (BOS) & Change of Character (CHoCH) - 5%**
   - BOS: Trend continuation when price breaks previous structure
   - CHoCH: Potential reversal when market structure changes
   - Enhanced market structure analysis using ICT concepts

## Smart Money Concepts (SMC) Implementation

### Fair Value Gaps (FVG)

Fair Value Gaps represent areas of inefficient price delivery where institutional orders create imbalances.

**Detection Criteria:**
- **Bullish FVG**: Previous high < Next low (gap up)
- **Bearish FVG**: Previous low > Next high (gap down)

**Key Features:**
- Mitigation tracking when price returns to fill the gap
- Strength calculation based on volume and gap size
- Consecutive FVG merging for cleaner analysis
- Time-based relevance scoring

**Scoring Logic:**
```python
# Proximity-based scoring
distance = abs(current_price - fvg_level) / current_price
proximity_score = max(0, 100 - (distance * 500))
strength_weighted = proximity_score * (fvg_strength / 100)

# Directional bias
if current_price > bullish_fvg_top:
    bullish_signal += strength_weighted
if current_price < bearish_fvg_bottom:
    bearish_signal += strength_weighted
```

### Liquidity Zones

Liquidity zones identify areas where institutional players target retail stop losses and liquidity pools.

**Detection Method:**
1. Identify swing highs and lows using configurable swing length
2. Cluster nearby swing points within percentage range (default 1%)
3. Create zones from clusters with minimum 2 swing points
4. Track liquidity sweeps (price breaks through and reverses)

**Zone Properties:**
- **Type**: Bullish (support) or Bearish (resistance)
- **Level**: Average price of clustered swing points
- **Strength**: Number of swing points in cluster
- **Swept Status**: Whether liquidity has been taken

**Scoring Factors:**
- Proximity to current price
- Zone strength (number of swing points)
- Sweep status (1.5x multiplier for swept zones)
- Directional bias based on price position

### Break of Structure (BOS) & Change of Character (CHoCH)

Advanced market structure analysis based on ICT methodology for identifying trend continuation and reversal signals.

**Definitions:**
- **BOS (Break of Structure)**: Price breaks previous structure in trend direction (continuation)
- **CHoCH (Change of Character)**: Price breaks previous structure against trend (potential reversal)

**Detection Process:**
1. Identify swing highs and lows
2. Determine current trend based on recent swing points
3. Monitor for structure breaks (close or high/low based)
4. Classify breaks as BOS or CHoCH based on trend direction

**Trend Determination:**
- **Bullish**: Higher highs and higher lows
- **Bearish**: Lower highs and lower lows
- **Neutral**: Mixed or insufficient data

**Strength Calculation:**
```python
# Volume factor
volume_factor = break_volume / avg_volume

# Time factor
time_factor = min(break_index - swing_index, 50) / 50

# Combined strength
strength = (volume_factor * 50) + (time_factor * 50)
```

## Configuration

### Component Weights

```yaml
confluence:
  weights:
    sub_components:
      price_structure:
        support_resistance: 0.18
        order_block: 0.18
        trend_position: 0.18
        swing_structure: 0.18
        composite_value: 0.05
        fair_value_gaps: 0.10      # SMC
        bos_choch: 0.05           # SMC
        range_score: 0.08         # Range Analysis
```

### SMC Parameters

```yaml
analysis:
  indicators:
    price_structure:
      parameters:
        # Fair Value Gaps
        fvg:
          join_consecutive: false
          min_gap_percentage: 0.001
          
        # Liquidity Zones
        liquidity:
          swing_length: 50
          cluster_range_percent: 0.01
          min_cluster_size: 2
          
        # BOS/CHoCH
        structure:
          swing_length: 20
          close_break: true
          min_strength: 10
```

## Score Interpretation

### Overall Score Ranges

- **0-20**: Strong Bearish - Multiple bearish confluences
- **20-40**: Bearish Bias - Bearish structure dominance
- **40-60**: Neutral/Consolidation - Mixed signals
- **60-80**: Bullish Bias - Bullish structure dominance  
- **80-100**: Strong Bullish - Multiple bullish confluences

### SMC-Specific Signals

**Fair Value Gap Signals:**
- **Score > 70**: Price near unmitigated bullish FVG (demand zone)
- **Score < 30**: Price near unmitigated bearish FVG (supply zone)
- **Score ≈ 50**: No significant FVG influence or mitigated gaps

**Liquidity Zone Signals:**
- **High scores**: Price above support liquidity or swept resistance
- **Low scores**: Price below resistance liquidity or swept support
- **Neutral**: Price away from significant liquidity zones

**BOS/CHoCH Signals:**
- **Recent BOS**: Trend continuation likely (adds to trend direction)
- **Recent CHoCH**: Potential reversal (counters trend direction)
- **No recent breaks**: Structure-neutral environment

## Usage Examples

### Basic Implementation

```python
from src.indicators.price_structure_indicators import PriceStructureIndicators

# Initialize with SMC components enabled
psi = PriceStructureIndicators(config, logger)

# Analyze market data
result = await psi.calculate(market_data)

print(f"Price Structure Score: {result['score']:.2f}")
print(f"Fair Value Gaps: {result['components']['fair_value_gaps']:.2f}")
print(f"Liquidity Zones: {result['components']['liquidity_zones']:.2f}")
print(f"BOS/CHoCH: {result['components']['bos_choch']:.2f}")
```

### Advanced SMC Analysis

```python
# Access detailed SMC data
fvgs = psi._detect_fair_value_gaps(df)
print(f"Bullish FVGs: {len(fvgs['bullish'])}")
print(f"Bearish FVGs: {len(fvgs['bearish'])}")

liquidity_zones = psi._detect_liquidity_zones(df)
print(f"Support zones: {len(liquidity_zones['bullish'])}")
print(f"Resistance zones: {len(liquidity_zones['bearish'])}")

swing_data = psi._detect_swing_highs_lows(df, swing_length=20)
bos_choch = psi._detect_bos_choch(df, swing_data)
print(f"BOS events: {len(bos_choch['bos'])}")
print(f"CHoCH events: {len(bos_choch['choch'])}")
```

## Integration with Trading Strategy

The SMC components enhance traditional technical analysis by providing:

1. **Entry Timing**: FVG mitigation and liquidity sweeps for precise entries
2. **Trend Analysis**: BOS/CHoCH for trend continuation vs reversal signals
3. **Risk Management**: Liquidity zones for stop loss placement
4. **Target Setting**: FVG levels as profit targets

### Confluence Trading

Combine SMC with traditional components for high-probability setups:

```python
# Example confluence check
if (result['components']['fair_value_gaps'] > 70 and 
    result['components']['order_blocks'] > 70 and
    result['components']['bos_choch'] > 60):
    print("Strong bullish confluence detected!")
```

## Performance Considerations

- SMC calculations are computationally intensive due to swing point detection
- Recommended minimum 200 candles for reliable SMC analysis
- Consider caching swing point calculations for multiple timeframes
- FVG detection scales linearly with data size

## Troubleshooting

### Common Issues

1. **No FVGs detected**: Increase data size or reduce gap criteria
2. **Too many liquidity zones**: Increase cluster range percentage
3. **No BOS/CHoCH events**: Reduce swing length or increase data size

### Debug Options

```yaml
analysis:
  indicators:
    price_structure:
      parameters:
        debug_logging: true
        smc_debug: true
```

This enables detailed logging of SMC detection processes and scoring calculations. 