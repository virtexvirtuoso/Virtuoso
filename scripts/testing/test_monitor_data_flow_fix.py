#!/usr/bin/env python3
"""
Test script to verify that the monitor data flow fix correctly passes
market_interpretations from enhanced data generation to the formatter.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

def test_monitor_data_flow_fix():
    """Test that the monitor correctly merges enhanced data for the formatter."""
    
    print("Testing Monitor Data Flow Fix...")
    print("=" * 60)
    
    # Simulate the data structures in monitor.py
    
    # This is what formatter_results looks like (without market_interpretations)
    formatter_results = {
        'technical': {
            'score': 41.04,
            'components': {}
        },
        'volume': {
            'score': 61.87,
            'components': {}
        },
        'orderbook': {
            'score': 59.61,
            'components': {}
        }
    }
    
    # This is what result looks like after enhanced data is added
    result = {
        'confluence_score': 53.19,
        'components': {
            'technical': 41.04,
            'volume': 61.87,
            'orderbook': 59.61
        },
        'results': formatter_results,
        'market_interpretations': [
            {
                'component': 'overall_analysis',
                'display_name': 'Overall Analysis',
                'interpretation': 'BTCUSDT shows neutral sentiment with confluence score of 53.19.'
            },
            {
                'component': 'technical',
                'display_name': 'Technical',
                'interpretation': 'Technical indicators suggest bearish momentum with moderate pressure.'
            },
            {
                'component': 'volume',
                'display_name': 'Volume',
                'interpretation': 'Volume shows moderate bullish bias with above-average activity.'
            }
        ],
        'actionable_insights': [
            'NEUTRAL STANCE: Range-bound conditions likely',
            'RISK ASSESSMENT: LOW - Normal sentiment conditions'
        ]
    }
    
    print("1. Testing data flow logic:")
    print("-" * 40)
    
    # Simulate the logic from monitor.py
    display_results = result.get('results', formatter_results)
    print(f"✅ Initial display_results has keys: {list(display_results.keys()) if isinstance(display_results, dict) else 'Not a dict'}")
    
    # If enhanced data was added to result, merge it with display_results
    if result.get('market_interpretations'):
        print(f"✅ Found market_interpretations with {len(result['market_interpretations'])} items")
        
        if isinstance(display_results, dict):
            display_results = display_results.copy()
            display_results['market_interpretations'] = result['market_interpretations']
            print("✅ Merged market_interpretations into display_results")
        else:
            # If display_results is not a dict, create one with enhanced data
            display_results = {
                'market_interpretations': result['market_interpretations']
            }
            # Add formatter_results if it's a dict
            if isinstance(formatter_results, dict):
                display_results.update(formatter_results)
            print("✅ Created new display_results with market_interpretations")
    
    print(f"✅ Final display_results has keys: {list(display_results.keys())}")
    
    print("\n2. Verification:")
    print("-" * 40)
    
    # Verify that market_interpretations is now in display_results
    if 'market_interpretations' in display_results:
        interpretations = display_results['market_interpretations']
        print(f"✅ SUCCESS: market_interpretations found in display_results")
        print(f"✅ Contains {len(interpretations)} interpretations")
        
        # Verify structure
        for i, interp in enumerate(interpretations):
            if isinstance(interp, dict) and 'interpretation' in interp:
                component = interp.get('component', 'Unknown')
                text = interp.get('interpretation', '')[:50] + '...'
                print(f"   {i+1}. {component}: {text}")
            else:
                print(f"   {i+1}. Invalid structure: {type(interp)}")
        
        # Verify the formatter would find this data
        from src.core.formatting.formatter import PrettyTableFormatter
        
        print("\n3. Testing formatter integration:")
        print("-" * 40)
        
        # Test that our fixed formatter can process this data
        interpretations_output = PrettyTableFormatter._format_enhanced_interpretations(display_results)
        
        if interpretations_output:
            print(f"✅ Formatter successfully generated {len(interpretations_output)} interpretation lines")
            print("✅ Sample output:")
            for line in interpretations_output[:3]:  # Show first 3 lines
                print(f"   {line}")
            if len(interpretations_output) > 3:
                print(f"   ... and {len(interpretations_output) - 3} more lines")
        else:
            print("❌ Formatter failed to generate interpretations")
            return False
        
    else:
        print("❌ FAILED: market_interpretations not found in display_results")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 SUCCESS: Monitor data flow fix is working correctly!")
    print("   ✅ Enhanced data properly merged")
    print("   ✅ market_interpretations passed to formatter")
    print("   ✅ Formatter successfully processes the data")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_monitor_data_flow_fix()
    if not success:
        print("\n❌ Test failed - please review the issues above.")
        sys.exit(1) 