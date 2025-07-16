#!/usr/bin/env python3
"""
Comprehensive test to verify that the complete enhanced confluence score table
formatting works correctly with the market_interpretations field fix.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.formatting.formatter import PrettyTableFormatter

def test_complete_enhanced_formatting():
    """Test the complete enhanced confluence score table formatting with market_interpretations."""
    
    print("Testing Complete Enhanced Confluence Score Table Formatting...")
    print("=" * 80)
    
    # Simulate the complete data structure that would be passed to the formatter
    # including the market_interpretations field from enhanced data generation
    symbol = "OMNIUSDT"
    confluence_score = 59.79
    components = {
        'technical': 36.70,
        'volume': 52.71,
        'orderbook': 66.08,
        'orderflow': 76.56,
        'sentiment': 58.19,
        'price_structure': 47.42
    }
    
    results = {
        'technical': {
            'score': 36.70,
            'components': {
                'rsi': 35.2,
                'macd': 38.1,
                'bollinger': 36.9
            }
        },
        'volume': {
            'score': 52.71,
            'components': {
                'volume_ratio': 54.3,
                'volume_trend': 51.1
            }
        },
        'orderbook': {
            'score': 66.08,
            'components': {
                'spread': 99.81,
                'liquidity': 97.82,
                'depth': 91.78
            }
        },
        'orderflow': {
            'score': 76.56,
            'components': {
                'open_interest_score': 100.00,
                'liquidity_score': 83.33
            }
        },
        'sentiment': {
            'score': 58.19,
            'components': {
                'funding_rate': 60.5,
                'social_sentiment': 55.9
            }
        },
        'price_structure': {
            'score': 47.42,
            'components': {
                'support_resistance': 48.1,
                'trend_strength': 46.7
            }
        },
        'top_influential': {
            'score': 75.0,
            'components': {}
        },
        # The key enhanced data field that contains the market interpretations
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
        ],
        'actionable_insights': [
            'NEUTRAL STANCE: Range-bound conditions likely - consider mean-reversion strategies',
            'RISK ASSESSMENT: LOW - Normal sentiment conditions',
            'STRENGTH: Orderflow shows strong bullish signals',
            'DIVERGENCE: Mixed signals across components - wait for clearer direction',
            'STRATEGY: Monitor for further confirmation before implementing directional strategies'
        ]
    }
    
    weights = {
        'technical': 0.15,
        'volume': 0.10,
        'orderbook': 0.25,
        'orderflow': 0.25,
        'sentiment': 0.15,
        'price_structure': 0.10
    }
    
    reliability = 1.0
    
    print("1. Testing Enhanced Confluence Score Table with Market Interpretations:")
    print("-" * 80)
    
    # Generate the complete enhanced confluence score table
    formatted_table = PrettyTableFormatter.format_enhanced_confluence_score_table(
        symbol=symbol,
        confluence_score=confluence_score,
        components=components,
        results=results,
        weights=weights,
        reliability=reliability,
        border_style="double"
    )
    
    print(formatted_table)
    
    print("\n2. Verification:")
    print("-" * 80)
    
    # Verify that the table contains all expected sections
    expected_sections = [
        "OMNIUSDT CONFLUENCE ANALYSIS",
        "Overall Score:",
        "Reliability:",
        "Component Breakdown:",
        "Top Influential Individual Components:",
        "Market Interpretations:",
        "Actionable Trading Insights:"
    ]
    
    missing_sections = []
    found_sections = []
    
    for section in expected_sections:
        if section in formatted_table:
            found_sections.append(section)
            print(f"✅ Found section: {section}")
        else:
            missing_sections.append(section)
            print(f"❌ Missing section: {section}")
    
    # Verify specific market interpretations content
    interpretation_checks = [
        ("Overall Analysis", "OMNIUSDT shows neutral sentiment"),
        ("Technical", "bearish momentum"),
        ("Volume", "moderate bullish bias"),
        ("Orderbook", "strong bullish sentiment"),
        ("Orderflow", "strong bullish signals"),
        ("Sentiment", "moderate bullish bias"),
        ("Price Structure", "neutral conditions"),
        ("Enhanced Analysis", "conflicted market environment")
    ]
    
    interpretation_found = 0
    for component, expected_text in interpretation_checks:
        if component in formatted_table and expected_text in formatted_table:
            interpretation_found += 1
            print(f"✅ Found {component} interpretation with expected content")
        else:
            print(f"❌ Missing {component} interpretation or expected content")
    
    # Verify actionable insights
    insight_checks = [
        "NEUTRAL STANCE",
        "RISK ASSESSMENT",
        "STRENGTH",
        "DIVERGENCE",
        "STRATEGY"
    ]
    
    insights_found = 0
    for insight in insight_checks:
        if insight in formatted_table:
            insights_found += 1
            print(f"✅ Found actionable insight: {insight}")
        else:
            print(f"❌ Missing actionable insight: {insight}")
    
    print(f"\n📊 Summary:")
    print(f"   Sections found: {len(found_sections)}/{len(expected_sections)}")
    print(f"   Interpretations found: {interpretation_found}/{len(interpretation_checks)}")
    print(f"   Actionable insights found: {insights_found}/{len(insight_checks)}")
    
    # Overall success check
    if (len(missing_sections) == 0 and 
        interpretation_found == len(interpretation_checks) and 
        insights_found == len(insight_checks)):
        print("\n🎉 SUCCESS: Complete enhanced formatting with Market Interpretations is working perfectly!")
        print("   ✅ All sections present")
        print("   ✅ All market interpretations included")
        print("   ✅ All actionable insights included")
        print("   ✅ Enhanced data field processing working correctly")
        return True
    else:
        print("\n❌ ISSUES DETECTED:")
        if missing_sections:
            print(f"   Missing sections: {missing_sections}")
        if interpretation_found < len(interpretation_checks):
            print(f"   Missing interpretations: {len(interpretation_checks) - interpretation_found}")
        if insights_found < len(insight_checks):
            print(f"   Missing insights: {len(insight_checks) - insights_found}")
        return False

if __name__ == "__main__":
    success = test_complete_enhanced_formatting()
    if success:
        print("\n" + "=" * 80)
        print("🚀 ALL TESTS PASSED! The Market Interpretations fix is fully operational!")
        print("   The live system should now display Market Interpretations correctly.")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ Some tests failed. Please review the issues above.")
        print("=" * 80) 