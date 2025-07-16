#!/usr/bin/env python3
"""
Test market data endpoints that don't require authentication
"""

import asyncio
import aiohttp
import json

async def test_market_data_endpoints():
    """Test public market data endpoints"""
    print("🔍 Testing Public Market Data Endpoints\n")
    
    endpoints = [
        {
            "name": "Server Time",
            "url": "https://api.bybit.com/v5/market/time",
            "description": "Get server time"
        },
        {
            "name": "Market Tickers",
            "url": "https://api.bybit.com/v5/market/tickers?category=linear&limit=5",
            "description": "Get market tickers for top 5 linear perpetuals"
        },
        {
            "name": "Instruments Info",
            "url": "https://api.bybit.com/v5/market/instruments-info?category=linear&limit=5",
            "description": "Get instruments info for linear perpetuals"
        },
        {
            "name": "BTCUSDT Ticker",
            "url": "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT",
            "description": "Get BTCUSDT ticker data"
        }
    ]
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            print(f"=== {endpoint['name']} ===")
            print(f"URL: {endpoint['url']}")
            
            try:
                async with session.get(endpoint['url']) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Success: {data.get('retMsg', 'OK')}")
                        
                        # Show sample data
                        if 'result' in data:
                            result = data['result']
                            if isinstance(result, dict):
                                print(f"   Sample keys: {list(result.keys())[:5]}")
                            elif isinstance(result, list) and result:
                                print(f"   Found {len(result)} items")
                                if result:
                                    print(f"   Sample item keys: {list(result[0].keys())[:5]}")
                        
                        results.append(True)
                    else:
                        print(f"❌ Failed: HTTP {response.status}")
                        text = await response.text()
                        print(f"   Response: {text[:200]}...")
                        results.append(False)
                        
            except Exception as e:
                print(f"❌ Error: {e}")
                results.append(False)
            
            print()
    
    print("=== SUMMARY ===")
    print(f"Public endpoints working: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✅ All public market data endpoints working")
        print("💡 Exchange Manager should work for public data")
        print("💡 The issue is likely with API credentials for private endpoints")
    else:
        print("❌ Some public endpoints failing - network or API issues")
    
    return all(results)

if __name__ == "__main__":
    asyncio.run(test_market_data_endpoints()) 