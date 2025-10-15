#!/usr/bin/env python3
"""
Dashboard UI Functionality Test
Tests actual browser loading and API calls from the dashboard
"""
import requests
import json
import time
from datetime import datetime

# VPS dashboard URL
DASHBOARD_URL = "45.77.40.77:8004"

def test_dashboard_html_loading():
    """Test if dashboard HTML pages load correctly"""
    endpoints_to_test = [
        ("Dashboard Root", f"http://{DASHBOARD_URL}/dashboard/"),
        ("Mobile Dashboard", f"http://{DASHBOARD_URL}/dashboard/mobile"),
    ]

    results = []

    for name, url in endpoints_to_test:
        try:
            response = requests.get(url, timeout=30)

            # Check if HTML content is returned
            content = response.text
            has_html = '<!DOCTYPE html>' in content or '<html' in content
            has_javascript = '<script' in content
            has_api_calls = 'fetch(' in content or 'xhr' in content.lower() or 'xmlhttprequest' in content.lower()

            # Look for specific API endpoint references in the HTML
            api_endpoints_found = []
            common_endpoints = [
                '/api/dashboard/overview',
                '/api/dashboard-cached/overview',
                '/api/dashboard-cached/mobile-data',
                '/api/market-overview',
                '/api/signals',
                '/dashboard/api/market/overview',
                '/dashboard/api/signals/top'
            ]

            for endpoint in common_endpoints:
                if endpoint in content:
                    api_endpoints_found.append(endpoint)

            result = {
                "name": name,
                "url": url,
                "status": response.status_code,
                "content_length": len(content),
                "has_html": has_html,
                "has_javascript": has_javascript,
                "has_api_calls": has_api_calls,
                "api_endpoints_found": api_endpoints_found,
                "success": response.status_code == 200 and has_html
            }

            results.append(result)
            print(f"✓ {name}: Status {response.status_code}, HTML: {has_html}, JS: {has_javascript}, APIs: {len(api_endpoints_found)}")

        except Exception as e:
            result = {
                "name": name,
                "url": url,
                "error": str(e),
                "success": False
            }
            results.append(result)
            print(f"✗ {name}: ERROR - {e}")

    return results

def test_cors_and_external_access():
    """Test if APIs can be accessed externally (CORS issues)"""
    external_api_tests = [
        f"http://{DASHBOARD_URL}/api/health",
        f"http://{DASHBOARD_URL}/api/dashboard/overview",
        f"http://{DASHBOARD_URL}/api/dashboard-cached/overview",
        f"http://{DASHBOARD_URL}/dashboard/api/market/overview"
    ]

    results = []

    for url in external_api_tests:
        try:
            # Test with different headers that a browser would send
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin': f'http://{DASHBOARD_URL}',
                'Referer': f'http://{DASHBOARD_URL}/dashboard/'
            }

            response = requests.get(url, headers=headers, timeout=10)

            result = {
                "url": url,
                "status": response.status_code,
                "headers": dict(response.headers),
                "cors_headers": {
                    "access_control_allow_origin": response.headers.get("access-control-allow-origin"),
                    "access_control_allow_methods": response.headers.get("access-control-allow-methods"),
                    "access_control_allow_headers": response.headers.get("access-control-allow-headers")
                },
                "success": response.status_code == 200
            }

            results.append(result)
            print(f"{'✓' if result['success'] else '✗'} External access {url}: {response.status_code}")

        except Exception as e:
            result = {
                "url": url,
                "error": str(e),
                "success": False
            }
            results.append(result)
            print(f"✗ External access {url}: ERROR - {e}")

    return results

def test_real_vs_mock_data():
    """Analyze if data is real or mock by looking for patterns"""
    test_urls = [
        f"http://{DASHBOARD_URL}/api/dashboard/overview",
        f"http://{DASHBOARD_URL}/api/dashboard-cached/overview",
        f"http://{DASHBOARD_URL}/api/dashboard-cached/symbols",
        f"http://{DASHBOARD_URL}/api/bitcoin-beta/realtime"
    ]

    results = []

    for url in test_urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()

                # Look for signs of mock data
                mock_indicators = []

                # Check for round numbers (often indicates mock data)
                def has_round_numbers(obj, path=""):
                    found = []
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if isinstance(v, (int, float)):
                                if isinstance(v, float) and v == int(v):  # Like 65000.0 -> 65000
                                    found.append(f"{path}.{k} = {v} (round float)")
                                elif isinstance(v, int) and v % 1000 == 0 and v > 1000:  # Round thousands
                                    found.append(f"{path}.{k} = {v} (round thousands)")
                            elif isinstance(v, (dict, list)):
                                found.extend(has_round_numbers(v, f"{path}.{k}"))
                    elif isinstance(obj, list):
                        for i, v in enumerate(obj):
                            found.extend(has_round_numbers(v, f"{path}[{i}]"))
                    return found

                round_numbers = has_round_numbers(data)
                if round_numbers:
                    mock_indicators.extend(round_numbers)

                # Check for identical timestamps (sign of mock data)
                timestamps = []
                def collect_timestamps(obj):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if 'timestamp' in k.lower() and isinstance(v, str):
                                timestamps.append(v)
                            elif isinstance(v, (dict, list)):
                                collect_timestamps(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            collect_timestamps(item)

                collect_timestamps(data)
                unique_timestamps = set(timestamps)
                if len(timestamps) > 1 and len(unique_timestamps) < len(timestamps):
                    mock_indicators.append(f"Duplicate timestamps found: {len(timestamps)} total, {len(unique_timestamps)} unique")

                # Look for static values that should change
                static_indicators = []
                if 'btc_price' in str(data) and '65000' in str(data):
                    static_indicators.append("BTC price appears to be static at 65000")

                result = {
                    "url": url,
                    "mock_indicators": mock_indicators,
                    "static_indicators": static_indicators,
                    "is_likely_mock": len(mock_indicators) > 0 or len(static_indicators) > 0,
                    "data_sample": str(data)[:200] + "..." if len(str(data)) > 200 else str(data)
                }

                results.append(result)
                print(f"{'⚠️' if result['is_likely_mock'] else '✓'} Data analysis {url}: {'Likely mock' if result['is_likely_mock'] else 'Appears real'}")
                if result['is_likely_mock']:
                    print(f"   Mock indicators: {len(mock_indicators)}, Static indicators: {len(static_indicators)}")

        except Exception as e:
            result = {
                "url": url,
                "error": str(e)
            }
            results.append(result)
            print(f"✗ Data analysis {url}: ERROR - {e}")

    return results

def main():
    print("=" * 80)
    print("DASHBOARD UI FUNCTIONALITY TESTING")
    print("=" * 80)
    print(f"Testing dashboard at: {DASHBOARD_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Test 1: HTML Loading
    print("1. TESTING HTML LOADING")
    print("-" * 40)
    html_results = test_dashboard_html_loading()
    print()

    # Test 2: External Access and CORS
    print("2. TESTING EXTERNAL ACCESS AND CORS")
    print("-" * 40)
    cors_results = test_cors_and_external_access()
    print()

    # Test 3: Real vs Mock Data Analysis
    print("3. TESTING DATA QUALITY (REAL VS MOCK)")
    print("-" * 40)
    data_results = test_real_vs_mock_data()
    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    html_success = sum(1 for r in html_results if r.get('success', False))
    cors_success = sum(1 for r in cors_results if r.get('success', False))
    mock_data_count = sum(1 for r in data_results if r.get('is_likely_mock', False))

    print(f"HTML Loading: {html_success}/{len(html_results)} successful")
    print(f"External API Access: {cors_success}/{len(cors_results)} successful")
    print(f"Data Quality: {len(data_results) - mock_data_count}/{len(data_results)} appear to use real data")
    print(f"Mock Data Detected: {mock_data_count}/{len(data_results)} endpoints")

    if mock_data_count > 0:
        print("\n⚠️ CRITICAL FINDING: Mock data detected in production endpoints")
        print("This indicates the dashboard is not connected to real trading data sources")

    # Save detailed results
    full_report = {
        "test_timestamp": datetime.now().isoformat(),
        "dashboard_url": DASHBOARD_URL,
        "html_loading_tests": html_results,
        "cors_tests": cors_results,
        "data_quality_tests": data_results,
        "summary": {
            "html_success_rate": f"{html_success}/{len(html_results)}",
            "cors_success_rate": f"{cors_success}/{len(cors_results)}",
            "real_data_rate": f"{len(data_results) - mock_data_count}/{len(data_results)}",
            "mock_data_detected": mock_data_count > 0
        }
    }

    with open("ui_functionality_report.json", "w") as f:
        json.dump(full_report, f, indent=2)

    print(f"\nDetailed report saved to: ui_functionality_report.json")

    return full_report

if __name__ == "__main__":
    main()