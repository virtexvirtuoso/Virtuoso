#!/usr/bin/env python3
"""
Simple API Audit Script for Virtuoso Trading System
Tests all API endpoints using basic requests library.
"""

import requests
import json
import time
from datetime import datetime
import sys

# VPS Configuration
VPS_BASE_URL = "http://45.77.40.77:8003"
TIMEOUT = 30

def test_endpoint(method, path, description, expected_fields=None):
    """Test a single API endpoint."""
    url = f"{VPS_BASE_URL}{path}"
    start_time = time.time()
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=TIMEOUT)
        elif method.upper() == "POST":
            response = requests.post(url, timeout=TIMEOUT)
        else:
            return {"status": "error", "error": f"Unsupported method: {method}"}
        
        response_time = time.time() - start_time
        
        # Try to parse JSON
        try:
            response_data = response.json()
        except:
            # If not JSON, treat as HTML/text
            response_data = {"content_type": response.headers.get("content-type", "unknown"),
                           "content_length": len(response.text),
                           "is_html": "html" in response.headers.get("content-type", "")}
        
        if response.status_code == 200:
            # Check if it has meaningful data
            has_data = check_has_data(response_data)
            
            return {
                "status": "success",
                "status_code": response.status_code,
                "response_time": round(response_time, 3),
                "has_data": has_data,
                "data_type": type(response_data).__name__,
                "data_size": len(str(response_data)),
                "sample_data": get_sample_data(response_data)
            }
        else:
            return {
                "status": "error",
                "status_code": response.status_code,
                "response_time": round(response_time, 3),
                "error": f"HTTP {response.status_code}"
            }
            
    except requests.exceptions.Timeout:
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

def check_has_data(data):
    """Check if response contains meaningful data."""
    if isinstance(data, dict):
        # HTML/UI endpoints
        if "is_html" in data and data["is_html"]:
            return data["content_length"] > 1000  # Reasonable HTML size
        
        # API endpoints - check for data indicators
        data_indicators = ['symbols', 'signals', 'alerts', 'data', 'results', 'opportunities']
        for indicator in data_indicators:
            if indicator in data and data[indicator]:
                if isinstance(data[indicator], list) and len(data[indicator]) > 0:
                    return True
                elif isinstance(data[indicator], dict) and len(data[indicator]) > 0:
                    return True
        
        # Check if it has any meaningful values
        return any(bool(v) for v in data.values() if v is not None and v != 0)
    elif isinstance(data, list):
        return len(data) > 0
    else:
        return bool(data)

def get_sample_data(data):
    """Get sample of response data."""
    if isinstance(data, dict):
        if "is_html" in data:
            return f"HTML page ({data['content_length']} bytes)"
        return {k: v for i, (k, v) in enumerate(data.items()) if i < 3}
    elif isinstance(data, list):
        return data[0] if data else []
    else:
        return str(data)[:100] + "..." if len(str(data)) > 100 else data

def main():
    """Run the API audit."""
    print(f"🔍 Starting API Audit for {VPS_BASE_URL}")
    print("=" * 80)
    
    # Define endpoints to test
    endpoints = [
        # Basic Health Checks
        ("GET", "/", "Root endpoint"),
        ("GET", "/health", "Health check"),
        ("GET", "/version", "Version info"),
        
        # Dashboard UI Routes
        ("GET", "/dashboard", "Dashboard selector page"),
        ("GET", "/dashboard/mobile", "Mobile dashboard"),
        ("GET", "/dashboard/desktop", "Desktop dashboard"),
        ("GET", "/dashboard/v1", "Classic dashboard"),
        ("GET", "/dashboard/v10", "Signal matrix dashboard"),
        
        # Core API Endpoints
        ("GET", "/api/health", "API health check"),
        ("GET", "/api/dashboard/overview", "Dashboard overview"),
        ("GET", "/api/dashboard/symbols", "Dashboard symbols"),
        ("GET", "/api/dashboard/signals", "Dashboard signals"),
        ("GET", "/api/dashboard/alerts", "Dashboard alerts"),
        
        # Market Data
        ("GET", "/api/top-symbols", "Top symbols"),
        ("GET", "/api/market-report", "Market report"),
        
        # Signals
        ("GET", "/api/signals/latest", "Latest signals"),
        
        # Bitcoin Beta
        ("GET", "/api/bitcoin-beta/status", "Bitcoin Beta status"),
        ("GET", "/api/bitcoin-beta/analysis", "Bitcoin Beta analysis"),
        ("GET", "/api/bitcoin-beta/health", "Bitcoin Beta health"),
        
        # Alpha Opportunities
        ("GET", "/api/alpha/opportunities", "Alpha opportunities"),
        
        # Whale Activity
        ("GET", "/api/whale-activity/alerts", "Whale alerts"),
        ("GET", "/api/whale-activity/activity", "Whale activity"),
        
        # Liquidation
        ("GET", "/api/liquidation/alerts", "Liquidation alerts"),
        
        # Sentiment
        ("GET", "/api/sentiment/market", "Market sentiment"),
        ("GET", "/api/sentiment/symbols", "Symbol sentiments"),
        
        # Admin (will likely require auth)
        ("GET", "/admin/login", "Admin login page"),
        ("GET", "/admin/dashboard", "Admin dashboard"),
    ]
    
    # Run tests
    results = {}
    total_tests = len(endpoints)
    passed = 0
    failed = 0
    timeouts = 0
    
    for i, (method, path, description) in enumerate(endpoints, 1):
        print(f"\n[{i}/{total_tests}] Testing: {method} {path}")
        print(f"Description: {description}")
        
        result = test_endpoint(method, path, description)
        results[path] = result
        
        if result["status"] == "success":
            print(f"✅ SUCCESS - {result['response_time']}s - Data: {result['has_data']} - Size: {result['data_size']} bytes")
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
    
    # Categorize results
    working_with_data = []
    working_no_data = []
    failed_endpoints = []
    timeout_endpoints = []
    
    for path, result in results.items():
        if result["status"] == "success":
            if result["has_data"]:
                working_with_data.append((path, result))
            else:
                working_no_data.append((path, result))
        elif result["status"] == "timeout":
            timeout_endpoints.append((path, result))
        else:
            failed_endpoints.append((path, result))
    
    # Detailed breakdown
    print("\n" + "=" * 80)
    print("📋 DETAILED BREAKDOWN")
    print("=" * 80)
    
    if working_with_data:
        print(f"\n🟢 Working with Data ({len(working_with_data)} endpoints):")
        for path, result in working_with_data:
            print(f"  ✅ {path} - {result['response_time']}s")
            sample = result.get('sample_data', {})
            if isinstance(sample, dict) and len(sample) > 0:
                print(f"      Sample: {list(sample.keys())}")
    
    if working_no_data:
        print(f"\n🟡 Working but No Data ({len(working_no_data)} endpoints):")
        for path, result in working_no_data:
            print(f"  ⚠️  {path} - {result['response_time']}s")
    
    if failed_endpoints:
        print(f"\n🔴 Failed ({len(failed_endpoints)} endpoints):")
        for path, result in failed_endpoints:
            print(f"  ❌ {path} - {result.get('error', 'Unknown error')}")
    
    if timeout_endpoints:
        print(f"\n🕐 Timeouts ({len(timeout_endpoints)} endpoints):")
        for path, result in timeout_endpoints:
            print(f"  ⏰ {path} - >{TIMEOUT}s")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("💡 RECOMMENDATIONS")
    print("=" * 80)
    
    if len(working_with_data) > 10:
        print("🎉 Good! Most endpoints are working and returning data")
    
    if len(working_no_data) > 5:
        print("⚠️  Several endpoints working but not returning data:")
        print("   - Check if monitoring services are running")
        print("   - Verify database connections")
        print("   - Check exchange API connections")
    
    if len(failed_endpoints) > 3:
        print("🚨 Multiple endpoint failures detected:")
        print("   - Check server logs for errors")
        print("   - Verify all services are running")
        print("   - Check dependencies and imports")
    
    if len(timeout_endpoints) > 0:
        print("⏰ Timeout issues found:")
        print("   - Some endpoints are too slow")
        print("   - Consider optimizing database queries")
        print("   - Check external API response times")
    
    print(f"\n📈 Overall Health Score: {(len(working_with_data)/total_tests)*100:.0f}%")
    
    if (len(working_with_data)/total_tests) > 0.8:
        print("🟢 System Status: HEALTHY")
    elif (len(working_with_data)/total_tests) > 0.6:
        print("🟡 System Status: NEEDS ATTENTION")
    else:
        print("🔴 System Status: CRITICAL - IMMEDIATE ACTION REQUIRED")

if __name__ == "__main__":
    print("🚀 Virtuoso API Endpoint Audit Tool")
    print(f"Target: {VPS_BASE_URL}")
    print(f"Timeout: {TIMEOUT}s")
    print()
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Audit interrupted by user")
    except Exception as e:
        print(f"\n❌ Audit failed: {e}")
        sys.exit(1)