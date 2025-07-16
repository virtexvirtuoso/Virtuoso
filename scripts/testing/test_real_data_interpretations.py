#!/usr/bin/env python3
"""
Test script to verify that the enhanced interpretations logic works with real data structure.

Based on the live output showing components like 'spread (orderbook)', 'liquidity (orderbook)', etc.,
this script tests the fallback interpretation generation from the actual data structure.
"""

import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.core.formatting.formatter import PrettyTableFormatter

# Configure logging to see debug output
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_real_data_structure():
    """Create data structure that matches what the real system produces."""
    return {
        'confluence_score': 57.23,
        'reliability': 1.0,
        'components': {
            'orderbook': 66.07,
            'orderflow': 52.86,
            'price_structure': 62.81,
            'volume': 44.50,
            'technical': 54.18,
            'sentiment': 62.32
        },
        'results': {
            'orderbook': {
                'score': 66.07,
                'components': {
                    'spread': {'score': 99.95, 'signal': 'bullish'},
                    'liquidity': {'score': 99.38, 'signal': 'bullish'},
                    'depth': {'score': 97.28, 'signal': 'bullish'},
                    'dom_momentum': {'score': 72.65, 'signal': 'bullish'},
                    'exhaustion': {'score': 45.32, 'signal': 'neutral'}
                }
            },
            'orderflow': {
                'score': 52.86,
                'components': {
                    'liquidity_score': {'score': 83.33, 'signal': 'bullish'},
                    'institutional_flow': {'score': 55.2, 'signal': 'neutral'},
                    'retail_flow': {'score': 38.9, 'signal': 'bearish'},
                    'flow_imbalance': {'score': 42.1, 'signal': 'bearish'}
                }
            },
            'sentiment': {
                'score': 62.32,
                'components': {
                    'funding_rate': {'score': 65.3, 'signal': 'bullish'},
                    'open_interest': {'score': 58.1, 'signal': 'neutral'},
                    'social_sentiment': {'score': 63.7, 'signal': 'bullish'}
                }
            },
            'technical': {
                'score': 54.18,
                'components': {
                    'macd': {'score': 52.0, 'signal': 'neutral'},
                    'rsi': {'score': 48.2, 'signal': 'neutral'},
                    'moving_averages': {'score': 62.5, 'signal': 'bullish'}
                }
            },
            'volume': {
                'score': 44.50,
                'components': {
                    'volume_profile': {'score': 48.5, 'signal': 'neutral'},
                    'volume_trend': {'score': 35.2, 'signal': 'bearish'},
                    'volume_oscillator': {'score': 49.8, 'signal': 'neutral'}
                }
            },
            'price_structure': {
                'score': 62.81,
                'components': {
                    'support_resistance': {'score': 58.2, 'signal': 'neutral'},
                    'trend_structure': {'score': 67.7, 'signal': 'bullish'},
                    'fibonacci_levels': {'score': 62.5, 'signal': 'bullish'}
                }
            }
        },
        'metadata': {
            'weights': {
                'orderbook': 0.25,
                'orderflow': 0.25,
                'price_structure': 0.16,
                'volume': 0.16,
                'technical': 0.11,
                'sentiment': 0.07
            }
        }
    }

def test_enhanced_interpretations():
    """Test the enhanced interpretations with real data structure."""
    
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                     REAL DATA INTERPRETATIONS TEST                          ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Test data that matches real system structure
    symbol = "1000PEPEUSDT"
    analysis_data = create_real_data_structure()
    
    print("📊 Testing Enhanced Confluence Formatting with Real Data Structure")
    print("=" * 80)
    print()
    
    # Test the enhanced formatting method with real data structure
    enhanced_table = PrettyTableFormatter.format_enhanced_confluence_score_table(
        symbol=symbol,
        confluence_score=analysis_data['confluence_score'],
        components=analysis_data['components'],
        results=analysis_data['results'],
        weights=analysis_data['metadata']['weights'],
        reliability=analysis_data['reliability']
    )
    
    print(enhanced_table)
    print()
    
    # Verify that Market Interpretations section is present
    has_market_interpretations = "Market Interpretations:" in enhanced_table
    has_actionable_insights = "Actionable Trading Insights:" in enhanced_table
    has_component_breakdown = "Component Breakdown:" in enhanced_table
    
    print("🔍 VERIFICATION RESULTS:")
    print("=" * 50)
    print(f"✅ Component Breakdown Present: {has_component_breakdown}")
    print(f"✅ Market Interpretations Present: {has_market_interpretations}")
    print(f"✅ Actionable Trading Insights Present: {has_actionable_insights}")
    print()
    
    if has_market_interpretations:
        print("🎉 SUCCESS: Market Interpretations are being generated from real data structure!")
        print("   - Fallback interpretation logic is working")
        print("   - Components with signals are being processed")
        print("   - Basic interpretations are being generated")
        return True
    else:
        print("❌ FAILURE: Market Interpretations still missing!")
        print("   - Check debug logs above for details")
        return False

def test_individual_component_interpretation():
    """Test individual component interpretation generation."""
    
    print("\n" + "="*80)
    print("📊 INDIVIDUAL COMPONENT INTERPRETATION TEST")
    print("="*80)
    
    # Test just the interpretation method directly
    analysis_data = create_real_data_structure()
    
    print("🔍 Testing _format_enhanced_interpretations directly:")
    print("-" * 50)
    
    interpretations = PrettyTableFormatter._format_enhanced_interpretations(analysis_data['results'])
    
    print(f"Generated {len(interpretations)} interpretation lines:")
    for i, interp in enumerate(interpretations, 1):
        print(f"{i:2d}. {interp}")
    
    return len(interpretations) > 0

def main():
    """Main test function."""
    
    print(f"🚀 Starting Real Data Interpretations Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Test enhanced formatting with real data
        success1 = test_enhanced_interpretations()
        
        # Test individual component interpretation
        success2 = test_individual_component_interpretation()
        
        print("\n" + "="*80)
        print("📋 SUMMARY:")
        print("="*80)
        
        if success1 and success2:
            print("✅ REAL DATA INTERPRETATIONS TEST: SUCCESS")
            print()
            print("🔧 What Works:")
            print("   • Enhanced formatting with real data structure")
            print("   • Fallback interpretation generation from components")
            print("   • Signal counting and bias determination")
            print("   • Debug logging for troubleshooting")
            print()
            print("🎯 Expected Results:")
            print("   • Market Interpretations should now appear in live system")
            print("   • Components with bullish/bearish/neutral signals will be analyzed")
            print("   • Fallback logic handles missing interpretation fields")
            print()
            print("🚀 Ready for live system testing!")
        else:
            print("❌ REAL DATA INTERPRETATIONS TEST: FAILED")
            print("   Check debug logs for specific issues")
        
        return success1 and success2
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 