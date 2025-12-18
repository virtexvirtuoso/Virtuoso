#!/usr/bin/env python3
"""
Investigate why widgets #4 (NERVE) and #6 (Market Intelligence Hub) are stuck updating
"""

from playwright.sync_api import sync_playwright
import time
import json

def investigate():
    console_logs = []

    def handle_console(msg):
        console_logs.append({
            'type': msg.type,
            'text': msg.text,
            'location': msg.location
        })
        # Only print errors and warnings related to widgets 4 and 6
        if msg.type in ['error', 'warning']:
            text = msg.text.lower()
            if 'widget 4' in text or 'widget 6' in text or 'nerve' in text or 'intelligence' in text:
                print(f"[{msg.type.upper()}] {msg.text}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.on('console', handle_console)

        print("🔍 Investigating Widgets #4 and #6...")
        page.goto('os.getenv("VPS_BASE_URL", "http://localhost:8002")/friday-night-fights', wait_until='domcontentloaded')

        print("⏳ Waiting for initial load...")
        time.sleep(5)

        # Check widget configurations
        print("\n📋 WIDGET CONFIGURATIONS:")
        print("="*80)

        widget_4_config = page.evaluate("""
            widgets.find(w => w.id === 4)
        """)

        widget_6_config = page.evaluate("""
            widgets.find(w => w.id === 6)
        """)

        print(f"\n🎯 Widget #4 (NERVE):")
        print(f"   Name: {widget_4_config['name']}")
        print(f"   APIs: {widget_4_config['apis']}")
        print(f"   Update Interval: {widget_4_config['updateInterval']}ms")
        print(f"   Render Function: {widget_4_config.get('render', 'N/A')}")

        print(f"\n🎯 Widget #6 (Market Intelligence Hub):")
        print(f"   Name: {widget_6_config['name']}")
        print(f"   APIs: {widget_6_config['apis']}")
        print(f"   Update Interval: {widget_6_config['updateInterval']}ms")
        print(f"   Render Function: {widget_6_config.get('render', 'N/A')}")

        # Test their APIs directly
        print("\n\n🌐 TESTING API ENDPOINTS:")
        print("="*80)

        for widget_id, apis in [(4, widget_4_config['apis']), (6, widget_6_config['apis'])]:
            print(f"\nWidget #{widget_id}:")
            for api in apis:
                print(f"   Testing: {api}")
                try:
                    response = page.evaluate(f"""
                        fetch('os.getenv("VPS_BASE_URL", "http://localhost:8002"){api}')
                            .then(r => r.json())
                            .then(data => JSON.stringify(data).substring(0, 200))
                            .catch(err => 'ERROR: ' + err.message)
                    """)
                    print(f"   ✅ Response: {response}")
                except Exception as e:
                    print(f"   ❌ Error: {e}")

        # Check DOM elements for widgets 4 and 6
        print("\n\n🔍 DOM ELEMENT CHECK:")
        print("="*80)

        for widget_id in [4, 6]:
            print(f"\nWidget #{widget_id}:")

            # Check if elements exist
            status_dot = page.locator(f'#status-{widget_id}').count()
            status_text = page.locator(f'#status-text-{widget_id}').count()
            content = page.locator(f'#content-{widget_id}').count()
            update = page.locator(f'#update-{widget_id}').count()

            print(f"   status-{widget_id}: {'✅' if status_dot > 0 else '❌'}")
            print(f"   status-text-{widget_id}: {'✅' if status_text > 0 else '❌'}")
            print(f"   content-{widget_id}: {'✅' if content > 0 else '❌'}")
            print(f"   update-{widget_id}: {'✅' if update > 0 else '❌'}")

            if status_text > 0:
                status_val = page.locator(f'#status-text-{widget_id}').text_content()
                print(f"   Current Status: {status_val}")

            if content > 0:
                content_html = page.locator(f'#content-{widget_id}').inner_html()
                print(f"   Content Length: {len(content_html)} chars")
                print(f"   Has Loading State: {'loading' in content_html.lower()}")

        # Monitor updates for 15 seconds
        print("\n\n⏱️  MONITORING UPDATES (15 seconds):")
        print("="*80)

        for i in range(3):
            time.sleep(5)
            print(f"\n[{(i+1)*5}s]")

            for widget_id in [4, 6]:
                try:
                    status = page.locator(f'#status-text-{widget_id}').text_content()
                    update_time = page.locator(f'#update-{widget_id}').text_content()
                    print(f"   Widget #{widget_id}: {status} (Last: {update_time})")
                except Exception as e:
                    print(f"   Widget #{widget_id}: Error reading status - {e}")

        # Check render function existence
        print("\n\n🎨 RENDER FUNCTION CHECK:")
        print("="*80)

        render_4_exists = page.evaluate("typeof renderNERVE === 'function'")
        render_6_exists = page.evaluate("typeof renderIntelligenceHub === 'function'")

        print(f"renderNERVE exists: {render_4_exists}")
        print(f"renderIntelligenceHub exists: {render_6_exists}")

        if not render_4_exists:
            print("❌ Widget #4 render function is MISSING!")
        if not render_6_exists:
            print("❌ Widget #6 render function is MISSING!")

        # Filter console logs for errors
        error_logs = [log for log in console_logs if log['type'] == 'error']
        widget_errors = [log for log in error_logs if 'widget 4' in log['text'].lower() or 'widget 6' in log['text'].lower()]

        print(f"\n\n📋 WIDGET-SPECIFIC ERRORS:")
        print("="*80)
        print(f"Total errors: {len(widget_errors)}")

        for log in widget_errors[:10]:
            print(f"\n{log['text']}")

        # Take screenshot
        page.screenshot(path='/tmp/widgets_4_6_investigation.png', full_page=True)
        print("\n📸 Screenshot saved to /tmp/widgets_4_6_investigation.png")

        # Keep browser open
        print("\n⏳ Keeping browser open for 5 seconds...")
        time.sleep(5)

        browser.close()

        print("\n" + "="*80)
        print("INVESTIGATION COMPLETE")
        print("="*80)

if __name__ == '__main__':
    investigate()
