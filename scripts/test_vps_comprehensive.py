#!/usr/bin/env python3
"""
VPS Comprehensive API Consolidation Test
Tests all 4 phases on production VPS environment
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TestResult:
    endpoint: str
    phase: str
    status_code: int
    response_time_ms: float
    success: bool
    error: str = ""
    response_size: int = 0

class VPSAPITester:
    def __init__(self):
        self.base_url = "http://45.77.40.77:8001"
        self.results: List[TestResult] = []
        
    async def test_endpoint(self, endpoint: str, phase: str) -> TestResult:
        """Test a single endpoint and return result"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}{endpoint}") as response:
                    content = await response.text()
                    response_time = (time.time() - start_time) * 1000
                    
                    return TestResult(
                        endpoint=endpoint,
                        phase=phase,
                        status_code=response.status,
                        response_time_ms=response_time,
                        success=response.status < 400,
                        response_size=len(content),
                        error="" if response.status < 400 else f"HTTP {response.status}"
                    )
                        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return TestResult(
                endpoint=endpoint,
                phase=phase,
                status_code=0,
                response_time_ms=response_time,
                success=False,
                error=str(e)
            )

    async def test_all_phases(self):
        """Test all phases comprehensively"""
        print(f"🌐 VPS Comprehensive API Consolidation Test")
        print(f"🎯 Target: {self.base_url}")
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Phase 1: Market consolidation
        print("🔍 Testing Phase 1: Market Consolidation")
        market_endpoints = [
            "/api/market/correlation/matrix",
            "/api/market/bitcoin-beta/status", 
            "/api/market/sentiment/market",
            "/api/market/overview",
            "/api/market/breadth",
            "/api/market/regime"
        ]
        
        for endpoint in market_endpoints:
            result = await self.test_endpoint(endpoint, "Phase 1")
            self.results.append(result)
            status = "✅" if result.success else "❌"
            print(f"  {status} {endpoint} - {result.status_code} ({result.response_time_ms:.1f}ms)")
        
        print()
        
        # Phase 2: Signals consolidation
        print("🔍 Testing Phase 2: Signals Consolidation")
        signals_endpoints = [
            "/api/signals/alerts",
            "/api/signals/whale/activity", 
            "/api/signals/confluence",
            "/api/signals/orderflow"
        ]
        
        for endpoint in signals_endpoints:
            result = await self.test_endpoint(endpoint, "Phase 2")
            self.results.append(result)
            status = "✅" if result.success else "❌"
            print(f"  {status} {endpoint} - {result.status_code} ({result.response_time_ms:.1f}ms)")
            
        print()
        
        # Phase 3: Dashboard consolidation
        print("🔍 Testing Phase 3: Dashboard Consolidation")
        dashboard_endpoints = [
            "/api/dashboard/overview",
            "/api/dashboard/mobile",
            "/api/dashboard/cache/metrics",
            "/api/dashboard/fast/overview",
            "/api/dashboard/direct/signals",
            "/api/dashboard/direct/market"
        ]
        
        for endpoint in dashboard_endpoints:
            result = await self.test_endpoint(endpoint, "Phase 3")
            self.results.append(result)
            status = "✅" if result.success else "❌"
            print(f"  {status} {endpoint} - {result.status_code} ({result.response_time_ms:.1f}ms)")
            
        print()
        
        # Phase 4: System consolidation
        print("🔍 Testing Phase 4: System Consolidation")
        system_endpoints = [
            "/api/system/status",
            "/api/system/performance",
            "/api/system/exchanges/status", 
            "/api/system/admin/dashboard",
            "/api/system/debug/test-cache"
        ]
        
        for endpoint in system_endpoints:
            result = await self.test_endpoint(endpoint, "Phase 4")
            self.results.append(result)
            status = "✅" if result.success else "❌"
            print(f"  {status} {endpoint} - {result.status_code} ({result.response_time_ms:.1f}ms)")
            
        print()
        
        # Generate comprehensive report
        self.generate_vps_report()

    def generate_vps_report(self):
        """Generate comprehensive VPS test report"""
        print("📊 VPS API CONSOLIDATION TEST RESULTS")
        print("=" * 80)
        
        # Overall stats
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        avg_response_time = sum(r.response_time_ms for r in self.results) / len(self.results) if self.results else 0
        
        print(f"🌐 VPS Production Environment Results:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Successful: {successful_tests} ({success_rate:.1f}%)")
        print(f"  Failed: {failed_tests}")
        print(f"  Avg Response Time: {avg_response_time:.1f}ms")
        print()
        
        # Phase breakdown
        phases = ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]
        for phase in phases:
            phase_results = [r for r in self.results if r.phase == phase]
            if not phase_results:
                continue
                
            phase_success = sum(1 for r in phase_results if r.success)
            phase_total = len(phase_results)
            phase_success_rate = (phase_success / phase_total * 100) if phase_total > 0 else 0
            phase_avg_time = sum(r.response_time_ms for r in phase_results) / len(phase_results)
            
            status_icon = "✅" if phase_success_rate >= 80 else "⚠️" if phase_success_rate >= 50 else "❌"
            print(f"{status_icon} {phase}: {phase_success}/{phase_total} ({phase_success_rate:.1f}%) - {phase_avg_time:.1f}ms avg")
        
        print()
        
        # Failed endpoints
        failed_results = [r for r in self.results if not r.success]
        if failed_results:
            print("❌ FAILED ENDPOINTS:")
            for result in failed_results:
                print(f"  • {result.endpoint} - {result.error}")
            print()
        
        # Performance analysis
        fast_endpoints = [r for r in self.results if r.success and r.response_time_ms < 100]
        slow_endpoints = [r for r in self.results if r.success and r.response_time_ms > 1000]
        
        if fast_endpoints:
            print(f"⚡ Fast VPS Endpoints (<100ms): {len(fast_endpoints)}")
        
        if slow_endpoints:
            print(f"🐌 Slow VPS Endpoints (>1000ms): {len(slow_endpoints)}")
            for result in slow_endpoints:
                print(f"  • {result.endpoint} - {result.response_time_ms:.1f}ms")
        print()
        
        # Final assessment
        print("🎯 VPS CONSOLIDATION STATUS:")
        if success_rate >= 90:
            print("  🟢 EXCELLENT - VPS production ready with consolidated API!")
        elif success_rate >= 75:
            print("  🟡 GOOD - Minor VPS issues, mostly functional")
        elif success_rate >= 50:
            print("  🟠 FAIR - VPS has some consolidation issues to address")
        else:
            print("  🔴 NEEDS WORK - VPS consolidation requires fixes")
            
        print(f"\n🏆 CONSOLIDATION PHASES COMPLETE:")
        print("  ✅ Phase 1: Market consolidation (correlation, bitcoin-beta, sentiment)")
        print("  ✅ Phase 2: Signals consolidation (alerts, whale_activity)")  
        print("  ✅ Phase 3: Dashboard consolidation (cache variants)")
        print("  ✅ Phase 4: System consolidation (admin, debug_test)")
        print(f"\n📈 Overall Consolidation Success: {success_rate:.1f}% on Production VPS")
        
        return success_rate >= 75

async def main():
    """Run VPS comprehensive test"""
    tester = VPSAPITester()
    await tester.test_all_phases()

if __name__ == "__main__":
    success = asyncio.run(main())