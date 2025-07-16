#!/usr/bin/env python3
"""
Direct Bybit API call to get Open Interest data
"""

import asyncio
import aiohttp
import json

async def test_direct_bybit_api():
    """Make direct API call to Bybit tickers endpoint to get Open Interest"""
    
    print("=" * 60)
    print("DIRECT BYBIT API TEST")
    print("=" * 60)
    
    # Bybit API endpoint for tickers
    base_url = "https://api.bybit.com"
    endpoint = "/v5/market/tickers"
    
    # Test parameters for linear contracts (USDT perpetuals)
    test_cases = [
        {"category": "linear", "symbol": "BTCUSDT"},
        {"category": "linear", "symbol": "ETHUSDT"},
        {"category": "spot", "symbol": "BTCUSDT"},
        {"category": "inverse", "symbol": "BTCUSD"},
    ]
    
    async with aiohttp.ClientSession() as session:
        for params in test_cases:
            print(f"\n{'='*50}")
            print(f"🧪 TESTING: {params}")
            print(f"{'='*50}")
            
            try:
                # Make direct API request
                url = f"{base_url}{endpoint}"
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        print(f"❌ API error: {response.status}")
                        continue
                    
                    data = await response.json()
                    
                    # Check response structure
                    if data.get('retCode') != 0:
                        print(f"❌ API returned error: {data}")
                        continue
                    
                    result = data.get('result', {})
                    ticker_list = result.get('list', [])
                    
                    if not ticker_list:
                        print(f"❌ No ticker data returned")
                        continue
                    
                    ticker = ticker_list[0]  # Get first ticker
                    print(f"✅ Received ticker data for {ticker.get('symbol', 'Unknown')}")
                    
                    # Check for Open Interest fields
                    oi_fields = ['openInterest', 'openInterestValue']
                    oi_data = {}
                    
                    for field in oi_fields:
                        if field in ticker:
                            value = ticker[field]
                            oi_data[field] = value
                            print(f"  🎯 {field}: {value}")
                    
                    if oi_data:
                        print(f"✅ Open Interest found!")
                        
                        # Convert to numbers for verification
                        try:
                            oi = float(oi_data.get('openInterest', 0))
                            oi_value = float(oi_data.get('openInterestValue', 0))
                            print(f"  📊 OI: {oi:,.2f}")
                            print(f"  💰 OI Value: ${oi_value:,.2f}")
                        except (ValueError, TypeError) as e:
                            print(f"  ⚠️ Error parsing OI values: {e}")
                    else:
                        print(f"❌ No Open Interest fields found")
                        print(f"  Available fields: {list(ticker.keys())}")
                    
                    # Show other relevant fields
                    key_fields = ['symbol', 'lastPrice', 'volume24h', 'turnover24h']
                    print(f"\n📈 Key data:")
                    for field in key_fields:
                        if field in ticker:
                            print(f"  {field}: {ticker[field]}")
                            
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("DIRECT API TEST COMPLETED")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(test_direct_bybit_api()) 