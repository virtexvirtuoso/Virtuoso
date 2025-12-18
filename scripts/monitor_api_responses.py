#!/usr/bin/env python3
"""
Monitor API responses over time to identify when data reverts to defaults.
Captures actual API responses every 30 seconds to match the frontend refresh interval.
"""

import requests
import json
import time
from datetime import datetime
from collections import defaultdict

def check_api_response(endpoint, label):
    """Fetch and analyze an API endpoint response"""
    try:
        response = requests.get(endpoint, timeout=10)
        data = response.json()

        # Check for empty/missing critical fields
        issues = []

        if endpoint.endswith('mobile-data'):
            # Check market overview fields
            if not data.get('market_regime') and not data.get('regime'):
                issues.append("Missing market_regime/regime")

            # Check for empty gainers/losers
            gainers = data.get('top_gainers') or data.get('gainers') or []
            losers = data.get('top_losers') or data.get('losers') or []

            if not gainers:
                issues.append("Empty top_gainers")
            if not losers:
                issues.append("Empty top_losers")

            # Check market overview nested data
            mo = data.get('market_overview', {})
            if isinstance(mo, dict):
                if mo.get('total_market_cap') == '$0':
                    issues.append("Market cap is $0")

        elif endpoint.endswith('perpetuals-pulse'):
            # Check perps pulse critical fields
            if data.get('funding_rate') is None:
                issues.append("Missing funding_rate")
            if not data.get('funding_sentiment'):
                issues.append("Missing funding_sentiment")
            if data.get('long_pct') is None or data.get('short_pct') is None:
                issues.append("Missing long/short percentages")
            if not data.get('total_open_interest'):
                issues.append("Missing open_interest")

        return {
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint,
            "label": label,
            "status": response.status_code,
            "ok": response.ok,
            "has_issues": len(issues) > 0,
            "issues": issues,
            "response_size": len(json.dumps(data)),
            "sample_data": {
                k: v for k, v in list(data.items())[:5]  # First 5 keys as sample
            }
        }
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint,
            "label": label,
            "error": str(e),
            "has_issues": True,
            "issues": [f"Request failed: {str(e)}"]
        }

def monitor_apis(duration_minutes=5, interval_seconds=30):
    """Monitor API endpoints for the specified duration"""

    base_url = "os.getenv("VPS_BASE_URL", "http://localhost:8002")"
    endpoints = {
        f"{base_url}/api/dashboard/mobile-data": "Mobile Data (Market Overview + Top Movers)",
        f"{base_url}/api/dashboard/perpetuals-pulse": "Perpetuals Pulse"
    }

    checks = []
    issue_summary = defaultdict(int)

    print("="*80)
    print(f"MONITORING API ENDPOINTS")
    print(f"Duration: {duration_minutes} minutes | Interval: {interval_seconds} seconds")
    print("="*80)

    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    check_num = 0

    while time.time() < end_time:
        check_num += 1
        print(f"\n[Check #{check_num}] {datetime.now().strftime('%H:%M:%S')}")
        print("-" * 80)

        for endpoint, label in endpoints.items():
            result = check_api_response(endpoint, label)
            checks.append(result)

            if result.get('has_issues'):
                print(f"⚠️  {label}")
                for issue in result.get('issues', []):
                    print(f"   - {issue}")
                    issue_summary[issue] += 1
            else:
                print(f"✅ {label} - OK")

        # Wait for next check (unless it's the last iteration)
        if time.time() < end_time:
            print(f"\nWaiting {interval_seconds}s for next check...")
            time.sleep(interval_seconds)

    # Generate summary report
    print("\n" + "="*80)
    print("MONITORING SUMMARY")
    print("="*80)

    total_checks = len(checks)
    issues_found = len([c for c in checks if c.get('has_issues')])

    print(f"\nTotal checks: {total_checks}")
    print(f"Checks with issues: {issues_found} ({issues_found/total_checks*100:.1f}%)")

    if issue_summary:
        print(f"\nIssue Breakdown:")
        for issue, count in sorted(issue_summary.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {issue}: {count} occurrences")

    # Save detailed log
    log_file = f"/tmp/api_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w') as f:
        json.dump({
            "duration_minutes": duration_minutes,
            "interval_seconds": interval_seconds,
            "total_checks": total_checks,
            "issues_found": issues_found,
            "issue_summary": dict(issue_summary),
            "checks": checks
        }, f, indent=2)

    print(f"\nDetailed log saved to: {log_file}")
    print("="*80)

if __name__ == "__main__":
    # Monitor for 3 minutes with 30-second intervals (to match frontend refresh)
    monitor_apis(duration_minutes=3, interval_seconds=30)
