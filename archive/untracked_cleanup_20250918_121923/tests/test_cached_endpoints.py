#!/usr/bin/env python3
"""
Test Cached Endpoints
Tests the cached dashboard endpoints to ensure they're working properly with real data
"""
import asyncio
import aiohttp
import json
import sys
import time

async def test_endpoint(session, url, endpoint_name):
    """Test a single endpoint"""
    try:
        start_time = time.time()
        async with session.get(url, timeout=10) as response:
            end_time = time.time()
            
            if response.status == 200:
                data = await response.json()
                response_time = (end_time - start_time) * 1000
                
                print(f"✅ {endpoint_name}")
                print(f"   Status: {response.status}")
                print(f"   Response time: {response_time:.1f}ms")
                
                # Analyze data content
                if isinstance(data, dict):
                    if 'confluence_scores' in data:
                        scores_count = len(data['confluence_scores'])
                        print(f"   Confluence scores: {scores_count}")
                        
                    if 'signals' in data:
                        signals_count = len(data['signals'])
                        print(f"   Signals: {signals_count}")
                        
                    if 'symbols' in data:
                        symbols_count = len(data['symbols'])
                        print(f"   Symbols: {symbols_count}")
                        
                    if 'market_overview' in data:
                        regime = data['market_overview'].get('market_regime', 'N/A')
                        volume = data['market_overview'].get('total_volume_24h', 0)
                        print(f"   Market regime: {regime}")
                        print(f"   Volume: ${volume/1e9:.1f}B")
                        
                    if 'total_symbols' in data:
                        print(f"   Total symbols: {data['total_symbols']}")
                        
                    if 'count' in data:
                        print(f"   Count: {data['count']}")
                        
                    # Check data source
                    source = data.get('source', 'unknown')
                    data_source = data.get('data_source', 'unknown')
                    print(f"   Source: {source}")
                    if data_source != 'unknown':
                        print(f"   Data source: {data_source}")
                
                print()
                return True
                
            else:
                print(f"❌ {endpoint_name}")
                print(f"   Status: {response.status}")
                text = await response.text()
                print(f"   Error: {text[:200]}")
                print()
                return False
                
    except Exception as e:
        print(f"❌ {endpoint_name}")
        print(f"   Error: {str(e)}")
        print()
        return False

async def main():
    """Test all cached endpoints"""
    # Define endpoints to test
    base_url = "http://localhost:8003"
    endpoints = [
        ("/api/dashboard-cached/mobile-data", "Mobile Dashboard Data"),
        ("/api/dashboard-cached/overview", "Dashboard Overview"), 
        ("/api/dashboard-cached/symbols", "Dashboard Symbols"),
        ("/api/dashboard-cached/signals", "Trading Signals"),
        ("/api/dashboard-cached/market-overview", "Market Overview"),
        ("/api/dashboard-cached/market-analysis", "Market Analysis"),
        ("/api/dashboard-cached/market-movers", "Market Movers"),
        ("/api/dashboard-cached/alerts", "System Alerts"),
        ("/api/dashboard-cached/confluence-scores", "Confluence Scores"),
        ("/api/dashboard-cached/opportunities", "Trading Opportunities"),
        ("/api/dashboard-cached/health", "Health Status")
    ]
    
    print("🧪 Testing Cached Dashboard Endpoints")
    print("=" * 50)
    
    # Test direct cache connection first
    try:
        sys.path.insert(0, '/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')
        from api.cache_adapter_direct import cache_adapter
        
        print("📊 Testing Direct Cache Connection...")
        health = await cache_adapter.health_check()
        cache_status = health.get('status', 'unknown')
        print(f"   Cache Status: {cache_status}")
        
        if cache_status == 'healthy':
            # Get some sample data
            overview = await cache_adapter.get_market_overview()
            signals = await cache_adapter.get_signals()
            print(f"   Cached Symbols: {overview.get('active_symbols', 0)}")
            print(f"   Cached Signals: {len(signals.get('signals', []))}")
        print()
        
    except Exception as e:
        print(f"❌ Cache connection failed: {e}")
        print()
    
    # Test HTTP endpoints
    print("🌐 Testing HTTP Endpoints...")
    async with aiohttp.ClientSession() as session:
        success_count = 0
        total_count = len(endpoints)
        
        for endpoint, name in endpoints:
            url = f"{base_url}{endpoint}"
            success = await test_endpoint(session, url, name)
            if success:
                success_count += 1
    
    # Summary
    print("=" * 50)
    print(f"📈 Test Summary: {success_count}/{total_count} endpoints working")
    
    if success_count == total_count:
        print("🎉 All cached endpoints are working properly!")
    elif success_count > 0:
        print("⚠️  Some endpoints working - cache population successful but HTTP server may have issues")
    else:
        print("❌ No endpoints working - check if FastAPI server is running")

if __name__ == "__main__":
    asyncio.run(main())