# Liquidation Alert System

## Overview

The Virtuoso Trading System includes a sophisticated liquidation monitoring system that detects significant liquidation events in the market and sends alerts when they exceed configurable thresholds. Liquidation events are important market signals that can indicate potential price volatility and trading opportunities.

## Key Features

- Real-time monitoring of liquidation events across all supported symbols
- Configurable USD threshold to filter out smaller, less significant liquidations
- Intelligent categorization of liquidation types (LONG vs SHORT)
- Rich, detailed alerts with impact analysis and visual indicators
- Configurable cooldown period to prevent alert spam during high-volatility periods

## How It Works

The liquidation alert system operates through the following process:

1. Real-time liquidation data is received from exchange websockets
2. Data is processed by the `MarketDataManager` which extracts key information
3. Liquidation events are passed to the `AlertManager.check_liquidation_threshold()` method
4. The AlertManager calculates the USD value of the liquidation
5. If the USD value exceeds the configured threshold, an alert is generated
6. The alert is formatted with detailed information and sent to configured channels (e.g., Discord)
7. A cooldown timer prevents duplicate alerts for the same symbol within the cooldown period

## Configuration

The liquidation alert system can be configured through the `config.yaml` file:

```yaml
monitoring:
  alerts:
    # Liquidation alert settings
    liquidation:
      cooldown: 300                 # Liquidation alert cooldown in seconds
      threshold: 250000             # Liquidation threshold in USD
```

### Parameters

- **threshold**: The minimum USD value that a liquidation event must exceed to trigger an alert (default: $250,000)
- **cooldown**: The minimum time in seconds between alerts for the same symbol (default: 300 seconds / 5 minutes)

## Alert Format

Liquidation alerts include the following information:

1. **Title**: Indicates liquidation type (LONG/SHORT) and symbol
2. **Size**: The amount of the asset liquidated
3. **Price**: The execution price of the liquidation
4. **Value**: The total USD value of the liquidation
5. **Impact Level**: Classification (LOW/MEDIUM/HIGH/CRITICAL) based on size
6. **Impact Meter**: Visual representation of impact relative to threshold
7. **Market Impact Analysis**: Description of expected market impact
8. **Time**: When the liquidation occurred

### Example Alert

```
🔴 LONG LIQUIDATION: BTCUSDT

💥 Large liquidation detected (HIGH impact)

• Size: 5.0000 BTC
• Price: $68,500.00
• Value: $342,500.00 !!
• Time: 21:45:32 UTC (2m ago)

Market Impact:
• Immediate selling 📉 pressure
• Impact Level: HIGH
• Impact Meter: █████████░

Analysis: Expect immediate downward price pressure as liquidated longs are sold
```

## Liquidation Types

The system correctly interprets liquidation side:

- **LONG Liquidation** (side = "BUY"): Long positions being force-closed, creating selling pressure
- **SHORT Liquidation** (side = "SELL"): Short positions being force-closed, creating buying pressure

## Integration with Other Components

The liquidation alert system integrates with:

1. **Market Data Manager**: Provides real-time liquidation data
2. **Alert Manager**: Processes and sends the alerts
3. **Metrics Manager**: Tracks liquidation statistics
4. **Market Monitor**: Uses liquidation data for market analysis

## Testing

A test script is available at `tests/liquidation_test.py` to verify the liquidation alert functionality. This script:

1. Creates a mock AlertManager with a test configuration
2. Simulates liquidation events of various sizes and types
3. Verifies that alerts are sent only for events exceeding the threshold
4. Validates the alert content and format

To run the test:

```bash
python tests/liquidation_test.py
```

## Troubleshooting

If liquidation alerts are not working as expected:

1. **Check Configuration**: Verify the liquidation threshold and cooldown settings
2. **Check Exchange Data**: Ensure the exchange provides liquidation data via websocket
3. **Check Webhook URLs**: Verify Discord or other notification channels are properly configured
4. **Check Logs**: Look for any errors related to liquidation processing
5. **Run Tests**: Execute the test script to verify basic functionality

## Future Enhancements

Planned improvements to the liquidation alert system:

1. Historical analysis of liquidation patterns
2. Correlation with market volatility and price action
3. Machine learning-based significance detection
4. Enhanced visualization with liquidation clusters
5. Time-based threshold adjustments based on market conditions 