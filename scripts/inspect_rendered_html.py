#!/usr/bin/env python3
"""
Inspect actual rendered HTML structure of Beta Rankings.
"""
from playwright.sync_api import sync_playwright

def inspect_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('os.getenv("VPS_BASE_URL", "http://localhost:8002")/mobile')
        page.wait_for_load_state('networkidle')

        beta_tab = page.locator('button.nav-item').filter(has_text='BETA')
        beta_tab.click()
        page.wait_for_timeout(2000)

        # Get first ranking item HTML
        first_item = page.locator('#mtfRankingsList > div').first
        html_content = first_item.inner_html()

        print("=== RENDERED HTML STRUCTURE ===\n")
        print(html_content[:2000])  # First 2000 chars

        browser.close()

if __name__ == '__main__':
    inspect_html()
