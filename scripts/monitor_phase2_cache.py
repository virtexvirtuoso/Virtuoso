#!/usr/bin/env python3
"""
Monitor Phase 2 Cache Performance
Shows cache contents, service health, and response times
"""
import asyncio
import json
import time
import sys
import os
from datetime import datetime
import aiomcache

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def monitor_cache():
    """Monitor cache contents and performance"""
    print("=" * 70)
    print("PHASE 2 CACHE MONITORING")
    print("=" * 70)
    
    cache = aiomcache.Client('localhost', 11211)
    
    try:
        # Service Health
        print("\n📊 SERVICE HEALTH")
        print("-" * 40)
        
        # Market Service
        market_status = await cache.get(b'service:market:status')
        if market_status:
            status = json.loads(market_status.decode())
            print(f"Market Service:  {status.get('status', 'unknown').upper()}")
            print(f"  Last Update:   {status.get('last_update', 'N/A')}")
            print(f"  Error Count:   {status.get('error_count', 0)}")
        else:
            print("Market Service:  NOT RUNNING")
        
        # Analysis Service
        analysis_status = await cache.get(b'service:analysis:status')
        if analysis_status:
            status = json.loads(analysis_status.decode())
            print(f"\nAnalysis Service: {status.get('status', 'unknown').upper()}")
            print(f"  Last Analysis: {status.get('last_analysis', 'N/A')}")
            print(f"  Error Count:   {status.get('error_count', 0)}")
        else:
            print("\nAnalysis Service: NOT RUNNING")
        
        # Cache Contents
        print("\n📦 CACHE CONTENTS")
        print("-" * 40)
        
        cache_keys = [
            (b'market:tickers', 'Market Tickers'),
            (b'market:dashboard', 'Dashboard Data'),
            (b'market:top_gainers', 'Top Gainers'),
            (b'market:top_losers', 'Top Losers'),
            (b'market:overview', 'Market Overview'),
            (b'market:health', 'Market Health'),
            (b'analysis:results', 'Analysis Results'),
            (b'analysis:market_regime', 'Market Regime'),
            (b'analysis:volatility', 'Volatility'),
            (b'analysis:momentum', 'Momentum')
        ]
        
        for key, name in cache_keys:
            data = await cache.get(key)
            if data:
                if key == b'analysis:market_regime':
                    print(f"✅ {name:20} = {data.decode()}")
                else:
                    parsed = json.loads(data.decode())
                    if isinstance(parsed, dict):
                        if 'timestamp' in parsed:
                            age = int(time.time() - parsed.get('timestamp', time.time()))
                            print(f"✅ {name:20} ({age}s old)")
                        else:
                            print(f"✅ {name:20} ({len(parsed)} items)")
                    else:
                        print(f"✅ {name:20} (available)")
            else:
                print(f"❌ {name:20} (missing)")
        
        # Performance Metrics
        print("\n⚡ PERFORMANCE METRICS")
        print("-" * 40)
        
        # Market data freshness
        market_health = await cache.get(b'market:health')
        if market_health:
            health = json.loads(market_health.decode())
            print(f"Market Fetch Time:    {health.get('fetch_time_ms', 0):.0f}ms")
            print(f"Symbol Count:         {health.get('symbol_count', 0)}")
            print(f"Update Interval:      {health.get('update_interval', 0)}s")
            
            last_update = health.get('last_update', 0)
            if last_update:
                age = int(time.time() - last_update)
                print(f"Data Age:            {age}s")
        
        # Analysis performance
        analysis_health = await cache.get(b'analysis:health')
        if analysis_health:
            health = json.loads(analysis_health.decode())
            print(f"\nAnalysis Time:       {health.get('analysis_time_ms', 0):.0f}ms")
            
            last_analysis = health.get('last_analysis', 0)
            if last_analysis:
                age = int(time.time() - last_analysis)
                print(f"Analysis Age:        {age}s")
        
        # Market Overview
        print("\n📈 MARKET OVERVIEW")
        print("-" * 40)
        
        overview = await cache.get(b'market:overview')
        if overview:
            data = json.loads(overview.decode())
            print(f"Total Symbols:       {data.get('total_symbols', 0)}")
            print(f"24h Volume:          ${data.get('total_volume_24h', 0):,.0f}")
            print(f"Avg 24h Change:      {data.get('average_change_24h', 0):.2f}%")
            print(f"Data Source:         {data.get('data_source', 'Unknown')}")
        
        # Analysis Summary
        analysis = await cache.get(b'analysis:results')
        if analysis:
            data = json.loads(analysis.decode())
            
            if 'momentum' in data:
                mom = data['momentum']
                print(f"\nMomentum:")
                print(f"  Gainers:           {mom.get('gainers', 0)}")
                print(f"  Losers:            {mom.get('losers', 0)}")
                print(f"  Score:             {mom.get('momentum_score', 0):.3f}")
            
            if 'volatility' in data:
                vol = data['volatility']
                print(f"\nVolatility:")
                print(f"  Level:             {vol.get('level', 'unknown')}")
                print(f"  Std Dev:           {vol.get('std_deviation', 0):.2f}")
        
        # Top Movers
        print("\n🚀 TOP MOVERS")
        print("-" * 40)
        
        # Top Gainers
        gainers = await cache.get(b'market:top_gainers')
        if gainers:
            gainers_list = json.loads(gainers.decode())
            print("Top 3 Gainers:")
            for g in gainers_list[:3]:
                print(f"  {g['symbol']:15} +{g['change_24h']:.2f}% ${g['price']:.4f}")
        
        # Top Losers
        losers = await cache.get(b'market:top_losers')
        if losers:
            losers_list = json.loads(losers.decode())
            print("\nTop 3 Losers:")
            for l in losers_list[:3]:
                print(f"  {l['symbol']:15} {l['change_24h']:.2f}% ${l['price']:.4f}")
        
        # Response Time Test
        print("\n⏱️  CACHE RESPONSE TIME TEST")
        print("-" * 40)
        
        test_keys = [b'market:tickers', b'analysis:results', b'market:overview']
        for key in test_keys:
            start = time.perf_counter()
            data = await cache.get(key)
            elapsed = (time.perf_counter() - start) * 1000
            key_name = key.decode().split(':')[1]
            print(f"{key_name:15} = {elapsed:.2f}ms")
        
        print("\n" + "=" * 70)
        print("END OF MONITORING REPORT")
        print("=" * 70)
        
        await cache.close()
        
    except Exception as e:
        print(f"❌ Monitoring error: {e}")
        await cache.close()


if __name__ == "__main__":
    asyncio.run(monitor_cache())