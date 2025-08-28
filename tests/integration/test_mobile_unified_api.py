#!/usr/bin/env python3
"""
Test script for the new Mobile Unified API
Tests performance improvements and functionality
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime

# Test endpoints
BASE_URL = "http://localhost:8001"
ENDPOINTS = [
    # New simplified mobile unified endpoints
    "/api/mobile-unified/dashboard-data",
    "/api/mobile-unified/health",
    "/api/mobile-unified/symbols",
    "/api/mobile-unified/market-overview",
    
    # Original complex endpoints for comparison
    "/api/dashboard/mobile-data",
]

async def test_endpoint(session: aiohttp.ClientSession, endpoint: str) -> dict:
    """Test a single endpoint and measure performance"""
    url = f"{BASE_URL}{endpoint}"
    start_time = time.perf_counter()
    
    try:
        async with session.get(url, timeout=10) as response:
            response_time = (time.perf_counter() - start_time) * 1000
            
            if response.status == 200:
                data = await response.json()
                return {
                    "endpoint": endpoint,
                    "status": "success",
                    "response_time_ms": round(response_time, 2),
                    "data_size": len(json.dumps(data)),
                    "has_confluence_scores": bool(data.get("confluence_scores") or data.get("symbols")),
                    "confluence_count": len(data.get("confluence_scores", data.get("symbols", []))),
                    "has_market_overview": "market_overview" in data,
                    "has_top_movers": "top_movers" in data,
                    "cache_performance": data.get("performance", {}),
                }
            else:
                return {
                    "endpoint": endpoint,
                    "status": "error",
                    "response_time_ms": round(response_time, 2),
                    "http_status": response.status,
                    "error": await response.text()
                }
                
    except asyncio.TimeoutError:
        response_time = (time.perf_counter() - start_time) * 1000
        return {
            "endpoint": endpoint,
            "status": "timeout",
            "response_time_ms": round(response_time, 2)
        }
    except Exception as e:
        response_time = (time.perf_counter() - start_time) * 1000
        return {
            "endpoint": endpoint,
            "status": "exception",
            "response_time_ms": round(response_time, 2),
            "error": str(e)
        }

async def run_performance_tests():
    """Run performance comparison tests"""
    print("🚀 Mobile API Performance Test")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Test all endpoints
        results = []
        for endpoint in ENDPOINTS:
            print(f"Testing {endpoint}...")
            result = await test_endpoint(session, endpoint)
            results.append(result)
            
            # Print immediate feedback
            if result["status"] == "success":
                print(f"  ✅ {result['response_time_ms']:.2f}ms")
                if result.get("confluence_count", 0) > 0:
                    print(f"     📊 {result['confluence_count']} symbols")
            else:
                print(f"  ❌ {result['status']}: {result.get('error', 'Unknown error')}")
            
            # Wait between tests
            await asyncio.sleep(0.5)
    
    # Analyze results
    print("\n📊 Performance Analysis")
    print("=" * 60)
    
    mobile_unified_results = [r for r in results if "mobile-unified" in r["endpoint"]]
    original_results = [r for r in results if "mobile-data" in r["endpoint"]]
    
    if mobile_unified_results:
        avg_unified = sum(r["response_time_ms"] for r in mobile_unified_results if r["status"] == "success") / len([r for r in mobile_unified_results if r["status"] == "success"])
        print(f"📱 Mobile Unified API Average: {avg_unified:.2f}ms")
    
    if original_results:
        avg_original = sum(r["response_time_ms"] for r in original_results if r["status"] == "success") / len([r for r in original_results if r["status"] == "success"])
        print(f"🔄 Original Mobile API Average: {avg_original:.2f}ms")
    
    if mobile_unified_results and original_results:
        if avg_unified < avg_original:
            improvement = ((avg_original - avg_unified) / avg_original) * 100
            print(f"🎯 Performance Improvement: {improvement:.1f}% faster")
        else:
            regression = ((avg_unified - avg_original) / avg_original) * 100
            print(f"⚠️  Performance Regression: {regression:.1f}% slower")
    
    # Detailed results
    print("\n📋 Detailed Results")
    print("=" * 60)
    
    for result in results:
        status_icon = "✅" if result["status"] == "success" else "❌"
        print(f"{status_icon} {result['endpoint']}")
        print(f"    Response Time: {result['response_time_ms']:.2f}ms")
        
        if result["status"] == "success":
            print(f"    Data Size: {result.get('data_size', 0)} bytes")
            print(f"    Confluence Scores: {result.get('confluence_count', 0)}")
            
            # Show cache performance if available
            cache_perf = result.get("cache_performance", {})
            if cache_perf:
                print(f"    Cache Performance: {cache_perf}")
        else:
            print(f"    Error: {result.get('error', 'Unknown')}")
        print()

async def test_data_consistency():
    """Test data consistency between endpoints"""
    print("🔍 Data Consistency Test")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Get data from both mobile endpoints
        unified_url = f"{BASE_URL}/api/mobile-unified/dashboard-data"
        original_url = f"{BASE_URL}/api/dashboard/mobile-data"
        
        try:
            # Fetch both endpoints
            async with session.get(unified_url, timeout=5) as resp1:
                unified_data = await resp1.json() if resp1.status == 200 else {}
            
            async with session.get(original_url, timeout=5) as resp2:
                original_data = await resp2.json() if resp2.status == 200 else {}
            
            # Compare key fields
            print("Comparing key data fields:")
            
            # Market Overview
            unified_overview = unified_data.get("market_overview", {})
            original_overview = original_data.get("market_overview", {})
            
            print(f"  Market Regime: {unified_overview.get('market_regime')} vs {original_overview.get('market_regime')}")
            print(f"  BTC Dominance: {unified_overview.get('btc_dominance')} vs {original_overview.get('btc_dominance')}")
            
            # Confluence Scores
            unified_scores = unified_data.get("confluence_scores", [])
            original_scores = original_data.get("confluence_scores", [])
            
            print(f"  Confluence Scores Count: {len(unified_scores)} vs {len(original_scores)}")
            
            if unified_scores and original_scores:
                # Check if we have similar symbols
                unified_symbols = {s.get("symbol") for s in unified_scores}
                original_symbols = {s.get("symbol") for s in original_scores}
                common_symbols = unified_symbols & original_symbols
                print(f"  Common Symbols: {len(common_symbols)}")
            
            # Top Movers
            unified_movers = unified_data.get("top_movers", {})
            original_movers = original_data.get("top_movers", {})
            
            print(f"  Gainers Count: {len(unified_movers.get('gainers', []))} vs {len(original_movers.get('gainers', []))}")
            print(f"  Losers Count: {len(unified_movers.get('losers', []))} vs {len(original_movers.get('losers', []))}")
            
        except Exception as e:
            print(f"❌ Error during consistency test: {e}")

async def main():
    """Main test function"""
    print(f"🧪 Mobile API Test Suite - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run performance tests
    await run_performance_tests()
    
    print()
    
    # Run consistency tests
    await test_data_consistency()
    
    print("\n✅ Test Suite Complete")

if __name__ == "__main__":
    asyncio.run(main())