#!/usr/bin/env python3
"""Capture desktop dashboard with Momentum Waves widget."""

from playwright.sync_api import sync_playwright
import subprocess
import time

def capture():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Wide viewport for desktop dashboard
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})

        print("🌐 Loading Desktop Dashboard...")
        page.goto("os.getenv("VPS_BASE_URL", "http://localhost:8002")/desktop")
        page.wait_for_load_state('networkidle')
        time.sleep(4)  # Let data load and animations start

        # Full viewport screenshot
        screenshot_path = '/tmp/desktop_momentum_waves.png'
        page.screenshot(path=screenshot_path, full_page=False)
        print(f"📸 Screenshot saved: {screenshot_path}")

        # Try to capture just the confluence widget
        widget = page.locator('#confluenceWidget').first
        if widget.count() > 0:
            widget.screenshot(path='/tmp/momentum_waves_widget.png')
            print("📸 Widget screenshot: /tmp/momentum_waves_widget.png")

        browser.close()

    # Open on local machine
    print("🖥️  Opening screenshots...")
    subprocess.run(['open', screenshot_path])
    print("✅ Done!")

if __name__ == "__main__":
    capture()
