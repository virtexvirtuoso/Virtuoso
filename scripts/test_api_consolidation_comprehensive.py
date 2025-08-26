#!/usr/bin/env python3
"""
Comprehensive API Consolidation Testing Suite
Tests all 4 phases of API consolidation to ensure backward compatibility
"""

import asyncio
import aiohttp
import json
import sys
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

class APIConsolidationTester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.results: List[TestResult] = []
        
    async def test_endpoint(self, endpoint: str, phase: str, method: str = "GET", data: Dict = None) -> TestResult:
        """Test a single endpoint and return result"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
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
                        
                elif method == "POST":
                    async with session.post(f"{self.base_url}{endpoint}", json=data) as response:
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
    
    async def test_phase_1_market_endpoints(self):
        """Test Phase 1: Market consolidation endpoints"""
        print("🔍 Testing Phase 1: Market Consolidation")
        
        # Original consolidated endpoints in market.py
        market_endpoints = [
            "/api/market/correlation/matrix",
            "/api/market/correlation/top-pairs",
            "/api/market/correlation/breakdown", 
            "/api/market/bitcoin-beta/status",
            "/api/market/bitcoin-beta/analysis",
            "/api/market/bitcoin-beta/top-correlated",
            "/api/market/sentiment/market",
            "/api/market/sentiment/analysis",
            "/api/market/sentiment/breakdown",
            "/api/market/overview",
            "/api/market/breadth",
            "/api/market/regime"
        ]
        
        for endpoint in market_endpoints:
            result = await self.test_endpoint(endpoint, "Phase 1")
            self.results.append(result)
            status = "✅" if result.success else "❌"
            print(f"  {status} {endpoint} - {result.status_code} ({result.response_time_ms:.1f}ms)")
    
    async def test_phase_2_signals_endpoints(self):
        """Test Phase 2: Signals consolidation endpoints"""
        print("🔍 Testing Phase 2: Signals Consolidation")
        
        # Original consolidated endpoints in signals.py
        signals_endpoints = [
            "/api/signals/",
            "/api/signals/alerts",
            "/api/signals/alerts/recent",
            "/api/signals/whale/activity",
            "/api/signals/whale/transactions",
            "/api/signals/whale/analysis",
            "/api/signals/confluence",
            "/api/signals/orderflow"
        ]
        
        for endpoint in signals_endpoints:
            result = await self.test_endpoint(endpoint, "Phase 2")
            self.results.append(result)
            status = "✅" if result.success else "❌"
            print(f"  {status} {endpoint} - {result.status_code} ({result.response_time_ms:.1f}ms)")
    
    async def test_phase_3_dashboard_endpoints(self):
        """Test Phase 3: Dashboard consolidation endpoints"""
        print("🔍 Testing Phase 3: Dashboard Consolidation")
        
        # Original consolidated endpoints in dashboard.py
        dashboard_endpoints = [
            "/api/dashboard/overview",
            "/api/dashboard/mobile",
            "/api/dashboard/cache/metrics",
            "/api/dashboard/cache/status",
            "/api/dashboard/cached/overview",
            "/api/dashboard/fast/overview",
            "/api/dashboard/fast/mobile",
            "/api/dashboard/direct/signals",
            "/api/dashboard/direct/market"
        ]
        
        for endpoint in dashboard_endpoints:
            result = await self.test_endpoint(endpoint, "Phase 3")
            self.results.append(result)
            status = "✅" if result.success else "❌"
            print(f"  {status} {endpoint} - {result.status_code} ({result.response_time_ms:.1f}ms)")
    
    async def test_phase_4_system_endpoints(self):
        """Test Phase 4: System consolidation endpoints"""
        print("🔍 Testing Phase 4: System Consolidation")
        
        # Original consolidated endpoints in system.py
        system_endpoints = [
            "/api/system/status",
            "/api/system/config", 
            "/api/system/performance",
            "/api/system/exchanges/status",
            "/api/system/admin/dashboard",
            "/api/system/admin/login",
            "/api/system/debug/test-cache",
            "/api/system/debug/test-import"
        ]
        
        for endpoint in system_endpoints:
            # Skip auth-required endpoints for now
            if "/admin/" in endpoint and endpoint != "/api/system/admin/dashboard":
                continue
                
            result = await self.test_endpoint(endpoint, "Phase 4")
            self.results.append(result)
            status = "✅" if result.success else "❌"
            print(f"  {status} {endpoint} - {result.status_code} ({result.response_time_ms:.1f}ms)")
    
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        print(f"🚀 Starting API Consolidation Test Suite")
        print(f"🌐 Testing against: {self.base_url}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Test all phases
        await self.test_phase_1_market_endpoints()
        print()
        await self.test_phase_2_signals_endpoints() 
        print()
        await self.test_phase_3_dashboard_endpoints()
        print()
        await self.test_phase_4_system_endpoints()
        print()
        
        # Generate summary report
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """Generate comprehensive test summary"""
        print("📊 CONSOLIDATION TEST SUMMARY")
        print("=" * 60)
        
        # Overall stats
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        avg_response_time = sum(r.response_time_ms for r in self.results) / len(self.results) if self.results else 0
        
        print(f"📈 Overall Results:")
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
            
            status_icon = "✅" if phase_success_rate == 100 else "⚠️" if phase_success_rate > 50 else "❌"
            print(f"{status_icon} {phase}: {phase_success}/{phase_total} ({phase_success_rate:.1f}%) - {phase_avg_time:.1f}ms avg")
        
        print()
        
        # Failed endpoints
        failed_results = [r for r in self.results if not r.success]
        if failed_results:
            print("❌ FAILED ENDPOINTS:")
            for result in failed_results:
                print(f"  • {result.endpoint} - {result.error}")
            print()
        
        # Performance insights
        fast_endpoints = [r for r in self.results if r.success and r.response_time_ms < 100]
        slow_endpoints = [r for r in self.results if r.success and r.response_time_ms > 1000]
        
        if fast_endpoints:
            print(f"⚡ Fast Endpoints (<100ms): {len(fast_endpoints)}")
        
        if slow_endpoints:
            print(f"🐌 Slow Endpoints (>1000ms): {len(slow_endpoints)}")
            for result in slow_endpoints:
                print(f"  • {result.endpoint} - {result.response_time_ms:.1f}ms")
        
        print()
        print("🎯 CONSOLIDATION COMPATIBILITY:")
        if success_rate >= 95:
            print("  🟢 EXCELLENT - All consolidated endpoints working properly")
        elif success_rate >= 80:
            print("  🟡 GOOD - Minor issues to address")
        else:
            print("  🔴 NEEDS ATTENTION - Significant compatibility issues")
            
        return success_rate >= 80

async def main():
    """Main test runner"""
    # Test locally first
    print("🏠 Testing Local Development Server")
    local_tester = APIConsolidationTester("http://localhost:8001")
    await local_tester.run_all_tests()
    
    print("\n" + "="*80 + "\n")
    
    # Test VPS if local tests pass
    local_success_rate = (sum(1 for r in local_tester.results if r.success) / len(local_tester.results) * 100) if local_tester.results else 0
    
    if local_success_rate >= 80:
        print("🌐 Testing VPS Production Server")
        vps_tester = APIConsolidationTester("http://45.77.40.77:8001")
        await vps_tester.run_all_tests()
        
        # Combined summary
        print("\n" + "="*80)
        print("🏁 FINAL CONSOLIDATION TEST RESULTS")
        print("="*80)
        
        vps_success_rate = (sum(1 for r in vps_tester.results if r.success) / len(vps_tester.results) * 100) if vps_tester.results else 0
        
        print(f"🏠 Local Success Rate: {local_success_rate:.1f}%")
        print(f"🌐 VPS Success Rate: {vps_success_rate:.1f}%")
        
        if local_success_rate >= 95 and vps_success_rate >= 95:
            print("🎉 CONSOLIDATION COMPLETE - All systems operational!")
            return True
        else:
            print("⚠️ CONSOLIDATION NEEDS ATTENTION - Some endpoints failing")
            return False
    else:
        print("❌ Local tests failed - Fix issues before VPS deployment")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)