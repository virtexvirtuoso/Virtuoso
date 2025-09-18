#!/usr/bin/env python3
"""
Test script to verify the Price Structure interpretation fix.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, '/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

from src.core.analysis.interpretation_generator import InterpretationGenerator

def test_price_structure_interpretation():
    """Test that price structure interpretation generates proper human-readable text."""
    
    print("🔍 Testing Price Structure Interpretation Fix")
    print("=" * 60)
    
    # Create test data similar to what we saw in the logs
    test_data = {
        'score': 47.82,
        'components': {
            'support_resistance': 47.05,
            'order_blocks': 63.39,
            'trend_position': 47.88,
            'volume_profile': 37.23,
            'market_structure': 29.07,
            'range_analysis': 91.0,
            'fair_value_gaps': 11.88,
            'liquidity_zones': 50.0,
            'bos_choch': 50.0
        },
        'signals': {
            'support_resistance': {
                'value': 47.05,
                'signal': 'weak_level',
                'bias': 'neutral',
                'strength': 'moderate'
            },
            'order_blocks': {
                'value': 63.39,
                'signal': 'neutral',
                'bias': 'bullish', 
                'strength': 'moderate'
            },
            'trend_position': {
                'value': 47.88,
                'signal': 'sideways',
                'bias': 'neutral',
                'strength': 'moderate'
            },
            'volume_profile': {
                'value': 37.23,
                'signal': 'low',
                'strength': 'moderate'
            },
            'market_structure': {
                'value': 29.07,
                'signal': 'bearish',
                'strength': 'moderate'
            },
            'range_analysis': {
                'value': 91.0,
                'signal': 'bullish_range',
                'bias': 'bullish',
                'strength': 'strong'
            },
            'fair_value_gaps': {
                'value': 11.88,
                'signal': 'bearish_fvg',
                'bias': 'bearish',
                'strength': 'strong',
                'interpretation': 'Strong bearish FVG - Price likely to continue downward'
            },
            'liquidity_zones': {
                'value': 50.0,
                'signal': 'neutral',
                'bias': 'neutral',
                'strength': 'moderate',
                'interpretation': 'Balanced liquidity - No clear directional bias'
            },
            'bos_choch': {
                'value': 50.0,
                'signal': 'ranging',
                'bias': 'neutral',
                'strength': 'moderate',
                'interpretation': 'Ranging structure - No clear BOS or CHoCH signals'
            }
        },
        'metadata': {
            'raw_values': {
                'support_resistance': 47.05,
                'order_blocks': 63.39,
                'trend_position': 47.88
            }
        }
    }
    
    # Initialize the interpretation generator
    generator = InterpretationGenerator()
    
    try:
        # Generate interpretation using the fixed method
        interpretation = generator._interpret_price_structure(test_data)
        
        print("\n✅ Generated Price Structure Interpretation:")
        print("-" * 60)
        print(f"Score: {test_data['score']:.2f}")
        print(f"Interpretation: {interpretation}")
        print("-" * 60)
        
        # Verify it's not raw dictionary data
        if not interpretation.startswith('support_resistance='):
            print("✅ SUCCESS: Interpretation is properly formatted human-readable text")
            print("✅ No raw dictionary data displayed")
            return True
        else:
            print("❌ FAILED: Still showing raw dictionary data")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_price_structure_interpretation()
    if success:
        print("\n🎉 Price Structure interpretation fix is working correctly!")
        sys.exit(0)
    else:
        print("\n💥 Price Structure interpretation fix needs more work")
        sys.exit(1)