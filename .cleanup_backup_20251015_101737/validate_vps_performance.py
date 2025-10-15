#!/usr/bin/env python3
"""
VPS Performance Validation Script
Validates the performance claims and system health after AsyncIO fixes
"""

import asyncio
import aiohttp
import time
import json
import subprocess
import logging
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VPSPerformanceValidator:
    """Validates VPS performance after AsyncIO fixes"""

    def __init__(self, vps_host="5.223.63.4", vps_port=8002):
        self.vps_host = vps_host
        self.vps_port = vps_port
        self.base_url = f"http://{vps_host}:{vps_port}"
        self.results = {}

    async def test_dashboard_accessibility(self):
        """Test if dashboard is accessible"""
        logger.info("🌐 Testing dashboard accessibility...")

        try:
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                async with session.get(f"{self.base_url}/", timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response_time = time.time() - start_time

                    self.results['dashboard_accessibility'] = {
                        'status': 'PASS' if response.status == 200 else 'FAIL',
                        'response_code': response.status,
                        'response_time_ms': round(response_time * 1000, 2),
                        'content_length': len(await response.text())
                    }

                    logger.info(f"✅ Dashboard accessible: {response.status} in {response_time*1000:.2f}ms")

        except Exception as e:
            self.results['dashboard_accessibility'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            logger.error(f"❌ Dashboard not accessible: {e}")

    async def test_api_endpoints(self):
        """Test key API endpoints"""
        logger.info("🔌 Testing API endpoints...")

        endpoints = [
            "/api/market/overview",
            "/api/health",
            "/api/cache/stats"
        ]

        endpoint_results = {}

        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                try:
                    start_time = time.time()
                    async with session.get(f"{self.base_url}{endpoint}", timeout=aiohttp.ClientTimeout(total=15)) as response:
                        response_time = time.time() - start_time

                        try:
                            data = await response.json()
                        except:
                            data = await response.text()

                        endpoint_results[endpoint] = {
                            'status': 'PASS' if response.status == 200 else 'FAIL',
                            'response_code': response.status,
                            'response_time_ms': round(response_time * 1000, 2),
                            'has_data': bool(data)
                        }

                        logger.info(f"✅ {endpoint}: {response.status} in {response_time*1000:.2f}ms")

                except Exception as e:
                    endpoint_results[endpoint] = {
                        'status': 'FAIL',
                        'error': str(e)
                    }
                    logger.error(f"❌ {endpoint} failed: {e}")

        self.results['api_endpoints'] = endpoint_results

    def get_vps_system_stats(self):
        """Get VPS system statistics via SSH"""
        logger.info("📊 Collecting VPS system statistics...")

        try:
            # Get CPU usage
            cpu_result = subprocess.run(['ssh', 'vps', 'top -bn1 | grep "Cpu(s)" | awk \'{print $2}\' | cut -d\'%\' -f1'],
                                      capture_output=True, text=True, timeout=10)
            cpu_usage = float(cpu_result.stdout.strip()) if cpu_result.stdout.strip() else 0

            # Get memory usage
            mem_result = subprocess.run(['ssh', 'vps', 'free -m | awk \'NR==2{printf "%.1f", $3*100/$2}\''],
                                      capture_output=True, text=True, timeout=10)
            memory_usage = float(mem_result.stdout.strip()) if mem_result.stdout.strip() else 0

            # Get process info
            proc_result = subprocess.run(['ssh', 'vps', 'ps aux | grep "python.*main.py" | grep -v grep | awk \'{print $3 " " $4}\''],
                                       capture_output=True, text=True, timeout=10)

            if proc_result.stdout.strip():
                proc_stats = proc_result.stdout.strip().split('\n')[0].split()
                process_cpu = float(proc_stats[0]) if proc_stats else 0
                process_mem = float(proc_stats[1]) if len(proc_stats) > 1 else 0
            else:
                process_cpu = 0
                process_mem = 0

            # Check disk usage
            disk_result = subprocess.run(['ssh', 'vps', 'df -h / | awk \'NR==2 {print $5}\' | cut -d\'%\' -f1'],
                                       capture_output=True, text=True, timeout=10)
            disk_usage = float(disk_result.stdout.strip()) if disk_result.stdout.strip() else 0

            self.results['system_stats'] = {
                'status': 'PASS',
                'system_cpu_percent': cpu_usage,
                'system_memory_percent': memory_usage,
                'process_cpu_percent': process_cpu,
                'process_memory_percent': process_mem,
                'disk_usage_percent': disk_usage,
                'timestamp': time.time()
            }

            logger.info(f"✅ System stats: CPU {cpu_usage}%, Memory {memory_usage}%, Process CPU {process_cpu}%")

        except Exception as e:
            self.results['system_stats'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            logger.error(f"❌ Failed to get system stats: {e}")

    def check_process_status(self):
        """Check if trading processes are running properly"""
        logger.info("🔍 Checking process status...")

        try:
            # Check main processes
            proc_result = subprocess.run(['ssh', 'vps', 'ps aux | grep "python.*main.py" | grep -v grep'],
                                       capture_output=True, text=True, timeout=10)

            processes = proc_result.stdout.strip().split('\n') if proc_result.stdout.strip() else []

            # Check for pending tasks warnings in recent logs
            log_result = subprocess.run(['ssh', 'vps', 'find /home/linuxuser/trading/Virtuoso_ccxt -name "*.log" -type f -exec grep -l "was destroyed but it is pending" {} \\; 2>/dev/null | head -1'],
                                      capture_output=True, text=True, timeout=10)

            pending_warnings = bool(log_result.stdout.strip())

            self.results['process_status'] = {
                'status': 'PASS' if len(processes) > 0 and not pending_warnings else 'WARN',
                'running_processes': len(processes),
                'has_pending_warnings': pending_warnings,
                'process_details': processes[:3]  # First 3 processes
            }

            logger.info(f"✅ Process status: {len(processes)} processes running, pending warnings: {pending_warnings}")

        except Exception as e:
            self.results['process_status'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            logger.error(f"❌ Failed to check process status: {e}")

    async def performance_stress_test(self):
        """Run a brief stress test on the API"""
        logger.info("🏋️ Running performance stress test...")

        async def make_request(session, endpoint):
            try:
                start = time.time()
                async with session.get(f"{self.base_url}{endpoint}", timeout=aiohttp.ClientTimeout(total=30)) as response:
                    duration = time.time() - start
                    return {
                        'success': response.status == 200,
                        'duration': duration,
                        'status_code': response.status
                    }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'duration': None
                }

        # Test multiple concurrent requests
        endpoints = ["/api/health", "/api/market/overview", "/api/cache/stats"]
        requests_per_endpoint = 5

        async with aiohttp.ClientSession() as session:
            tasks = []
            for endpoint in endpoints:
                for _ in range(requests_per_endpoint):
                    tasks.append(make_request(session, endpoint))

            start_time = time.time()
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time

            successful_requests = sum(1 for r in results if r['success'])
            total_requests = len(results)
            avg_response_time = sum(r['duration'] for r in results if r['duration']) / max(1, len([r for r in results if r['duration']]))

            self.results['stress_test'] = {
                'status': 'PASS' if successful_requests / total_requests > 0.8 else 'FAIL',
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'success_rate': round(successful_requests / total_requests * 100, 2),
                'total_time_seconds': round(total_time, 2),
                'avg_response_time_ms': round(avg_response_time * 1000, 2)
            }

            logger.info(f"✅ Stress test: {successful_requests}/{total_requests} requests successful, avg {avg_response_time*1000:.2f}ms")

    async def validate_exchange_connections(self):
        """Test exchange connection latencies"""
        logger.info("🔗 Validating exchange connections...")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/market/overview", timeout=aiohttp.ClientTimeout(total=20)) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            exchanges = data.get('exchanges', {}) if isinstance(data, dict) else {}

                            self.results['exchange_connections'] = {
                                'status': 'PASS' if exchanges else 'WARN',
                                'exchanges_found': len(exchanges),
                                'exchange_details': exchanges
                            }

                            logger.info(f"✅ Exchange connections: {len(exchanges)} exchanges detected")

                        except Exception as e:
                            self.results['exchange_connections'] = {
                                'status': 'WARN',
                                'error': f"Failed to parse response: {e}"
                            }
                    else:
                        self.results['exchange_connections'] = {
                            'status': 'FAIL',
                            'error': f"HTTP {response.status}"
                        }

        except Exception as e:
            self.results['exchange_connections'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            logger.error(f"❌ Exchange connection test failed: {e}")

    async def run_validation(self):
        """Run all VPS validation tests"""
        logger.info("🚀 Starting VPS Performance Validation")

        try:
            await self.test_dashboard_accessibility()
            await self.test_api_endpoints()
            self.get_vps_system_stats()
            self.check_process_status()
            await self.performance_stress_test()
            await self.validate_exchange_connections()

            return True

        except Exception as e:
            logger.error(f"VPS validation failed: {e}")
            return False

    def generate_report(self):
        """Generate VPS performance validation report"""
        print("\n" + "="*80)
        print("🖥️ VPS PERFORMANCE VALIDATION REPORT")
        print("="*80)

        passed_tests = 0
        total_tests = len(self.results)

        for test_name, result in self.results.items():
            status = result.get('status', 'UNKNOWN')
            status_icon = "✅" if status == 'PASS' else "⚠️" if status == 'WARN' else "❌"

            print(f"\n{status_icon} {test_name.replace('_', ' ').title()}: {status}")

            if test_name == 'dashboard_accessibility':
                if 'response_time_ms' in result:
                    print(f"   Response Time: {result['response_time_ms']}ms")
                    print(f"   Status Code: {result['response_code']}")

            elif test_name == 'system_stats' and status == 'PASS':
                print(f"   System CPU: {result['system_cpu_percent']:.1f}%")
                print(f"   System Memory: {result['system_memory_percent']:.1f}%")
                print(f"   Process CPU: {result['process_cpu_percent']:.1f}%")
                print(f"   Process Memory: {result['process_memory_percent']:.1f}%")

            elif test_name == 'stress_test':
                if 'success_rate' in result:
                    print(f"   Success Rate: {result['success_rate']}%")
                    print(f"   Avg Response: {result['avg_response_time_ms']}ms")

            elif test_name == 'process_status':
                if 'running_processes' in result:
                    print(f"   Running Processes: {result['running_processes']}")
                    print(f"   Pending Warnings: {result.get('has_pending_warnings', 'Unknown')}")

            if 'error' in result:
                print(f"   Error: {result['error']}")

            if status == 'PASS':
                passed_tests += 1

        print(f"\n📊 VPS SUMMARY: {passed_tests}/{total_tests} tests passed")

        # Performance analysis
        if 'system_stats' in self.results and self.results['system_stats']['status'] == 'PASS':
            stats = self.results['system_stats']
            print(f"\n🎯 PERFORMANCE ANALYSIS:")
            print(f"   Process CPU Usage: {stats['process_cpu_percent']:.1f}% (Target: <70%)")
            print(f"   Process Memory Usage: {stats['process_memory_percent']:.1f}% (Target: <15%)")

            # Check against claimed improvements
            cpu_target = 70  # Target based on claimed 68% improvement
            if stats['process_cpu_percent'] <= cpu_target:
                print(f"   ✅ CPU usage within target ({cpu_target}%)")
            else:
                print(f"   ⚠️ CPU usage above target ({cpu_target}%)")

        return passed_tests == total_tests

async def main():
    """Main validation function"""
    validator = VPSPerformanceValidator()

    try:
        success = await validator.run_validation()
        report_success = validator.generate_report()

        return success and report_success

    except Exception as e:
        logger.error(f"VPS validation failed: {e}")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        exit(0 if result else 1)
    except Exception as e:
        logger.error(f"Failed to run VPS validation: {e}")
        exit(1)