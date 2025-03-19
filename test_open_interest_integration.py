#!/usr/bin/env python3

import asyncio
import logging
import yaml
import json
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.core.exchanges.bybit import BybitExchange
from src.indicators.orderflow_indicators import OrderflowIndicators

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger('test_open_interest_integration')

def print_ohlcv_check(title, market_data):
    """Print detailed information about OHLCV data structure"""
    print(f"\n\n=== {title} ===")
    print(f"Market data keys: {list(market_data.keys())}")
    
    if 'ohlcv' in market_data:
        ohlcv = market_data['ohlcv']
        print(f"OHLCV data structure: {list(ohlcv.keys())}")
        
        # Check each timeframe
        for tf in ohlcv.keys():
            print(f"\nTimeframe: {tf}")
            tf_data = ohlcv[tf]
            
            if isinstance(tf_data, dict):
                print(f"  - Data keys: {list(tf_data.keys())}")
                if 'data' in tf_data and isinstance(tf_data['data'], pd.DataFrame):
                    df = tf_data['data']
                    print(f"  - DataFrame shape: {df.shape}")
                    print(f"  - DataFrame empty: {df.empty}")
                    print(f"  - DataFrame columns: {list(df.columns)}")
                    print(f"  - DataFrame index type: {type(df.index).__name__}")
                    if not df.empty:
                        print(f"  - First candle: {df.iloc[0].to_dict()}")
                        print(f"  - Last candle: {df.iloc[-1].to_dict()}")
            elif isinstance(tf_data, pd.DataFrame):
                print(f"  - Direct DataFrame shape: {tf_data.shape}")
                print(f"  - DataFrame empty: {tf_data.empty}")
                print(f"  - DataFrame columns: {list(tf_data.columns)}")
                print(f"  - DataFrame index type: {type(tf_data.index).__name__}")
                if not tf_data.empty:
                    print(f"  - First candle: {tf_data.iloc[0].to_dict()}")
                    print(f"  - Last candle: {tf_data.iloc[-1].to_dict()}")
            else:
                print(f"  - Unexpected data type: {type(tf_data)}")
    
    print(f"=== END {title} ===\n")

async def main():
    # Flag to control whether to use dummy data or live data
    use_dummy_data = False
    
    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create exchange instance
    exchange = await BybitExchange.get_instance(config)
    
    # Create OrderflowIndicators instance
    indicator = OrderflowIndicators(config)
    
    # Test symbol
    symbol = 'BTCUSDT'
    
    # Fetch market data with integrated open interest
    logger.info(f"Fetching market data for {symbol}...")
    market_data = await exchange.fetch_market_data(symbol)
    
    # Print original OHLCV data structure
    print_ohlcv_check("ORIGINAL OHLCV DATA CHECK", market_data)
    
    if use_dummy_data:
        # Create dummy OHLCV data for testing
        print("\n\n=== FORCING OHLCV DATA FOR TESTING ===")
        print("Creating dummy OHLCV data for testing")
        
        # Create a dummy DataFrame with 30 candles
        now = datetime.now()
        timestamps = [now - timedelta(minutes=5*i) for i in range(30)]
        timestamps.reverse()  # Oldest first
        
        dummy_data = {
            'open': [50000 + i for i in range(30)],
            'high': [50050 + i for i in range(30)],
            'low': [49950 + i for i in range(30)],
            'close': [50025 + i for i in range(30)],
            'volume': [100 + i*10 for i in range(30)]
        }
        
        dummy_df = pd.DataFrame(dummy_data, index=pd.DatetimeIndex([t.strftime('%Y-%m-%d %H:%M:%S') for t in timestamps], name='timestamp'))
        print(f"Created dummy OHLCV data with {len(dummy_df)} candles")
        print(f"Dummy data shape: {dummy_df.shape}")
        print(f"Dummy data first row: {dummy_df.iloc[0].to_dict()}")
        print(f"Dummy data last row: {dummy_df.iloc[-1].to_dict()}")
        print(f"Dummy data index: {dummy_df.index}")
        
        # Add dummy data to all timeframes
        timeframes = ['base', 'ltf', 'mtf', 'htf', '1', '5', '30', '240']
        for tf in timeframes:
            if tf not in market_data['ohlcv']:
                market_data['ohlcv'][tf] = {'data': dummy_df.copy()}
            else:
                market_data['ohlcv'][tf]['data'] = dummy_df.copy()
            print(f"Added dummy OHLCV data to timeframe: {tf}")
        
        # Also add direct DataFrame versions for testing
        for tf in timeframes:
            # Create a direct DataFrame version
            market_data['ohlcv'][f"{tf}_direct"] = dummy_df.copy()
            print(f"Added direct DataFrame to timeframe: {tf}_direct")
        
        print("=== END FORCING OHLCV DATA ===\n\n")
        
        # Print updated OHLCV data structure
        print_ohlcv_check("UPDATED OHLCV DATA CHECK", market_data)
    else:
        print("\n\n=== USING LIVE DATA FOR TESTING ===")
        print("Using real market data from the exchange")
        print("=== END USING LIVE DATA ===\n\n")
    
    # Calculate OrderflowIndicators with the data
    logger.info(f"Calculating OrderflowIndicators...")
    result = indicator.calculate(market_data)
    
    # Print the final score
    print(f"\n\nFinal Order Flow Score: {result['score']:.2f}")
    print(f"Classification: {'Bullish' if result['score'] > 60 else 'Bearish' if result['score'] < 40 else 'Neutral'}")
    
    # Print component scores
    print("\nComponent Scores:")
    for component, score in result['components'].items():
        print(f"- {component}: {score:.2f}")
    
    # Check for price-OI divergence
    if 'divergences' in result and 'price_oi' in result['divergences']:
        div_info = result['divergences']['price_oi']
        logger.info(f"Price-OI divergence detected: {div_info['type']}, strength: {div_info['strength']:.2f}")
        print(f"\nPrice-OI Divergence: {div_info['type'].capitalize()} (Strength: {div_info['strength']:.2f})")
    else:
        logger.info("No price-OI divergence detected")
        print("\nNo price-OI divergence detected")
    
    # Check for price-CVD divergence
    if 'divergences' in result and 'price_cvd' in result['divergences']:
        div_info = result['divergences']['price_cvd']
        logger.info(f"Price-CVD divergence detected: {div_info['type']}, strength: {div_info['strength']:.2f}")
        print(f"\nPrice-CVD Divergence: {div_info['type'].capitalize()} (Strength: {div_info['strength']:.2f})")
    else:
        logger.info("No price-CVD divergence detected")
        print("\nNo price-CVD divergence detected")
    
    # Close exchange connection
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(main()) 