#!/usr/bin/env python3
"""
Investigate mobile dashboard issues at os.getenv("VPS_BASE_URL", "http://localhost:8002")/mobile
Captures screenshots, console logs, and network errors
"""
from playwright.sync_api import sync_playwright
import json
from datetime import datetime

def investigate_mobile_dashboard():
    print("[INVESTIGATION] Starting mobile dashboard analysis...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 375, 'height': 812},  # iPhone X size
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'
        )
        page = context.new_page()

        # Capture console messages
        console_messages = []
        def handle_console(msg):
            console_messages.append({
                'type': msg.type,
                'text': msg.text,
                'location': msg.location
            })
            if msg.type in ['error', 'warning']:
                print(f"[CONSOLE {msg.type.upper()}] {msg.text}")

        page.on('console', handle_console)

        # Capture network failures
        network_failures = []
        def handle_response(response):
            if response.status >= 400:
                network_failures.append({
                    'url': response.url,
                    'status': response.status,
                    'statusText': response.status_text
                })
                print(f"[NETWORK ERROR] {response.status} - {response.url}")

        page.on('response', handle_response)

        # Capture page errors
        page_errors = []
        def handle_page_error(error):
            page_errors.append(str(error))
            print(f"[PAGE ERROR] {error}")

        page.on('pageerror', handle_page_error)

        try:
            print("\n[NAVIGATION] Loading os.getenv("VPS_BASE_URL", "http://localhost:8002")/mobile...")
            page.goto('os.getenv("VPS_BASE_URL", "http://localhost:8002")/mobile', timeout=15000)

            print("[WAIT] Waiting for network to be idle...")
            page.wait_for_load_state('networkidle', timeout=10000)

            print("[WAIT] Waiting additional 3s for dynamic content...")
            page.wait_for_timeout(3000)

            # Take screenshots
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot_path = f'/tmp/mobile_dashboard_{timestamp}.png'
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"\n[SCREENSHOT] Saved to {screenshot_path}")

            # Check for specific elements
            print("\n[DOM INSPECTION] Checking for key elements...")

            elements_to_check = {
                'header': 'header',
                'signal_cards': '[class*="signal"]',
                'perps_card': '#perpsPulseCard',
                'beta_chart': '#betaChartCard',
                'alerts_section': '#alertsSection',
                'error_message': '.error, [class*="error"]'
            }

            found_elements = {}
            for name, selector in elements_to_check.items():
                try:
                    count = page.locator(selector).count()
                    found_elements[name] = count
                    print(f"  ✓ {name}: {count} element(s)")
                except Exception as e:
                    found_elements[name] = 0
                    print(f"  ✗ {name}: Not found")

            # Check page title
            title = page.title()
            print(f"\n[PAGE TITLE] {title}")

            # Get visible text to check for error messages
            body_text = page.locator('body').inner_text()
            if 'error' in body_text.lower() or 'failed' in body_text.lower():
                print("\n[WARNING] Found error text in page body!")
                # Find specific error elements
                error_divs = page.locator('text=/error|failed/i').all()
                for i, div in enumerate(error_divs[:5]):  # Limit to first 5
                    print(f"  Error {i+1}: {div.inner_text()[:100]}")

            # Save report
            report = {
                'timestamp': timestamp,
                'url': 'os.getenv("VPS_BASE_URL", "http://localhost:8002")/mobile',
                'title': title,
                'console_messages': console_messages,
                'network_failures': network_failures,
                'page_errors': page_errors,
                'found_elements': found_elements,
                'screenshot_path': screenshot_path
            }

            report_path = f'/tmp/mobile_investigation_{timestamp}.json'
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)

            print(f"\n[REPORT] Saved to {report_path}")

            # Summary
            print("\n" + "="*60)
            print("INVESTIGATION SUMMARY")
            print("="*60)
            print(f"Console Errors: {len([m for m in console_messages if m['type'] == 'error'])}")
            print(f"Console Warnings: {len([m for m in console_messages if m['type'] == 'warning'])}")
            print(f"Network Failures: {len(network_failures)}")
            print(f"Page Errors: {len(page_errors)}")
            print(f"Screenshot: {screenshot_path}")
            print("="*60)

        except Exception as e:
            print(f"\n[FATAL ERROR] {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()
            print("\n[INVESTIGATION] Complete!")

if __name__ == '__main__':
    investigate_mobile_dashboard()
