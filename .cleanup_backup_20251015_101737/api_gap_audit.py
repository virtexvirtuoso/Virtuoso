#!/usr/bin/env python3
"""
Comprehensive API Gap Audit for VPS Dashboard Port 8004
Tests all endpoints systematically and identifies gaps
"""
import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Base URL for VPS dashboard
BASE_URL = "http://localhost:8004"

# All endpoints from simple_web_server.py
ENDPOINTS = {
    # Core dashboard endpoints
    "Dashboard Root": "/dashboard/",
    "Dashboard Mobile": "/dashboard/mobile",

    # Dashboard API endpoints
    "Dashboard Market Overview": "/dashboard/api/market/overview",
    "Dashboard Signals Top": "/dashboard/api/signals/top",
    "Dashboard Data": "/dashboard/api/data",
    "Dashboard Cache Status": "/dashboard/api/cache-status",
    "Dashboard Health": "/dashboard/health",

    # Health endpoints
    "API Health": "/api/health",
    "Health": "/health",

    # Dashboard-cached API endpoints
    "Dashboard Cached Overview": "/api/dashboard-cached/overview",
    "Dashboard Cached Symbols": "/api/dashboard-cached/symbols",
    "Dashboard Cached Market Overview": "/api/dashboard-cached/market-overview",
    "Dashboard Cached Mobile Data": "/api/dashboard-cached/mobile-data",
    "Dashboard Cached Signals": "/api/dashboard-cached/signals",
    "Dashboard Cached Opportunities": "/api/dashboard-cached/opportunities",
    "Dashboard Cached Alerts": "/api/dashboard-cached/alerts",

    # Bitcoin beta endpoints
    "Bitcoin Beta Realtime": "/api/bitcoin-beta/realtime",
    "Bitcoin Beta History": "/api/bitcoin-beta/history/BTCUSDT",

    # Cache metrics endpoints
    "Cache Metrics Overview": "/api/cache-metrics/overview",
    "Cache Metrics Hit Rates": "/api/cache-metrics/hit-rates",
    "Cache Metrics Health": "/api/cache-metrics/health",
    "Cache Metrics Performance": "/api/cache-metrics/performance",

    # Main API endpoints
    "API Dashboard Overview": "/api/dashboard/overview",
    "API Signals": "/api/signals",
    "API Recent Alerts": "/api/alerts/recent",
    "API Alpha Opportunities": "/api/alpha-opportunities",
    "API Market Overview": "/api/market-overview",
    "API Confluence Analysis": "/api/confluence-analysis/BTCUSDT",
    "API Symbols": "/api/symbols",
    "API Performance": "/api/performance",

    # Cache API endpoints
    "API Cache Dashboard": "/api/cache/dashboard",
    "API Cache Health": "/api/cache/health",
    "API Cache Test": "/api/cache/test",

    # Mobile dashboard endpoints
    "API Mobile Beta Dashboard": "/api/dashboard/mobile/beta-dashboard",
    "API Confluence Analysis Page": "/api/dashboard/confluence-analysis-page",
}

class APIAuditor:
    def __init__(self):
        self.results = {}
        self.session = None

    async def test_endpoint(self, name, endpoint):
        """Test a single endpoint and collect comprehensive metrics"""
        url = BASE_URL + endpoint
        start_time = time.time()

        try:
            async with self.session.get(url, timeout=30) as response:
                response_time = (time.time() - start_time) * 1000  # ms

                # Get response details
                status = response.status
                headers = dict(response.headers)
                content_type = headers.get('content-type', 'unknown')
                content_length = headers.get('content-length', '0')

                # Try to read response body
                try:
                    if 'application/json' in content_type:
                        body = await response.json()
                        body_preview = json.dumps(body, indent=2)[:500] + "..." if len(json.dumps(body)) > 500 else json.dumps(body, indent=2)
                    else:
                        text_body = await response.text()
                        body_preview = text_body[:500] + "..." if len(text_body) > 500 else text_body
                        body = text_body
                except Exception as e:
                    body = f"Error reading body: {e}"
                    body_preview = body

                return {
                    "name": name,
                    "endpoint": endpoint,
                    "url": url,
                    "status": status,
                    "response_time_ms": round(response_time, 2),
                    "content_type": content_type,
                    "content_length": content_length,
                    "headers": headers,
                    "body_preview": body_preview,
                    "success": 200 <= status < 300,
                    "timestamp": datetime.now().isoformat()
                }

        except asyncio.TimeoutError:
            return {
                "name": name,
                "endpoint": endpoint,
                "url": url,
                "status": "TIMEOUT",
                "response_time_ms": (time.time() - start_time) * 1000,
                "error": "Request timeout after 30 seconds",
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "name": name,
                "endpoint": endpoint,
                "url": url,
                "status": "ERROR",
                "response_time_ms": (time.time() - start_time) * 1000,
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat()
            }

    async def audit_all_endpoints(self):
        """Test all endpoints concurrently"""
        print(f"Starting comprehensive API audit of {len(ENDPOINTS)} endpoints...")
        print(f"Base URL: {BASE_URL}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("-" * 80)

        connector = aiohttp.TCPConnector(limit=10)
        async with aiohttp.ClientSession(connector=connector) as session:
            self.session = session

            # Test all endpoints concurrently
            tasks = [self.test_endpoint(name, endpoint) for name, endpoint in ENDPOINTS.items()]
            results = await asyncio.gather(*tasks)

            # Organize results
            successful = []
            failed = []
            slow = []

            for result in results:
                if result["success"]:
                    successful.append(result)
                else:
                    failed.append(result)

                if isinstance(result.get("response_time_ms"), (int, float)) and result["response_time_ms"] > 5000:
                    slow.append(result)

            # Print summary
            print(f"\n{'='*80}")
            print(f"API AUDIT SUMMARY")
            print(f"{'='*80}")
            print(f"Total Endpoints Tested: {len(results)}")
            print(f"Successful (2xx): {len(successful)}")
            print(f"Failed: {len(failed)}")
            print(f"Slow (>5s): {len(slow)}")
            print(f"Success Rate: {len(successful)/len(results)*100:.1f}%")

            # Detailed results
            print(f"\n{'='*80}")
            print(f"DETAILED RESULTS")
            print(f"{'='*80}")

            # Group by status
            status_groups = {}
            for result in results:
                status = result["status"]
                if status not in status_groups:
                    status_groups[status] = []
                status_groups[status].append(result)

            for status in sorted(status_groups.keys()):
                print(f"\n--- STATUS {status} ({len(status_groups[status])} endpoints) ---")
                for result in status_groups[status]:
                    print(f"  {result['name']}")
                    print(f"    URL: {result['url']}")
                    print(f"    Response Time: {result.get('response_time_ms', 'N/A')}ms")
                    if 'content_type' in result:
                        print(f"    Content-Type: {result['content_type']}")
                    if 'error' in result:
                        print(f"    Error: {result['error']}")
                    if result["success"] and 'body_preview' in result:
                        print(f"    Response Preview: {result['body_preview'][:200]}...")
                    print()

            # Save detailed results to file
            report = {
                "audit_timestamp": datetime.now().isoformat(),
                "base_url": BASE_URL,
                "total_endpoints": len(results),
                "successful_count": len(successful),
                "failed_count": len(failed),
                "slow_count": len(slow),
                "success_rate": len(successful)/len(results)*100,
                "results": results
            }

            return report

async def main():
    auditor = APIAuditor()
    report = await auditor.audit_all_endpoints()

    # Save to JSON file
    with open("api_audit_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nDetailed report saved to: api_audit_report.json")

    # Critical gaps analysis
    critical_gaps = [r for r in report["results"] if not r["success"] and r["endpoint"] in [
        "/api/dashboard/overview",
        "/api/dashboard-cached/overview",
        "/api/dashboard-cached/mobile-data",
        "/api/market-overview",
        "/api/signals"
    ]]

    if critical_gaps:
        print(f"\n{'='*80}")
        print(f"CRITICAL API GAPS IDENTIFIED: {len(critical_gaps)}")
        print(f"{'='*80}")
        for gap in critical_gaps:
            print(f"- {gap['name']}: {gap['status']} ({gap.get('error', 'No error details')})")

if __name__ == "__main__":
    asyncio.run(main())