#!/usr/bin/env python3
"""
Diagnose Bybit API timeout issues
"""

import asyncio
import aiohttp
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_direct_api():
    """Test direct API calls to Bybit"""
    print("Testing direct API calls to Bybit...")
    
    async with aiohttp.ClientSession() as session:
        endpoints = [
            ("Server Time", "https://api.bybit.com/v5/market/time"),
            ("Ticker", "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"),
            ("Kline", "https://api.bybit.com/v5/market/kline?category=linear&symbol=BTCUSDT&interval=1&limit=10"),
        ]
        
        for name, url in endpoints:
            try:
                start = time.time()
                async with session.get(url) as response:
                    data = await response.json()
                    elapsed = time.time() - start
                    
                    if data.get('retCode') == 0:
                        print(f"✓ {name}: SUCCESS in {elapsed:.2f}s")
                    else:
                        print(f"✗ {name}: FAILED - {data.get('retMsg', 'Unknown error')}")
            except Exception as e:
                print(f"✗ {name}: ERROR - {str(e)}")

async def test_connection_pool():
    """Test connection pool behavior"""
    print("\nTesting connection pool...")
    
    # Test with different configurations
    configs = [
        {"limit": 10, "limit_per_host": 5},
        {"limit": 100, "limit_per_host": 40},
        {"limit": 150, "limit_per_host": 40},
    ]
    
    for config in configs:
        print(f"\nTesting with config: {config}")
        
        connector = aiohttp.TCPConnector(**config)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Make multiple concurrent requests
            urls = [
                f"https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"
                for _ in range(20)
            ]
            
            tasks = []
            for i, url in enumerate(urls):
                async def fetch(session, url, idx):
                    try:
                        start = time.time()
                        async with session.get(url) as response:
                            data = await response.json()
                            elapsed = time.time() - start
                            return idx, elapsed, data.get('retCode', -1)
                    except asyncio.TimeoutError:
                        return idx, -1, "TIMEOUT"
                    except Exception as e:
                        return idx, -1, str(e)
                
                tasks.append(fetch(session, url, i))
            
            results = await asyncio.gather(*tasks)
            
            success = sum(1 for _, elapsed, code in results if code == 0)
            timeouts = sum(1 for _, elapsed, code in results if code == "TIMEOUT")
            avg_time = sum(elapsed for _, elapsed, _ in results if elapsed > 0) / max(1, sum(1 for _, elapsed, _ in results if elapsed > 0))
            
            print(f"  Success: {success}/20, Timeouts: {timeouts}/20, Avg time: {avg_time:.2f}s")

async def test_existing_implementation():
    """Test the existing Bybit implementation"""
    print("\nTesting existing Bybit implementation...")
    
    try:
        from src.core.exchanges.bybit import BybitExchange
        
        # Create instance
        exchange = BybitExchange({
            'apiKey': 'test',
            'secret': 'test',
            'testnet': True
        })
        
        # Initialize
        await exchange.initialize()
        
        # Test a simple call
        try:
            start = time.time()
            ticker = await exchange.fetch_ticker('BTC/USDT')
            elapsed = time.time() - start
            print(f"✓ fetch_ticker: SUCCESS in {elapsed:.2f}s")
        except Exception as e:
            print(f"✗ fetch_ticker: ERROR - {str(e)}")
        
        # Cleanup
        await exchange.close()
        
    except Exception as e:
        print(f"✗ Failed to test implementation: {str(e)}")

async def main():
    """Run all diagnostic tests"""
    print("=== Bybit API Timeout Diagnostics ===\n")
    
    # Test direct API
    await test_direct_api()
    
    # Test connection pools
    await test_connection_pool()
    
    # Test existing implementation
    await test_existing_implementation()
    
    print("\n=== Diagnostics Complete ===")

if __name__ == "__main__":
    asyncio.run(main())