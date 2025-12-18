#!/usr/bin/env python3
"""
Extract the current dashboard layout configuration from the live dashboard.
This reads the Vue Grid Layout state and outputs the configuration.
"""

from playwright.sync_api import sync_playwright
import json

def extract_layout():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})

        print("Navigating to dashboard...")
        page.goto('os.getenv("VPS_BASE_URL", "http://localhost:8002")/desktop-v2')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(3000)

        print("\nExtracting layout configuration from Vue Grid Layout...")

        # Extract the layout array from Vue's data
        layout_config = page.evaluate("""
            () => {
                // Access Vue instance from the #app element
                const app = document.querySelector('#app');
                if (!app || !app.__vue__) {
                    return { error: 'Vue instance not found' };
                }

                // Get the layout from Vue data
                const vueData = app.__vue__.$data || app.__vue__;
                if (vueData && vueData.layout) {
                    return {
                        success: true,
                        layout: vueData.layout
                    };
                }

                return { error: 'Layout data not found in Vue instance' };
            }
        """)

        if layout_config.get('error'):
            print(f"❌ Error: {layout_config['error']}")
            print("\nTrying alternative method...")

            # Alternative: Read from localStorage if Vue Grid Layout persists it
            layout_config = page.evaluate("""
                () => {
                    const stored = localStorage.getItem('dashboard-layout');
                    if (stored) {
                        return {
                            success: true,
                            layout: JSON.parse(stored)
                        };
                    }
                    return { error: 'No layout found in localStorage' };
                }
            """)

        if layout_config.get('success'):
            layout = layout_config['layout']
            print("✅ Layout extracted successfully!\n")
            print("=" * 60)
            print("CURRENT LAYOUT CONFIGURATION:")
            print("=" * 60)
            print()
            print("layout: [")

            # Sort by y position then x position for readability
            sorted_layout = sorted(layout, key=lambda item: (item['y'], item['x']))

            for item in sorted_layout:
                print(f"    {{ i: '{item['i']}', x: {item['x']}, y: {item['y']}, w: {item['w']}, h: {item['h']} }},")

            print("],")
            print()
            print("=" * 60)

            # Create a visual representation
            print("\nVISUAL LAYOUT MAP:")
            print("=" * 60)

            # Create a grid to visualize
            max_y = max(item['y'] + item['h'] for item in layout)
            grid = [[' ' * 10 for _ in range(12)] for _ in range(max_y)]

            widget_names = {
                'marketOverview': 'Market',
                'betaChart': 'Beta Chart',
                'confluence': 'Confluence',
                'perpsPulse': 'PerpsPulse',
                'alerts': 'Alerts',
                'alertedSignals': 'AlertSignal',
                'topMovers': 'TopMovers'
            }

            for item in layout:
                widget_name = widget_names.get(item['i'], item['i'])[:10].ljust(10)
                for dy in range(item['h']):
                    for dx in range(item['w']):
                        y_pos = item['y'] + dy
                        x_pos = item['x'] + dx
                        if y_pos < max_y and x_pos < 12:
                            grid[y_pos][x_pos] = widget_name

            for row_idx, row in enumerate(grid):
                print(f"y={row_idx:2d} | {''.join(row)}")

            print()
            print("=" * 60)

            # Save to file
            output_file = '/tmp/dashboard_layout_config.json'
            with open(output_file, 'w') as f:
                json.dump(layout, f, indent=2)

            print(f"\n✅ Layout configuration saved to: {output_file}")
            print("\nCopy the 'layout: [...]' section above and replace it in:")
            print("  src/dashboard/templates/dashboard_desktop_v2.html")
            print("  (around line 3667)")

        else:
            print(f"❌ Error: {layout_config.get('error', 'Unknown error')}")

        input("\nPress Enter to close browser...")
        browser.close()

if __name__ == '__main__':
    extract_layout()
