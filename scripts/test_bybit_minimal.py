#!/usr/bin/env python3
"""Minimal test to isolate Bybit connection issue"""
import asyncio
import aiohttp
import time
import json

async def test_basic_aiohttp():
    """Test basic aiohttp connection to Bybit"""
    print("Testing basic aiohttp connection...")
    
    url = "https://api.bybit.com/v5/market/tickers"
    params = {"category": "linear"}
    
    start = time.time()
    try:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                elapsed = time.time() - start
                print(f"✅ Success in {elapsed:.2f}s")
                print(f"   Status: {response.status}")
                print(f"   Got {len(data.get('result', {}).get('list', []))} tickers")
                return True
    except asyncio.TimeoutError:
        elapsed = time.time() - start
        print(f"❌ Timeout after {elapsed:.2f}s")
        return False
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ Error after {elapsed:.2f}s: {e}")
        return False

async def test_with_connector():
    """Test with custom connector settings"""
    print("\nTesting with custom connector...")
    
    url = "https://api.bybit.com/v5/market/tickers"
    params = {"category": "linear"}
    
    start = time.time()
    try:
        # Use minimal connector settings
        connector = aiohttp.TCPConnector(
            limit=1,  # Only 1 connection
            force_close=True,  # Force close connections
            enable_cleanup_closed=True
        )
        timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=50)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                elapsed = time.time() - start
                print(f"✅ Success in {elapsed:.2f}s")
                print(f"   Got {len(data.get('result', {}).get('list', []))} tickers")
                return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ Error after {elapsed:.2f}s: {e}")
        return False

async def test_simple_fetch():
    """Test simplest possible fetch"""
    print("\nTesting simplest fetch (just status check)...")
    
    url = "https://api.bybit.com/v5/market/time"
    
    start = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                data = await response.json()
                elapsed = time.time() - start
                print(f"✅ Time API works in {elapsed:.2f}s")
                print(f"   Server time: {data.get('result', {}).get('timeSecond', 'unknown')}")
                return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ Error after {elapsed:.2f}s: {e}")
        return False

async def test_chunked_fetch():
    """Test fetching data in chunks"""
    print("\nTesting chunked fetch (limited symbols)...")
    
    # Try to get just BTCUSDT
    url = "https://api.bybit.com/v5/market/tickers"
    params = {"category": "linear", "symbol": "BTCUSDT"}
    
    start = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=30) as response:
                data = await response.json()
                elapsed = time.time() - start
                
                if data.get('retCode') == 0:
                    tickers = data.get('result', {}).get('list', [])
                    print(f"✅ Single symbol fetch in {elapsed:.2f}s")
                    if tickers:
                        btc = tickers[0]
                        print(f"   BTC/USDT: ${btc.get('lastPrice', 'N/A')}")
                    return True
                else:
                    print(f"❌ API error: {data.get('retMsg')}")
                    return False
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ Error after {elapsed:.2f}s: {e}")
        return False

async def main():
    """Run all tests"""
    print("=" * 50)
    print("BYBIT CONNECTION DIAGNOSTICS")
    print("=" * 50)
    
    # Test 1: Simple time API
    await test_simple_fetch()
    
    # Test 2: Single symbol
    await test_chunked_fetch()
    
    # Test 3: Basic full fetch
    await test_basic_aiohttp()
    
    # Test 4: Custom connector
    await test_with_connector()
    
    print("\n" + "=" * 50)
    print("DIAGNOSTICS COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())