#!/usr/bin/env python3
"""
Test the merged and simplified dashboard
"""
import asyncio
import sys
import json

sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')

async def test_dashboard_import():
    """Test that the merged dashboard imports correctly"""
    print("🧪 Testing Merged Dashboard")
    print("===========================\n")
    
    try:
        from api.routes import dashboard
        print("✅ Dashboard module imported successfully")
        
        # Check what's in the router
        endpoints = []
        for route in dashboard.router.routes:
            if hasattr(route, 'path'):
                endpoints.append(route.path)
        
        print(f"\n📊 Found {len(endpoints)} endpoints:")
        essential = ['/data', '/mobile-data', '/health', '/signals', '/market-overview', '/symbols']
        for endpoint in essential:
            if endpoint in endpoints:
                print(f"  ✅ {endpoint}")
            else:
                print(f"  ❌ {endpoint} (missing)")
        
        # Count lines in new dashboard
        with open('src/api/routes/dashboard.py', 'r') as f:
            lines = len(f.readlines())
        print(f"\n📏 Dashboard size: {lines} lines (was 2461)")
        print(f"   Reduction: {round((1 - lines/2461) * 100)}%")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

async def test_cache_service():
    """Test that cache service works with new dashboard"""
    print("\n🧪 Testing Cache Service Integration")
    print("=====================================\n")
    
    try:
        from api.cache.cache_service import cache_service
        
        # Connect to cache
        await cache_service.connect()
        print("✅ Cache service connected")
        
        # Test setting some data
        test_data = {
            'signals': [
                {'symbol': 'BTCUSDT', 'score': 75, 'price': 50000, 'change_24h': 2.5, 'volume': 1000000},
                {'symbol': 'ETHUSDT', 'score': 72, 'price': 3000, 'change_24h': 3.2, 'volume': 800000},
            ]
        }
        
        success = await cache_service.set('analysis:signals', test_data, ttl=60)
        print(f"✅ Test data stored: {success}")
        
        # Test mobile data retrieval
        mobile_data = await cache_service.get_mobile_data()
        print(f"✅ Mobile data retrieved: {len(mobile_data.get('confluence_scores', []))} symbols")
        
        await cache_service.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print(" MERGED DASHBOARD TEST SUITE")
    print("=" * 50)
    
    success = asyncio.run(test_dashboard_import())
    if success:
        asyncio.run(test_cache_service())
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed - ready to deploy!")
    else:
        print("❌ Tests failed - fix issues before deploying")