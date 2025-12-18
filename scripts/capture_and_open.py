#!/usr/bin/env python3
"""Capture screenshot with Chromium and open locally."""

from playwright.sync_api import sync_playwright
import subprocess
import time

def capture():
    with sync_playwright() as p:
        # Use Chromium
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1400, 'height': 1000})

        print("🌐 Loading Momentum Waves with Chromium...")
        page.goto("os.getenv("VPS_BASE_URL", "http://localhost:8002")/confluence")
        page.wait_for_load_state('networkidle')
        time.sleep(3)  # Let animations settle

        # Capture screenshot
        screenshot_path = '/tmp/momentum_waves_live.png'
        page.screenshot(path=screenshot_path, full_page=False)
        print(f"📸 Screenshot saved: {screenshot_path}")

        browser.close()

    # Open on local machine
    print("🖥️  Opening screenshot...")
    subprocess.run(['open', screenshot_path])
    print("✅ Done!")

if __name__ == "__main__":
    capture()
