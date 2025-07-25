#!/usr/bin/env python3
"""
Comprehensive Dashboard API Endpoint Test Script
Tests all API endpoints used in dashboard_v10.html
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
import websockets
from colorama import init, Fore, Style

init(autoreset=True)

# Configuration
API_BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/dashboard"

# All API endpoints identified in dashboard_v10.html
API_ENDPOINTS = {
    "Dashboard Overview": {
        "url": "/api/dashboard/overview",
        "method": "GET",
        "critical": True
    },
    "Liquidation Alerts": {
        "url": "/api/liquidation/alerts",
        "method": "GET",
        "critical": True
    },
    "Stress Indicators": {
        "url": "/api/liquidation/stress-indicators",
        "method": "GET",
        "critical": True
    },
    "Cascade Risk": {
        "url": "/api/liquidation/cascade-risk",
        "method": "GET",
        "critical": True
    },
    "Alpha Opportunities": {
        "url": "/api/alpha/opportunities",
        "method": "GET",
        "critical": True
    },
    "Alpha Scan": {
        "url": "/api/alpha/scan",
        "method": "POST",
        "body": {"symbols": ["BTCUSDT"]},
        "critical": True
    },
    "System Status": {
        "url": "/api/system/status",
        "method": "GET",
        "critical": True
    },
    "System Performance": {
        "url": "/api/system/performance",
        "method": "GET",
        "critical": True
    },
    "Trading Portfolio": {
        "url": "/api/trading/portfolio",
        "method": "GET",
        "critical": False
    },
    "Trading Orders": {
        "url": "/api/trading/orders?limit=10",
        "method": "GET",
        "critical": False
    },
    "Trading Positions": {
        "url": "/api/trading/positions",
        "method": "GET",
        "critical": False
    },
    "Market Overview": {
        "url": "/api/market/overview",
        "method": "GET",
        "critical": True
    },
    "Bitcoin Beta Status": {
        "url": "/api/bitcoin-beta/status",
        "method": "GET",
        "critical": False
    },
    "Signal Tracking (Example)": {
        "url": "/api/signal-tracking/tracked/test-signal",
        "method": "DELETE",
        "critical": False
    }
}

class DashboardAPITester:
    def __init__(self):
        self.results = []
        self.start_time = datetime.now()
        
    async def test_endpoint(self, session: aiohttp.ClientSession, name: str, config: Dict) -> Tuple[str, bool, str, float]:
        """Test a single API endpoint"""
        url = f"{API_BASE_URL}{config['url']}"
        method = config.get('method', 'GET')
        body = config.get('body', None)
        
        start = time.time()
        try:
            if method == 'GET':
                async with session.get(url) as response:
                    elapsed = time.time() - start
                    data = await response.json()
                    
                    if response.status == 200:
                        return (name, True, f"OK - {response.status}", elapsed)
                    else:
                        return (name, False, f"HTTP {response.status}: {data.get('error', 'Unknown error')}", elapsed)
                        
            elif method == 'POST':
                async with session.post(url, json=body) as response:
                    elapsed = time.time() - start
                    data = await response.json()
                    
                    if response.status in [200, 201]:
                        return (name, True, f"OK - {response.status}", elapsed)
                    else:
                        return (name, False, f"HTTP {response.status}: {data.get('error', 'Unknown error')}", elapsed)
                        
            elif method == 'DELETE':
                async with session.delete(url) as response:
                    elapsed = time.time() - start
                    
                    if response.status in [200, 204, 404]:  # 404 is OK for delete
                        return (name, True, f"OK - {response.status}", elapsed)
                    else:
                        data = await response.json()
                        return (name, False, f"HTTP {response.status}: {data.get('error', 'Unknown error')}", elapsed)
                        
        except aiohttp.ClientError as e:
            elapsed = time.time() - start
            return (name, False, f"Connection error: {str(e)}", elapsed)
        except Exception as e:
            elapsed = time.time() - start
            return (name, False, f"Error: {str(e)}", elapsed)
    
    async def test_websocket(self) -> Tuple[str, bool, str, float]:
        """Test WebSocket connection"""
        start = time.time()
        try:
            async with websockets.connect(WS_URL) as websocket:
                # Send a test message
                await websocket.send(json.dumps({
                    "type": "subscribe",
                    "channel": "dashboard"
                }))
                
                # Wait for response with timeout
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                elapsed = time.time() - start
                
                data = json.loads(response)
                return ("WebSocket Connection", True, f"Connected - Received: {data.get('type', 'unknown')}", elapsed)
                
        except asyncio.TimeoutError:
            elapsed = time.time() - start
            return ("WebSocket Connection", False, "Timeout waiting for response", elapsed)
        except Exception as e:
            elapsed = time.time() - start
            return ("WebSocket Connection", False, f"Error: {str(e)}", elapsed)
    
    async def run_tests(self):
        """Run all API endpoint tests"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}Dashboard API Endpoint Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.CYAN}Testing Base URL: {API_BASE_URL}")
        print(f"{Fore.CYAN}{'='*80}\n")
        
        # Test HTTP endpoints
        async with aiohttp.ClientSession() as session:
            tasks = []
            for name, config in API_ENDPOINTS.items():
                tasks.append(self.test_endpoint(session, name, config))
            
            results = await asyncio.gather(*tasks)
            self.results.extend(results)
        
        # Test WebSocket
        ws_result = await self.test_websocket()
        self.results.append(ws_result)
        
        # Display results
        self.display_results()
        
    def display_results(self):
        """Display test results in a formatted table"""
        print(f"\n{Fore.WHITE}Test Results:")
        print(f"{'-'*80}")
        print(f"{'Endpoint':<30} {'Status':<10} {'Response':<30} {'Time (s)':<10}")
        print(f"{'-'*80}")
        
        passed = 0
        failed = 0
        critical_failures = []
        
        for name, success, message, elapsed in self.results:
            status_color = Fore.GREEN if success else Fore.RED
            status_text = "PASS" if success else "FAIL"
            
            print(f"{name:<30} {status_color}{status_text:<10}{Style.RESET_ALL} {message:<30} {elapsed:.3f}")
            
            if success:
                passed += 1
            else:
                failed += 1
                if name in API_ENDPOINTS and API_ENDPOINTS[name].get('critical', False):
                    critical_failures.append(name)
        
        print(f"{'-'*80}")
        print(f"\n{Fore.CYAN}Summary:")
        print(f"  Total Tests: {len(self.results)}")
        print(f"  {Fore.GREEN}Passed: {passed}")
        print(f"  {Fore.RED}Failed: {failed}")
        
        if critical_failures:
            print(f"\n{Fore.RED}CRITICAL FAILURES:")
            for failure in critical_failures:
                print(f"  - {failure}")
        
        # Performance summary
        avg_response_time = sum(r[3] for r in self.results) / len(self.results)
        max_response_time = max(r[3] for r in self.results)
        min_response_time = min(r[3] for r in self.results)
        
        print(f"\n{Fore.CYAN}Performance Metrics:")
        print(f"  Average Response Time: {avg_response_time:.3f}s")
        print(f"  Max Response Time: {max_response_time:.3f}s")
        print(f"  Min Response Time: {min_response_time:.3f}s")
        
        # Generate report file
        self.generate_report()
        
    def generate_report(self):
        """Generate a detailed test report"""
        report_path = f"test_output/dashboard_api_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            "test_run": {
                "timestamp": self.start_time.isoformat(),
                "base_url": API_BASE_URL,
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r[1]),
                "failed": sum(1 for r in self.results if not r[1])
            },
            "results": [
                {
                    "endpoint": r[0],
                    "success": r[1],
                    "message": r[2],
                    "response_time": r[3]
                }
                for r in self.results
            ],
            "performance": {
                "average_response_time": sum(r[3] for r in self.results) / len(self.results),
                "max_response_time": max(r[3] for r in self.results),
                "min_response_time": min(r[3] for r in self.results)
            }
        }
        
        import os
        os.makedirs("test_output", exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{Fore.GREEN}Detailed report saved to: {report_path}")

async def main():
    """Main test runner"""
    tester = DashboardAPITester()
    
    # Check if server is running
    print(f"{Fore.YELLOW}Checking if server is running...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/api/system/status") as response:
                if response.status != 200:
                    print(f"{Fore.RED}Server is not responding properly. Please ensure the application is running.")
                    return
    except Exception as e:
        print(f"{Fore.RED}Cannot connect to server: {e}")
        print(f"{Fore.YELLOW}Please ensure the application is running on {API_BASE_URL}")
        return
    
    await tester.run_tests()

if __name__ == "__main__":
    asyncio.run(main())