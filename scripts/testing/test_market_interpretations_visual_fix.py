#!/usr/bin/env python3
"""
Test script to verify that the Market Interpretations section now has
proper borders and enhanced visual formatting.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.formatting.formatter import PrettyTableFormatter

def test_market_interpretations_visual_enhancement():
    """Test that the Market Interpretations section has proper bordered formatting."""
    
    print("Testing Market Interpretations Visual Enhancement...")
    print("=" * 80)
    
    # Simulate the complete data structure with market_interpretations
    test_results = {
        'technical': {
            'score': 41.04,
            'components': {}
        },
        'volume': {
            'score': 52.71,
            'components': {}
        },
        'orderbook': {
            'score': 76.50,
            'components': {}
        },
        'orderflow': {
            'score': 49.20,
            'components': {}
        },
        'sentiment': {
            'score': 62.00,
            'components': {}
        },
        'price_structure': {
            'score': 50.75,
            'components': {}
        },
        'market_interpretations': [
            {
                'component': 'overall_analysis',
                'display_name': 'Overall Analysis',
                'interpretation': 'ADAUSDT shows neutral sentiment with confluence score of 54.6. Price is in consolidation with no clear directional bias.'
            },
            {
                'component': 'technical', 
                'display_name': 'Technical',
                'interpretation': 'Technical indicators show slight bearish bias within overall neutrality. MACD shows neutral trend conditions (50.0). CCI shows bearish momentum without being oversold (36.0).'
            },
            {
                'component': 'orderbook',
                'display_name': 'Orderbook', 
                'interpretation': 'Orderbook shows Strong bid-side dominance with high bid-side liquidity and tight spreads suggesting buyers controlling price action, providing strong price support below current level.'
            },
            {
                'component': 'sentiment',
                'display_name': 'Sentiment',
                'interpretation': 'Moderately bullish market sentiment with high risk conditions and neutral funding rates suggesting potential for sharp reversals, indicating balanced long/short positioning.'
            }
        ]
    }
    
    # Test the enhanced confluence score table formatting
    formatted_output = PrettyTableFormatter.format_enhanced_confluence_score_table(
        symbol="ADAUSDT",
        confluence_score=54.64,
        components={'technical': 41.04, 'volume': 52.71, 'orderbook': 76.50, 'orderflow': 49.20, 'sentiment': 62.00, 'price_structure': 50.75},
        results=test_results,
        weights={'orderflow': 0.25, 'orderbook': 0.25, 'volume': 0.16, 'price_structure': 0.16, 'technical': 0.11, 'sentiment': 0.07},
        reliability=1.0
    )
    
    print("FORMATTED OUTPUT:")
    print("=" * 80)
    print(formatted_output)
    print("=" * 80)
    
    # Check for visual enhancements
    lines = formatted_output.split('\n')
    
    # Look for Market Interpretations section
    market_interp_start = -1
    market_interp_end = -1
    
    for i, line in enumerate(lines):
        if 'Market Interpretations' in line and '╔' in lines[i-1] if i > 0 else False:
            market_interp_start = i - 1  # Include the top border
        elif market_interp_start != -1 and '╚' in line:
            market_interp_end = i
            break
    
    if market_interp_start != -1 and market_interp_end != -1:
        print("✅ SUCCESS: Market Interpretations section found with borders!")
        print(f"   Section spans lines {market_interp_start} to {market_interp_end}")
        
        # Show the bordered section
        print("\nBORDERED MARKET INTERPRETATIONS SECTION:")
        print("-" * 80)
        for i in range(market_interp_start, market_interp_end + 1):
            if i < len(lines):
                print(lines[i])
        print("-" * 80)
        
        # Verify border characters
        top_border = lines[market_interp_start]
        bottom_border = lines[market_interp_end]
        
        if '╔' in top_border and '╗' in top_border:
            print("✅ Top border formatting correct")
        else:
            print("❌ Top border formatting issue")
            
        if '╚' in bottom_border and '╝' in bottom_border:
            print("✅ Bottom border formatting correct")
        else:
            print("❌ Bottom border formatting issue")
            
        # Check for side borders
        side_border_count = 0
        for i in range(market_interp_start + 1, market_interp_end):
            if i < len(lines) and '║' in lines[i]:
                side_border_count += 1
                
        if side_border_count > 0:
            print(f"✅ Side borders found in {side_border_count} lines")
        else:
            print("❌ No side borders found")
            
    else:
        print("❌ FAILURE: Market Interpretations section with borders not found")
        print("   Searching for 'Market Interpretations' in output...")
        for i, line in enumerate(lines):
            if 'Market Interpretations' in line:
                print(f"   Found at line {i}: {line}")
    
    print("\n" + "=" * 80)
    print("Visual Enhancement Test Complete!")

if __name__ == "__main__":
    test_market_interpretations_visual_enhancement() 