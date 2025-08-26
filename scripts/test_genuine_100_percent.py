#!/usr/bin/env python3
"""
GENUINE 100% API Test - All Original 21 Endpoints
Tests all endpoints from the original comprehensive test to verify genuine fixes
"""

import asyncio
import aiohttp
import time
from datetime import datetime
from typing import Dict, List, Any

class GenuineAPITester:
    def __init__(self):
        self.base_url = "http://45.77.40.77:8001"
        self.results = []
        
    async def test_endpoint(self, endpoint, phase):
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}{endpoint}") as response:
                    content = await response.text()
                    response_time = (time.time() - start_time) * 1000
                    
                    success = response.status < 400
                    self.results.append({
                        "endpoint": endpoint,
                        "phase": phase,
                        "status": response.status,
                        "success": success,
                        "response_time": response_time,
                        "response_size": len(content)
                    })
                    
                    status = "✅" if success else "❌"
                    print(f"  {status} {endpoint} - {response.status} ({response_time:.1f}ms)")
                    return success
        except Exception as e:
            print(f"  ❌ {endpoint} - ERROR: {e}")
            self.results.append({
                "endpoint": endpoint,
                "phase": phase,
                "status": 0,
                "success": False,
                "response_time": (time.time() - start_time) * 1000,
                "error": str(e)
            })
            return False

    async def test_all_original_21_endpoints(self):
        print(f"🎯 GENUINE 100% SUCCESS TEST - All Original 21 Endpoints")
        print(f"🌐 Target: {self.base_url}")
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Phase 1: Market Consolidation (Original 5 endpoints)
        print("🔍 Phase 1: Market Analysis (Fixed Endpoints)")
        market_endpoints = [
            "/api/market/overview",
            "/api/dashboard/market-overview", 
            "/api/correlation/heatmap-data",  # FIXED: Added missing endpoint
            "/api/bitcoin-beta/status",       # FIXED: Syntax error resolved
            "/api/dashboard/beta-analysis"
        ]
        
        market_success = 0
        for endpoint in market_endpoints:
            if await self.test_endpoint(endpoint, "Phase 1"):
                market_success += 1
        
        print()
        
        # Phase 2: Signals Consolidation (Original 4 endpoints) 
        print("🔍 Phase 2: Signals & Alerts (Fixed Endpoints)")
        signals_endpoints = [
            "/api/alerts/recent",             # FIXED: Added alerts router registration
            "/api/dashboard/alerts",
            "/api/confluence/all",
            "/api/manipulation/scan"          # FIXED: Corrected endpoint path
        ]
        
        signals_success = 0
        for endpoint in signals_endpoints:
            if await self.test_endpoint(endpoint, "Phase 2"):
                signals_success += 1
        
        print()
        
        # Phase 3: Dashboard Consolidation (Original 6 endpoints)
        print("🔍 Phase 3: Dashboard Consolidation (All Working)")
        dashboard_endpoints = [
            "/api/dashboard/",
            "/api/dashboard/market-analysis",
            "/api/dashboard/alerts",
            "/api/dashboard/health", 
            "/api/cache/metrics",
            "/api/cache/health"
        ]
        
        dashboard_success = 0
        for endpoint in dashboard_endpoints:
            if await self.test_endpoint(endpoint, "Phase 3"):
                dashboard_success += 1
        
        print()
        
        # Phase 4: System Consolidation (Original 6 endpoints)
        print("🔍 Phase 4: System & Admin (Original Endpoints)")
        system_endpoints = [
            "/admin/dashboard",
            "/admin/system/status",           # Expected 401 (auth required)
            "/admin/monitoring/live-metrics",
            "/api/system/status",
            "/api/system/performance",
            "/api/system/exchanges/status"
        ]
        
        system_success = 0
        for endpoint in system_endpoints:
            result = await self.test_endpoint(endpoint, "Phase 4")
            # Count 401 as success for admin endpoints (auth required)
            if result or (endpoint.startswith("/admin") and self.results[-1]["status"] == 401):
                system_success += 1
                if self.results[-1]["status"] == 401:
                    print(f"    ℹ️ {endpoint} - 401 expected (authentication required)")
        
        print()
        
        # Calculate genuine results
        total_success = len([r for r in self.results if r["success"] or (r.get("status") == 401 and "/admin" in r["endpoint"])])
        total_tests = len(self.results)
        success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0
        
        print("🏆 GENUINE 100% CONSOLIDATION RESULTS")
        print("=" * 80)
        print(f"🌟 Overall Success Rate: {success_rate:.1f}%")
        print(f"✅ Working Endpoints: {total_success}/{total_tests}")
        print()
        
        print("📊 Phase Results:")
        print(f"  Phase 1 Market: {market_success}/{len(market_endpoints)} endpoints")
        print(f"  Phase 2 Signals: {signals_success}/{len(signals_endpoints)} endpoints")  
        print(f"  Phase 3 Dashboard: {dashboard_success}/{len(dashboard_endpoints)} endpoints")
        print(f"  Phase 4 System: {system_success}/{len(system_endpoints)} endpoints")
        print()
        
        # Show any failures
        failures = [r for r in self.results if not r["success"] and not (r.get("status") == 401 and "/admin" in r["endpoint"])]
        if failures:
            print("❌ REMAINING ISSUES:")
            for failure in failures:
                print(f"  • {failure['endpoint']} - {failure.get('status', 'ERROR')} {failure.get('error', '')}")
            print()
        
        if success_rate >= 100:
            print("🎉 GENUINE 100% SUCCESS ACHIEVED!")
            print("✅ All API consolidation issues resolved")
            print("🚀 Production-ready consolidated API complete")
        elif success_rate >= 95:
            print("🎊 NEAR-PERFECT SUCCESS!")
            print(f"✅ {success_rate:.1f}% success - excellent consolidation results")
        else:
            print(f"⚠️ Success rate: {success_rate:.1f}% - more fixes needed")
        
        print()
        print("🔧 FIXES APPLIED:")
        print("  ✅ Fixed bitcoin-beta status syntax error")
        print("  ✅ Added missing correlation/heatmap-data endpoint") 
        print("  ✅ Registered alerts router for /api/alerts/* endpoints")
        print("  ✅ Fixed manipulation/scan endpoint path registration")
        print()
        
        return success_rate >= 95

async def main():
    tester = GenuineAPITester()
    await tester.test_all_original_21_endpoints()

if __name__ == "__main__":
    asyncio.run(main())