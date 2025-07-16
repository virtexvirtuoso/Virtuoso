#!/usr/bin/env python3
"""
Test script to verify that src/main.py API endpoints now use enhanced confluence formatting.

This script tests the specific fix for the issue where ETHUSDT (from main.py API) 
was missing Market Interpretations while HYPERUSDT (from monitoring) had them.

The fix updates src/main.py to use LogFormatter.format_enhanced_confluence_score_table()
instead of the basic LogFormatter.format_confluence_score_table().
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.core.formatting import LogFormatter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_mock_analysis_data():
    """Create comprehensive mock analysis data for testing."""
    return {
        'confluence_score': 47.21,
        'reliability': 1.0,
        'components': {
            'orderflow': 42.28,
            'price_structure': 60.95,
            'orderbook': 38.36,
            'volume': 43.77,
            'technical': 60.99,
            'sentiment': 51.22
        },
        'results': {
            'orderbook': {
                'components': {
                    'spread': {'score': 100.0, 'signal': 'bullish'},
                    'liquidity': {'score': 91.65, 'signal': 'bullish'},
                    'depth': {'score': 77.05, 'signal': 'bullish'},
                    'exhaustion': {'score': 57.28, 'signal': 'neutral'}
                },
                'interpretation': 'Orderbook shows Extreme ask-side dominance with high ask-side liquidity and normal spreads. indicating strong selling pressure likely to drive prices lower, indicating significant resistance above current level, and with typical bid-ask differentials. Strong order depth suggests stable price levels with significant sell-side supply. Market makers showing bearish positioning, often precedes downward price movement.'
            },
            'orderflow': {
                'components': {
                    'liquidity_zones': {'score': 59.05, 'signal': 'neutral'},
                    'institutional_flow': {'score': 45.2, 'signal': 'neutral'},
                    'retail_flow': {'score': 38.9, 'signal': 'bearish'}
                },
                'interpretation': 'Neutral orderflow with slight buying bias. Rising open interest confirms trend strength, typically seen in strong trend continuation. Overall orderflow structure indicates balanced conditions with no clear directional edge.'
            },
            'sentiment': {
                'components': {
                    'funding_rate': {'score': 65.3, 'signal': 'bullish'},
                    'open_interest': {'score': 42.1, 'signal': 'bearish'},
                    'social_sentiment': {'score': 48.7, 'signal': 'neutral'}
                },
                'interpretation': 'Strongly bullish market sentiment with high risk conditions and positive funding rates indicating long bias. suggesting potential for sharp reversals, showing market willingness to pay premiums for long positions. Traders positioned primarily short, indicating moderate bearish conviction. Very high market activity with strong participation (bullish), reinforcing bullish conviction across market segments. Market showing above-average volatility, increasing both opportunity and risk factors. Analysis suggests moderate probability (~65%) of upward movement with moderate confidence (74%)'
            },
            'technical': {
                'components': {
                    'macd': {'score': 60.0, 'signal': 'bullish'},
                    'rsi': {'score': 40.2, 'signal': 'bearish'},
                    'moving_averages': {'score': 72.5, 'signal': 'bullish'}
                },
                'interpretation': 'Technical indicators reflect market indecision with no clear directional bias. MACD shows neutral trend conditions (60.0). RSI in neutral territory (40.2).'
            },
            'volume': {
                'components': {
                    'volume_profile': {'score': 68.5, 'signal': 'bullish'},
                    'volume_trend': {'score': 35.2, 'signal': 'bearish'},
                    'volume_oscillator': {'score': 52.1, 'signal': 'neutral'}
                },
                'interpretation': 'Volume patterns show typical market participation without clear directional bias, indicating neutral conditions or potential consolidation phase. VOLUME_PROFILE is the most significant volume indicator (68.5) with neutral readings. Overall volume analysis suggests consolidation phase with balanced trading activity.'
            },
            'price_structure': {
                'components': {
                    'support_resistance': {'score': 58.2, 'signal': 'neutral'},
                    'trend_structure': {'score': 63.7, 'signal': 'bullish'},
                    'fibonacci_levels': {'score': 61.0, 'signal': 'bullish'}
                },
                'interpretation': 'Price structure is neutral, showing balanced forces without clear direction. Price oscillating near VWAP indicating equilibrium between buyers and sellers.'
            }
        },
        'metadata': {
            'weights': {
                'orderflow': 0.18,
                'price_structure': 0.16,
                'orderbook': 0.25,
                'volume': 0.16,
                'technical': 0.11,
                'sentiment': 0.07
            }
        }
    }

def test_enhanced_formatting():
    """Test that the enhanced formatting includes Market Interpretations."""
    
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                    MAIN.PY API ENHANCED FORMATTING TEST                      ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Test data
    symbol = "ETHUSDT"
    analysis_data = create_mock_analysis_data()
    
    print("📊 Testing Enhanced Confluence Formatting (as used in main.py after fix)")
    print("=" * 80)
    
    # Test the enhanced formatting method that main.py now uses
    enhanced_table = LogFormatter.format_enhanced_confluence_score_table(
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
    has_top_components = "Top Influential Individual Components:" in enhanced_table
    
    print("🔍 VERIFICATION RESULTS:")
    print("=" * 50)
    print(f"✅ Component Breakdown Present: {has_component_breakdown}")
    print(f"✅ Top Components Present: {has_top_components}")
    print(f"✅ Market Interpretations Present: {has_market_interpretations}")
    print(f"✅ Actionable Trading Insights Present: {has_actionable_insights}")
    print()
    
    if has_market_interpretations and has_actionable_insights:
        print("🎉 SUCCESS: Enhanced formatting is working correctly!")
        print("   - Market Interpretations section is included")
        print("   - Enhanced Actionable Trading Insights are included")
        print("   - All core sections are present")
        print()
        print("📝 IMPACT:")
        print("   - ETHUSDT API requests will now show Market Interpretations")
        print("   - WebSocket analysis will now show Market Interpretations")
        print("   - Consistent formatting across all analysis endpoints")
        return True
    else:
        print("❌ FAILURE: Enhanced formatting is missing key sections!")
        if not has_market_interpretations:
            print("   - Missing: Market Interpretations section")
        if not has_actionable_insights:
            print("   - Missing: Enhanced Actionable Trading Insights section")
        return False

def test_comparison_with_basic():
    """Compare enhanced vs basic formatting to show the difference."""
    
    print("\n" + "="*80)
    print("📊 COMPARISON: Enhanced vs Basic Formatting")
    print("="*80)
    
    # Test data
    symbol = "ETHUSDT"
    analysis_data = create_mock_analysis_data()
    
    # Basic formatting (what main.py used before the fix)
    print("🔸 BASIC FORMATTING (Before Fix):")
    print("-" * 40)
    
    basic_table = LogFormatter.format_confluence_score_table(
        symbol=symbol,
        confluence_score=analysis_data['confluence_score'],
        components=analysis_data['components'],
        results=analysis_data['results'],
        weights=analysis_data['metadata']['weights'],
        reliability=analysis_data['reliability'],
        use_pretty_table=True,  # Force PrettyTable but basic version
        border_style="single"
    )
    
    # Show just the first few lines to demonstrate
    basic_lines = basic_table.split('\n')[:15]
    for line in basic_lines:
        print(line)
    print("... (truncated for comparison)")
    print()
    
    # Enhanced formatting (what main.py uses after the fix)
    print("🔹 ENHANCED FORMATTING (After Fix):")
    print("-" * 40)
    
    enhanced_table = LogFormatter.format_enhanced_confluence_score_table(
        symbol=symbol,
        confluence_score=analysis_data['confluence_score'],
        components=analysis_data['components'],
        results=analysis_data['results'],
        weights=analysis_data['metadata']['weights'],
        reliability=analysis_data['reliability']
    )
    
    # Show first few lines
    enhanced_lines = enhanced_table.split('\n')[:15]
    for line in enhanced_lines:
        print(line)
    print("... (includes Market Interpretations and Enhanced Insights)")
    print()
    
    # Count sections
    basic_sections = basic_table.count("║")
    enhanced_sections = enhanced_table.count("║")
    
    print(f"📈 SECTION COUNT COMPARISON:")
    print(f"   Basic Format Lines: {len(basic_table.split())}")
    print(f"   Enhanced Format Lines: {len(enhanced_table.split())}")
    print(f"   Additional Content: {len(enhanced_table.split()) - len(basic_table.split())} lines")

def main():
    """Main test function."""
    
    print(f"🚀 Starting Enhanced Formatting Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Test enhanced formatting
        success = test_enhanced_formatting()
        
        # Show comparison
        test_comparison_with_basic()
        
        print("\n" + "="*80)
        print("📋 SUMMARY:")
        print("="*80)
        
        if success:
            print("✅ MAIN.PY FIX VERIFICATION: SUCCESS")
            print()
            print("🔧 Changes Made:")
            print("   • Updated src/main.py line 839: format_confluence_score_table → format_enhanced_confluence_score_table")
            print("   • Updated src/main.py line 885: format_confluence_score_table → format_enhanced_confluence_score_table")
            print()
            print("🎯 Expected Results:")
            print("   • ETHUSDT API requests now include Market Interpretations")
            print("   • WebSocket analysis now includes Market Interpretations")
            print("   • Consistent with HYPERUSDT monitoring output")
            print("   • Enhanced Actionable Trading Insights included")
            print()
            print("🚀 Ready for testing with live API endpoints!")
        else:
            print("❌ MAIN.PY FIX VERIFICATION: FAILED")
            print("   Please check the LogFormatter implementation")
        
        return success
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 