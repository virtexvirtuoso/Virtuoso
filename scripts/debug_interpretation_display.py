#!/usr/bin/env python3
"""Debug script to test interpretation display issue."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.formatting.formatter import PrettyTableFormatter
import logging

# Set up debug logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

# Test data matching what's created by the system
test_results = {
    'market_interpretations': [
        {
            'component': 'technical',
            'display_name': 'Technical',
            'interpretation': 'Technical indicators reflect market indecision with no clear directional bias. MACD shows neutral trend conditions (41.2). RSI in neutral territory (54.9). AO indicates bearish momentum building (44.1). CCI shows bullish momentum without being overbought (66.0).'
        },
        {
            'component': 'volume',
            'display_name': 'Volume',
            'interpretation': 'Volume patterns show typical market participation without clear directional bias, indicating neutral conditions or potential consolidation phase. VOLUME_PROFILE is particularly strong (70.4), reinforcing the volume analysis. Overall volume analysis suggests consolidation phase with balanced trading activity.'
        },
        {
            'component': 'orderbook',
            'display_name': 'Orderbook',
            'interpretation': 'Orderbook shows Balanced order book with moderate liquidity and normal spreads. suggesting equilibrium between buyers and sellers, providing average market depth, and with typical bid-ask differentials. Overall orderbook structure suggests consolidation or sideways movement.'
        },
        {
            'component': 'orderflow',
            'display_name': 'Orderflow',
            'interpretation': 'Neutral orderflow with slight selling bias. Strong negative cumulative volume delta showing dominant selling activity. Overall orderflow structure indicates balanced conditions with no clear directional edge.'
        },
        {
            'component': 'sentiment',
            'display_name': 'Sentiment',
            'interpretation': 'Moderately bullish market sentiment with high risk conditions and neutral funding rates. suggesting potential for sharp reversals, indicating balanced long/short positioning.'
        },
        {
            'component': 'price_structure',
            'display_name': 'Price Structure',
            'interpretation': 'Price structure is neutral, showing balanced forces without clear direction. Price oscillating near VWAP indicating equilibrium between buyers and sellers.'
        }
    ]
}

print("Testing interpretation display with 6 components...")
print(f"Input has {len(test_results['market_interpretations'])} interpretations")
print()

# Test the formatting
formatted = PrettyTableFormatter._format_interpretations_table(test_results, border_style="double")

print("Output:")
print(formatted)
print()

# Count how many component rows are in the output
output_lines = formatted.split('\n')
component_count = 0
for line in output_lines:
    if '║' in line and any(comp in line for comp in ['Technical', 'Volume', 'Orderbook', 'Orderflow', 'Sentiment', 'Price Structure']):
        component_count += 1
        print(f"Found component line: {line[:50]}...")

print(f"\nComponents found in output: {component_count}/6")

# Also test the _format_enhanced_interpretations function directly
print("\n" + "="*80)
print("Testing _format_enhanced_interpretations directly...")
interpretations = PrettyTableFormatter._format_enhanced_interpretations(test_results)
print(f"Generated {len(interpretations)} interpretation lines")
for i, line in enumerate(interpretations[:10]):  # Show first 10 lines
    print(f"Line {i}: {repr(line)}")