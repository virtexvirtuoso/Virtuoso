#!/usr/bin/env python3
"""
Test the simplified cache system
"""
import asyncio
import json
import sys
import time

sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

async def test_cache_service():
    """Test the new consolidated cache service"""
    from api.cache.cache_service import cache_service
    
    print("🧪 Testing Simplified Cache System")
    print("===================================\n")
    
    # Test 1: Connection
    print("Test 1: Cache Connection")
    await cache_service.connect()
    if cache_service.connected:
        print("  ✅ Connected to memcached")
    else:
        print("  ❌ Failed to connect")
        return
    
    # Test 2: Set and Get
    print("\nTest 2: Basic Set/Get Operations")
    test_data = {'test': 'value', 'timestamp': int(time.time())}
    success = await cache_service.set('test:key', test_data, ttl=60)
    print(f"  Set operation: {'✅' if success else '❌'}")
    
    retrieved = await cache_service.get('test:key')
    print(f"  Get operation: {'✅' if retrieved == test_data else '❌'}")
    
    # Test 3: Mobile Data
    print("\nTest 3: Mobile Data Retrieval")
    
    # First populate some test signals
    test_signals = {
        'signals': [
            {
                'symbol': f'TEST{i}USDT',
                'score': 70 + i,
                'price': 100 * (i + 1),
                'change_24h': 2.5 - (i * 0.2),
                'volume': 1000000 + (i * 100000),
                'sentiment': 'BULLISH' if i < 5 else 'NEUTRAL',
                'components': {
                    'technical': 65 + i,
                    'volume': 70 + i,
                    'orderflow': 68 + i
                }
            }
            for i in range(15)  # Create 15 test signals
        ],
        'timestamp': int(time.time())
    }
    
    await cache_service.set('analysis:signals', test_signals, ttl=60)
    print("  📝 Populated cache with 15 test signals")
    
    # Get mobile data
    mobile_data = await cache_service.get_mobile_data()
    
    print(f"  📱 Mobile data retrieved:")
    print(f"     - Confluence scores: {len(mobile_data['confluence_scores'])} symbols")
    print(f"     - Market regime: {mobile_data['market_overview']['market_regime']}")
    print(f"     - Has movers: {bool(mobile_data['top_movers'])}")
    
    if mobile_data['confluence_scores']:
        print(f"\n  📊 First 3 symbols:")
        for score in mobile_data['confluence_scores'][:3]:
            print(f"     • {score['symbol']}: Score={score['score']}, Price=${score['price']}")
    
    # Test 4: Performance
    print("\nTest 4: Performance Test")
    start = time.perf_counter()
    for _ in range(10):
        await cache_service.get('test:key')
    elapsed = (time.perf_counter() - start) * 1000
    avg_time = elapsed / 10
    print(f"  ⚡ Average get time: {avg_time:.2f}ms")
    print(f"  {'✅' if avg_time < 10 else '⚠️'} Performance: {'Excellent' if avg_time < 5 else 'Good' if avg_time < 10 else 'Needs optimization'}")
    
    # Cleanup
    await cache_service.close()
    print("\n✅ All tests completed!")

async def test_unified_dashboard():
    """Test the unified dashboard endpoints"""
    print("\n\n🧪 Testing Unified Dashboard")
    print("============================\n")
    
    import aiohttp
    
    base_url = "http://localhost:8003/api/dashboard"
    
    async with aiohttp.ClientSession() as session:
        # Test health endpoint
        print("Test 1: Health Check")
        try:
            async with session.get(f"{base_url}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"  ✅ Health: {data.get('status', 'unknown')}")
                    print(f"     Cache: {data.get('cache_connected', False)}")
                else:
                    print(f"  ❌ Health check failed: {resp.status}")
        except Exception as e:
            print(f"  ⚠️  Server not running: {e}")
            print("     Start server with: ./venv311/bin/python src/main.py")
            return
        
        # Test mobile-data endpoint
        print("\nTest 2: Mobile Data Endpoint")
        try:
            async with session.get(f"{base_url}/mobile-data") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    scores = data.get('confluence_scores', [])
                    print(f"  ✅ Mobile endpoint returned {len(scores)} symbols")
                    print(f"     Response time: {data.get('response_time_ms', 'N/A')}ms")
                    print(f"     Source: {data.get('source', 'unknown')}")
                else:
                    print(f"  ❌ Mobile endpoint failed: {resp.status}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # Test signals endpoint
        print("\nTest 3: Signals Endpoint")
        try:
            async with session.get(f"{base_url}/signals?limit=5") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    signals = data.get('signals', [])
                    print(f"  ✅ Signals endpoint returned {len(signals)} signals")
                    print(f"     Total available: {data.get('count', 0)}")
                else:
                    print(f"  ❌ Signals endpoint failed: {resp.status}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n✅ Dashboard tests completed!")

if __name__ == "__main__":
    print("=" * 50)
    print(" SIMPLIFIED CACHE SYSTEM TEST SUITE")
    print("=" * 50)
    
    # Run cache service tests
    asyncio.run(test_cache_service())
    
    # Run dashboard tests
    asyncio.run(test_unified_dashboard())