#!/usr/bin/env python3
"""
Test confluence cache integration to verify the fix is working
"""

import asyncio
import sys
import os
import json
import time
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_confluence_cache():
    """Test that confluence analysis is being cached properly."""
    
    print("🚀 Testing confluence cache integration...")
    
    try:
        import aiomcache
        
        # Connect to memcache
        client = aiomcache.Client('localhost', 11211)
        
        # Test symbols that should be monitored
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        print(f"\n🔍 Checking cache for symbols: {test_symbols}")
        
        cache_results = {}
        
        for symbol in test_symbols:
            try:
                # Check for confluence breakdown data
                breakdown_key = f'confluence:breakdown:{symbol}'
                breakdown_data = await client.get(breakdown_key.encode())
                
                # Check for simple score
                score_key = f'confluence:score:{symbol}' 
                score_data = await client.get(score_key.encode())
                
                cache_results[symbol] = {
                    'has_breakdown': breakdown_data is not None,
                    'has_score': score_data is not None
                }
                
                if breakdown_data:
                    try:
                        parsed_data = json.loads(breakdown_data.decode())
                        score = parsed_data.get('score', 'N/A')
                        timestamp = parsed_data.get('timestamp', 0)
                        age_seconds = time.time() - timestamp if timestamp else 999
                        
                        print(f"  ✅ {symbol}: Score={score:.2f}, Age={age_seconds:.1f}s")
                        
                        # Show components if available
                        components = parsed_data.get('components', {})
                        if components:
                            comp_str = ", ".join([f"{k}={v:.1f}" for k, v in list(components.items())[:3]])
                            print(f"     Components: {comp_str}...")
                            
                    except json.JSONDecodeError as e:
                        print(f"  ⚠️  {symbol}: Cache data invalid JSON: {e}")
                        
                elif score_data:
                    score = score_data.decode()
                    print(f"  ✅ {symbol}: Score only = {score}")
                    
                else:
                    print(f"  ❌ {symbol}: No cached data found")
                    
            except Exception as e:
                print(f"  ❌ {symbol}: Error checking cache: {e}")
                cache_results[symbol] = {'has_breakdown': False, 'has_score': False, 'error': str(e)}
        
        await client.close()
        
        # Summary
        print(f"\n📊 CACHE TEST SUMMARY:")
        total_symbols = len(test_symbols)
        symbols_with_data = sum(1 for r in cache_results.values() 
                               if r.get('has_breakdown') or r.get('has_score'))
        
        print(f"  Total symbols tested: {total_symbols}")
        print(f"  Symbols with cached data: {symbols_with_data}")
        print(f"  Cache success rate: {(symbols_with_data/total_symbols)*100:.1f}%")
        
        if symbols_with_data == 0:
            print(f"\n⚠️  NO CACHED DATA FOUND")
            print(f"     This could mean:")
            print(f"     1. MarketMonitor hasn't run long enough to generate data")
            print(f"     2. The caching integration isn't working")  
            print(f"     3. Memcached is not running")
            print(f"     4. The symbols aren't being monitored")
            return False
        elif symbols_with_data == total_symbols:
            print(f"\n🎉 ALL SYMBOLS HAVE CACHED DATA - INTEGRATION SUCCESS!")
            return True
        else:
            print(f"\n⚠️  PARTIAL SUCCESS - Some symbols missing cached data")
            return False
            
    except ImportError:
        print(f"❌ aiomcache not available - cannot test cache")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def test_api_endpoint():
    """Test the API endpoint to see if it's receiving cached data."""
    
    print(f"\n🌐 Testing API endpoint...")
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            url = "http://localhost:8003/api/dashboard/confluence-analysis/BTCUSDT"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    score = data.get('score', 'N/A')
                    analysis = data.get('analysis', '')
                    components = data.get('components', {})
                    
                    print(f"  ✅ API Response received:")
                    print(f"     Score: {score}")
                    print(f"     Analysis length: {len(analysis)} chars")
                    print(f"     Components: {len(components)} items")
                    
                    # Check if this looks like real data vs loading message
                    if isinstance(score, (int, float)) and score != 50:
                        print(f"  🎉 REAL CONFLUENCE DATA IS FLOWING TO API!")
                        return True
                    elif len(analysis) > 500:
                        print(f"  🎉 DETAILED ANALYSIS DATA IS FLOWING!")
                        return True
                    else:
                        print(f"  ⏳ API shows loading/default data - may need more time")
                        return False
                else:
                    print(f"  ❌ API returned status {response.status}")
                    return False
                    
    except ImportError:
        print(f"  ⚠️  aiohttp not available - skipping API test")
        return None
    except Exception as e:
        print(f"  ❌ API test failed: {e}")
        return False

async def main():
    """Run the complete test suite."""
    
    print("=" * 60)
    print("CONFLUENCE CACHE INTEGRATION TEST")
    print("=" * 60)
    
    # Test 1: Cache check
    cache_success = await test_confluence_cache()
    
    # Test 2: API endpoint check  
    api_success = await test_api_endpoint()
    
    # Final verdict
    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    print("=" * 60)
    
    print(f"Cache Integration: {'✅ SUCCESS' if cache_success else '❌ FAILED'}")
    print(f"API Data Flow: {'✅ SUCCESS' if api_success else '❌ FAILED' if api_success is False else '⚠️ SKIPPED'}")
    
    if cache_success and api_success:
        print(f"\n🎉 CONFLUENCE CACHE INTEGRATION IS WORKING!")
        print(f"   Real confluence data is now flowing to the mobile dashboard.")
    elif cache_success:
        print(f"\n⚠️  CACHE WORKING BUT API ISSUES")
        print(f"   Data is being cached but may not be reaching the API properly.")
    else:
        print(f"\n❌ INTEGRATION NOT WORKING YET")
        print(f"   Data is not being cached. Check MarketMonitor logs.")
        
    return cache_success and (api_success is not False)

if __name__ == "__main__":
    asyncio.run(main())
