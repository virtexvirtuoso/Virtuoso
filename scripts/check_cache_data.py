#!/usr/bin/env python3
"""
Check what data is actually in the cache and compare with dashboard
"""
import asyncio
import aiomcache
import json
from datetime import datetime
import aiohttp

async def check_cache_contents():
    """Directly read all cache keys and display contents"""
    
    print("=" * 80)
    print("CACHE DATA INVESTIGATION")
    print("=" * 80)
    print(f"Time: {datetime.now()}")
    print("-" * 80)
    
    # Connect to memcached on VPS (via SSH tunnel if needed)
    cache_client = aiomcache.Client('45.77.40.77', 11211)
    
    # Keys to check
    keys_to_check = [
        b'market:tickers',
        b'market:overview',
        b'analysis:signals',
        b'analysis:market_regime',
        b'market:movers',
        b'system:alerts',
        b'confluence:scores'
    ]
    
    print("\n📦 CACHE CONTENTS:")
    print("-" * 40)
    
    cache_data = {}
    
    for key in keys_to_check:
        try:
            data = await cache_client.get(key)
            key_str = key.decode()
            
            if data:
                # Try to parse as JSON
                try:
                    if key_str == 'analysis:market_regime':
                        parsed = data.decode()
                        cache_data[key_str] = parsed
                        print(f"\n✅ {key_str}:")
                        print(f"   Value: {parsed}")
                    else:
                        parsed = json.loads(data.decode())
                        cache_data[key_str] = parsed
                        
                        print(f"\n✅ {key_str}:")
                        
                        if isinstance(parsed, dict):
                            # Show summary of dict contents
                            for k, v in list(parsed.items())[:5]:
                                if isinstance(v, list):
                                    print(f"   {k}: {len(v)} items")
                                elif isinstance(v, (int, float)):
                                    print(f"   {k}: {v}")
                                elif isinstance(v, str):
                                    print(f"   {k}: {v[:50]}...")
                                else:
                                    print(f"   {k}: {type(v).__name__}")
                        elif isinstance(parsed, list):
                            print(f"   List with {len(parsed)} items")
                            if parsed:
                                print(f"   First item: {parsed[0]}")
                except Exception as e:
                    print(f"\n⚠️  {key_str}: Parse error - {e}")
            else:
                print(f"\n❌ {key_str}: EMPTY")
                
        except Exception as e:
            print(f"\n❌ {key.decode()}: Error - {e}")
    
    await cache_client.close()
    
    # Now check what dashboard is showing
    print("\n" + "=" * 80)
    print("📊 DASHBOARD DATA COMPARISON:")
    print("-" * 40)
    
    async with aiohttp.ClientSession() as session:
        # Check different endpoints
        endpoints = [
            ('/api/dashboard/overview', 'Regular Dashboard'),
            ('/api/dashboard-cached/overview', 'Cached Dashboard'),
            ('/api/fast/overview', 'Fast Dashboard'),
        ]
        
        for endpoint, name in endpoints:
            try:
                async with session.get(f'http://45.77.40.77:8001{endpoint}') as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        print(f"\n{name} ({endpoint}):")
                        
                        # Check key fields
                        if 'summary' in data:
                            summary = data['summary']
                            print(f"   Total Symbols: {summary.get('total_symbols', 'N/A')}")
                            print(f"   Total Volume: {summary.get('total_volume', 'N/A')}")
                            
                        if 'market_regime' in data:
                            print(f"   Market Regime: {data['market_regime']}")
                            
                        if 'signals' in data:
                            signals = data.get('signals', [])
                            print(f"   Signals: {len(signals)} items")
                            
                        if 'cache_hit' in data:
                            print(f"   Cache Hit: {data['cache_hit']}")
                    else:
                        print(f"\n{name}: HTTP {response.status}")
            except Exception as e:
                print(f"\n{name}: Error - {e}")
    
    # Analysis
    print("\n" + "=" * 80)
    print("🔍 DATA CONSISTENCY ANALYSIS:")
    print("-" * 40)
    
    # Check if cache has market data
    if 'market:overview' in cache_data:
        market_data = cache_data['market:overview']
        print(f"\n✅ Market Overview in Cache:")
        print(f"   - Total Symbols: {market_data.get('total_symbols', 0)}")
        print(f"   - Total Volume: {market_data.get('total_volume_24h', 0)}")
    else:
        print("\n❌ No Market Overview in Cache")
    
    # Check if cache has signals
    if 'analysis:signals' in cache_data:
        signals = cache_data['analysis:signals']
        if isinstance(signals, dict) and 'signals' in signals:
            print(f"\n✅ Signals in Cache: {len(signals['signals'])} items")
        else:
            print(f"\n⚠️  Signals in unexpected format")
    else:
        print("\n❌ No Signals in Cache")
    
    print("\n" + "=" * 80)

async def check_service_logs():
    """Check what services are writing to cache"""
    print("\n📝 SERVICE ACTIVITY CHECK:")
    print("-" * 40)
    
    # This would need SSH access to check logs
    print("To check service logs on VPS, run:")
    print("  ssh linuxuser@45.77.40.77 'tail -n 50 /tmp/phase2_services.log'")
    print("  ssh linuxuser@45.77.40.77 'tail -n 50 logs/market_service.log'")
    print("  ssh linuxuser@45.77.40.77 'tail -n 50 logs/analysis_service.log'")

async def main():
    """Run all checks"""
    try:
        await check_cache_contents()
        await check_service_logs()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nNote: Make sure you can connect to VPS memcached on port 11211")
        print("You may need to set up SSH tunnel: ssh -L 11211:localhost:11211 linuxuser@45.77.40.77")

if __name__ == "__main__":
    print("\n🔍 Starting Cache Data Investigation...")
    asyncio.run(main())