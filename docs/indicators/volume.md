# Volume Indicators

## Overview

The `VolumeIndicators` class provides tools for analyzing trading volume patterns and price-volume relationships. These indicators help identify trading activity intensity, buying/selling pressure, and potential trend reversals.

## Available Indicators

### 1. Volume Weighted Average Price (VWAP)
```python
def calculate_vwap(
    prices: pd.Series,
    volumes: pd.Series,
    period: str = '1D'
) -> pd.Series:
    """Calculate Volume Weighted Average Price.
    
    Args:
        prices: Price series
        volumes: Volume series
        period: Reset period ('1D', '1H', etc.)
        
    Returns:
        Series containing VWAP values
    """
```

### 2. On-Balance Volume (OBV)
```python
def calculate_obv(
    close: pd.Series,
    volume: pd.Series
) -> pd.Series:
    """Calculate On-Balance Volume.
    
    Args:
        close: Close prices
        volume: Volume data
        
    Returns:
        Series containing OBV values
    """
```

### 3. Volume Profile
```python
def calculate_volume_profile(
    prices: pd.Series,
    volumes: pd.Series,
    n_bins: int = 50
) -> pd.DataFrame:
    """Calculate Volume Profile.
    
    Args:
        prices: Price series
        volumes: Volume series
        n_bins: Number of price bins
        
    Returns:
        DataFrame with price levels and volume distribution
    """
```

## Usage Examples

### Basic Usage
```python
from src.indicators import VolumeIndicators

# Initialize
volume = VolumeIndicators()

# Calculate VWAP
vwap = volume.calculate_vwap(prices, volumes)

# Calculate OBV
obv = volume.calculate_obv(close, volume_data)

# Calculate Volume Profile
profile = volume.calculate_volume_profile(prices, volumes)
```

### Advanced Usage
```python
# Custom configuration
volume = VolumeIndicators(
    config={
        'vwap': {
            'anchor_point': 'session_open',
            'include_after_hours': False
        },
        'volume_profile': {
            'value_area_volume': 0.70,  # 70% of volume
            'dynamic_bins': True
        }
    }
)

# Batch calculation
results = volume.calculate_batch(
    prices,
    volumes,
    indicators=['vwap', 'obv'],
    periods={'vwap': '1D'}
)
```

## Signal Generation

### Volume-Price Divergence
```python
def detect_volume_divergence(
    prices: pd.Series,
    volumes: pd.Series,
    window: int = 20
) -> pd.Series:
    """Detect volume-price divergence patterns.
    
    Returns:
        Series with values:
        1: Bullish divergence
        -1: Bearish divergence
        0: No divergence
    """
```

### Volume Zone Analysis
```python
def analyze_volume_zones(
    prices: pd.Series,
    volumes: pd.Series,
    n_zones: int = 3
) -> pd.DataFrame:
    """Analyze volume distribution zones.
    
    Returns:
        DataFrame containing:
        - Price zones
        - Volume concentration
        - Zone classification
    """
```

## Performance Optimization

### Caching
```python
# Enable caching for repeated calculations
volume.enable_cache()

# Cache with custom TTL
volume.enable_cache(ttl=300)  # 5 minutes

# Clear cache
volume.clear_cache()
```

### Batch Processing
```python
# Process multiple symbols
symbols = ['BTC-USD', 'ETH-USD']
results = {}

for symbol in symbols:
    results[symbol] = volume.calculate_batch(
        prices[symbol],
        volumes[symbol],
        indicators=['vwap', 'obv']
    )
```

## Configuration Options

```python
config = {
    'vwap': {
        'anchor_point': 'session_open',  # or 'daily_open'
        'include_after_hours': False,
        'reset_period': '1D',
        'price_type': 'typical'  # or 'close'
    },
    'obv': {
        'smooth_period': 0,  # 0 for raw OBV
        'signal_period': 20
    },
    'volume_profile': {
        'n_bins': 50,
        'value_area_volume': 0.70,
        'dynamic_bins': True,
        'min_volume_threshold': 0.01
    }
}
```

## Error Handling

```python
try:
    vwap = volume.calculate_vwap(prices, volumes)
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
   # Align price and volume data
   prices, volumes = volume.align_data(prices, volumes)
   
   # Remove zero volume periods
   mask = volumes > 0
   prices = prices[mask]
   volumes = volumes[mask]
   
   # Handle outliers
   volumes = volume.remove_volume_outliers(volumes)
   ```

2. **Session Handling**
   ```python
   # Configure session times
   volume.set_session_times(
       start='09:30',
       end='16:00',
       timezone='America/New_York'
   )
   
   # Calculate session VWAP
   session_vwap = volume.calculate_vwap(
       prices,
       volumes,
       session_only=True
   )
   ```

3. **Volume Analysis**
   ```python
   # Analyze volume patterns
   patterns = volume.analyze_volume_patterns(
       prices,
       volumes,
       window=20
   )
   
   # Get significant volume levels
   levels = volume.get_significant_levels(
       prices,
       volumes,
       n_levels=5
   )
   ```

4. **Performance Monitoring**
   ```python
   # Track calculation time
   with volume.timer('vwap_calculation'):
       vwap = volume.calculate_vwap(prices, volumes)
   
   # Get performance stats
   stats = volume.get_performance_stats()
   print(f"Average VWAP calculation time: {stats['vwap_avg_time']}")
   ```

## Integration Examples

### 1. With Order Flow Analysis
```python
# Combine volume profile with order flow
profile = volume.calculate_volume_profile(prices, volumes)
flow = orderflow.calculate_order_flow(trades)

# Analyze volume and flow alignment
alignment = volume.analyze_volume_flow_alignment(profile, flow)
```

### 2. With Position Sizing
```python
# Use volume analysis for position sizing
vwap = volume.calculate_vwap(prices, volumes)
vol_zones = volume.analyze_volume_zones(prices, volumes)

# Calculate position size based on volume zones
position_size = position.calculate_size_from_volume(
    price=current_price,
    volume_zones=vol_zones,
    risk_factor=0.02
)
```

### 3. With Market Making
```python
# Use volume profile for market making
profile = volume.calculate_volume_profile(prices, volumes)

# Generate quotes based on volume distribution
quotes = market_maker.generate_quotes(
    current_price=price,
    volume_profile=profile,
    spread_factor=0.001
)
``` 