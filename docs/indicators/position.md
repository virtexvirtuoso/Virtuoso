# Position Indicators

## Overview

The `PositionIndicators` class provides tools for analyzing and managing trading positions, risk metrics, and portfolio performance. These indicators help optimize position sizing, manage risk exposure, and track performance metrics across multiple positions.

## Available Indicators

### 1. Position Risk Metrics
```python
def calculate_position_risk(
    position: pd.Series,
    prices: pd.Series,
    volatility: pd.Series,
    risk_free_rate: float = 0.02
) -> pd.DataFrame:
    """Calculate position risk metrics.
    
    Args:
        position: Series with position sizes
        prices: Price series
        volatility: Volatility series
        risk_free_rate: Annual risk-free rate
        
    Returns:
        DataFrame with risk metrics (VaR, ES, Beta, etc.)
    """
```

### 2. Portfolio Exposure
```python
def calculate_exposure(
    positions: pd.DataFrame,
    prices: pd.DataFrame,
    group_by: str = None
) -> pd.DataFrame:
    """Calculate portfolio exposure metrics.
    
    Args:
        positions: DataFrame with positions
        prices: Price data for positions
        group_by: Group exposure by category
        
    Returns:
        DataFrame with exposure metrics by asset/group
    """
```

### 3. Position Performance
```python
def calculate_performance(
    positions: pd.DataFrame,
    prices: pd.DataFrame,
    include_fees: bool = True
) -> pd.DataFrame:
    """Calculate position performance metrics.
    
    Args:
        positions: DataFrame with positions
        prices: Price data for positions
        include_fees: Whether to include trading fees
        
    Returns:
        DataFrame with performance metrics
    """
```

## Usage Examples

### Basic Usage
```python
from src.indicators import PositionIndicators

# Initialize
position = PositionIndicators()

# Calculate risk metrics
risk = position.calculate_position_risk(pos, prices, vol)

# Calculate exposure
exposure = position.calculate_exposure(positions, prices)

# Calculate performance
performance = position.calculate_performance(positions, prices)
```

### Advanced Usage
```python
# Custom configuration
position = PositionIndicators(
    config={
        'risk': {
            'var_confidence': 0.99,
            'lookback_window': 252
        },
        'exposure': {
            'net_grouping': True,
            'include_derivatives': True
        }
    }
)

# Batch calculation
results = position.calculate_batch(
    positions,
    prices,
    indicators=['risk', 'exposure', 'performance']
)
```

## Signal Generation

### Risk Signals
```python
def generate_risk_signals(
    positions: pd.DataFrame,
    risk_metrics: pd.DataFrame,
    thresholds: Dict[str, float]
) -> pd.Series:
    """Generate signals based on risk metrics.
    
    Returns:
        Series with values:
        1: Reduce position (risk too high)
        -1: Increase position (risk low)
        0: No action needed
    """
```

### Exposure Signals
```python
def generate_exposure_signals(
    exposures: pd.DataFrame,
    limits: Dict[str, float]
) -> pd.DataFrame:
    """Generate signals based on exposure limits.
    
    Returns:
        DataFrame with exposure adjustment signals
    """
```

## Performance Optimization

### Caching
```python
# Enable caching for repeated calculations
position.enable_cache()

# Cache with custom TTL
position.enable_cache(ttl=300)  # 5 minutes

# Clear cache
position.clear_cache()
```

### Batch Processing
```python
# Process multiple portfolios
portfolios = ['PORTFOLIO1', 'PORTFOLIO2']
results = {}

for portfolio in portfolios:
    results[portfolio] = position.calculate_batch(
        positions[portfolio],
        prices,
        indicators=['risk', 'exposure']
    )
```

## Configuration Options

```python
config = {
    'risk': {
        'var_confidence': 0.99,
        'es_confidence': 0.975,
        'lookback_window': 252,
        'decay_factor': 0.94,
        'include_correlation': True
    },
    'exposure': {
        'net_grouping': True,
        'include_derivatives': True,
        'base_currency': 'USD',
        'leverage_limits': {
            'gross': 3.0,
            'net': 2.0
        }
    },
    'performance': {
        'include_fees': True,
        'fee_structure': {
            'maker': 0.001,
            'taker': 0.002
        },
        'metrics': ['pnl', 'sharpe', 'sortino']
    }
}
```

## Error Handling

```python
try:
    risk = position.calculate_position_risk(pos, prices, vol)
except ValidationError as e:
    logger.error(f"Invalid position data: {e}")
except CalculationError as e:
    logger.error(f"Calculation failed: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

## Best Practices

1. **Data Preparation**
   ```python
   # Align position and price data
   positions, prices = position.align_data(positions, prices)
   
   # Fill missing values
   positions = position.fill_missing_positions(positions)
   
   # Convert currencies
   positions = position.convert_to_base_currency(positions)
   ```

2. **Risk Management**
   ```python
   # Set position limits
   position.set_limits(
       max_position_size=1000000,
       max_leverage=3.0,
       concentration_limit=0.2
   )
   
   # Monitor risk limits
   violations = position.check_risk_limits(positions, risk_metrics)
   ```

3. **Performance Analysis**
   ```python
   # Calculate attribution
   attribution = position.calculate_attribution(
       positions=positions,
       prices=prices,
       factors=['market', 'size', 'momentum']
   )
   
   # Generate performance report
   report = position.generate_report(
       positions=positions,
       metrics=['pnl', 'sharpe', 'drawdown']
   )
   ```

4. **Performance Monitoring**
   ```python
   # Track calculation time
   with position.timer('risk_calculation'):
       risk = position.calculate_position_risk(pos, prices, vol)
   
   # Get performance stats
   stats = position.get_performance_stats()
   print(f"Average risk calculation time: {stats['risk_avg_time']}")
   ```

## Integration Examples

### 1. With Order Management
```python
# Use position metrics for order sizing
risk = position.calculate_position_risk(pos, prices, vol)
exposure = position.calculate_exposure(positions, prices)

# Generate order size
order_size = order_manager.calculate_order_size(
    risk_metrics=risk,
    current_exposure=exposure,
    target_risk=0.01
)
```

### 2. With Portfolio Optimization
```python
# Use position analysis for optimization
performance = position.calculate_performance(positions, prices)
risk = position.calculate_position_risk(pos, prices, vol)

# Optimize portfolio weights
weights = optimizer.optimize_weights(
    performance_metrics=performance,
    risk_metrics=risk,
    constraints={'max_weight': 0.2}
)
```

### 3. With Risk Reporting
```python
# Generate comprehensive risk report
risk = position.calculate_position_risk(pos, prices, vol)
exposure = position.calculate_exposure(positions, prices)
performance = position.calculate_performance(positions, prices)

# Create risk report
report = risk_reporter.generate_report(
    risk_metrics=risk,
    exposure_metrics=exposure,
    performance_metrics=performance,
    format='pdf'
)
``` 