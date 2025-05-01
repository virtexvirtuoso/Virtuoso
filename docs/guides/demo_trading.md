# Bybit Demo Trading Guide

This guide explains how to use the Bybit demo trading integration with the confluence-based strategy.

## Overview

The Bybit demo trading integration allows you to test trading strategies in a simulated environment using real market data. The system uses confluence analysis to determine entry and exit points, with position sizing based on the confluence score.

## Prerequisites

- Bybit account with API keys for the demo environment
- Python 3.9+ with required dependencies (see requirements.txt)
- Basic knowledge of trading concepts

## Setup Instructions

1. **Configure API Keys**

   First, you need to obtain API keys from Bybit for their demo environment. Visit [Bybit](https://www.bybit.com/) and register for an account if you don't already have one.

   Once you have your API keys, update the configuration file at `config/demo_trading.json`:

   ```json
   {
     "exchanges": {
       "bybit": {
         "api_credentials": {
           "api_key": "YOUR_BYBIT_API_KEY",
           "api_secret": "YOUR_BYBIT_API_SECRET"
         }
       }
     }
   }
   ```

   The system will automatically create this file with default settings when you first run the demo trading script if it doesn't exist.

2. **Configure Trading Parameters**

   You can customize various parameters in the configuration file:

   **Position Sizing Parameters:**
   - `position_manager.base_position_pct`: Base position size as a percentage of account (default: 0.03 or 3%)
   - `position_manager.max_position_pct`: Maximum position size as a percentage (default: 0.10 or 10%)
   - `position_manager.scale_factor`: Scaling factor per point above/below threshold (default: 0.01 or 1%)
   
   **Entry and Exit Parameters:**
   - `strategy.long_threshold`: Minimum confluence score to enter long positions (default: 6)
   - `strategy.short_threshold`: Maximum confluence score to enter short positions (default: 30)
   - `position_manager.trailing_stop_pct`: Trailing stop distance as a percentage (default: 0.02 or 2%)
   
   **Scaling Thresholds:**
   - `position_manager.scaling_threshold.long`: Score above which to start scaling for longs (default: 75)
   - `position_manager.scaling_threshold.short`: Score below which to start scaling for shorts (default: 25)
   
   **Symbol Selection:**
   - `trading.use_signals`: Whether to use dynamic symbol selection from signals (default: true)
   - `exchanges.bybit.websocket.symbols`: Initial symbols to trade if using static symbols
   - `trading.fallback_symbols`: Fallback symbols if no signals are available
   
   **Other Settings:**
   - `strategy.max_active_positions`: Maximum number of concurrent positions (default: 5)
   - `strategy.update_interval`: Number of seconds between market evaluations (default: 60)

## Dynamic Symbol Handling

The system can operate in two modes for symbol selection:

1. **Dynamic Mode (default)**: Automatically trades on symbols that receive signals from the confluence analyzer.
   - Enable by setting `trading.use_signals` to `true`
   - The system starts with a small set of default symbols and adds more as signals are received
   - Fallback symbols are used if no signals are detected

2. **Static Mode**: Trades only on pre-defined symbols specified in configuration.
   - Enable by setting `trading.use_signals` to `false` 
   - Specify symbols in `exchanges.bybit.websocket.symbols` array

You can also specify symbols directly from the command line:
```bash
python src/demo_trading_runner.py --symbols BTCUSDT,ETHUSDT,SOLUSDT
```

## Position Sizing Explained

The system calculates position size based on the confluence score:

1. **Base Position Size**: All trades start with a base position size of 3% of account balance.

2. **Scaling Up for Long Positions**:
   - If the confluence score is above 75, the position size increases.
   - For each point above 75, the position increases by an additional 1% of account balance.
   - Example: A score of 85 would add 10% (85-75) × 1% = 10%, for a total of 13% position size.
   - Position size is capped at 10% of account balance.

3. **Scaling Up for Short Positions**:
   - If the confluence score is below 25, the position size increases.
   - For each point below 25, the position increases by an additional 1% of account balance.
   - Example: A score of 15 would add 10% (25-15) × 1% = 10%, for a total of 13% position size.
   - Position size is capped at 10% of account balance.

## Running the Demo Trading System

Run the demo trading system with:

```bash
python src/demo_trading_runner.py --config config/demo_trading.json --timeout 60
```

This will start the demo trading system with the specified configuration and run it for 60 minutes.

Command line options:
- `--config`: Path to configuration file (default: config/demo_trading.json)
- `--timeout`: Number of minutes to run before stopping (default: 60)
- `--symbols`: Comma-separated list of symbols to trade (overrides config)

## How It Works

The demo trading system consists of the following components:

1. **BybitDemoExchange**: Extends the regular Bybit exchange integration to use the demo API endpoints.

2. **ConfluenceBasedPositionManager**: Manages positions based on confluence scores.
   - Position sizing scales with confluence strength (3%-10% of account)
   - Sets trailing stops at 2% distance from entry
   - Updates trailing stops as the market moves in favor

3. **ConfluenceTradingStrategy**: The core trading strategy that:
   - Analyzes market using the ConfluenceAnalyzer
   - Takes long positions when score ≥ 6
   - Takes short positions when score ≤ 30
   - Manages multiple symbols concurrently

4. **BybitDataFetcher**: Fetches and prepares market data required for analysis.

## Trailing Stop Logic

The system implements dynamic trailing stops to protect profits:

1. For long positions, a trailing stop is set 2% below the entry price.
2. As the price moves up, the stop moves up to maintain the 2% distance from the current price.
3. For short positions, a trailing stop is set 2% above the entry price.
4. As the price moves down, the stop moves down to maintain the 2% distance from the current price.

This ensures that profits are protected while allowing the position to capture maximum gains.

## Logging

Logs are stored in `logs/demo_trading.log` and provide detailed information about:
- Market analysis and confluence scores
- Position entries with size calculations
- Trailing stop placements and updates
- Position exits and P&L
- Errors and warnings

## Extending the System

You can extend the system by:
- Adding new indicators to the ConfluenceAnalyzer
- Implementing custom position sizing logic
- Adding support for more complex order types
- Integrating with other exchanges

## Troubleshooting

If you encounter issues:

1. Check the logs for specific error messages
2. Verify your API credentials are correct
3. Ensure your Bybit account has sufficient demo funds
4. Make sure the system has internet access to connect to Bybit API

## Disclaimer

This is a demo trading system for educational and testing purposes. It is not financial advice. Always use proper risk management when trading with real funds. 