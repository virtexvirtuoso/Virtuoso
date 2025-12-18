#!/usr/bin/env python3
"""Capture v2 dashboard with vue-grid-layout."""

from playwright.sync_api import sync_playwright
import subprocess
import time

def capture():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})

        print("🌐 Loading Desktop Dashboard V2 (vue-grid-layout)...")
        page.goto("os.getenv("VPS_BASE_URL", "http://localhost:8002")/desktop-v2")
        page.wait_for_load_state('networkidle')
        time.sleep(5)  # Let Vue mount and data load

        # Full viewport screenshot
        screenshot_path = '/tmp/desktop_v2.png'
        page.screenshot(path=screenshot_path, full_page=False)
        print(f"📸 Screenshot saved: {screenshot_path}")

        browser.close()

    # Open on local machine
    print("🖥️  Opening screenshot...")
    subprocess.run(['open', screenshot_path])
    print("✅ Done!")

if __name__ == "__main__":
    capture()
