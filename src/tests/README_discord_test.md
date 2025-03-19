# Testing Discord Alerts with Confluence Scores

This guide explains how to test the Discord alerting functionality when a confluence score meets the buy or sell threshold in the MarketMonitor system.

## Prerequisites

1. A Discord server where you have permission to create webhooks
2. Python 3.7+ installed on your system
3. Required Python packages installed (see main project requirements.txt)

## Setup Discord Webhook

1. In your Discord server, go to the channel where you want to receive alerts
2. Click the settings icon (gear) next to the channel name
3. Navigate to "Integrations" → "Webhooks"
4. Click "New Webhook"
5. Give it a name (e.g., "Market Monitor Alerts")
6. Copy the webhook URL

## Configure Environment

1. Create a copy of the `.env.example` file and name it `.env`:
   ```
   cp .env.example .env
   ```

2. Edit the `.env` file and replace the `DISCORD_WEBHOOK_URL` value with your copied webhook URL:
   ```
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your-actual-webhook-url
   ```

## Run the Test Script

From the project root directory, run:

```bash
python src/tests/test_discord_alert.py
```

## What the Test Does

The test script runs three different test scenarios:

1. **Bullish Alert Test**: Creates a mock signal with a high confluence score (75.0) that should trigger a BUY signal alert.

2. **Bearish Alert Test**: Creates a mock signal with a low confluence score (25.0) that should trigger a SELL signal alert.

3. **Direct Confluence Alert Test**: Bypasses the SignalGenerator and sends a confluence alert directly through the AlertManager.

## Expected Results

After running the test, you should see alerts in your Discord channel. The alerts will include:

- Formatted confluence score tables
- Signal information (BUY/SELL)
- Component scores (volume, technical, orderflow, etc.)
- Detailed interpretations for each component
- Reliability score

If you don't see the alerts, check:

1. The console output for any error messages
2. That your Discord webhook URL is correct
3. Your Discord server permissions
4. Network connectivity

## Troubleshooting

- **"DISCORD_WEBHOOK_URL environment variable is not set!"**: Make sure you've created the `.env` file with the correct webhook URL.
  
- **"Discord webhook is not properly configured!"**: Check if the webhook URL is valid and if the Discord integration is properly set up.

- **No alerts appearing in Discord**: Check if there are any errors in the console output, and verify that your webhook URL is correct.

- **Error with module imports**: Make sure you're running the script from the project root directory, not from inside the `src/tests` directory.

## Customizing the Test

You can modify the test data in the script to test different scenarios:

- Change the confluence scores to test different thresholds
- Modify component scores to see how they affect the alerts
- Add or modify the interpretations for each component

## Next Steps

After confirming that Discord alerts work correctly with simulated data, you can integrate this functionality into your production system, ensuring that real market conditions that meet your threshold criteria will trigger appropriate alerts. 