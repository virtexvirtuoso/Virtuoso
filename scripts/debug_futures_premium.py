#!/usr/bin/env python3
"""
Debug script to test Bybit futures premium calculation
"""

import os
import sys
import json
import asyncio
import aiohttp
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

async def test_bybit_api_directly():
    """Test Bybit API directly to see data structure"""
    
    print("🔍 Testing Bybit API directly for futures premium data")
    print("=" * 60)
    
    symbols_to_test = [
        ("BTCUSDT", "linear"),      # Perpetual
        ("BTCUSDM25", "inverse"),   # June quarterly  
        ("ETHUSDM25", "inverse"),   # ETH June quarterly
        ("ETHUSDT", "linear"),      # ETH Perpetual
    ]
    
    async with aiohttp.ClientSession() as session:
        for symbol, category in symbols_to_test:
            print(f"\n📊 Testing {symbol} (category: {category})")
            print("-" * 40)
            
            url = "https://api.bybit.com/v5/market/tickers"
            params = {"category": category, "symbol": symbol}
            
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if result.get('retCode') == 0 and result.get('result') and result['result'].get('list'):
                            ticker_data = result['result']['list'][0]
                            
                            print(f"✅ API Response Structure:")
                            print(f"   Symbol: {ticker_data.get('symbol')}")
                            print(f"   Last Price: {ticker_data.get('lastPrice')}")
                            print(f"   Mark Price: {ticker_data.get('markPrice')}")
                            print(f"   Index Price: {ticker_data.get('indexPrice')}")
                            print(f"   Funding Rate: {ticker_data.get('fundingRate')}")
                            print(f"   Basis: {ticker_data.get('basis')}")
                            
                            # Test our field extraction logic
                            print(f"\n🔧 Testing Field Extraction:")
                            mark_price = test_extract_field(ticker_data, 'mark_price')
                            index_price = test_extract_field(ticker_data, 'index_price') 
                            funding_rate = test_extract_field(ticker_data, 'funding_rate')
                            
                            print(f"   Extracted Mark Price: {mark_price}")
                            print(f"   Extracted Index Price: {index_price}")
                            print(f"   Extracted Funding Rate: {funding_rate}")
                            
                            # Calculate premium if possible
                            if mark_price > 0 and index_price > 0:
                                premium = ((mark_price - index_price) / index_price) * 100
                                print(f"   📈 Calculated Premium: {premium:.4f}%")
                            else:
                                print(f"   ❌ Cannot calculate premium (mark: {mark_price}, index: {index_price})")
                        else:
                            print(f"❌ No data in API response")
                            print(f"   Response: {result}")
                    else:
                        print(f"❌ HTTP Error {response.status}")
                        
            except Exception as e:
                print(f"❌ Error fetching {symbol}: {e}")

def test_extract_field(data, field_type):
    """Test the field extraction logic used by the system"""
    
    # Field mappings from MarketReporter
    BYBIT_FIELD_MAPPINGS = {
        'mark_price': ['markPrice', 'mark_price'],
        'index_price': ['indexPrice', 'index_price'],
        'funding_rate': ['fundingRate', 'funding_rate'],
        'last': ['lastPrice', 'last', 'price']
    }
    
    if data is None:
        return 0
        
    # Try direct access
    field_names = BYBIT_FIELD_MAPPINGS.get(field_type, [field_type])
    for name in field_names:
        if name in data:
            try:
                return float(data[name])
            except (ValueError, TypeError):
                continue
                
    return 0

async def test_via_exchange_wrapper():
    """Test via the actual exchange wrapper to see if there's a difference"""
    
    print("\n\n🔧 Testing via Exchange Wrapper")
    print("=" * 60)
    
    try:
        # Import the exchange
        from core.exchanges.bybit import BybitExchange
        
        # Initialize exchange 
        exchange = BybitExchange(api_key="", secret="", sandbox=False)
        
        # Test perpetual ticker
        print("\n📊 Testing BTCUSDT via exchange wrapper:")
        try:
            ticker = await exchange.fetch_ticker('BTCUSDT')
            print(f"   Exchange ticker structure: {type(ticker)}")
            if isinstance(ticker, dict):
                print(f"   Keys available: {list(ticker.keys())}")
                
                # Check if there's an 'info' field
                if 'info' in ticker:
                    info = ticker['info']
                    print(f"   Info keys: {list(info.keys()) if isinstance(info, dict) else 'Not a dict'}")
                    print(f"   Mark Price from info: {info.get('markPrice', 'Not found')}")
                    print(f"   Index Price from info: {info.get('indexPrice', 'Not found')}")
                
                # Check direct fields
                print(f"   Direct mark price: {ticker.get('markPrice', 'Not found')}")
                print(f"   Direct index price: {ticker.get('indexPrice', 'Not found')}")
                
        except Exception as e:
            print(f"   ❌ Error via exchange: {e}")
            
        await exchange.close()
        
    except Exception as e:
        print(f"❌ Error testing exchange wrapper: {e}")

async def main():
    """Main test function"""
    
    print("🚀 Debugging Bybit Futures Premium Calculation")
    print("=" * 60)
    
    # Test 1: Direct API calls
    await test_bybit_api_directly()
    
    # Test 2: Exchange wrapper
    await test_via_exchange_wrapper()
    
    print("\n\n📋 SUMMARY")
    print("=" * 60)
    print("This script helps identify why futures premium calculation")
    print("is returning 'mark: 0' in the logs despite API having valid data.")
    print("\nNext steps:")
    print("1. Check if field extraction logic matches API response structure")
    print("2. Verify if exchange wrapper modifies the data structure")
    print("3. Update field mappings if needed")

if __name__ == '__main__':
    asyncio.run(main()) 