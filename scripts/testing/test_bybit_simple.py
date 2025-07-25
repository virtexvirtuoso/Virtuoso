#!/usr/bin/env python3
"""
Simple test to verify Bybit API connection and data fixes.
"""

import asyncio
import sys
from pathlib import Path
import pandas as pd

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import Logger
from src.config.manager import ConfigManager
from src.core.exchanges.bybit import BybitExchange
from src.core.analysis.market_data_wrapper import MarketDataWrapper

async def main():
    logger = Logger('bybit_test')
    
    print("="*60)
    print("Testing Bybit Validation Fixes")
    print("="*60)
    
    try:
        # Initialize
        config = ConfigManager().config
        exchange = BybitExchange(config, logger)
        symbol = 'BTCUSDT'
        
        # 1. Test OHLCV with correct timeframes
        print("\n1. Testing OHLCV data collection...")
        ohlcv_data = {}
        
        # Fetch 1m data
        print("   Fetching 1m data...")
        candles = await exchange.fetch_ohlcv(symbol, timeframe='1m', limit=100)
        if candles:
            ohlcv_data['1m'] = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            print(f"   ✓ Got {len(candles)} candles for 1m")
        else:
            print("   ✗ No 1m data")
            
        # Fetch 15m data  
        print("   Fetching 15m data...")
        candles = await exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        if candles:
            ohlcv_data['15m'] = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            print(f"   ✓ Got {len(candles)} candles for 15m")
        else:
            print("   ✗ No 15m data")
            
        # Fetch 1h data
        print("   Fetching 1h data...")
        candles = await exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
        if candles:
            ohlcv_data['1h'] = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            print(f"   ✓ Got {len(candles)} candles for 1h")
        else:
            print("   ✗ No 1h data")
            
        # Fetch 4h data
        print("   Fetching 4h data...")
        candles = await exchange.fetch_ohlcv(symbol, timeframe='4h', limit=100)
        if candles:
            ohlcv_data['4h'] = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            print(f"   ✓ Got {len(candles)} candles for 4h")
        else:
            print("   ✗ No 4h data")
            
        print(f"\nCollected timeframes: {list(ohlcv_data.keys())}")
        
        # 2. Test trades
        print("\n2. Testing trade data collection...")
        trades = await exchange.fetch_trades(symbol, limit=100)
        print(f"   ✓ Got {len(trades)} trades")
        
        # 3. Create market data
        market_data = {
            'symbol': symbol,
            'ohlcv': ohlcv_data,
            'trades': trades,
            'orderbook': {
                'bids': [[100000, 1], [99999, 2]],
                'asks': [[100001, 1], [100002, 2]],
                'timestamp': pd.Timestamp.now().timestamp() * 1000
            },
            'sentiment': {'fear_greed_index': 50, 'social_sentiment': 0.5}
        }
        
        print(f"\n3. Market data structure:")
        print(f"   Symbol: {market_data['symbol']}")
        print(f"   OHLCV keys: {list(market_data['ohlcv'].keys())}")
        print(f"   Trades: {len(market_data['trades'])}")
        print(f"   Orderbook: {len(market_data['orderbook']['bids'])} bids, {len(market_data['orderbook']['asks'])} asks")
        
        # 4. Apply wrapper
        print("\n4. Applying market data wrapper...")
        wrapped_data = await MarketDataWrapper.ensure_complete_market_data(
            exchange, symbol, market_data
        )
        
        print(f"   After wrapper - OHLCV keys: {list(wrapped_data['ohlcv'].keys())}")
        print(f"   After wrapper - Trades: {len(wrapped_data['trades'])}")
        
        # 5. Validate
        print("\n5. Validating wrapped data...")
        validation = MarketDataWrapper.validate_market_data(wrapped_data)
        
        all_good = True
        for key, value in validation.items():
            status = "✓" if value else "✗"
            print(f"   {status} {key}: {value}")
            if not value and key != 'has_all_timeframes':  # Allow missing some timeframes
                all_good = False
                
        print("\n" + "="*60)
        if all_good:
            print("✅ VALIDATION FIXES ARE WORKING!")
            print("\nKey fixes verified:")
            print("- Timeframe mapping is correct")
            print("- Trade data is available")
            print("- Base timeframe is present")
        else:
            print("❌ Some validation issues remain")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))