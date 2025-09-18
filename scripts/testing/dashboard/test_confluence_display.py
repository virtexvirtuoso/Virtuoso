#!/usr/bin/env python3
"""Test the confluence analysis display formatting."""

import requests
import re
import sys

def test_confluence_display(symbol="BTCUSDT"):
    """Test the confluence analysis display."""
    
    # Fetch the analysis
    url = f"http://5.223.63.4:8003/api/dashboard/confluence-analysis/{symbol}"
    response = requests.get(url)
    data = response.json()
    
    if 'analysis' not in data:
        print(f"Error: No analysis found for {symbol}")
        return
    
    # Get the raw analysis
    raw_analysis = data['analysis']
    
    # Remove ANSI color codes (same as the JavaScript does)
    clean_analysis = re.sub(r'\x1b\[[0-9;]*m', '', raw_analysis)
    
    # Print a sample of the cleaned output
    print(f"=== Cleaned Analysis for {symbol} ===")
    print(clean_analysis[:2000])
    print("\n... (truncated)")
    
    # Check for key formatting elements
    print("\n=== Format Verification ===")
    print(f"✓ Box drawing characters present: {'╔' in clean_analysis}")
    print(f"✓ Table borders present: {'═' in clean_analysis and '║' in clean_analysis}")
    print(f"✓ Component Breakdown section: {'Component Breakdown' in clean_analysis}")
    print(f"✓ Market Interpretations section: {'Market Interpretations' in clean_analysis}")
    print(f"✓ Actionable Insights section: {'Actionable Trading Insights' in clean_analysis}")
    print(f"✓ Gauge bars present: {'█' in clean_analysis or '▓' in clean_analysis}")

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
    test_confluence_display(symbol)