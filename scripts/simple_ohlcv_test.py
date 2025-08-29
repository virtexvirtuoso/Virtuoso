#!/usr/bin/env python3
"""
Simple OHLCV diagnostic script - runs on VPS to test exchange connectivity.
"""

import asyncio
import os
import traceback
from datetime import datetime
import json

# Try basic CCXT import
try:
    import ccxt
    print("✅ CCXT import successful")
except ImportError as e:
    print(f"❌ CCXT import failed: {e}")
    exit(1)


async def test_basic_ccxt():
    """Test basic CCXT functionality directly."""
    print("=" * 60)
    print("DIRECT CCXT OHLCV TEST")
    print("=" * 60)
    
    # Get API credentials from environment
    api_key = os.getenv('BYBIT_API_KEY')
    api_secret = os.getenv('BYBIT_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ Missing API credentials in environment")
        return False
    
    print("✅ API credentials found")
    
    try:
        # Initialize Bybit exchange directly
        exchange = ccxt.bybit({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': False,
            'enableRateLimit': True,
            'timeout': 30000,
        })
        
        print(f"✅ Bybit exchange initialized: {exchange.id}")
        
        # Test basic connectivity with ticker
        print("\nTesting basic connectivity...")
        ticker = await exchange.fetch_ticker('BTC/USDT')
        print(f"✅ BTC ticker: ${ticker['last']}")
        
        # Test OHLCV fetching
        print("\nTesting OHLCV fetching...")
        test_symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
        timeframes = ['5m', '30m', '4h']
        
        for symbol in test_symbols:
            print(f"\nTesting {symbol}:")
            
            for timeframe in timeframes:
                try:
                    candles = await exchange.fetch_ohlcv(symbol, timeframe, limit=10)
                    if candles and len(candles) > 0:
                        print(f"  ✅ {timeframe}: {len(candles)} candles")
                        # Show latest candle info
                        latest = candles[-1]
                        timestamp = datetime.fromtimestamp(latest[0] / 1000)
                        print(f"     Latest ({timestamp}): O:{latest[1]:.4f} C:{latest[4]:.4f} V:{latest[5]:.2f}")
                    else:
                        print(f"  ❌ {timeframe}: Empty candles array")
                        
                except Exception as e:
                    print(f"  ❌ {timeframe}: {str(e)}")
        
        await exchange.close()
        return True
        
    except Exception as e:
        print(f"❌ CCXT test failed: {str(e)}")
        traceback.print_exc()
        return False


async def test_environment():
    """Test environment and dependencies."""
    print("=" * 60) 
    print("ENVIRONMENT TEST")
    print("=" * 60)
    
    # Check Python version
    import sys
    print(f"Python version: {sys.version}")
    
    # Check CCXT version
    print(f"CCXT version: {ccxt.__version__}")
    
    # Check environment variables
    env_vars = [
        'BYBIT_API_KEY',
        'BYBIT_API_SECRET', 
        'APP_PORT',
        'MONITORING_PORT',
        'CACHE_TYPE'
    ]
    
    print("\nEnvironment variables:")
    for var in env_vars:
        value = os.getenv(var)
        if var.endswith('SECRET') or var.endswith('KEY'):
            # Mask sensitive values
            masked = f"{value[:4]}...{value[-4:]}" if value and len(value) > 8 else "NOT SET"
            print(f"  {var}: {masked}")
        else:
            print(f"  {var}: {value or 'NOT SET'}")
    
    # Check working directory
    print(f"\nWorking directory: {os.getcwd()}")
    
    # Check if src directory exists
    src_exists = os.path.exists('src')
    print(f"src directory exists: {src_exists}")
    
    return True


async def main():
    """Run diagnostic tests."""
    print("VIRTUOSO CCXT - SIMPLE OHLCV DIAGNOSTIC")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print("=" * 60)
    
    # Run tests
    await test_environment()
    await test_basic_ccxt()
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())