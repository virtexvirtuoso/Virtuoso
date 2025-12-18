#!/usr/bin/env python3
"""
Inspect aggr.trade layout to fix toolbar overlap issue.
"""

from playwright.sync_api import sync_playwright

def inspect_aggr_layout():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print("Navigating to aggr.trade page...")
        page.goto('os.getenv("VPS_BASE_URL", "http://localhost:8002")/aggr')

        # Wait for page to load
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)  # Extra time for Vue app to initialize

        # Take initial screenshot
        page.screenshot(path='/tmp/aggr_before_fix.png', full_page=False)
        print("Screenshot saved: /tmp/aggr_before_fix.png")

        # Inspect the main app container
        print("\n=== Inspecting Main App Structure ===")

        # Check if there's an #app element
        app_element = page.locator('#app').first
        if app_element.count() > 0:
            # Get computed styles
            app_styles = page.evaluate("""
                () => {
                    const app = document.querySelector('#app');
                    if (!app) return null;
                    const computed = window.getComputedStyle(app);
                    return {
                        position: computed.position,
                        top: computed.top,
                        paddingTop: computed.paddingTop,
                        marginTop: computed.marginTop
                    };
                }
            """)
            print(f"#app styles: {app_styles}")

        # Check for any fixed/absolute positioned elements at the top
        top_elements = page.evaluate("""
            () => {
                const elements = Array.from(document.querySelectorAll('*'));
                const topFixed = elements.filter(el => {
                    const computed = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return (computed.position === 'fixed' || computed.position === 'absolute')
                           && rect.top < 100;
                }).map(el => ({
                    tag: el.tagName,
                    classes: el.className,
                    position: window.getComputedStyle(el).position,
                    top: window.getComputedStyle(el).top,
                    zIndex: window.getComputedStyle(el).zIndex,
                    rect: el.getBoundingClientRect()
                }));
                return topFixed;
            }
        """)

        print("\n=== Fixed/Absolute Elements at Top ===")
        for i, el in enumerate(top_elements):
            print(f"\nElement {i + 1}:")
            print(f"  Tag: {el['tag']}")
            print(f"  Classes: {el['classes']}")
            print(f"  Position: {el['position']}")
            print(f"  Top: {el['top']}")
            print(f"  Z-index: {el['zIndex']}")
            print(f"  Rect: top={el['rect']['y']:.1f}, height={el['rect']['height']:.1f}")

        # Check toolbar height
        toolbar_height = page.evaluate("""
            () => {
                const toolbar = document.querySelector('.virtuoso-aggr-toolbar');
                if (!toolbar) return null;
                return toolbar.getBoundingClientRect().height;
            }
        """)
        print(f"\n=== Virtuoso Toolbar ===")
        print(f"Toolbar height: {toolbar_height}px")

        # Check body padding
        body_padding = page.evaluate("""
            () => {
                const computed = window.getComputedStyle(document.body);
                return computed.paddingTop;
            }
        """)
        print(f"Body paddingTop: {body_padding}")

        input("\nPress Enter to close browser...")
        browser.close()

if __name__ == '__main__':
    inspect_aggr_layout()
