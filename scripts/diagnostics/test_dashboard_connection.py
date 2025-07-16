#!/usr/bin/env python3
"""
Dashboard Connection Diagnostic Tool
Tests all API endpoints that the dashboard_v10.html requires
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# API endpoints to test (matching dashboard requirements)
ENDPOINTS = {
    'dashboard_overview': 'http://localhost:8001/api/dashboard/overview',
    'top_symbols': 'http://localhost:8001/api/top-symbols',
    'liquidation_alerts': 'http://localhost:8001/api/liquidation/alerts',
    'liquidation_stress': 'http://localhost:8001/api/liquidation/stress-indicators',
    'liquidation_cascade': 'http://localhost:8001/api/liquidation/cascade-risk',
    'alpha_opportunities': 'http://localhost:8001/api/alpha/opportunities',
    'system_status': 'http://localhost:8001/api/system/status',
    'system_performance': 'http://localhost:8001/api/system/performance',
    'trading_portfolio': 'http://localhost:8001/api/trading/portfolio',
    'trading_orders': 'http://localhost:8001/api/trading/orders?limit=10',
    'trading_positions': 'http://localhost:8001/api/trading/positions',
    'market_overview': 'http://localhost:8001/api/market/overview',
    'bitcoin_beta': 'http://localhost:8001/api/bitcoin-beta/status',
    'signals_latest': 'http://localhost:8001/api/signals/latest?limit=10',
    'dashboard_alerts': 'http://localhost:8001/api/dashboard/alerts/recent?limit=10',
    'manipulation_alerts': 'http://localhost:8001/api/manipulation/alerts',
    'manipulation_stats': 'http://localhost:8001/api/manipulation/stats',
    'correlation_matrix': 'http://localhost:8001/api/correlation/live-matrix',
    'signals_active': 'http://localhost:8001/api/signals/active'
}

class DashboardDiagnostic:
    def __init__(self):
        self.results = {}
        self.session = None
        
    async def test_endpoint(self, name: str, url: str) -> Dict[str, Any]:
        """Test a single API endpoint"""
        try:
            start_time = time.time()
            
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                response_time = (time.time() - start_time) * 1000  # ms
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        data_size = len(json.dumps(data)) if data else 0
                        
                        return {
                            'status': 'SUCCESS',
                            'status_code': response.status,
                            'response_time_ms': round(response_time, 2),
                            'data_size_bytes': data_size,
                            'has_data': bool(data),
                            'data_preview': str(data)[:200] + '...' if data else 'No data'
                        }
                    except json.JSONDecodeError:
                        text = await response.text()
                        return {
                            'status': 'ERROR',
                            'status_code': response.status,
                            'response_time_ms': round(response_time, 2),
                            'error': 'Invalid JSON response',
                            'response_preview': text[:200] + '...' if text else 'Empty response'
                        }
                else:
                    error_text = await response.text()
                    return {
                        'status': 'HTTP_ERROR',
                        'status_code': response.status,
                        'response_time_ms': round(response_time, 2),
                        'error': f'HTTP {response.status}',
                        'response_preview': error_text[:200] + '...' if error_text else 'No error details'
                    }
                    
        except asyncio.TimeoutError:
            return {
                'status': 'TIMEOUT',
                'error': 'Request timed out after 5 seconds'
            }
        except aiohttp.ClientConnectorError:
            return {
                'status': 'CONNECTION_ERROR',
                'error': 'Could not connect to server'
            }
        except Exception as e:
            return {
                'status': 'UNEXPECTED_ERROR',
                'error': str(e)
            }
    
    async def run_diagnostics(self) -> Dict[str, Any]:
        """Run diagnostics on all endpoints"""
        print("🔍 Starting Dashboard API Diagnostics...")
        print(f"📅 Timestamp: {datetime.now().isoformat()}")
        print(f"🎯 Testing {len(ENDPOINTS)} endpoints")
        print("=" * 60)
        
        # Create aiohttp session
        connector = aiohttp.TCPConnector(limit=10)
        self.session = aiohttp.ClientSession(connector=connector)
        
        try:
            # Test all endpoints concurrently
            tasks = []
            for name, url in ENDPOINTS.items():
                task = asyncio.create_task(self.test_endpoint(name, url))
                tasks.append((name, task))
            
            # Collect results
            for name, task in tasks:
                result = await task
                self.results[name] = result
                
                # Print result
                status_emoji = {
                    'SUCCESS': '✅',
                    'HTTP_ERROR': '❌',
                    'CONNECTION_ERROR': '🔌',
                    'TIMEOUT': '⏰',
                    'ERROR': '⚠️',
                    'UNEXPECTED_ERROR': '💥'
                }.get(result['status'], '❓')
                
                print(f"{status_emoji} {name:<25} {result['status']:<15} ", end="")
                
                if result.get('response_time_ms'):
                    print(f"{result['response_time_ms']:>6.1f}ms ", end="")
                
                if result.get('data_size_bytes'):
                    print(f"{result['data_size_bytes']:>8}B ", end="")
                
                if result.get('error'):
                    print(f"- {result['error']}")
                else:
                    print()
        
        finally:
            await self.session.close()
        
        # Generate summary
        summary = self.generate_summary()
        return {
            'timestamp': datetime.now().isoformat(),
            'summary': summary,
            'detailed_results': self.results
        }
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate diagnostic summary"""
        total_endpoints = len(self.results)
        successful = sum(1 for r in self.results.values() if r['status'] == 'SUCCESS')
        failed = total_endpoints - successful
        
        avg_response_time = 0
        response_times = [r.get('response_time_ms', 0) for r in self.results.values() if r.get('response_time_ms')]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
        
        # Categorize failures
        failure_types = {}
        for result in self.results.values():
            if result['status'] != 'SUCCESS':
                failure_types[result['status']] = failure_types.get(result['status'], 0) + 1
        
        return {
            'total_endpoints': total_endpoints,
            'successful': successful,
            'failed': failed,
            'success_rate': round((successful / total_endpoints) * 100, 1),
            'avg_response_time_ms': round(avg_response_time, 2),
            'failure_breakdown': failure_types
        }

async def main():
    """Main diagnostic function"""
    diagnostic = DashboardDiagnostic()
    results = await diagnostic.run_diagnostics()
    
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    summary = results['summary']
    print(f"✅ Successful endpoints: {summary['successful']}/{summary['total_endpoints']} ({summary['success_rate']}%)")
    print(f"⚡ Average response time: {summary['avg_response_time_ms']} ms")
    
    if summary['failed'] > 0:
        print(f"❌ Failed endpoints: {summary['failed']}")
        print("📋 Failure breakdown:")
        for failure_type, count in summary['failure_breakdown'].items():
            print(f"   • {failure_type}: {count}")
    
    print("\n🎯 Dashboard Status:")
    if summary['success_rate'] >= 80:
        print("✅ Dashboard should work properly - Most endpoints are responding")
    elif summary['success_rate'] >= 50:
        print("⚠️  Dashboard may have limited functionality - Some endpoints failing")
    else:
        print("❌ Dashboard likely won't work - Too many endpoint failures")
    
    # Check critical endpoints
    critical_endpoints = ['dashboard_overview', 'top_symbols', 'system_status']
    critical_working = all(results['detailed_results'].get(ep, {}).get('status') == 'SUCCESS' 
                          for ep in critical_endpoints)
    
    if critical_working:
        print("✅ Critical endpoints (dashboard_overview, top_symbols, system_status) are working")
    else:
        print("❌ Some critical endpoints are not working - dashboard may show 'NO DATA'")
    
    print(f"\n📁 Full results saved to: dashboard_diagnostic_results.json")
    
    # Save detailed results
    with open('dashboard_diagnostic_results.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main()) 