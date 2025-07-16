#!/usr/bin/env python3
"""
Test script for Enhanced PrettyTable Confluence Breakdown

This script tests the enhanced PrettyTable formatting for confluence analysis
to ensure it includes all sections: component breakdown, top influential components,
market interpretations, and actionable insights.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.core.formatting.formatter import LogFormatter

def test_enhanced_confluence_prettytable():
    """Test the enhanced confluence breakdown with PrettyTable formatting."""
    
    print("🧪 Testing Enhanced PrettyTable Confluence Breakdown")
    print("=" * 80)
    
    # Test data based on the user's HYPERUSDT example
    symbol = "HYPERUSDT"
    confluence_score = 55.69
    reliability = 1.0
    
    components = {
        'orderbook': 61.89,
        'orderflow': 61.49,
        'volume': 48.46,
        'price_structure': 42.64,
        'technical': 60.56,
        'sentiment': 51.52
    }
    
    weights = {
        'orderbook': 0.25,
        'orderflow': 0.25,
        'volume': 0.16,
        'price_structure': 0.16,
        'technical': 0.11,
        'sentiment': 0.07
    }
    
    # Enhanced results with detailed interpretations
    results = {
        'orderbook': {
            'score': 61.89,
            'components': {
                'spread': 99.98,
                'liquidity': 99.79,
                'depth': 91.12,
                'imbalance': 45.32
            },
            'interpretation': {
                'summary': 'Orderbook shows Balanced order book with high neutral-side liquidity and tight spreads. suggesting equilibrium between buyers and sellers, providing both support and resistance around current price, and indicating high market efficiency and low execution costs. Strong order depth suggests stable price levels.'
            },
            'enhanced_interpretation': 'Orderbook shows Balanced order book with high neutral-side liquidity and tight spreads. suggesting equilibrium between buyers and sellers, providing both support and resistance around current price, and indicating high market efficiency and low execution costs. Strong order depth suggests stable price levels.'
        },
        'orderflow': {
            'score': 61.49,
            'components': {
                'liquidity_score': 83.33,
                'cvd': 77.94,
                'liquidity_zones': 60.33,
                'open_interest': 35.12
            },
            'interpretation': {
                'summary': 'Neutral orderflow with slight buying bias. Declining open interest suggests trend exhaustion, often precedes consolidation or reversal. Strong positive cumulative volume delta showing dominant buying activity.'
            },
            'enhanced_interpretation': 'Neutral orderflow with slight buying bias. Declining open interest suggests trend exhaustion, often precedes consolidation or reversal. Strong positive cumulative volume delta showing dominant buying activity.'
        },
        'volume': {
            'score': 48.46,
            'components': {
                'obv': 70.3,
                'volume_profile': 45.2,
                'volume_trend': 30.1
            },
            'interpretation': {
                'summary': 'Volume patterns show typical market participation without clear directional bias, indicating neutral conditions or potential consolidation phase. OBV showing strong upward trajectory (70.3), confirming price trend with accumulation. Overall volume analysis suggests consolidation phase with balanced trading activity.'
            },
            'enhanced_interpretation': 'Volume patterns show typical market participation without clear directional bias, indicating neutral conditions or potential consolidation phase. OBV showing strong upward trajectory (70.3), confirming price trend with accumulation. Overall volume analysis suggests consolidation phase with balanced trading activity.'
        },
        'technical': {
            'score': 60.56,
            'components': {
                'macd': 56.0,
                'williams_r': 88.5,
                'rsi': 52.3
            },
            'interpretation': {
                'summary': 'Technical indicators show slight bullish bias within overall neutrality. MACD shows neutral trend conditions (56.0). WILLIAMS_R indicates overbought conditions (88.5), potential reversal zone.'
            },
            'enhanced_interpretation': 'Technical indicators show slight bullish bias within overall neutrality. MACD shows neutral trend conditions (56.0). WILLIAMS_R indicates overbought conditions (88.5), potential reversal zone.'
        },
        'sentiment': {
            'score': 51.52,
            'components': {
                'funding_rate': 45.2,
                'fear_greed': 58.1,
                'social_sentiment': 51.0
            },
            'interpretation': {
                'summary': 'Neutral market sentiment with high risk conditions and neutral funding rates. suggesting potential for sharp reversals, indicating balanced long/short positioning. Traders positioned primarily long, confirming directional bias with moderate conviction. Market showing below-average volatility.'
            },
            'enhanced_interpretation': 'Neutral market sentiment with high risk conditions and neutral funding rates. suggesting potential for sharp reversals, indicating balanced long/short positioning. Traders positioned primarily long, confirming directional bias with moderate conviction. Market showing below-average volatility.'
        },
        'price_structure': {
            'score': 42.64,
            'components': {
                'vwap': 48.2,
                'support_resistance': 40.1,
                'trend_strength': 39.6
            },
            'interpretation': {
                'summary': 'Price structure has a bearish bias without clear trend definition. Price oscillating near VWAP indicating equilibrium between buyers and sellers.'
            },
            'enhanced_interpretation': 'Price structure has a bearish bias without clear trend definition. Price oscillating near VWAP indicating equilibrium between buyers and sellers.'
        },
        'top_influential': {
            'components': {
                'spread (orderbook)': 99.98,
                'liquidity (orderbook)': 99.79,
                'depth (orderbook)': 91.12,
                'liquidity score (orderflow)': 83.33,
                'cvd (orderflow)': 77.94
            }
        }
    }
    
    print("📊 Testing Enhanced PrettyTable Confluence Analysis")
    print("-" * 50)
    
    # Test the enhanced PrettyTable formatting
    enhanced_table = LogFormatter.format_enhanced_confluence_score_table(
        symbol=symbol,
        confluence_score=confluence_score,
        components=components,
        results=results,
        weights=weights,
        reliability=reliability,
        use_pretty_table=True
    )
    
    print(enhanced_table)
    
    print("\n✅ Enhanced PrettyTable Test Results:")
    print("-" * 40)
    
    # Check for key sections
    sections_found = {
        'Component Breakdown': 'Component Breakdown:' in enhanced_table,
        'Top Influential Components': 'Top Influential Individual Components:' in enhanced_table,
        'Market Interpretations': 'Market Interpretations:' in enhanced_table,
        'Actionable Trading Insights': 'Actionable Trading Insights:' in enhanced_table
    }
    
    for section, found in sections_found.items():
        status = "✅ FOUND" if found else "❌ MISSING"
        print(f"  {section}: {status}")
    
    # Check for specific content
    content_checks = {
        'PrettyTable format': '+--' in enhanced_table and '|' in enhanced_table,
        'Color formatting': '\033[' in enhanced_table,
        'Visual gauges': '█' in enhanced_table or '▓' in enhanced_table,
        'Detailed interpretations': 'Orderbook shows Balanced' in enhanced_table,
        'Severity indicators': '🔵' in enhanced_table or '🟡' in enhanced_table,
        'Actionable insights': 'NEUTRAL STANCE' in enhanced_table
    }
    
    print("\n📋 Content Verification:")
    print("-" * 25)
    for check, found in content_checks.items():
        status = "✅ PASS" if found else "❌ FAIL"
        print(f"  {check}: {status}")
    
    # Compare with basic version
    print("\n🔄 Comparing with Basic PrettyTable Version:")
    print("-" * 45)
    
    basic_table = LogFormatter.format_enhanced_confluence_score_table(
        symbol=symbol,
        confluence_score=confluence_score,
        components=components,
        results=results,
        weights=weights,
        reliability=reliability,
        use_pretty_table=False  # Use EnhancedFormatter instead
    )
    
    enhanced_length = len(enhanced_table.split('\n'))
    basic_length = len(basic_table.split('\n'))
    
    print(f"  Enhanced PrettyTable lines: {enhanced_length}")
    print(f"  Basic Enhanced lines: {basic_length}")
    print(f"  Difference: {enhanced_length - basic_length} lines")
    
    # Check if all sections are present
    all_sections_found = all(sections_found.values())
    all_content_valid = all(content_checks.values())
    
    if all_sections_found and all_content_valid:
        print("\n🎉 SUCCESS: Enhanced PrettyTable confluence breakdown is working correctly!")
        print("   All sections present with proper formatting and content.")
        return True
    else:
        print("\n❌ ISSUES DETECTED:")
        if not all_sections_found:
            missing = [k for k, v in sections_found.items() if not v]
            print(f"   Missing sections: {', '.join(missing)}")
        if not all_content_valid:
            failed = [k for k, v in content_checks.items() if not v]
            print(f"   Failed content checks: {', '.join(failed)}")
        return False

if __name__ == "__main__":
    success = test_enhanced_confluence_prettytable()
    sys.exit(0 if success else 1) 