#!/usr/bin/env python3
"""
Deep investigation of API endpoint performance and data loading patterns.
Captures timing metrics, API call sequences, and identifies slow/failing data loads.
"""

from playwright.sync_api import sync_playwright
import json
from datetime import datetime
from collections import defaultdict

def investigate_api_performance():
    url = "os.getenv("VPS_BASE_URL", "http://localhost:8002")/desktop-v2"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        # Track API calls with detailed timing
        api_calls = []
        api_timing = defaultdict(list)
        slow_requests = []

        def handle_request(request):
            if '/api/' in request.url or request.url.startswith('os.getenv("VPS_BASE_URL", "http://localhost:8002")'):
                api_calls.append({
                    "url": request.url,
                    "method": request.method,
                    "timestamp": datetime.now().isoformat(),
                    "type": "request"
                })

        def handle_response(response):
            if '/api/' in response.url or response.url.startswith('os.getenv("VPS_BASE_URL", "http://localhost:8002")'):
                timing = response.request.timing
                total_time = (
                    timing.get('responseEnd', 0) - timing.get('requestStart', 0)
                    if timing.get('responseEnd') and timing.get('requestStart')
                    else 0
                )

                api_data = {
                    "url": response.url,
                    "status": response.status,
                    "timing_ms": total_time,
                    "ok": response.ok,
                    "timestamp": datetime.now().isoformat()
                }

                api_calls.append(api_data)

                # Track endpoint patterns
                endpoint = response.url.split('?')[0]  # Remove query params
                api_timing[endpoint].append(total_time)

                # Flag slow requests (>2 seconds)
                if total_time > 2000:
                    slow_requests.append({
                        "url": response.url,
                        "status": response.status,
                        "time_ms": total_time
                    })

        page.on("request", handle_request)
        page.on("response", handle_response)

        # Capture console for data loading errors
        console_logs = []
        page.on("console", lambda msg: console_logs.append({
            "type": msg.type,
            "text": msg.text
        }))

        print(f"[1/7] Navigating to {url}...")
        start_time = datetime.now()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        print("[2/7] Waiting for initial render...")
        page.wait_for_load_state("load", timeout=60000)

        print("[3/7] Waiting for network idle...")
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except:
            print("WARNING: Network didn't become idle within 30s")

        # Wait for additional dynamic content
        print("[4/7] Waiting for dynamic API calls...")
        page.wait_for_timeout(5000)

        end_time = datetime.now()
        total_load_time = (end_time - start_time).total_seconds()

        print("[5/7] Analyzing data loading patterns...")

        # Check for empty data states
        empty_charts = page.locator('canvas:empty, svg:empty').count()
        loading_spinners = page.locator('[class*="spinner"], [class*="loading"]').count()

        # Check for "No data" or empty state messages
        no_data_messages = []
        try:
            no_data_elements = page.locator('text=/no data|loading|unavailable|error loading/i').all()
            no_data_messages = [elem.text_content() for elem in no_data_elements[:10]]
        except:
            pass

        # Analyze API endpoint performance
        endpoint_stats = {}
        for endpoint, times in api_timing.items():
            if times:
                endpoint_stats[endpoint] = {
                    "count": len(times),
                    "avg_ms": sum(times) / len(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "total_ms": sum(times)
                }

        # Sort by slowest average
        sorted_endpoints = sorted(
            endpoint_stats.items(),
            key=lambda x: x[1]['avg_ms'],
            reverse=True
        )

        print("[6/7] Taking screenshot of current state...")
        screenshot_path = f"/tmp/api_performance_{timestamp}.png"
        page.screenshot(path=screenshot_path, full_page=True)

        browser.close()

        print("[7/7] Generating performance report...")

        report = {
            "timestamp": timestamp,
            "url": url,
            "total_load_time_seconds": total_load_time,
            "api_summary": {
                "total_api_calls": len([call for call in api_calls if 'status' in call]),
                "unique_endpoints": len(api_timing),
                "slow_requests_count": len(slow_requests)
            },
            "slow_requests": slow_requests,
            "endpoint_performance": dict(sorted_endpoints[:10]),  # Top 10 slowest
            "data_loading_issues": {
                "empty_charts": empty_charts,
                "loading_spinners_visible": loading_spinners,
                "no_data_messages": no_data_messages
            },
            "console_warnings": [log for log in console_logs if log['type'] in ['warning', 'error']],
            "all_api_calls": api_calls
        }

        # Save report
        report_path = f"/tmp/api_performance_{timestamp}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        # Print summary
        print("\n" + "="*80)
        print("API PERFORMANCE ANALYSIS")
        print("="*80)
        print(f"\n⏱️  Total Page Load Time: {total_load_time:.2f} seconds")
        print(f"\n📡 API Activity:")
        print(f"  - Total API calls: {report['api_summary']['total_api_calls']}")
        print(f"  - Unique endpoints: {report['api_summary']['unique_endpoints']}")
        print(f"  - Slow requests (>2s): {report['api_summary']['slow_requests_count']}")

        if slow_requests:
            print(f"\n🐌 Slow API Requests (>2 seconds):")
            for req in slow_requests[:5]:
                print(f"  - [{req['status']}] {req['url']}")
                print(f"    Time: {req['time_ms']:.0f}ms")

        if sorted_endpoints:
            print(f"\n📊 Slowest Endpoints (by average):")
            for endpoint, stats in sorted_endpoints[:5]:
                print(f"  - {endpoint}")
                print(f"    Avg: {stats['avg_ms']:.0f}ms | Max: {stats['max_ms']:.0f}ms | Calls: {stats['count']}")

        if loading_spinners > 0:
            print(f"\n⚠️  Loading indicators still visible: {loading_spinners}")

        if empty_charts > 0:
            print(f"\n⚠️  Empty charts detected: {empty_charts}")

        if no_data_messages:
            print(f"\n⚠️  Data loading messages found:")
            for msg in no_data_messages:
                print(f"  - {msg}")

        console_issues = [log for log in console_logs if log['type'] in ['warning', 'error']]
        if console_issues:
            print(f"\n🐛 Console Issues ({len(console_issues)} total):")
            for log in console_issues[:10]:
                print(f"  - [{log['type'].upper()}] {log['text']}")

        print(f"\n📁 Files Generated:")
        print(f"  - Screenshot: {screenshot_path}")
        print(f"  - Performance report: {report_path}")
        print("="*80)

        return report

if __name__ == "__main__":
    investigate_api_performance()
