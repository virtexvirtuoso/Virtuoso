# Trade Execution Alerts

This document explains how to use the trade execution alert system in the Virtuoso trading platform.

## Overview

The trade execution alert system sends notifications when trades are executed, allowing you to stay informed about your trading activities in real-time. Alerts are sent via Discord webhooks and include detailed information about the trade.

## Alert Types

The system supports the following types of trade alerts:

1. **Entry Alerts**: Sent when a new position is opened
   - Long entries are displayed with a green circle emoji 🟢
   - Short entries are displayed with a red circle emoji 🔴

2. **Exit Alerts**: Sent when a position is closed
   - All exits are displayed with a white circle emoji ⚪

## Alert Content

Trade execution alerts include the following information:

- **Symbol**: The trading pair (e.g., BTC/USDT)
- **Price**: The execution price
- **Quantity**: The amount of the base asset traded
- **Value**: The total value of the trade in USD
- **Exchange**: The exchange where the trade was executed
- **Order ID**: A unique identifier for the order
- **Risk Management**: Stop loss and take profit levels (if set)
- **Signal Confidence**: The confidence level based on the confluence score that triggered the trade

## How to Configure

### 1. Setting Up Discord Webhook

To receive trade alerts, you need to configure a Discord webhook:

1. Create a Discord server or use an existing one
2. Create a channel for trade alerts
3. Go to Server Settings > Integrations > Webhooks
4. Click "New Webhook"
5. Name it "Virtuoso Trading Alerts" and select the channel
6. Copy the webhook URL

### 2. Configure the Alert Manager

Add the webhook URL to your configuration:

```json
{
  "monitoring": {
    "alerts": {
      "discord_webhook_url": "YOUR_DISCORD_WEBHOOK_URL"
    }
  }
}
```

Alternatively, set the environment variable:

```bash
export DISCORD_WEBHOOK_URL="YOUR_DISCORD_WEBHOOK_URL"
```

## Testing the Alert System

The platform includes a dedicated test script `test_trade_alerts.py` that allows you to test the trade execution alert system without making actual trades or sending real webhook notifications.

### Running the Test Script

The test script can be run in the following modes:

1. **Direct Mode**: Tests the AlertManager directly
   ```bash
   python test_trade_alerts.py --mode direct
   ```

2. **Executor Mode**: Tests alert integration with the TradeExecutor
   ```bash
   python test_trade_alerts.py --mode executor
   ```

3. **Both Modes**: Tests both direct and executor modes
   ```bash
   python test_trade_alerts.py --mode both
   ```

By default, the script runs in **mock mode**, which formats and captures alerts without sending actual webhook requests. If you want to test the actual webhook delivery, you can use the `--live` flag:

```bash
python test_trade_alerts.py --live
```

> **Warning**: Using the `--live` flag will send actual alerts to your configured Discord webhook.

### Mock Mode and Alert Capture

For testing purposes, the alert system includes two special features:

1. **Mock Mode**: When enabled, the system formats alerts but doesn't send actual webhook requests.
2. **Alert Capture**: Stores formatted alerts in memory for inspection.

Enable these features in your configuration:

```json
{
  "monitoring": {
    "alerts": {
      "mock_mode": true,
      "capture_alerts": true
    }
  }
}
```

These features are useful during development and testing to validate alert formatting without sending alerts to Discord.

## Integration with TradeExecutor

The alert system is integrated directly with the `TradeExecutor` class:

- When `execute_trade()` is called, an entry alert is automatically sent
- When `close_position()` is called, an exit alert is automatically sent
- When `simulate_trade()` is called in dry run mode, a simulated trade alert is sent

## Example Alerts

### Long Entry Alert

```
🟢 LONG POSITION OPENED: BTC/USDT
Price: $50,000.00
Quantity: 0.01000000
Value: $500.00
Exchange: Bybit

Risk Management:
Stop Loss: 3.00% ($48,500.00)
Take Profit: 5.00% ($52,500.00)

Signal Confidence: High (75.5/100)
```

### Short Entry Alert

```
🔴 SHORT POSITION OPENED: ETH/USDT
Price: $3,500.00
Quantity: 0.10000000
Value: $350.00
Exchange: Bybit

Risk Management:
Stop Loss: 3.00% ($3,605.00)

Signal Confidence: Very High (85.0/100)
```

### Position Exit Alert

```
⚪ LONG POSITION CLOSED: BTC/USDT
Price: $52,000.00
Quantity: 0.01000000
Value: $520.00
Exchange: Bybit
```

## Testing Trade Alerts

You can test the trade alert system using the provided test script:

```bash
python test_trade_alerts.py
```

This script tests different types of trade alerts without making actual trades.

## Customization

The alert appearance can be customized by modifying the `send_trade_execution_alert` method in the `AlertManager` class:

- To change icons, modify the emoji assignments based on trade type and side
- To change colors, modify the color values (in hex format)
- To add or remove fields, modify the description list construction

## Benefits

- Real-time trade notifications
- Detailed trade information in a clean, readable format
- Clear visual differentiation between entry and exit trades
- Integration with existing monitoring systems
- Easy tracking of trading activity across multiple symbols 