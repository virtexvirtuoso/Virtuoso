#!/usr/bin/env python3
"""
Test script to replicate the exact futures premium calculation flow
"""

import os
import sys
import asyncio
import aiohttp
import logging

# Add src to path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_real_flow():
    """Test the exact flow used by the market reporter"""
    
    print("🔧 Testing Real Market Reporter Flow")
    print("=" * 60)
    
    # Test symbols from the logs
    symbols_to_test = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "AVAXUSDT"]
    
    for symbol in symbols_to_test:
        print(f"\n📊 Testing {symbol}")
        print("-" * 40)
        
        # Step 1: Fetch perpetual ticker (this should work)
        print("Step 1: Fetching perpetual ticker...")
        perp_ticker = await fetch_ticker_direct(symbol, "linear")
        
        if perp_ticker:
            # Extract fields using the same logic as MarketReporter
            mark_price = extract_bybit_field(perp_ticker, 'mark_price')
            index_price = extract_bybit_field(perp_ticker, 'index_price')
            print(f"   ✅ Perpetual: mark={mark_price}, index={index_price}")
            
            # Step 2: Try to find quarterly futures
            print("Step 2: Finding quarterly futures...")
            quarterly_found = await find_quarterly_futures(symbol.replace('USDT', ''))
            
            if quarterly_found:
                print(f"   ✅ Found quarterly futures!")
                for contract in quarterly_found:
                    print(f"      {contract['symbol']}: mark={contract['mark']}, price={contract['price']}")
                    
                    # Step 3: Try premium calculation
                    if mark_price > 0 and index_price > 0:
                        premium = ((mark_price - index_price) / index_price) * 100
                        print(f"   📈 Premium calculation: {premium:.4f}%")
                    else:
                        print(f"   ❌ Cannot calculate premium: mark={mark_price}, index={index_price}")
            else:
                print("   ❌ No quarterly futures found")
                
        else:
            print("   ❌ Failed to fetch perpetual ticker")

async def fetch_ticker_direct(symbol, category):
    """Fetch ticker using direct API call"""
    url = "https://api.bybit.com/v5/market/tickers"
    params = {"category": category, "symbol": symbol}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('retCode') == 0 and result.get('result') and result['result'].get('list'):
                        return result['result']['list'][0]
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
    
    return None

async def find_quarterly_futures(base_asset):
    """Find quarterly futures using the same logic as MarketReporter"""
    from datetime import datetime, timedelta
    
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Generate quarterly symbols (same logic as MarketReporter)
    quarterly_symbols = []
    
    # June quarterly (M25)
    if 6 >= current_month or 6 == 12:
        quarterly_symbols.append((f"{base_asset}USDM25", "inverse"))
        quarterly_symbols.append((f"{base_asset}USDT-26JUN25", "linear"))
    
    # September quarterly (U25)  
    if 9 >= current_month or 9 == 12:
        quarterly_symbols.append((f"{base_asset}USDU25", "inverse"))
        quarterly_symbols.append((f"{base_asset}USDT-27SEP25", "linear"))
    
    # December quarterly (Z25)
    quarterly_symbols.append((f"{base_asset}USDZ25", "inverse"))
    quarterly_symbols.append((f"{base_asset}USDT-29DEC25", "linear"))
    
    found_contracts = []
    
    for symbol_item in quarterly_symbols:
        if isinstance(symbol_item, tuple):
            symbol, category = symbol_item
        else:
            symbol = symbol_item
            category = "linear"
            
        print(f"   Trying {symbol} (category: {category})")
        
        ticker = await fetch_ticker_direct(symbol, category)
        if ticker:
            mark_price = extract_bybit_field(ticker, 'mark_price')
            last_price = extract_bybit_field(ticker, 'last')
            
            if mark_price > 0 or last_price > 0:
                found_contracts.append({
                    'symbol': symbol,
                    'category': category,
                    'mark': mark_price,
                    'price': last_price or mark_price,
                    'ticker_data': ticker
                })
                print(f"      ✅ Found: {symbol} - mark: {mark_price}, price: {last_price}")
                break  # Found working format
        else:
            print(f"      ❌ Not found: {symbol}")
    
    return found_contracts

def extract_bybit_field(data, field_type, default=0):
    """Extract field using MarketReporter logic"""
    BYBIT_FIELD_MAPPINGS = {
        'mark_price': ['markPrice', 'mark_price'],
        'index_price': ['indexPrice', 'index_price'],
        'funding_rate': ['fundingRate', 'funding_rate'],
        'last': ['lastPrice', 'last', 'price']
    }
    
    if data is None:
        return default
        
    # Try to get from 'info' if it exists (common in CCXT)
    if 'info' in data:
        info = data['info']
        field_names = BYBIT_FIELD_MAPPINGS.get(field_type, [field_type])
        
        for name in field_names:
            if name in info:
                try:
                    return float(info[name])
                except (ValueError, TypeError):
                    continue
    
    # Try direct access as fallback
    field_names = BYBIT_FIELD_MAPPINGS.get(field_type, [field_type])
    for name in field_names:
        if name in data:
            try:
                return float(data[name])
            except (ValueError, TypeError):
                continue
                
    return default

async def main():
    """Main test function"""
    print("🚀 Testing Real Futures Premium Flow")
    print("=" * 60)
    print("This script replicates the exact logic used by MarketReporter")
    print("to identify why 'mark: 0' appears in logs.\n")
    
    await test_real_flow()
    
    print("\n\n📋 CONCLUSION")
    print("=" * 60)
    print("If this script shows valid data but the logs show 'mark: 0',")
    print("the issue is likely in:")
    print("1. Exchange wrapper data transformation")
    print("2. Async execution timing") 
    print("3. Error handling that silently fails")

if __name__ == '__main__':
    asyncio.run(main()) 