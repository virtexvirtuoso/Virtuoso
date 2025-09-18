#!/usr/bin/env python3
"""Debug technical indicators returning 0.00 for BTCUSDT"""

import asyncio
import pandas as pd
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.exchanges.bybit import BybitExchange
from src.indicators.technical_indicators import TechnicalIndicators
from src.config.manager import ConfigManager
from src.core.logger import Logger

async def test_technical_indicators():
    """Test technical indicator calculations for BTCUSDT"""

    # Initialize components
    config_manager = ConfigManager()
    config = config_manager.config
    logger = Logger("debug_technical")

    # Initialize exchange and fetch data
    exchange = BybitExchange(config, logger)
    await exchange.initialize()

    print("\n=== Testing Technical Indicators for BTCUSDT ===\n")

    # Fetch OHLCV data for different timeframes
    symbol = "BTC/USDT"

    # Fetch data for different timeframes
    timeframes = {
        'base': '1m',
        'ltf': '5m',
        'mtf': '30m',
        'htf': '4h'
    }

    market_data = {
        'symbol': symbol,
        'ohlcv': {}
    }

    for tf_name, tf_value in timeframes.items():
        print(f"Fetching {tf_name} ({tf_value}) data...")
        ohlcv = await exchange.fetch_ohlcv(symbol, tf_value, limit=100)

        if ohlcv:
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            print(f"  - Got {len(df)} candles")
            print(f"  - Latest close: {df['close'].iloc[-1]:.2f}")
            print(f"  - Price range: {df['close'].min():.2f} - {df['close'].max():.2f}")
            market_data['ohlcv'][tf_name] = df
        else:
            print(f"  - ERROR: No data received!")

    # Initialize technical indicators
    print("\n=== Calculating Technical Indicators ===\n")
    tech_indicators = TechnicalIndicators(config, logger)

    # Calculate indicators
    result = await tech_indicators.calculate(market_data)

    print(f"Overall Score: {result.get('score', 0):.2f}")
    print("\nComponent Scores:")

    components = result.get('components', {})
    for component, value in components.items():
        if isinstance(value, dict):
            score = value.get('score', 0)
            weight = value.get('weight', 0)
            print(f"  {component:15s}: Score={score:6.2f}, Weight={weight:.2f}")
        else:
            print(f"  {component:15s}: {value}")

    # Print raw RSI calculation for base timeframe
    print("\n=== Direct RSI Calculation Test ===")
    base_df = market_data['ohlcv']['base']

    # Try calculating RSI directly
    import talib
    rsi = talib.RSI(base_df['close'], timeperiod=14)
    print(f"Raw RSI values (last 5): {rsi.tail().tolist()}")
    print(f"Current RSI: {rsi.iloc[-1]:.2f}")

    # Check if we have NaN values
    nan_count = rsi.isna().sum()
    print(f"NaN values in RSI: {nan_count}")

    print("\n=== Checking Data Quality ===")
    print(f"Close prices (last 5): {base_df['close'].tail().tolist()}")
    print(f"Has NaN in close: {base_df['close'].isna().any()}")
    print(f"Data type of close: {base_df['close'].dtype}")

    await exchange.cleanup()

if __name__ == "__main__":
    asyncio.run(test_technical_indicators())