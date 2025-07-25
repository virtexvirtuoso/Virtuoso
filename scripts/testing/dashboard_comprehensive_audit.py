#!/usr/bin/env python3
"""
Comprehensive Dashboard Audit Script
Tests all aspects of dashboard_v10.html functionality
"""

import asyncio
import aiohttp
import json
import time
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import websockets
from colorama import init, Fore, Style
import pandas as pd

init(autoreset=True)

# Configuration
API_BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/dashboard"

# Dashboard HTML location
DASHBOARD_PATH = "src/dashboard/templates/dashboard_v10.html"

class DashboardAuditor:
    def __init__(self):
        self.results = {
            "connectivity": [],
            "api_endpoints": [],
            "websocket": [],
            "ui_elements": [],
            "data_flow": []
        }
        self.start_time = datetime.now()
        
    def print_header(self, title: str):
        """Print section header"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{title}")
        print(f"{Fore.CYAN}{'='*80}\n")
        
    async def check_server_running(self) -> bool:
        """Check if the server is running"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_BASE_URL}/") as response:
                    return response.status in [200, 404]  # 404 is OK, means server is up
        except:
            return False
    
    async def test_api_endpoint(self, session: aiohttp.ClientSession, name: str, url: str, method: str = "GET", body: Optional[Dict] = None) -> Dict:
        """Test a single API endpoint"""
        start = time.time()
        full_url = f"{API_BASE_URL}{url}"
        
        try:
            if method == "GET":
                async with session.get(full_url) as response:
                    elapsed = time.time() - start
                    data = await response.text()
                    
                    try:
                        json_data = json.loads(data)
                    except:
                        json_data = None
                    
                    return {
                        "name": name,
                        "url": url,
                        "method": method,
                        "status": response.status,
                        "success": response.status == 200,
                        "response_time": elapsed,
                        "data_keys": list(json_data.keys()) if json_data and isinstance(json_data, dict) else None,
                        "error": json_data.get("error") if json_data and not response.status == 200 else None
                    }
                    
            elif method == "POST":
                async with session.post(full_url, json=body or {}) as response:
                    elapsed = time.time() - start
                    data = await response.text()
                    
                    try:
                        json_data = json.loads(data)
                    except:
                        json_data = None
                    
                    return {
                        "name": name,
                        "url": url,
                        "method": method,
                        "status": response.status,
                        "success": response.status in [200, 201],
                        "response_time": elapsed,
                        "data_keys": list(json_data.keys()) if json_data and isinstance(json_data, dict) else None,
                        "error": json_data.get("error") if json_data and response.status not in [200, 201] else None
                    }
                    
        except Exception as e:
            elapsed = time.time() - start
            return {
                "name": name,
                "url": url,
                "method": method,
                "status": 0,
                "success": False,
                "response_time": elapsed,
                "data_keys": None,
                "error": str(e)
            }
    
    async def test_websocket_connection(self) -> Dict:
        """Test WebSocket connectivity"""
        start = time.time()
        try:
            async with websockets.connect(WS_URL) as websocket:
                # Send subscription
                await websocket.send(json.dumps({
                    "type": "subscribe",
                    "channel": "dashboard"
                }))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                elapsed = time.time() - start
                data = json.loads(response)
                
                return {
                    "success": True,
                    "response_time": elapsed,
                    "message_type": data.get("type"),
                    "data": data
                }
                
        except asyncio.TimeoutError:
            return {
                "success": False,
                "response_time": time.time() - start,
                "error": "Timeout waiting for WebSocket response"
            }
        except Exception as e:
            return {
                "success": False,
                "response_time": time.time() - start,
                "error": str(e)
            }
    
    def analyze_dashboard_html(self):
        """Analyze dashboard HTML for UI elements and data bindings"""
        if not os.path.exists(DASHBOARD_PATH):
            return {"error": f"Dashboard file not found: {DASHBOARD_PATH}"}
        
        with open(DASHBOARD_PATH, 'r') as f:
            content = f.read()
        
        # Extract key information
        analysis = {
            "file_size": len(content),
            "api_calls": content.count("fetch("),
            "websocket_references": content.count("WebSocket"),
            "event_listeners": content.count("addEventListener"),
            "update_functions": [],
            "charts": [],
            "data_bindings": []
        }
        
        # Find update functions
        import re
        update_functions = re.findall(r'function\s+update(\w+)\s*\(', content)
        analysis["update_functions"] = list(set(update_functions))
        
        # Find chart configurations
        chart_types = re.findall(r"type:\s*['\"](\w+)['\"]", content)
        analysis["charts"] = list(set(chart_types))
        
        # Find data binding elements
        bindings = re.findall(r'id=["\']([^"\']+)["\']', content)
        analysis["data_bindings"] = [b for b in bindings if any(keyword in b for keyword in ['status', 'data', 'chart', 'alert', 'signal'])][:20]
        
        return analysis
    
    async def run_comprehensive_audit(self):
        """Run all audit tests"""
        self.print_header("Dashboard Comprehensive Audit Report")
        print(f"Timestamp: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"API Base URL: {API_BASE_URL}")
        print(f"WebSocket URL: {WS_URL}")
        
        # Step 1: Check server connectivity
        self.print_header("1. Server Connectivity Check")
        is_running = await self.check_server_running()
        
        if not is_running:
            print(f"{Fore.RED}✗ Server is not running!")
            print(f"\n{Fore.YELLOW}To start the application:")
            print(f"  1. Open a terminal in the project directory")
            print(f"  2. Run: source venv311/bin/activate")
            print(f"  3. Run: python src/main.py")
            print(f"     OR")
            print(f"  Run: ./scripts/start_virtuoso.sh")
            return
        
        print(f"{Fore.GREEN}✓ Server is running")
        
        # Step 2: Test all API endpoints
        self.print_header("2. API Endpoint Tests")
        
        endpoints = [
            ("Dashboard Overview", "/api/dashboard/overview", "GET"),
            ("System Status", "/api/system/status", "GET"),
            ("System Performance", "/api/system/performance", "GET"),
            ("Market Overview", "/api/market/overview", "GET"),
            ("Liquidation Alerts", "/api/liquidation/alerts", "GET"),
            ("Stress Indicators", "/api/liquidation/stress-indicators", "GET"),
            ("Cascade Risk", "/api/liquidation/cascade-risk", "GET"),
            ("Alpha Opportunities", "/api/alpha/opportunities", "GET"),
            ("Alpha Scan", "/api/alpha/scan", "POST", {"symbols": ["BTCUSDT"]}),
            ("Trading Portfolio", "/api/trading/portfolio", "GET"),
            ("Trading Orders", "/api/trading/orders?limit=10", "GET"),
            ("Trading Positions", "/api/trading/positions", "GET"),
            ("Bitcoin Beta Status", "/api/bitcoin-beta/status", "GET"),
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint_data in endpoints:
                name = endpoint_data[0]
                url = endpoint_data[1]
                method = endpoint_data[2]
                body = endpoint_data[3] if len(endpoint_data) > 3 else None
                
                result = await self.test_api_endpoint(session, name, url, method, body)
                self.results["api_endpoints"].append(result)
                
                # Display result
                status_icon = "✓" if result["success"] else "✗"
                status_color = Fore.GREEN if result["success"] else Fore.RED
                
                print(f"{status_color}{status_icon} {name:<30} Status: {result['status']:<4} Time: {result['response_time']:.3f}s")
                
                if result["data_keys"]:
                    print(f"  Data keys: {', '.join(result['data_keys'][:5])}")
                if result["error"]:
                    print(f"  {Fore.RED}Error: {result['error']}")
        
        # Step 3: Test WebSocket connection
        self.print_header("3. WebSocket Connection Test")
        ws_result = await self.test_websocket_connection()
        self.results["websocket"] = ws_result
        
        if ws_result["success"]:
            print(f"{Fore.GREEN}✓ WebSocket connected successfully")
            print(f"  Response time: {ws_result['response_time']:.3f}s")
            print(f"  Message type: {ws_result.get('message_type', 'N/A')}")
        else:
            print(f"{Fore.RED}✗ WebSocket connection failed")
            print(f"  Error: {ws_result.get('error', 'Unknown error')}")
        
        # Step 4: Analyze dashboard HTML
        self.print_header("4. Dashboard HTML Analysis")
        html_analysis = self.analyze_dashboard_html()
        self.results["ui_elements"] = html_analysis
        
        if "error" not in html_analysis:
            print(f"File size: {html_analysis['file_size']:,} bytes")
            print(f"API calls: {html_analysis['api_calls']}")
            print(f"WebSocket references: {html_analysis['websocket_references']}")
            print(f"Event listeners: {html_analysis['event_listeners']}")
            print(f"Update functions: {len(html_analysis['update_functions'])}")
            if html_analysis['update_functions']:
                print(f"  - {', '.join(html_analysis['update_functions'][:5])}")
            print(f"Chart types: {', '.join(html_analysis['charts'])}")
            print(f"Data bindings: {len(html_analysis['data_bindings'])}")
        else:
            print(f"{Fore.RED}✗ {html_analysis['error']}")
        
        # Step 5: Generate summary report
        self.print_header("5. Summary Report")
        self.generate_summary()
        
    def generate_summary(self):
        """Generate audit summary"""
        # API endpoint summary
        api_results = self.results["api_endpoints"]
        total_endpoints = len(api_results)
        successful = sum(1 for r in api_results if r["success"])
        failed = total_endpoints - successful
        
        print(f"\n{Fore.CYAN}API Endpoints:")
        print(f"  Total tested: {total_endpoints}")
        print(f"  {Fore.GREEN}Successful: {successful}")
        print(f"  {Fore.RED}Failed: {failed}")
        
        if failed > 0:
            print(f"\n{Fore.RED}Failed endpoints:")
            for result in api_results:
                if not result["success"]:
                    print(f"  - {result['name']}: {result.get('error', 'Unknown error')}")
        
        # Performance metrics
        avg_response_time = sum(r["response_time"] for r in api_results) / len(api_results) if api_results else 0
        max_response_time = max((r["response_time"] for r in api_results), default=0)
        
        print(f"\n{Fore.CYAN}Performance:")
        print(f"  Average response time: {avg_response_time:.3f}s")
        print(f"  Max response time: {max_response_time:.3f}s")
        
        # WebSocket status
        ws_status = self.results.get("websocket", {})
        print(f"\n{Fore.CYAN}WebSocket:")
        if ws_status.get("success"):
            print(f"  {Fore.GREEN}✓ Connected and responsive")
        else:
            print(f"  {Fore.RED}✗ Connection failed: {ws_status.get('error', 'Unknown error')}")
        
        # Save detailed report
        self.save_detailed_report()
        
    def save_detailed_report(self):
        """Save detailed audit report to file"""
        report_dir = "test_output"
        os.makedirs(report_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"{report_dir}/dashboard_audit_{timestamp}.json"
        
        report = {
            "audit_timestamp": self.start_time.isoformat(),
            "api_base_url": API_BASE_URL,
            "results": self.results,
            "summary": {
                "total_api_endpoints": len(self.results["api_endpoints"]),
                "successful_endpoints": sum(1 for r in self.results["api_endpoints"] if r["success"]),
                "websocket_connected": self.results.get("websocket", {}).get("success", False)
            }
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n{Fore.GREEN}Detailed report saved to: {report_path}")

async def main():
    """Main entry point"""
    auditor = DashboardAuditor()
    await auditor.run_comprehensive_audit()

if __name__ == "__main__":
    asyncio.run(main())