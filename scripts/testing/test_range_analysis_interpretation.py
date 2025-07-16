#!/usr/bin/env python3
"""
Test Range Analysis Interpretation Generation
Validates that the range analysis component is properly integrated with interpretation generation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.analysis.interpretation_generator import InterpretationGenerator
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_range_analysis_interpretation():
    """Test that range analysis interpretations are generated correctly."""
    print("🔍 Testing Range Analysis Interpretation Generation...")
    
    # Create interpretation generator
    generator = InterpretationGenerator()
    
    # Test data with range analysis component
    test_data = {
        'score': 75.0,
        'components': {
            'support_resistance': 60.0,
            'order_blocks': 65.0,
            'trend_position': 70.0,
            'volume_profile': 55.0,
            'market_structure': 68.0,
            'range_analysis': 80.0  # Strong bullish range analysis
        },
        'signals': {
            'range_analysis': {
                'value': 80.0,
                'signal': 'bullish_range',
                'bias': 'bullish',
                'strength': 'strong'
            },
            'trend': {
                'value': 70.0,
                'signal': 'uptrend',
                'strength': 0.7
            },
            'support_resistance': {
                'value': 60.0,
                'signal': 'strong_level',
                'bias': 'bullish',
                'distance': 0.03
            }
        }
    }
    
    # Generate interpretation
    interpretation = generator._interpret_price_structure(test_data)
    
    print(f"✅ Generated Interpretation:")
    print(f"   {interpretation}")
    
    # Validate interpretation contains range analysis
    assert 'range analysis' in interpretation.lower(), "Interpretation should mention range analysis"
    assert 'bullish' in interpretation.lower(), "Should reflect bullish bias"
    
    # Test bearish range analysis
    test_data_bearish = {
        'score': 25.0,
        'components': {
            'support_resistance': 40.0,
            'order_blocks': 35.0,
            'trend_position': 30.0,
            'volume_profile': 45.0,
            'market_structure': 32.0,
            'range_analysis': 20.0  # Strong bearish range analysis
        },
        'signals': {
            'range_analysis': {
                'value': 20.0,
                'signal': 'bearish_range',
                'bias': 'bearish',
                'strength': 'strong'
            },
            'trend': {
                'value': 30.0,
                'signal': 'downtrend',
                'strength': 0.6
            }
        }
    }
    
    interpretation_bearish = generator._interpret_price_structure(test_data_bearish)
    
    print(f"✅ Generated Bearish Interpretation:")
    print(f"   {interpretation_bearish}")
    
    # Validate bearish interpretation
    assert 'range analysis' in interpretation_bearish.lower(), "Bearish interpretation should mention range analysis"
    assert 'bearish' in interpretation_bearish.lower(), "Should reflect bearish bias"
    
    # Test neutral range analysis
    test_data_neutral = {
        'score': 50.0,
        'components': {
            'support_resistance': 50.0,
            'order_blocks': 48.0,
            'trend_position': 52.0,
            'volume_profile': 49.0,
            'market_structure': 51.0,
            'range_analysis': 48.0  # Neutral range analysis
        },
        'signals': {
            'range_analysis': {
                'value': 48.0,
                'signal': 'neutral_range',
                'bias': 'neutral',
                'strength': 'moderate'
            },
            'trend': {
                'value': 52.0,
                'signal': 'sideways',
                'strength': 0.3
            }
        }
    }
    
    interpretation_neutral = generator._interpret_price_structure(test_data_neutral)
    
    print(f"✅ Generated Neutral Interpretation:")
    print(f"   {interpretation_neutral}")
    
    # Validate neutral interpretation
    assert 'range analysis' in interpretation_neutral.lower(), "Neutral interpretation should mention range analysis"
    assert ('neutral' in interpretation_neutral.lower() or 'consolidation' in interpretation_neutral.lower()), "Should reflect neutral/consolidation state"
    
    print("✅ All range analysis interpretation tests passed!")
    return True

def test_component_integration():
    """Test that range analysis integrates properly with other components."""
    print("\n🔍 Testing Range Analysis Component Integration...")
    
    # Test with configuration-style component data
    config_data = {
        'score': 72.0,
        'components': {
            'support_resistance': 65.0,
            'order_blocks': 70.0,  # Note: config uses 'order_blocks' not 'order_block'
            'trend_position': 68.0,
            'volume_profile': 60.0,
            'market_structure': 75.0,
            'range_analysis': 78.0
        },
        'signals': {
            'range_analysis': {
                'value': 78.0,
                'signal': 'bullish_range',
                'bias': 'bullish',
                'strength': 'strong'
            }
        }
    }
    
    generator = InterpretationGenerator()
    interpretation = generator._interpret_price_structure(config_data)
    
    print(f"✅ Component Integration Test:")
    print(f"   {interpretation}")
    
    # Validate that all components are considered
    assert len(interpretation) > 50, "Interpretation should be comprehensive"
    assert 'range analysis' in interpretation.lower(), "Should include range analysis"
    
    print("✅ Component integration test passed!")
    return True

def main():
    """Run all range analysis interpretation tests."""
    print("🚀 Starting Range Analysis Interpretation Tests...")
    
    try:
        # Test basic interpretation generation
        test_range_analysis_interpretation()
        
        # Test component integration
        test_component_integration()
        
        print("\n🎉 All tests passed! Range analysis interpretation is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 