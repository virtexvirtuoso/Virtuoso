# Whale Activity Monitoring System

## Overview

The Virtuoso Trading System includes a sophisticated whale activity monitoring system that detects significant market movements caused by large traders ("whales"). The system currently uses two complementary methods to detect whale activity:

1. **Orderbook-Based Whale Detection**: Analyzes order book imbalances to detect large accumulation or distribution patterns
2. **Trade-Based Whale Detection**: Analyzes executed trades to identify patterns of significant buying or selling activity

This dual approach provides a more comprehensive view of whale activity by combining both intentions (orders) and actions (trades).

## Key Features

- Real-time monitoring of order books and trades across multiple symbols
- Detection of significant accumulation and distribution patterns
- Configurable thresholds to reduce noise and focus on meaningful events
- Intelligent classification of whale trades using standard deviation-based thresholds
- Trade imbalance analysis to identify directional bias
- Detailed alerts with USD values and market impact estimates
- Configurable cooldown periods to prevent alert spam

## Orderbook-Based Whale Alerts

### How It Works

The orderbook-based whale detection analyzes the order book to identify significant buy or sell walls that may indicate accumulation or distribution intentions by large market participants.

1. **Accumulation Detection**: Identifies large buy orders positioned near the current price that suggest accumulation intent
2. **Distribution Detection**: Identifies large sell orders positioned near the current price that suggest distribution intent
3. **Orderbook Imbalance**: Calculates the imbalance between buy and sell sides to determine market direction bias

### Configuration Parameters

```yaml
whale_activity:
  enabled: true                  # Enable whale activity monitoring
  accumulation_threshold: 5000000  # $5M default threshold for significant accumulation
  distribution_threshold: 5000000  # $5M default threshold for significant distribution
  cooldown: 1800                 # 30 minutes between alerts for same symbol
  imbalance_threshold: 0.3       # 30% order book imbalance threshold
  min_order_count: 8             # Minimum number of whale orders to consider
  market_percentage: 0.05        # 5% of market volume to be considered significant
```

## Trade-Based Whale Alerts

### How It Works

The trade-based whale detection analyzes executed trades to identify patterns of significant buying or selling by large market participants.

1. **Whale Trade Classification**: Uses a statistical approach (3 standard deviations above mean trade size) to identify abnormally large trades
2. **Trade Imbalance Analysis**: Calculates the imbalance between buy and sell volume to determine directional bias
3. **Cluster Detection**: Identifies clusters of large trades in the same direction, suggesting coordinated whale activity

### Configuration Parameters

```yaml
whale_activity:
  # Existing orderbook parameters...
  
  # Trade-based whale alert parameters
  trade_alerts_enabled: true     # Enable trade-based whale alerts
  trade_cooldown: 900            # 15 minutes between trade alerts
  min_whale_trades: 5            # Minimum number of whale trades to trigger alert
  min_trade_volume_usd: 500000   # Minimum USD value for significant trade volume
  min_trade_imbalance: 0.75      # Minimum 75% imbalance for significant trade activity
```

## Implementation Details

The whale activity monitoring is implemented in the `MarketMonitor` class with two primary methods:

1. `_monitor_whale_activity`: Analyzes orderbook data to detect accumulation/distribution patterns
2. `_monitor_trade_whale_activity`: Analyzes trade data to detect significant trade-based whale activity

The system can be tested and evaluated using dedicated test scripts:
- `test_whale_alerts.py`: Tests the orderbook-based whale alerts using synthetic data
- `test_whale_alerts_live.py`: Tests both alerting systems with live exchange data
- `test_trade_whale_alerts.py`: Standalone test for trade-based whale alerts

## Example Alert Output

### Orderbook-Based Alert

```
🐋 WHALE ALERT: BTC/USDT
Significant ACCUMULATION detected ($8.5M)
- Large buy orders detected: 12 orders
- Order book imbalance: 45% in favor of buyers
- Current price: $63,245.00
- Impact: Likely support at $62,900-$63,100
```

### Trade-Based Alert

```
🐋 WHALE TRADE ALERT: ETH/USDT
Large BUY pressure detected
- 7 whale-sized trades in last 5 minutes
- Volume: $2.3M (85% buy-side)
- Current price: $3,245.00 (↑1.5% in last 10m)
- Impact: Strong bullish momentum building
```

## Recent Enhancements

The whale alert system was recently enhanced to:

1. Add dedicated trade-based whale alerts
2. Increase detection thresholds for both systems to reduce noise:
   - Increased standard deviation multiplier from 2 to 3
   - Increased minimum USD thresholds
   - Increased required imbalance percentage
   - Extended cooldown periods
3. Improved detection accuracy by adding more sophisticated statistical analysis
4. Added detailed debugging for better visibility into detection logic

## Integration with Other Components

The whale activity monitoring integrates with:

1. **Alert Manager**: For delivering alerts to configured channels (Discord, console, etc.)
2. **Metrics Manager**: For tracking and analyzing whale activity over time
3. **Confluence System**: Whale activity data can be used as an input to trading signals

## Future Improvements

Potential future enhancements to consider:

1. Machine learning-based pattern recognition for more sophisticated whale detection
2. Integration with news sentiment analysis to correlate whale activity with market events
3. Historical whale activity analysis to identify recurring patterns
4. Cross-exchange whale activity correlation to detect coordinated movements 