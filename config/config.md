# Virtuoso Trading System Configuration Guide

## Overview

This guide explains the key configuration options for the Virtuoso Trading System. Each section describes what the settings control and how to adjust them for your needs.

## System Settings

### Environment Configuration
- `environment`: Choose between "production" or "development" mode
  - Use "development" for testing and debugging
  - Use "production" for live trading
- `log_level`: Controls logging detail (DEBUG, INFO, WARNING, ERROR)
  - Set to "DEBUG" for detailed logs during development
  - Use "INFO" or "WARNING" for production

### Directory Settings
- `data_dir`: Where market data is stored
- `cache_dir`: Location for temporary data storage

## Exchange Settings

### Bybit Configuration
- API credentials: Required for connecting to your Bybit account
- Rate limits: Configure request limits to prevent API throttling
- WebSocket settings: Control connection parameters and reconnection behavior

## Market Data Settings

### Symbol Selection
Controls which trading pairs the system monitors:
- Enable `use_static_list` to use a predefined list of symbols
- Set `max_symbols` to limit how many pairs to track (current: 15)
- Use `min_turnover` and `min_volume` to filter out low-activity pairs
- Configure `top_symbols_update_interval_hours` to control how often the list updates

### Timeframes
The system uses multiple timeframes for analysis:
- Base timeframe (1-minute): Primary data collection
- LTF (5-minute): Short-term analysis
- MTF (30-minute): Medium-term analysis
- HTF (4-hour): Long-term trend analysis

Each timeframe has settings for:
- Required candles
- Validation parameters
- Weight in multi-timeframe analysis

### Data Validation
Ensures data quality before analysis:
- Price validation (min/max values)
- Volume validation
- Candle relationship checks
- Gap detection and handling

## Analysis Settings

### Component Weights
Balance different analysis factors by adjusting their weights in the confluence section:
- Technical (traditional indicators): 20%
- Orderflow (trade flow dynamics): 25%
- Sentiment (market mood indicators): 10%
- Orderbook (market microstructure): 20%
- Volume (trading volume patterns): 10%
- Price Structure (market geometry): 15%

Weights must total 1.0. Increase weights for factors you want to emphasize.

### Orderbook Indicators
Fine-tuned parameters for market microstructure analysis:

#### Market Imbalance (25%)
```yaml
imbalance:
  lookback: 20              # Periods for imbalance analysis
  threshold: 0.2            # Threshold for imbalance significance
  smoothing: 3              # Smoothing factor for calculations
  extreme_threshold: 0.5    # Threshold for extreme imbalance
```

#### Market Pressure Index (20%)
```yaml
mpi:
  lookback: 10              # Periods for MPI calculation
  threshold: 0.3            # Threshold for significant pressure
  sensitivity: 0.75         # Sensitivity factor for calculations
```

#### Depth Analysis (20%)
```yaml
depth:
  levels: 25                # Price levels to analyze
  weight_decay: 0.95        # Weight decay for depth calculations
  significance_threshold: 0.1 # Threshold for significance
```

#### Other Orderbook Components
- Liquidity (10%): Measures available market liquidity
- Absorption/Exhaustion (10%): Detects supply/demand zones
- DOM Momentum (5%): Tracks order book velocity
- Spread Analysis (5%): Evaluates bid-ask spreads
- OBPS (5%): Order Book Pressure Score

### Orderflow Indicators
Parameters for analyzing the flow of trades:

#### Cumulative Volume Delta (25%)
```yaml
cvd:
  lookback: 50              # Lookback period for calculations
  smoothing: 3              # Smoothing factor for CVD curve
  threshold: 0.25           # Threshold for significant changes
```

#### Trade Flow (30%)
```yaml
trade_flow:
  window: 20                # Window size for calculations
  momentum_lookback: 10     # Lookback for momentum
  pressure_sensitivity: 0.8 # Sensitivity for pressure
```

#### Open Interest (25%)
```yaml
open_interest:
  lookback: 24              # Hours to look back
  change_threshold: 0.05    # Threshold for significant change
  trend_period: 12          # Period for trend calculation
```

#### Other Orderflow Components
- Imbalance (20%): Trade flow imbalance
- Order Block (15%): Significant supply/demand zones

### Volume Indicators
Detailed parameters for volume analysis:

#### Volume Delta (25%)
```yaml
volume_delta:
  window: 20                # Window for calculations
  min_trades: 100           # Minimum trades required
```

#### On-Balance Volume (20%)
```yaml
obv:
  trend_lookback: 14        # Lookback for trend analysis
  smoothing: 3              # Smoothing factor
```

#### Other Volume Components
- ADL (20%): Accumulation/Distribution Line
- CMF (15%): Chaikin Money Flow
- Relative Volume (20%): Volume comparison

### Technical Indicators
Standard technical analysis parameters:
- RSI (20%): 14-period with 70/30 thresholds
- AO (20%): 14-period Awesome Oscillator
- MACD (15%): 12/26/9 configuration
- ATR (15%): 14-period Average True Range
- CCI (15%): 20-period Commodity Channel Index
- Williams %R (15%): 14-period setting

### Price Structure Analysis
Parameters for analyzing market structure:
- Volume Profile (25%): Price distribution analysis
- VWAP (20%): Volume-Weighted Average Price
- Order Block (15%): Key supply/demand zones
- Market Structure (15%): Higher highs/lower lows
- Composite Value (15%): Combined price levels
- Support/Resistance (10%): Key price levels

## Confluence Settings

### Signal Generation
Controls when trading signals are generated:
- `buy`: Score threshold for bullish signals (70)
- `sell`: Score threshold for bearish signals (40)
- `neutral_buffer`: Buffer to prevent signal flipping (5)

### Weight Configurations
The system uses a hierarchical weighting system:
1. Component weights (orderbook, orderflow, etc.)
2. Sub-component weights within each component

## Data Processing Settings

### Pipeline Configuration
Controls how data flows through the system:
1. Validation: Data quality checks
2. Normalization: Standardizing data
3. Feature Engineering: Creating derived metrics
4. Aggregation: Combining different signals

### Performance Settings
Optimize system performance:
- Caching: Enable/disable and control cache size
- Parallel processing: Use multiple CPU cores
- Batch processing: Control batch sizes

## Monitoring Configuration

### Performance Monitoring
Track system health and performance:
- Memory tracking: Monitor memory usage
- CPU tracking: Track processor utilization
- Calculation time: Measure processing speed
- Error rates: Track system errors

### Alerts
Configure notification systems:
- Discord alerts: Set webhook URL
- Configure alert channels (console, database, webhook)
- Set cooldown periods between alerts

## Quick Start Examples

### Development Setup
```yaml
system:
  environment: "development"
  log_level: "DEBUG"

market:
  symbols:
    use_static_list: true
    static_symbols: ["BTCUSDT", "ETHUSDT"]
```

### Production Setup
```yaml
system:
  environment: "production" 
  log_level: "INFO"

market:
  symbols:
    use_static_list: false
    max_symbols: 15
    min_turnover: 5000000
```

## Customizing Indicator Settings

### Adjusting Orderbook Sensitivity
```yaml
orderbook:
  parameters:
    imbalance:
      threshold: 0.15         # More sensitive (default: 0.2)
    depth:
      weight_decay: 0.9       # Faster decay (default: 0.95)
    mpi:
      sensitivity: 0.8        # More sensitive (default: 0.75)
```

### Adjusting Orderflow Parameters
```yaml
orderflow:
  cvd:
    threshold: 0.2           # More sensitive (default: 0.25)
  trade_flow:
    pressure_sensitivity: 0.9 # More sensitive (default: 0.8)
```

### Adjusting Volume Analysis
```yaml
volume:
  parameters:
    volume_delta:
      window: 15             # Shorter window (default: 20)
    relative_volume:
      significant_threshold: 1.3 # Lower threshold (default: 1.5)
```

## Best Practices

1. Start in Development Mode
   - Use development environment first
   - Start with few symbols
   - Enable detailed logging

2. Production Migration
   - Switch to production environment
   - Reduce log level
   - Enable alerts
   - Use dynamic symbol selection

3. Performance Optimization
   - Adjust timeframes based on strategy
   - Balance analysis weights
   - Monitor system resources

4. Indicator Tuning
   - Start with default parameters
   - Adjust one component at a time
   - Backtest changes before implementing
   - Document performance improvements

## Common Adjustments

1. Changing Trading Pairs
   - Enable/disable static selection
   - Modify minimum turnover and volume
   - Update static symbols list

2. Adjusting Analysis
   - Modify component weights
   - Change lookback periods
   - Adjust sensitivity thresholds

3. Alert Configuration
   - Configure Discord webhook
   - Adjust alert cooldown periods
   - Set liquidation thresholds

4. Performance Tuning
   - Adjust batch sizes
   - Enable/disable caching
   - Configure parallel processing

## Need Help?

- Check logs for detailed error messages
- Review performance metrics
- Refer to indicator documentation for details on parameters
- See the source code for implementation details 