#!/usr/bin/env python3
"""
Script to diagnose OHLCV data collection issues on the VPS.

This script will:
1. Test exchange connectivity
2. Try to fetch OHLCV data directly
3. Check data transformation pipeline
4. Identify where the empty data is coming from
"""

import asyncio
import sys
import os
import traceback
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from core.exchanges.manager import ExchangeManager
from monitoring.data_collector import DataCollector


async def test_exchange_connectivity():
    """Test basic exchange connectivity."""
    print("=" * 60)
    print("1. TESTING EXCHANGE CONNECTIVITY")
    print("=" * 60)
    
    try:
        # Initialize exchange manager
        exchange_manager = ExchangeManager()
        await exchange_manager.initialize()
        
        # Get primary exchange
        exchange = await exchange_manager.get_primary_exchange()
        if not exchange:
            print("❌ ERROR: No primary exchange available")
            return False
            
        print(f"✅ Connected to {exchange.exchange_id}")
        
        # Test basic API call
        ticker = await exchange.fetch_ticker('BTCUSDT')
        print(f"✅ Ticker test successful: BTC = ${ticker['last']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Exchange connectivity failed: {str(e)}")
        traceback.print_exc()
        return False


async def test_ohlcv_fetching():
    """Test OHLCV data fetching directly."""
    print("\n" + "=" * 60)
    print("2. TESTING OHLCV DATA FETCHING")
    print("=" * 60)
    
    try:
        # Initialize exchange manager
        exchange_manager = ExchangeManager()
        await exchange_manager.initialize()
        
        # Get primary exchange
        exchange = await exchange_manager.get_primary_exchange()
        if not exchange:
            print("❌ ERROR: No primary exchange available")
            return False
        
        # Test symbols
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        timeframes = ['5m', '30m', '4h']
        
        for symbol in test_symbols:
            print(f"\nTesting {symbol}:")
            
            for timeframe in timeframes:
                try:
                    candles = await exchange.fetch_ohlcv(symbol, timeframe, limit=10)
                    if candles:
                        print(f"  ✅ {timeframe}: {len(candles)} candles")
                        # Show latest candle
                        latest = candles[-1]
                        print(f"     Latest: O:{latest[1]} H:{latest[2]} L:{latest[3]} C:{latest[4]} V:{latest[5]}")
                    else:
                        print(f"  ❌ {timeframe}: No candles returned")
                        
                except Exception as e:
                    print(f"  ❌ {timeframe}: Error - {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ OHLCV fetching test failed: {str(e)}")
        traceback.print_exc()
        return False


async def test_data_collector():
    """Test the DataCollector class."""
    print("\n" + "=" * 60)
    print("3. TESTING DATA COLLECTOR")
    print("=" * 60)
    
    try:
        # Initialize exchange manager
        exchange_manager = ExchangeManager()
        await exchange_manager.initialize()
        
        # Initialize data collector
        config = {
            'timeframes': {
                'ltf': '5m',
                'mtf': '30m', 
                'htf': '4h'
            },
            'ohlcv_limit': 50
        }
        
        collector = DataCollector(exchange_manager, config)
        await collector.initialize()
        
        # Test data collection
        test_symbol = 'BTCUSDT'
        print(f"Testing data collection for {test_symbol}...")
        
        market_data = await collector.fetch_market_data(test_symbol)
        
        print(f"Market data keys: {list(market_data.keys())}")
        
        if 'ohlcv' in market_data:
            ohlcv = market_data['ohlcv']
            print(f"OHLCV type: {type(ohlcv)}")
            if isinstance(ohlcv, dict):
                print(f"OHLCV timeframes: {list(ohlcv.keys())}")
                for tf, data in ohlcv.items():
                    print(f"  {tf}: {len(data) if hasattr(data, '__len__') else 'N/A'} rows")
            else:
                print(f"❌ OHLCV is not a dictionary: {ohlcv}")
        else:
            print("❌ No OHLCV data in market_data")
        
        return True
        
    except Exception as e:
        print(f"❌ Data collector test failed: {str(e)}")
        traceback.print_exc()
        return False


async def test_confluence_data_transformation():
    """Test the confluence analysis data transformation."""
    print("\n" + "=" * 60)
    print("4. TESTING CONFLUENCE DATA TRANSFORMATION")
    print("=" * 60)
    
    try:
        # Initialize exchange manager
        exchange_manager = ExchangeManager()
        await exchange_manager.initialize()
        
        # Initialize data collector
        config = {
            'timeframes': {
                'ltf': '5m',
                'mtf': '30m', 
                'htf': '4h'
            },
            'ohlcv_limit': 50
        }
        
        collector = DataCollector(exchange_manager, config)
        await collector.initialize()
        
        # Get market data
        market_data = await collector.fetch_market_data('BTCUSDT')
        
        print("Raw market data structure:")
        for key, value in market_data.items():
            if isinstance(value, dict):
                if key == 'ohlcv':
                    print(f"  {key}: {type(value)} with timeframes: {list(value.keys()) if value else 'EMPTY'}")
                else:
                    print(f"  {key}: {type(value)} with keys: {list(value.keys()) if value else 'EMPTY'}")
            else:
                print(f"  {key}: {type(value)}")
        
        # Try to simulate confluence data transformation
        from core.analysis.confluence import ConfluenceAnalyzer
        
        analyzer = ConfluenceAnalyzer()
        
        # Test technical transformation
        print("\nTesting technical data transformation:")
        try:
            technical_data = analyzer._transform_data_for_indicator('technical', market_data)
            print(f"Technical data keys: {list(technical_data.keys())}")
            print(f"Technical OHLCV: {type(technical_data.get('ohlcv'))} - {list(technical_data.get('ohlcv', {}).keys()) if technical_data.get('ohlcv') else 'EMPTY'}")
        except Exception as e:
            print(f"Technical transformation error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Confluence transformation test failed: {str(e)}")
        traceback.print_exc()
        return False


async def main():
    """Run all diagnostic tests."""
    print("VIRTUOSO CCXT - OHLCV DIAGNOSTIC TOOL")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print("=" * 60)
    
    tests = [
        ("Exchange Connectivity", test_exchange_connectivity),
        ("OHLCV Fetching", test_ohlcv_fetching),
        ("Data Collector", test_data_collector),
        ("Confluence Transformation", test_confluence_data_transformation)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    print(f"\nPassed: {total_passed}/{total_tests}")
    
    if total_passed < total_tests:
        print("\n⚠️  Some tests failed. Check the detailed output above.")
        return 1
    else:
        print("\n✅ All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))