#!/usr/bin/env python3
"""
Test Open Interest fix using direct Bybit API
"""

import asyncio
import aiohttp
from src.core.exchanges.manager import ExchangeManager
from src.config.manager import ConfigManager

async def fetch_bybit_open_interest_direct(symbol: str) -> float:
    """
    Fetch Open Interest directly from Bybit API bypassing CCXT
    
    Args:
        symbol: CCXT format symbol (e.g., 'BTC/USDT:USDT')
        
    Returns:
        float: Open Interest value
    """
    try:
        # Convert CCXT symbol to Bybit format
        if ':USDT' in symbol:  # Perpetual futures
            bybit_symbol = symbol.replace('/USDT:USDT', 'USDT')  # BTC/USDT:USDT -> BTCUSDT
            category = 'linear'
        elif '/USDT' in symbol:  # Spot
            bybit_symbol = symbol.replace('/', '')  # BTC/USDT -> BTCUSDT  
            category = 'spot'
        elif '/USD' in symbol:  # Inverse contracts
            bybit_symbol = symbol.replace('/', '')  # BTC/USD -> BTCUSD
            category = 'inverse'
        else:
            # Assume it's already in Bybit format
            bybit_symbol = symbol
            category = 'linear'  # Default to linear
        
        # Bybit API endpoint
        url = "https://api.bybit.com/v5/market/tickers"
        params = {
            'category': category,
            'symbol': bybit_symbol
        }
        
        print(f"🔍 Fetching OI for {symbol} -> {bybit_symbol} ({category})")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    print(f"❌ Bybit API error for {symbol}: HTTP {response.status}")
                    return 0
                
                data = await response.json()
                
                if data.get('retCode') != 0:
                    print(f"❌ Bybit API returned error for {symbol}: {data}")
                    return 0
                
                result = data.get('result', {})
                ticker_list = result.get('list', [])
                
                if not ticker_list:
                    print(f"❌ No Bybit ticker data for {symbol} ({bybit_symbol})")
                    return 0
                
                ticker = ticker_list[0]
                
                # Extract Open Interest
                oi_raw = ticker.get('openInterest') or ticker.get('openInterestValue')
                if oi_raw:
                    try:
                        oi = float(oi_raw)
                        print(f"🎯 SUCCESS: OI for {symbol}: {oi:,.2f} ({category}/{bybit_symbol})")
                        return oi
                    except (ValueError, TypeError) as e:
                        print(f"❌ Error parsing Bybit OI for {symbol}: {oi_raw} - {e}")
                        return 0
                else:
                    print(f"❌ No OI fields in Bybit response for {symbol}")
                    return 0
                    
    except Exception as e:
        print(f"❌ Error fetching Bybit OI for {symbol}: {e}")
        return 0

async def test_oi_fix():
    """Test the Open Interest fix with market reporter symbols"""
    
    print("=" * 60)
    print("TESTING OPEN INTEREST FIX")
    print("=" * 60)
    
    # Test symbols from market reporter
    test_symbols = [
        'BTC/USDT:USDT',
        'ETH/USDT:USDT', 
        'SOL/USDT:USDT',
        'DOGE/USDT:USDT',
        'XRP/USDT:USDT'
    ]
    
    total_oi = 0
    successful_extractions = 0
    
    for symbol in test_symbols:
        print(f"\n{'='*40}")
        print(f"Testing: {symbol}")
        print(f"{'='*40}")
        
        oi = await fetch_bybit_open_interest_direct(symbol)
        
        if oi > 0:
            total_oi += oi
            successful_extractions += 1
            print(f"✅ Success: {oi:,.2f}")
        else:
            print(f"❌ Failed: 0")
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successful extractions: {successful_extractions}/{len(test_symbols)}")
    print(f"📊 Total Open Interest: {total_oi:,.2f}")
    print(f"💰 Average OI per symbol: {total_oi/len(test_symbols):,.2f}")
    
    if successful_extractions > 0:
        print(f"\n🎯 SUCCESS: Direct API approach works!")
        print(f"   This proves the fix will resolve the Open Interest issue.")
    else:
        print(f"\n❌ FAILED: Direct API approach not working")

if __name__ == "__main__":
    asyncio.run(test_oi_fix()) 