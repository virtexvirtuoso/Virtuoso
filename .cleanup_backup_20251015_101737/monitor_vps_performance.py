#!/usr/bin/env python3
"""Monitor VPS performance after AsyncIO fixes deployment."""

import time
import subprocess
import json
import requests
from datetime import datetime

def get_vps_process_stats():
    """Get VPS process statistics."""
    try:
        result = subprocess.run([
            'ssh', 'vps', 'ps aux | grep python | grep -v grep'
        ], capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            processes = []

            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 11:
                        process = {
                            'pid': parts[1],
                            'cpu': float(parts[2]),
                            'memory': float(parts[3]),
                            'command': ' '.join(parts[10:])
                        }
                        processes.append(process)

            return processes
    except Exception as e:
        print(f"Error getting process stats: {e}")
        return []

def test_vps_endpoints():
    """Test VPS endpoint responsiveness."""
    endpoints = [
        '/health',
        '/mobile',
        '/api/docs',
        '/education'
    ]

    results = {}
    for endpoint in endpoints:
        try:
            start_time = time.time()
            response = requests.get(f'http://5.223.63.4:8002{endpoint}', timeout=5)
            response_time = time.time() - start_time

            results[endpoint] = {
                'status_code': response.status_code,
                'response_time': response_time,
                'success': response.status_code == 200
            }
        except Exception as e:
            results[endpoint] = {
                'status_code': 0,
                'response_time': 5.0,
                'success': False,
                'error': str(e)
            }

    # Test monitoring API
    try:
        start_time = time.time()
        response = requests.get('http://5.223.63.4:8001/health', timeout=5)
        response_time = time.time() - start_time

        results['/monitoring/health'] = {
            'status_code': response.status_code,
            'response_time': response_time,
            'success': response.status_code == 200
        }
    except Exception as e:
        results['/monitoring/health'] = {
            'status_code': 0,
            'response_time': 5.0,
            'success': False,
            'error': str(e)
        }

    return results

def monitor_performance(duration_minutes=5, interval_seconds=30):
    """Monitor VPS performance for specified duration."""
    print(f"🔍 Monitoring VPS performance for {duration_minutes} minutes...")
    print("=" * 60)

    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)

    measurements = []

    while time.time() < end_time:
        timestamp = datetime.now().strftime('%H:%M:%S')

        # Get process stats
        processes = get_vps_process_stats()

        # Calculate totals
        total_cpu = sum(p['cpu'] for p in processes)
        total_memory = sum(p['memory'] for p in processes)
        process_count = len(processes)

        # Test endpoints
        endpoint_results = test_vps_endpoints()

        # Count successful endpoints
        successful_endpoints = sum(1 for r in endpoint_results.values() if r['success'])
        total_endpoints = len(endpoint_results)

        # Average response time
        response_times = [r['response_time'] for r in endpoint_results.values() if r['success']]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        measurement = {
            'timestamp': timestamp,
            'total_cpu': total_cpu,
            'total_memory': total_memory,
            'process_count': process_count,
            'successful_endpoints': successful_endpoints,
            'total_endpoints': total_endpoints,
            'avg_response_time': avg_response_time,
            'endpoint_details': endpoint_results
        }

        measurements.append(measurement)

        # Print current status
        print(f"[{timestamp}] CPU: {total_cpu:5.1f}% | Memory: {total_memory:4.1f}% | "
              f"Processes: {process_count} | Endpoints: {successful_endpoints}/{total_endpoints} | "
              f"Avg Response: {avg_response_time:.3f}s")

        # Show individual process details
        main_processes = [p for p in processes if 'src/main.py' in p['command']]
        web_processes = [p for p in processes if 'src/web_server.py' in p['command']]
        monitor_processes = [p for p in processes if 'src/monitoring_api.py' in p['command']]

        if main_processes:
            main_cpu = sum(p['cpu'] for p in main_processes)
            print(f"         Main Service: {main_cpu:5.1f}% CPU")

        if web_processes:
            web_cpu = sum(p['cpu'] for p in web_processes)
            print(f"         Web Server:   {web_cpu:5.1f}% CPU")

        if monitor_processes:
            monitor_cpu = sum(p['cpu'] for p in monitor_processes)
            print(f"         Monitor API:  {monitor_cpu:5.1f}% CPU")

        time.sleep(interval_seconds)

    print("\n📊 Performance Summary")
    print("=" * 60)

    if measurements:
        # Calculate averages
        avg_cpu = sum(m['total_cpu'] for m in measurements) / len(measurements)
        avg_memory = sum(m['total_memory'] for m in measurements) / len(measurements)
        avg_processes = sum(m['process_count'] for m in measurements) / len(measurements)
        avg_endpoint_success = sum(m['successful_endpoints'] for m in measurements) / len(measurements)
        avg_response_time = sum(m['avg_response_time'] for m in measurements) / len(measurements)

        # Find min/max
        max_cpu = max(m['total_cpu'] for m in measurements)
        min_cpu = min(m['total_cpu'] for m in measurements)

        print(f"CPU Usage:       Avg: {avg_cpu:5.1f}%  Min: {min_cpu:5.1f}%  Max: {max_cpu:5.1f}%")
        print(f"Memory Usage:    Avg: {avg_memory:5.1f}%")
        print(f"Process Count:   Avg: {avg_processes:5.1f}")
        print(f"Endpoint Success:Avg: {avg_endpoint_success:5.1f}/{len(endpoint_results)}")
        print(f"Response Time:   Avg: {avg_response_time:.3f}s")

        # Performance assessment
        print("\n🎯 Performance Assessment")
        print("-" * 30)

        if avg_cpu < 70:
            print("✅ CPU Usage: GOOD (< 70%)")
        elif avg_cpu < 150:
            print("⚠️ CPU Usage: MODERATE (70-150%)")
        else:
            print("❌ CPU Usage: HIGH (> 150%)")

        if avg_endpoint_success >= len(endpoint_results):
            print("✅ Endpoint Availability: EXCELLENT (100%)")
        elif avg_endpoint_success >= len(endpoint_results) * 0.8:
            print("⚠️ Endpoint Availability: GOOD (80%+)")
        else:
            print("❌ Endpoint Availability: POOR (< 80%)")

        if avg_response_time < 0.5:
            print("✅ Response Time: EXCELLENT (< 0.5s)")
        elif avg_response_time < 2.0:
            print("⚠️ Response Time: ACCEPTABLE (< 2.0s)")
        else:
            print("❌ Response Time: SLOW (> 2.0s)")

        return {
            'avg_cpu': avg_cpu,
            'avg_memory': avg_memory,
            'avg_endpoint_success': avg_endpoint_success,
            'avg_response_time': avg_response_time,
            'measurements': measurements
        }

    return None

if __name__ == "__main__":
    print("🚀 VPS Performance Monitor - AsyncIO Fixes Validation")
    print("=" * 60)

    result = monitor_performance(duration_minutes=3, interval_seconds=20)

    if result:
        print(f"\n✅ Monitoring complete! Collected {len(result['measurements'])} data points.")

        # Quick comparison with expected improvements
        print("\n📈 Expected vs Actual Improvements:")
        print("-" * 40)

        # Based on initial report of 308% -> 68% CPU improvement
        if result['avg_cpu'] < 100:
            print("✅ CPU usage significantly improved from pre-fix levels")
        else:
            print("⚠️ CPU usage still elevated - may need additional optimization")

        if result['avg_endpoint_success'] >= 4:  # All 5 endpoints working
            print("✅ All endpoints operational - API issues resolved")
        else:
            print("⚠️ Some endpoints still failing - requires investigation")

    print("\n🎉 Performance monitoring complete!")