#!/usr/bin/env python3
"""Inspect score circle styling in Momentum Waves dashboard."""

from playwright.sync_api import sync_playwright

def inspect():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})

        page.goto("os.getenv("VPS_BASE_URL", "http://localhost:8002")/confluence")
        page.wait_for_load_state('networkidle')

        # Get score circle details
        print("\n📐 SCORE CIRCLE INSPECTION")
        print("=" * 50)

        # Find score value elements
        score_values = page.locator('.score-value').all()
        print(f"\nFound {len(score_values)} .score-value elements")

        if score_values:
            # Get computed styles of first score value
            styles = page.evaluate('''() => {
                const el = document.querySelector('.score-value');
                if (!el) return null;
                const computed = window.getComputedStyle(el);
                return {
                    fontSize: computed.fontSize,
                    fontWeight: computed.fontWeight,
                    lineHeight: computed.lineHeight,
                    width: el.offsetWidth,
                    height: el.offsetHeight,
                    text: el.innerText
                };
            }''')

            if styles:
                print(f"\n.score-value styles:")
                print(f"   Font size: {styles['fontSize']}")
                print(f"   Font weight: {styles['fontWeight']}")
                print(f"   Line height: {styles['lineHeight']}")
                print(f"   Element size: {styles['width']}x{styles['height']}px")
                print(f"   Content: '{styles['text']}'")

        # Get score circle container
        circle_styles = page.evaluate('''() => {
            const el = document.querySelector('.score-circle');
            if (!el) return null;
            const computed = window.getComputedStyle(el);
            return {
                width: computed.width,
                height: computed.height
            };
        }''')

        if circle_styles:
            print(f"\n.score-circle container:")
            print(f"   Size: {circle_styles['width']} x {circle_styles['height']}")

        # Screenshot the first card's score area
        first_card = page.locator('.asset-card').first
        if first_card.count() > 0:
            # Get the score circle from first card
            score_area = first_card.locator('.score-circle, .momentum-score').first
            if score_area.count() > 0:
                score_area.screenshot(path='/tmp/score_circle_current.png')
                print("\n📸 Screenshot: /tmp/score_circle_current.png")

        # Get all CSS rules for score-value
        css_rules = page.evaluate('''() => {
            const rules = [];
            for (const sheet of document.styleSheets) {
                try {
                    for (const rule of sheet.cssRules) {
                        if (rule.selectorText && rule.selectorText.includes('score-value')) {
                            rules.push({
                                selector: rule.selectorText,
                                css: rule.cssText.substring(0, 200)
                            });
                        }
                    }
                } catch (e) {}
            }
            return rules;
        }''')

        print(f"\n📋 CSS Rules containing 'score-value':")
        for rule in css_rules[:5]:
            print(f"   {rule['selector']}")
            print(f"      {rule['css'][:100]}...")

        browser.close()
        print("\n✅ Inspection complete")

if __name__ == "__main__":
    inspect()
