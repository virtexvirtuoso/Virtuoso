#!/usr/bin/env python3
"""
Comprehensive API Audit Script for Virtuoso Trading System
Tests all API endpoints on VPS to ensure they're working and returning data.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path

# VPS Configuration
VPS_BASE_URL = "http://${VPS_HOST}:8003"
TIMEOUT = 30  # seconds

class APIAuditor:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results = {}
        self.session = None
        
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_endpoint(self, method: str, path: str, description: str, 
                          expected_fields: Optional[List[str]] = None,
                          params: Optional[Dict] = None,
                          data: Optional[Dict] = None) -> Dict[str, Any]:
        """Test a single API endpoint."""
        url = f"{self.base_url}{path}"
        start_time = time.time()
        
        try:
            if method.upper() == "GET":
                async with self.session.get(url, params=params) as response:
                    response_data = await response.json()
                    status_code = response.status
            elif method.upper() == "POST":
                async with self.session.post(url, json=data, params=params) as response:
                    response_data = await response.json()
                    status_code = response.status
            else:
                return {
                    "status": "error",
                    "error": f"Unsupported method: {method}",
                    "response_time": 0
                }
            
            response_time = time.time() - start_time
            
            # Check if response is successful
            if status_code == 200:
                # Validate expected fields if provided
                missing_fields = []
                if expected_fields and isinstance(response_data, dict):
                    for field in expected_fields:
                        if field not in response_data:
                            missing_fields.append(field)
                
                # Check if response has data
                has_data = self._check_has_data(response_data)
                
                return {
                    "status": "success",
                    "status_code": status_code,
                    "response_time": round(response_time, 3),
                    "has_data": has_data,
                    "data_type": type(response_data).__name__,
                    "data_size": len(str(response_data)),
                    "missing_fields": missing_fields,
                    "sample_data": self._get_sample_data(response_data)
                }
            else:
                return {
                    "status": "error",
                    "status_code": status_code,
                    "response_time": round(response_time, 3),
                    "error": f"HTTP {status_code}",
                    "response": response_data
                }
                
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "response_time": TIMEOUT,
                "error": "Request timeout"
            }
        except Exception as e:
            return {
                "status": "error",
                "response_time": round(time.time() - start_time, 3),
                "error": str(e)
            }
    
    def _check_has_data(self, data: Any) -> bool:
        """Check if response contains meaningful data."""
        if isinstance(data, dict):
            # Check for common data indicators
            data_indicators = ['symbols', 'signals', 'alerts', 'data', 'results', 'opportunities']
            for indicator in data_indicators:
                if indicator in data and data[indicator]:
                    if isinstance(data[indicator], list) and len(data[indicator]) > 0:
                        return True
                    elif isinstance(data[indicator], dict) and len(data[indicator]) > 0:
                        return True
            
            # Check if it has any non-empty values
            return any(bool(v) for v in data.values() if v is not None)
        elif isinstance(data, list):
            return len(data) > 0
        else:
            return bool(data)
    
    def _get_sample_data(self, data: Any) -> Any:
        """Get sample of response data for inspection."""
        if isinstance(data, dict):
            # Return first few key-value pairs
            return {k: v for i, (k, v) in enumerate(data.items()) if i < 3}
        elif isinstance(data, list):
            # Return first item if list is not empty
            return data[0] if data else []
        else:
            return str(data)[:100] + "..." if len(str(data)) > 100 else data

    async def run_audit(self):
        """Run comprehensive API audit."""
        print(f"🔍 Starting API Audit for {self.base_url}")
        print("=" * 80)
        
        # Define all endpoints to test
        endpoints = [
            # Basic Health Checks
            ("GET", "/", "Root endpoint", ["message"]),
            ("GET", "/health", "Health check", ["status", "timestamp"]),
            ("GET", "/version", "Version info", ["version", "service"]),
            
            # Dashboard Routes
            ("GET", "/dashboard", "Dashboard selector page", None),
            ("GET", "/dashboard/mobile", "Mobile dashboard", None),
            ("GET", "/dashboard/desktop", "Desktop dashboard", None),
            ("GET", "/dashboard/v1", "Classic dashboard", None),
            ("GET", "/dashboard/v10", "Signal matrix dashboard", None),
            
            # Core API Endpoints
            ("GET", "/api/health", "API health check", ["status"]),
            ("GET", "/api/dashboard/overview", "Dashboard overview", ["signals", "alerts"]),
            ("GET", "/api/dashboard/symbols", "Dashboard symbols", ["symbols"]),
            ("GET", "/api/dashboard/signals", "Dashboard signals", None),
            ("GET", "/api/dashboard/alerts", "Dashboard alerts", None),
            
            # Market Data
            ("GET", "/api/market/overview", "Market overview", None),
            ("GET", "/api/top-symbols", "Top symbols", ["symbols"]),
            ("GET", "/api/market-report", "Market report", ["status"]),
            
            # Signals
            ("GET", "/api/signals/latest", "Latest signals", None),
            
            # Bitcoin Beta
            ("GET", "/api/bitcoin-beta/status", "Bitcoin Beta status", None),
            ("GET", "/api/bitcoin-beta/analysis", "Bitcoin Beta analysis", None),
            ("GET", "/api/bitcoin-beta/health", "Bitcoin Beta health", None),
            
            # Alpha Opportunities
            ("GET", "/api/alpha/opportunities", "Alpha opportunities", None),
            
            # Whale Activity
            ("GET", "/api/whale-activity/alerts", "Whale alerts", None),
            ("GET", "/api/whale-activity/activity", "Whale activity", None),
            
            # Liquidation
            ("GET", "/api/liquidation/alerts", "Liquidation alerts", None),
            
            # Sentiment
            ("GET", "/api/sentiment/market", "Market sentiment", None),
            ("GET", "/api/sentiment/symbols", "Symbol sentiments", None),
            
            # System
            ("GET", "/api/system/metrics", "System metrics", None),
            
            # Admin (will likely fail without auth, but test accessibility)
            ("GET", "/admin/login", "Admin login page", None),
            ("GET", "/admin/dashboard", "Admin dashboard", None),
        ]
        
        # Run tests
        total_tests = len(endpoints)
        passed = 0
        failed = 0
        timeouts = 0
        
        for i, (method, path, description, expected_fields) in enumerate(endpoints, 1):
            print(f"\n[{i}/{total_tests}] Testing: {method} {path}")
            print(f"Description: {description}")
            
            result = await self.test_endpoint(method, path, description, expected_fields)
            self.results[path] = result
            
            if result["status"] == "success":
                print(f"✅ SUCCESS - {result['response_time']}s - Data: {result['has_data']} - Size: {result['data_size']} bytes")
                if result["missing_fields"]:
                    print(f"⚠️  Missing expected fields: {result['missing_fields']}")
                passed += 1
            elif result["status"] == "timeout":
                print(f"⏰ TIMEOUT - {result['response_time']}s")
                timeouts += 1
            else:
                print(f"❌ FAILED - {result['response_time']}s - Error: {result['error']}")
                failed += 1
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 AUDIT SUMMARY")
        print("=" * 80)
        print(f"Total Endpoints Tested: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⏰ Timeouts: {timeouts}")
        print(f"Success Rate: {(passed/total_tests)*100:.1f}%")
        
        # Detailed Results
        print("\n" + "=" * 80)
        print("📋 DETAILED RESULTS")
        print("=" * 80)
        
        categories = {
            "Working with Data": [],
            "Working but No Data": [],
            "Failed": [],
            "Timeouts": []
        }
        
        for path, result in self.results.items():
            if result["status"] == "success":
                if result["has_data"]:
                    categories["Working with Data"].append((path, result))
                else:
                    categories["Working but No Data"].append((path, result))
            elif result["status"] == "timeout":
                categories["Timeouts"].append((path, result))
            else:
                categories["Failed"].append((path, result))
        
        for category, endpoints in categories.items():
            if endpoints:
                print(f"\n🔸 {category} ({len(endpoints)} endpoints):")
                for path, result in endpoints:
                    print(f"  {path} - {result['response_time']}s")
                    if result["status"] == "success" and "sample_data" in result:
                        print(f"    Sample: {json.dumps(result['sample_data'], indent=2)[:100]}...")
                    elif result["status"] != "success":
                        print(f"    Error: {result.get('error', 'Unknown')}")
        
        # Recommendations
        print("\n" + "=" * 80)
        print("💡 RECOMMENDATIONS")
        print("=" * 80)
        
        if failed > 0:
            print("❌ Failed Endpoints Need Investigation:")
            for path, result in self.results.items():
                if result["status"] == "error":
                    print(f"  - {path}: {result['error']}")
        
        if timeouts > 0:
            print("⏰ Timeout Issues:")
            print(f"  - {timeouts} endpoints timed out (>{TIMEOUT}s)")
            print("  - Consider optimizing slow endpoints or increasing timeout")
        
        no_data_count = len(categories["Working but No Data"])
        if no_data_count > 0:
            print(f"📊 Data Issues:")
            print(f"  - {no_data_count} endpoints working but returning no data")
            print("  - Check if services are properly initialized")
            print("  - Verify database connections and data sources")
        
        success_rate = (passed / total_tests) * 100
        if success_rate < 80:
            print("🚨 Low Success Rate - System needs attention")
        elif success_rate < 95:
            print("⚠️  Good but could be improved")
        else:
            print("🎉 Excellent - System is healthy!")

async def main():
    """Run the API audit."""
    async with APIAuditor(VPS_BASE_URL) as auditor:
        await auditor.run_audit()

if __name__ == "__main__":
    print("🚀 Virtuoso API Endpoint Audit Tool")
    print(f"Target: {VPS_BASE_URL}")
    print(f"Timeout: {TIMEOUT}s")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Audit interrupted by user")
    except Exception as e:
        print(f"\n❌ Audit failed: {e}")
        sys.exit(1)