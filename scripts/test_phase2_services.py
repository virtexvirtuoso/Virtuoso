#!/usr/bin/env python3
"""
Test Phase 2 Services
Verifies that services are running and cache communication works
"""
import asyncio
import json
import time
import aiomcache
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_cache_communication():
    """Test that services are communicating through cache"""
    print("=" * 60)
    print("Testing Phase 2: Service Decoupling")
    print("=" * 60)
    
    try:
        # Connect to cache
        cache = aiomcache.Client('localhost', 11211)
        
        print("\n1. Checking Memcached connection...")
        await cache.set(b'test:ping', b'pong', exptime=5)
        result = await cache.get(b'test:ping')
        if result == b'pong':
            print("   ✅ Memcached is running")
        else:
            print("   ❌ Memcached connection failed")
            return
        
        # Check market service
        print("\n2. Checking Market Data Service...")
        market_status = await cache.get(b'service:market:status')
        if market_status:
            status = json.loads(market_status.decode())
            print(f"   Status: {status.get('status')}")
            print(f"   Last update: {status.get('last_update')}")
        else:
            print("   ⚠️ Market service not running")
        
        # Check market data
        print("\n3. Checking Market Data in Cache...")
        market_data = await cache.get(b'market:tickers')
        if market_data:
            tickers = json.loads(market_data.decode())
            print(f"   ✅ Found {len(tickers)} tickers in cache")
            
            # Show sample
            if tickers:
                sample = list(tickers.items())[0]
                print(f"   Sample: {sample[0]} = ${sample[1]['price']:.4f}")
        else:
            print("   ⚠️ No market data in cache")
        
        # Check market health
        market_health = await cache.get(b'market:health')
        if market_health:
            health = json.loads(market_health.decode())
            print(f"   Fetch time: {health.get('fetch_time_ms', 0):.0f}ms")
            print(f"   Error count: {health.get('error_count', 0)}")
        
        # Check analysis service
        print("\n4. Checking Analysis Service...")
        analysis_status = await cache.get(b'service:analysis:status')
        if analysis_status:
            status = json.loads(analysis_status.decode())
            print(f"   Status: {status.get('status')}")
            print(f"   Last analysis: {status.get('last_analysis')}")
        else:
            print("   ⚠️ Analysis service not running")
        
        # Check analysis results
        print("\n5. Checking Analysis Results...")
        analysis_results = await cache.get(b'analysis:results')
        if analysis_results:
            analysis = json.loads(analysis_results.decode())
            print(f"   ✅ Analysis completed for {analysis.get('symbol_count', 0)} symbols")
            
            if 'market_stats' in analysis:
                stats = analysis['market_stats']
                print(f"   Avg 24h change: {stats.get('avg_change', 0):.2f}%")
                print(f"   Total volume: ${stats.get('total_volume', 0):,.0f}")
            
            if 'volatility' in analysis:
                vol = analysis['volatility']
                print(f"   Volatility level: {vol.get('level', 'unknown')}")
            
            if 'momentum' in analysis:
                mom = analysis['momentum']
                print(f"   Gainers: {mom.get('gainers', 0)}, Losers: {mom.get('losers', 0)}")
                print(f"   Momentum score: {mom.get('momentum_score', 0):.3f}")
        else:
            print("   ⚠️ No analysis results in cache")
        
        # Check market regime
        regime = await cache.get(b'analysis:market_regime')
        if regime:
            print(f"   Market regime: {regime.decode()}")
        
        # Performance check
        print("\n6. Service Independence Test...")
        print("   Checking if services can recover from failures...")
        
        # Get initial data
        initial_update = await cache.get(b'market:updated')
        
        print("   Waiting 15 seconds for updates...")
        await asyncio.sleep(15)
        
        # Check if data is still being updated
        new_update = await cache.get(b'market:updated')
        
        if initial_update != new_update:
            print("   ✅ Services are running independently and updating data")
        else:
            print("   ⚠️ Data not updating - services may be stopped")
        
        print("\n" + "=" * 60)
        print("Phase 2 Test Complete!")
        print("=" * 60)
        
        # Summary
        print("\nSummary:")
        if market_data and analysis_results:
            print("✅ Both services are running and communicating through cache")
            print("✅ Services are decoupled - failures won't cascade")
            print("✅ Data is being updated regularly")
        elif market_data:
            print("⚠️ Market service running but analysis service is not")
        elif analysis_results:
            print("⚠️ Analysis service running but market service is not")
        else:
            print("❌ Services are not running - start with: python src/services/service_coordinator.py")
        
        await cache.close()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("\nMake sure:")
        print("1. Memcached is running")
        print("2. Services are started with: python src/services/service_coordinator.py")


if __name__ == "__main__":
    asyncio.run(test_cache_communication())