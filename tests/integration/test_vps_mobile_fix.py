#!/usr/bin/env python3
"""
Test script for mobile dashboard fix on VPS
"""
import asyncio
import aiohttp
import json

async def test_vps_mobile_api():
    """Test the VPS mobile API endpoint"""
    url = "http://localhost:8000/api/dashboard/mobile-data"
    
    timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            print("🔄 Testing VPS mobile API...")
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Status: {data.get('status', 'unknown')}")
                    print(f"✅ Live data count: {data.get('live_data_count', 0)}")
                    
                    # Check confluence scores
                    confluence_scores = data.get('confluence_scores', [])
                    print(f"✅ Confluence scores: {len(confluence_scores)} symbols")
                    
                    if confluence_scores:
                        print("📈 Sample symbols with live prices:")
                        for symbol_data in confluence_scores[:3]:
                            symbol = symbol_data.get('symbol', 'N/A')
                            price = symbol_data.get('price', 0)
                            change = symbol_data.get('change_24h', 0)
                            print(f"   {symbol}: ${price} ({change:+.2f}%)")
                    
                    # Check top movers
                    top_movers = data.get('top_movers', {})
                    gainers = top_movers.get('gainers', [])
                    losers = top_movers.get('losers', [])
                    print(f"📊 Top movers - Gainers: {len(gainers)}, Losers: {len(losers)}")
                    
                    if gainers:
                        print("🟢 Top gainers:")
                        for gainer in gainers[:3]:
                            symbol = gainer.get('symbol', 'N/A')
                            change = gainer.get('change', 0)
                            price = gainer.get('price', 0)
                            print(f"   {symbol}: ${price} (+{change:.2f}%)")
                    
                    if losers:
                        print("🔴 Top losers:")
                        for loser in losers[:3]:
                            symbol = loser.get('symbol', 'N/A')
                            change = loser.get('change', 0) 
                            price = loser.get('price', 0)
                            print(f"   {symbol}: ${price} ({change:.2f}%)")
                    
                    print("✅ Mobile dashboard fix is working!")
                    return True
                else:
                    print(f"❌ API returned status {response.status}")
                    text = await response.text()
                    print(f"Response: {text[:200]}...")
                    return False
                    
    except asyncio.TimeoutError:
        print("❌ Timeout - API took too long to respond")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_vps_mobile_api())
    print(f"\n🏁 Test result: {'PASS' if result else 'FAIL'}")