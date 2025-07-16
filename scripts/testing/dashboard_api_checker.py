#!/usr/bin/env python3
"""
Dashboard API Endpoint Checker

This script verifies that all API endpoints required by the dashboard are working correctly.
It tests each endpoint and reports their status, helping identify any missing or broken endpoints.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class EndpointStatus(Enum):
    SUCCESS = "✅ SUCCESS"
    WARNING = "⚠️  WARNING"
    ERROR = "❌ ERROR"
    MISSING = "🔍 MISSING"

@dataclass
class EndpointResult:
    path: str
    status: EndpointStatus
    status_code: Optional[int]
    response_time: Optional[float]
    error_message: Optional[str]
    data_structure: Optional[Dict[str, Any]]

class DashboardAPIChecker:
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.session = None
        self.results: List[EndpointResult] = []
        
        # Define all endpoints that the dashboard needs
        self.endpoints = {
            # Core Dashboard Endpoints
            "/api/dashboard/overview": {"method": "GET", "critical": True},
            "/api/dashboard/alerts/recent": {"method": "GET", "critical": True},
            "/api/dashboard/performance": {"method": "GET", "critical": False},
            "/api/dashboard/symbols": {"method": "GET", "critical": False},
            
            # Market Data Endpoints
            "/api/market/overview": {"method": "GET", "critical": True},
            "/api/market/ticker/BTCUSDT": {"method": "GET", "critical": True},
            "/api/top-symbols": {"method": "GET", "critical": True},
            
            # System Endpoints
            "/api/system/status": {"method": "GET", "critical": True},
            "/api/system/performance": {"method": "GET", "critical": True},
            
            # Trading Endpoints
            "/api/trading/portfolio": {"method": "GET", "critical": True},
            "/api/trading/orders": {"method": "GET", "critical": True},
            "/api/trading/positions": {"method": "GET", "critical": True},
            
            # Signal Endpoints
            "/api/signals/signals/latest": {"method": "GET", "critical": True},
            "/api/signals/active": {"method": "GET", "critical": True},
            
            # Specialized Analysis Endpoints
            "/api/alpha/opportunities": {"method": "GET", "critical": False},
            "/api/alpha/scan": {"method": "POST", "critical": False},
            "/api/liquidation/alerts": {"method": "GET", "critical": False},
            "/api/liquidation/stress-indicators": {"method": "GET", "critical": False},
            "/api/liquidation/cascade-risk": {"method": "GET", "critical": False},
            "/api/manipulation/alerts": {"method": "GET", "critical": False},
            "/api/manipulation/stats": {"method": "GET", "critical": False},
            "/api/correlation/live-matrix": {"method": "GET", "critical": False},
            "/api/bitcoin-beta/status": {"method": "GET", "critical": False},
            
            # WebSocket Endpoint (special case)
            "/api/dashboard/ws": {"method": "WS", "critical": False},
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def check_endpoint(self, path: str, config: Dict[str, Any]) -> EndpointResult:
        """Check a single API endpoint."""
        url = f"{self.base_url}{path}"
        start_time = time.time()
        
        try:
            if config["method"] == "GET":
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            data_structure = self._analyze_data_structure(data)
                            return EndpointResult(
                                path=path,
                                status=EndpointStatus.SUCCESS,
                                status_code=response.status,
                                response_time=response_time,
                                error_message=None,
                                data_structure=data_structure
                            )
                        except json.JSONDecodeError:
                            return EndpointResult(
                                path=path,
                                status=EndpointStatus.WARNING,
                                status_code=response.status,
                                response_time=response_time,
                                error_message="Invalid JSON response",
                                data_structure=None
                            )
                    else:
                        return EndpointResult(
                            path=path,
                            status=EndpointStatus.ERROR,
                            status_code=response.status,
                            response_time=response_time,
                            error_message=f"HTTP {response.status}",
                            data_structure=None
                        )
            
            elif config["method"] == "POST":
                # For POST endpoints, send appropriate test data
                test_data = self._get_test_data(path)
                async with self.session.post(url, json=test_data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response_time = time.time() - start_time
                    
                    if response.status in [200, 201]:
                        try:
                            data = await response.json()
                            data_structure = self._analyze_data_structure(data)
                            return EndpointResult(
                                path=path,
                                status=EndpointStatus.SUCCESS,
                                status_code=response.status,
                                response_time=response_time,
                                error_message=None,
                                data_structure=data_structure
                            )
                        except json.JSONDecodeError:
                            return EndpointResult(
                                path=path,
                                status=EndpointStatus.WARNING,
                                status_code=response.status,
                                response_time=response_time,
                                error_message="Invalid JSON response",
                                data_structure=None
                            )
                    else:
                        return EndpointResult(
                            path=path,
                            status=EndpointStatus.ERROR,
                            status_code=response.status,
                            response_time=response_time,
                            error_message=f"HTTP {response.status}",
                            data_structure=None
                        )
            
            elif config["method"] == "WS":
                # WebSocket endpoints need special handling
                return EndpointResult(
                    path=path,
                    status=EndpointStatus.WARNING,
                    status_code=None,
                    response_time=None,
                    error_message="WebSocket endpoint - manual testing required",
                    data_structure=None
                )
                
        except asyncio.TimeoutError:
            return EndpointResult(
                path=path,
                status=EndpointStatus.ERROR,
                status_code=None,
                response_time=None,
                error_message="Request timeout",
                data_structure=None
            )
        except Exception as e:
            return EndpointResult(
                path=path,
                status=EndpointStatus.ERROR,
                status_code=None,
                response_time=None,
                error_message=str(e),
                data_structure=None
            )
    
    def _get_test_data(self, path: str) -> Dict[str, Any]:
        """Get appropriate test data for POST endpoints."""
        if path == "/api/alpha/scan":
            return {
                "symbols": ["BTCUSDT", "ETHUSDT"],
                "timeframes": ["1h", "4h"],
                "min_confluence_score": 0.5
            }
        return {}
    
    def _analyze_data_structure(self, data: Any) -> Dict[str, Any]:
        """Analyze the structure of returned data."""
        if isinstance(data, dict):
            return {
                "type": "object",
                "keys": list(data.keys()),
                "key_count": len(data.keys())
            }
        elif isinstance(data, list):
            return {
                "type": "array",
                "length": len(data),
                "item_type": type(data[0]).__name__ if data else "empty"
            }
        else:
            return {
                "type": type(data).__name__,
                "value": str(data)[:100]  # Truncate long values
            }
    
    async def check_all_endpoints(self) -> List[EndpointResult]:
        """Check all dashboard endpoints."""
        print(f"🔍 Checking {len(self.endpoints)} dashboard API endpoints...")
        print(f"📡 Base URL: {self.base_url}")
        print("-" * 80)
        
        tasks = []
        for path, config in self.endpoints.items():
            task = self.check_endpoint(path, config)
            tasks.append(task)
        
        self.results = await asyncio.gather(*tasks)
        return self.results
    
    def print_summary(self):
        """Print a summary of all endpoint checks."""
        critical_endpoints = [r for r in self.results if self.endpoints[r.path]["critical"]]
        non_critical_endpoints = [r for r in self.results if not self.endpoints[r.path]["critical"]]
        
        success_count = len([r for r in self.results if r.status == EndpointStatus.SUCCESS])
        warning_count = len([r for r in self.results if r.status == EndpointStatus.WARNING])
        error_count = len([r for r in self.results if r.status == EndpointStatus.ERROR])
        
        print("\n" + "="*80)
        print("📊 DASHBOARD API ENDPOINT SUMMARY")
        print("="*80)
        print(f"Total Endpoints: {len(self.results)}")
        print(f"✅ Success: {success_count}")
        print(f"⚠️  Warning: {warning_count}")
        print(f"❌ Error: {error_count}")
        print()
        
        # Critical endpoints
        print("🔥 CRITICAL ENDPOINTS:")
        for result in critical_endpoints:
            self._print_endpoint_result(result)
        
        print("\n📋 NON-CRITICAL ENDPOINTS:")
        for result in non_critical_endpoints:
            self._print_endpoint_result(result)
        
        # Overall health assessment
        critical_errors = [r for r in critical_endpoints if r.status == EndpointStatus.ERROR]
        if critical_errors:
            print(f"\n❌ DASHBOARD HEALTH: CRITICAL ISSUES DETECTED")
            print(f"   {len(critical_errors)} critical endpoints are failing")
            print("   Dashboard may not function properly")
        elif error_count > 0:
            print(f"\n⚠️  DASHBOARD HEALTH: MINOR ISSUES DETECTED")
            print(f"   {error_count} non-critical endpoints are failing")
            print("   Dashboard should work with reduced functionality")
        else:
            print(f"\n✅ DASHBOARD HEALTH: ALL SYSTEMS OPERATIONAL")
            print("   All endpoints are responding correctly")
    
    def _print_endpoint_result(self, result: EndpointResult):
        """Print a single endpoint result."""
        time_str = f"{result.response_time:.3f}s" if result.response_time else "N/A"
        status_str = f"[{result.status_code}]" if result.status_code else "[N/A]"
        
        print(f"  {result.status.value} {result.path} {status_str} ({time_str})")
        
        if result.error_message:
            print(f"      Error: {result.error_message}")
        
        if result.data_structure:
            if result.data_structure["type"] == "object":
                print(f"      Data: {result.data_structure['key_count']} keys - {result.data_structure['keys'][:3]}...")
            elif result.data_structure["type"] == "array":
                print(f"      Data: {result.data_structure['length']} items ({result.data_structure['item_type']})")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a detailed report for integration with other tools."""
        return {
            "timestamp": time.time(),
            "base_url": self.base_url,
            "total_endpoints": len(self.results),
            "success_count": len([r for r in self.results if r.status == EndpointStatus.SUCCESS]),
            "warning_count": len([r for r in self.results if r.status == EndpointStatus.WARNING]),
            "error_count": len([r for r in self.results if r.status == EndpointStatus.ERROR]),
            "critical_failures": [
                r.path for r in self.results 
                if r.status == EndpointStatus.ERROR and self.endpoints[r.path]["critical"]
            ],
            "results": [
                {
                    "path": r.path,
                    "status": r.status.name,
                    "status_code": r.status_code,
                    "response_time": r.response_time,
                    "error_message": r.error_message,
                    "is_critical": self.endpoints[r.path]["critical"]
                }
                for r in self.results
            ]
        }

async def main():
    """Main function to run the API checker."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check Dashboard API Endpoints")
    parser.add_argument("--url", default="http://localhost:8003", help="Base URL for API")
    parser.add_argument("--output", help="Output file for JSON report")
    args = parser.parse_args()
    
    async with DashboardAPIChecker(args.url) as checker:
        await checker.check_all_endpoints()
        checker.print_summary()
        
        if args.output:
            report = checker.generate_report()
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Report saved to: {args.output}")

if __name__ == "__main__":
    asyncio.run(main()) 