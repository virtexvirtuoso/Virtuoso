#!/usr/bin/env python3
"""
Simple Dashboard Audit Script
Tests all aspects of dashboard_v10.html functionality without external dependencies
"""

import asyncio
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Optional
import urllib.request
import urllib.error

# Configuration
API_BASE_URL = "http://localhost:8000"
DASHBOARD_PATH = "src/dashboard/templates/dashboard_v10.html"

class DashboardAuditor:
    def __init__(self):
        self.results = {
            "connectivity": [],
            "api_endpoints": [],
            "ui_analysis": {}
        }
        self.start_time = datetime.now()
        
    def print_header(self, title: str):
        """Print section header"""
        print(f"\n{'='*60}")
        print(f"{title}")
        print(f"{'='*60}\n")
        
    def check_server_running(self) -> bool:
        """Check if the server is running"""
        try:
            response = urllib.request.urlopen(f"{API_BASE_URL}/", timeout=5)
            return True
        except urllib.error.HTTPError as e:
            # 404 is OK, means server is up but no root route
            return e.code == 404
        except:
            return False
    
    def test_api_endpoint(self, name: str, url: str, method: str = "GET") -> Dict:
        """Test a single API endpoint"""
        start = time.time()
        full_url = f"{API_BASE_URL}{url}"
        
        try:
            if method == "GET":
                response = urllib.request.urlopen(full_url, timeout=10)
                data = response.read().decode('utf-8')
                elapsed = time.time() - start
                
                try:
                    json_data = json.loads(data)
                    data_keys = list(json_data.keys()) if isinstance(json_data, dict) else None
                except:
                    json_data = None
                    data_keys = None
                
                return {
                    "name": name,
                    "url": url,
                    "method": method,
                    "status": response.code,
                    "success": response.code == 200,
                    "response_time": elapsed,
                    "data_keys": data_keys
                }
                
        except urllib.error.HTTPError as e:
            elapsed = time.time() - start
            return {
                "name": name,
                "url": url,
                "method": method,
                "status": e.code,
                "success": False,
                "response_time": elapsed,
                "error": f"HTTP {e.code}"
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
            "api_endpoints_found": []
        }
        
        # Find API endpoints
        import re
        api_patterns = re.findall(r'\$\{API_BASE_URL\}([^`\'\"]+)', content)
        analysis["api_endpoints_found"] = list(set(api_patterns))[:20]
        
        return analysis
    
    def run_audit(self):
        """Run all audit tests"""
        self.print_header("Dashboard Audit Report")
        print(f"Timestamp: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"API Base URL: {API_BASE_URL}")
        
        # Step 1: Check server connectivity
        self.print_header("1. Server Connectivity Check")
        is_running = self.check_server_running()
        
        if not is_running:
            print("✗ Server is not running!")
            print("\nTo start the application:")
            print("  1. Open a terminal in the project directory")
            print("  2. Run: source venv311/bin/activate")
            print("  3. Run: python src/main.py")
            print("     OR")
            print("  Run: ./scripts/start_virtuoso.sh")
            return
        
        print("✓ Server is running")
        
        # Step 2: Test API endpoints
        self.print_header("2. API Endpoint Tests")
        
        endpoints = [
            ("Dashboard Overview", "/api/dashboard/overview"),
            ("System Status", "/api/system/status"),
            ("System Performance", "/api/system/performance"),
            ("Market Overview", "/api/market/overview"),
            ("Liquidation Alerts", "/api/liquidation/alerts"),
            ("Stress Indicators", "/api/liquidation/stress-indicators"),
            ("Cascade Risk", "/api/liquidation/cascade-risk"),
            ("Alpha Opportunities", "/api/alpha/opportunities"),
            ("Trading Portfolio", "/api/trading/portfolio"),
            ("Trading Orders", "/api/trading/orders?limit=10"),
            ("Trading Positions", "/api/trading/positions"),
            ("Bitcoin Beta Status", "/api/bitcoin-beta/status"),
        ]
        
        for name, url in endpoints:
            result = self.test_api_endpoint(name, url)
            self.results["api_endpoints"].append(result)
            
            # Display result
            status = "✓" if result["success"] else "✗"
            print(f"{status} {name:<30} Status: {result.get('status', 0):<4} Time: {result['response_time']:.3f}s")
            
            if result.get("data_keys"):
                print(f"  Data keys: {', '.join(result['data_keys'][:5])}")
            if result.get("error"):
                print(f"  Error: {result['error']}")
        
        # Step 3: Analyze dashboard HTML
        self.print_header("3. Dashboard HTML Analysis")
        html_analysis = self.analyze_dashboard_html()
        self.results["ui_analysis"] = html_analysis
        
        if "error" not in html_analysis:
            print(f"File size: {html_analysis['file_size']:,} bytes")
            print(f"API fetch() calls: {html_analysis['api_calls']}")
            print(f"WebSocket references: {html_analysis['websocket_references']}")
            print(f"Event listeners: {html_analysis['event_listeners']}")
            print(f"\nAPI endpoints found in HTML:")
            for endpoint in html_analysis['api_endpoints_found'][:10]:
                print(f"  - {endpoint}")
        else:
            print(f"✗ {html_analysis['error']}")
        
        # Step 4: Generate summary
        self.print_header("4. Summary")
        self.generate_summary()
        
    def generate_summary(self):
        """Generate audit summary"""
        api_results = self.results["api_endpoints"]
        total_endpoints = len(api_results)
        successful = sum(1 for r in api_results if r["success"])
        failed = total_endpoints - successful
        
        print(f"API Endpoints:")
        print(f"  Total tested: {total_endpoints}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        
        if failed > 0:
            print(f"\nFailed endpoints:")
            for result in api_results:
                if not result["success"]:
                    print(f"  - {result['name']}: {result.get('error', 'Unknown error')}")
        
        # Performance metrics
        if api_results:
            avg_response_time = sum(r["response_time"] for r in api_results) / len(api_results)
            max_response_time = max(r["response_time"] for r in api_results)
            
            print(f"\nPerformance:")
            print(f"  Average response time: {avg_response_time:.3f}s")
            print(f"  Max response time: {max_response_time:.3f}s")
        
        # Save report
        self.save_report()
        
    def save_report(self):
        """Save audit report to file"""
        report_dir = "test_output"
        os.makedirs(report_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"{report_dir}/dashboard_audit_{timestamp}.json"
        
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\nDetailed report saved to: {report_path}")

def main():
    """Main entry point"""
    auditor = DashboardAuditor()
    auditor.run_audit()

if __name__ == "__main__":
    main()