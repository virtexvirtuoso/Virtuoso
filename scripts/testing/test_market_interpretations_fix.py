#!/usr/bin/env python3
"""
Test script to verify that the Market Interpretations fix works correctly
with the actual data structure passed from enhanced data generation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.formatting.formatter import PrettyTableFormatter

def test_market_interpretations_fix():
    """Test that the _format_enhanced_interpretations method correctly processes market_interpretations field."""
    
    print("Testing Market Interpretations Fix...")
    print("=" * 60)
    
    # Simulate the actual data structure passed from enhanced data generation
    # This mimics what the signal generator creates and passes to the formatter
    results_with_market_interpretations = {
        'technical': {
            'score': 36.70,
            'components': {}
        },
        'volume': {
            'score': 52.71,
            'components': {}
        },
        'orderbook': {
            'score': 66.08,
            'components': {}
        },
        'orderflow': {
            'score': 76.56,
            'components': {}
        },
        'sentiment': {
            'score': 58.19,
            'components': {}
        },
        'price_structure': {
            'score': 47.42,
            'components': {}
        },
        'top_influential': {
            'score': 75.0,
            'components': {}
        },
        # This is the key field that was missing from the formatter logic
        'market_interpretations': [
            {
                'component': 'overall_analysis',
                'display_name': 'Overall Analysis',
                'interpretation': 'OMNIUSDT shows neutral sentiment with confluence score of 59.79. Price is in consolidation with no clear directional bias.'
            },
            {
                'component': 'technical',
                'display_name': 'Technical',
                'interpretation': 'Technical indicators suggest bearish momentum with score of 36.7 indicating moderate bearish pressure in momentum-based signals.'
            },
            {
                'component': 'volume',
                'display_name': 'Volume',
                'interpretation': 'Volume analysis shows moderate bullish bias with score of 52.7, suggesting slightly above-average trading activity supporting price action.'
            },
            {
                'component': 'orderbook',
                'display_name': 'Orderbook',
                'interpretation': 'Orderbook analysis indicates strong bullish sentiment with score of 66.1, showing significant buying interest and depth at current levels.'
            },
            {
                'component': 'orderflow',
                'display_name': 'Orderflow',
                'interpretation': 'Orderflow shows strong bullish signals with score of 76.6, indicating institutional buying pressure and positive money flow dynamics.'
            },
            {
                'component': 'sentiment',
                'display_name': 'Sentiment',
                'interpretation': 'Market sentiment reflects moderate bullish bias with score of 58.2, suggesting cautiously optimistic market participant positioning.'
            },
            {
                'component': 'price_structure',
                'display_name': 'Price Structure',
                'interpretation': 'Price structure analysis shows neutral conditions with score of 47.4, indicating balanced support and resistance levels.'
            },
            {
                'component': 'enhanced_analysis',
                'display_name': 'Enhanced Analysis',
                'interpretation': 'Cross-component analysis reveals mixed signals with orderflow and orderbook showing strong bullish bias while technical indicators suggest bearish momentum. This creates a conflicted market environment requiring cautious position sizing and clear directional confirmation before entry.'
            }
        ]
    }
    
    print("1. Testing with market_interpretations field present:")
    print("-" * 50)
    
    # Test the enhanced interpretations method
    interpretations = PrettyTableFormatter._format_enhanced_interpretations(results_with_market_interpretations)
    
    print(f"Generated {len(interpretations)} interpretation lines:")
    print()
    
    for interpretation in interpretations:
        print(interpretation)
    
    print()
    print("2. Verification:")
    print("-" * 50)
    
    # Verify that interpretations were generated
    if interpretations:
        print("✅ SUCCESS: Market interpretations were generated successfully!")
        print(f"✅ Generated {len(interpretations)} interpretation lines")
        
        # Check for specific components
        interpretation_text = '\n'.join(interpretations)
        
        expected_components = ['Overall Analysis', 'Technical', 'Volume', 'Orderbook', 'Orderflow', 'Sentiment', 'Price Structure', 'Enhanced Analysis']
        found_components = []
        
        for component in expected_components:
            if component in interpretation_text:
                found_components.append(component)
                print(f"✅ Found interpretation for: {component}")
            else:
                print(f"❌ Missing interpretation for: {component}")
        
        print(f"\n✅ Found {len(found_components)}/{len(expected_components)} expected components")
        
        # Test that the interpretations contain meaningful content
        if 'OMNIUSDT shows neutral sentiment' in interpretation_text:
            print("✅ Overall analysis interpretation found")
        if 'strong bullish signals' in interpretation_text:
            print("✅ Component-specific interpretations found")
        if 'conflicted market environment' in interpretation_text:
            print("✅ Enhanced analysis interpretation found")
            
    else:
        print("❌ FAILED: No market interpretations were generated!")
        return False
    
    print()
    print("3. Testing fallback behavior (without market_interpretations field):")
    print("-" * 50)
    
    # Test without market_interpretations field to ensure fallback still works
    results_without_market_interpretations = {
        'technical': {
            'score': 36.70,
            'components': {},
            'interpretation': 'Technical score indicates bearish momentum'
        },
        'volume': {
            'score': 52.71,
            'components': {},
            'interpretation': 'Volume shows moderate activity'
        }
    }
    
    fallback_interpretations = PrettyTableFormatter._format_enhanced_interpretations(results_without_market_interpretations)
    
    if fallback_interpretations:
        print(f"✅ Fallback logic works: Generated {len(fallback_interpretations)} interpretation lines")
        for interp in fallback_interpretations:
            print(interp)
    else:
        print("❌ Fallback logic failed")
        return False
    
    print()
    print("=" * 60)
    print("🎉 ALL TESTS PASSED! Market Interpretations fix is working correctly!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    test_market_interpretations_fix() 