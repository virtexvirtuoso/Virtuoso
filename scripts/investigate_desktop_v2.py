#!/usr/bin/env python3
"""
Investigation script for desktop-v2 loading issues.
Captures console logs, network requests, screenshots, and DOM state.
"""

from playwright.sync_api import sync_playwright
import json
from datetime import datetime

def investigate_loading_issues():
    url = "os.getenv("VPS_BASE_URL", "http://localhost:8002")/desktop-v2"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        # Capture console messages
        console_logs = []
        page.on("console", lambda msg: console_logs.append({
            "type": msg.type,
            "text": msg.text,
            "location": msg.location
        }))

        # Capture network requests and responses
        network_logs = []
        failed_requests = []

        def handle_request(request):
            network_logs.append({
                "method": request.method,
                "url": request.url,
                "type": "request"
            })

        def handle_response(response):
            status = response.status
            url = response.url
            network_logs.append({
                "url": url,
                "status": status,
                "type": "response",
                "ok": response.ok
            })
            if not response.ok:
                failed_requests.append({
                    "url": url,
                    "status": status,
                    "status_text": response.status_text
                })

        page.on("request", handle_request)
        page.on("response", handle_response)

        # Capture page errors
        page_errors = []
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        print(f"[1/6] Navigating to {url}...")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"ERROR: Failed to navigate: {e}")
            browser.close()
            return

        print("[2/6] Waiting for network idle...")
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except Exception as e:
            print(f"WARNING: Network didn't become idle: {e}")

        # Wait a bit more for dynamic content
        print("[3/6] Waiting for dynamic content to load...")
        page.wait_for_timeout(3000)

        # Take screenshot
        print("[4/6] Capturing screenshot...")
        screenshot_path = f"/tmp/desktop_v2_screenshot_{timestamp}.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to: {screenshot_path}")

        # Inspect DOM for loading indicators or errors
        print("[5/6] Analyzing DOM state...")

        # Check for common loading indicators
        loading_elements = page.locator('[class*="loading"], [class*="spinner"], [class*="skeleton"]').count()
        error_elements = page.locator('[class*="error"], [class*="alert-danger"]').count()

        # Check for specific dashboard elements
        dashboard_elements = {
            "widgets": page.locator('[class*="widget"], [class*="card"]').count(),
            "charts": page.locator('canvas, svg[class*="chart"]').count(),
            "tables": page.locator('table').count(),
            "empty_states": page.locator('[class*="empty"], [class*="no-data"]').count()
        }

        # Get page title and any error messages
        page_title = page.title()

        # Check for any visible error messages
        error_messages = []
        try:
            error_texts = page.locator('[class*="error"], [class*="alert"]').all_text_contents()
            error_messages = [text for text in error_texts if text.strip()]
        except:
            pass

        # Get the HTML content
        html_content = page.content()

        print("[6/6] Compiling report...")

        # Generate report
        report = {
            "timestamp": timestamp,
            "url": url,
            "page_title": page_title,
            "page_errors": page_errors,
            "console_logs": console_logs,
            "failed_requests": failed_requests,
            "network_summary": {
                "total_requests": len([log for log in network_logs if log["type"] == "request"]),
                "total_responses": len([log for log in network_logs if log["type"] == "response"]),
                "failed_count": len(failed_requests)
            },
            "dom_analysis": {
                "loading_indicators": loading_elements,
                "error_elements": error_elements,
                "dashboard_elements": dashboard_elements,
                "error_messages": error_messages
            }
        }

        # Save detailed report
        report_path = f"/tmp/desktop_v2_report_{timestamp}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        # Save HTML snapshot
        html_path = f"/tmp/desktop_v2_html_{timestamp}.html"
        with open(html_path, 'w') as f:
            f.write(html_content)

        browser.close()

        # Print summary
        print("\n" + "="*80)
        print("INVESTIGATION SUMMARY")
        print("="*80)
        print(f"\nPage Title: {page_title}")
        print(f"\n📊 DOM Analysis:")
        print(f"  - Loading indicators visible: {loading_elements}")
        print(f"  - Error elements visible: {error_elements}")
        print(f"  - Widgets/Cards found: {dashboard_elements['widgets']}")
        print(f"  - Charts found: {dashboard_elements['charts']}")
        print(f"  - Tables found: {dashboard_elements['tables']}")
        print(f"  - Empty state elements: {dashboard_elements['empty_states']}")

        print(f"\n🌐 Network Activity:")
        print(f"  - Total requests: {report['network_summary']['total_requests']}")
        print(f"  - Failed requests: {report['network_summary']['failed_count']}")

        if failed_requests:
            print(f"\n❌ Failed Requests:")
            for req in failed_requests[:10]:  # Show first 10
                print(f"  - [{req['status']}] {req['url']}")

        if page_errors:
            print(f"\n🚨 Page Errors:")
            for error in page_errors:
                print(f"  - {error}")

        console_errors = [log for log in console_logs if log['type'] == 'error']
        if console_errors:
            print(f"\n🐛 Console Errors ({len(console_errors)} total):")
            for log in console_errors[:10]:  # Show first 10
                print(f"  - {log['text']}")

        console_warnings = [log for log in console_logs if log['type'] == 'warning']
        if console_warnings:
            print(f"\n⚠️  Console Warnings ({len(console_warnings)} total):")
            for log in console_warnings[:5]:  # Show first 5
                print(f"  - {log['text']}")

        if error_messages:
            print(f"\n💬 Visible Error Messages:")
            for msg in error_messages:
                print(f"  - {msg}")

        print(f"\n📁 Files Generated:")
        print(f"  - Screenshot: {screenshot_path}")
        print(f"  - Full report: {report_path}")
        print(f"  - HTML snapshot: {html_path}")
        print("="*80)

        return report

if __name__ == "__main__":
    investigate_loading_issues()
