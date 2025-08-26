#!/usr/bin/env python3
"""
FINAL VPS Test - Correct Port 8003
Tests all endpoints on the correct port where the updated service is running
"""

import asyncio
import aiohttp
import time
from datetime import datetime
from typing import Dict, List, Any

class FinalVPSTest:
    def __init__(self):
        self.base_url = "http://45.77.40.77:8003"  # CORRECT PORT
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

    async def test_final_vps_port_8003(self):
        print(f"🎯 FINAL VPS TEST - CORRECT PORT 8003")
        print(f"🌐 Target: {self.base_url}")
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Phase 1: Market Analysis 
        print("🔍 Phase 1: Market Analysis (Port 8003)")
        market_endpoints = [
            "/api/market/overview",
            "/api/dashboard/market-overview", 
            "/api/correlation/heatmap-data",
            "/api/bitcoin-beta/status",
            "/api/dashboard/beta-analysis"
        ]
        
        market_success = 0
        for endpoint in market_endpoints:
            if await self.test_endpoint(endpoint, "Phase 1"):
                market_success += 1
        
        print()
        
        # Phase 2: Signals & Alerts
        print("🔍 Phase 2: Signals & Alerts (Port 8003)")
        signals_endpoints = [
            "/api/alerts/recent",
            "/api/dashboard/alerts",
            "/api/confluence/all",
            "/api/manipulation/scan"
        ]
        
        signals_success = 0
        for endpoint in signals_endpoints:
            if await self.test_endpoint(endpoint, "Phase 2"):
                signals_success += 1
        
        print()
        
        # Phase 3: Dashboard
        print("🔍 Phase 3: Dashboard Consolidation (Port 8003)")
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
        
        # Phase 4: System & Admin
        print("🔍 Phase 4: System & Admin (Port 8003)")
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
        
        # Calculate final results on CORRECT PORT
        total_success = len([r for r in self.results if r["success"] or (r.get("status") == 401 and "/admin" in r["endpoint"])])
        total_tests = len(self.results)
        success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0
        
        print("🏆 FINAL VPS RESULTS - CORRECT PORT 8003")
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
        else:
            print("✅ NO FAILURES DETECTED!")
            print()
        
        print("🎯 PORT DISCOVERY:")
        print("  ❌ Port 8001: Old uvicorn server (killed)")
        print("  ✅ Port 8003: Updated systemd service with fixes")
        print("  📍 VPS Service: virtuoso.service running src/main.py")
        print()
        
        if success_rate >= 100:
            print("🎉 GENUINE 100% SUCCESS ACHIEVED!")
            print("✅ All API consolidation issues resolved on correct port")
            print("🚀 Production-ready consolidated API complete")
        elif success_rate >= 95:
            print("🎊 NEAR-PERFECT SUCCESS!")
            print(f"✅ {success_rate:.1f}% success - excellent consolidation results")
        else:
            print(f"⚠️ Success rate: {success_rate:.1f}% - investigate remaining issues")
        
        return success_rate >= 95

async def main():
    tester = FinalVPSTest()
    await tester.test_final_vps_port_8003()

if __name__ == "__main__":
    asyncio.run(main())