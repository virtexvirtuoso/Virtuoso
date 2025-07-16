#!/usr/bin/env python3
"""
Test script for Live Enhanced PrettyTable Confluence Breakdown

This script simulates the exact data flow from the monitor to test
the enhanced confluence breakdown with real system data.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.core.formatting.formatter import LogFormatter

def test_live_enhanced_confluence():
    """Test with data similar to what the monitor produces."""
    
    print("🔴 Testing Live Enhanced Confluence Breakdown")
    print("=" * 80)
    
    # Data from the user's SEIUSDT example (current output)
    symbol = "SEIUSDT"
    confluence_score = 54.81
    reliability = 1.0
    
    components = {
        'orderbook': 71.30,
        'orderflow': 40.89,
        'price_structure': 59.22,
        'volume': 46.35,
        'technical': 50.54,
        'sentiment': 61.68
    }
    
    weights = {
        'orderbook': 0.25,
        'orderflow': 0.25,
        'volume': 0.16,
        'price_structure': 0.16,
        'technical': 0.11,
        'sentiment': 0.07
    }
    
    # Simulate real results data from the monitor
    results = {
        'orderbook': {
            'score': 71.30,
            'components': {
                'spread': 99.79,
                'liquidity': 97.63,
                'depth': 94.39,
                'imbalance': 48.52
            },
            'interpretation': {
                'summary': 'Strong orderbook with excellent liquidity conditions. Tight spreads indicate high market efficiency. Deep order book provides strong support and resistance levels.'
            },
            'buy_threshold': 60.0,
            'sell_threshold': 40.0
        },
        'orderflow': {
            'score': 40.89,
            'components': {
                'liquidity_score': 70.57,
                'liquidity_zones': 60.33,
                'cvd': 45.12,
                'open_interest': 25.45
            },
            'interpretation': {
                'summary': 'Mixed orderflow signals with declining momentum. Liquidity zones show moderate activity. CVD suggests balanced buying and selling pressure.'
            }
        },
        'volume': {
            'score': 46.35,
            'components': {
                'obv': 52.1,
                'volume_profile': 44.2,
                'volume_trend': 42.8
            },
            'interpretation': {
                'summary': 'Volume patterns indicate consolidation phase. OBV shows neutral trend with slight accumulation bias. Volume profile suggests range-bound trading.'
            }
        },
        'technical': {
            'score': 50.54,
            'components': {
                'macd': 48.2,
                'rsi': 52.1,
                'williams_r': 51.3
            },
            'interpretation': {
                'summary': 'Technical indicators show neutral conditions with slight bullish bias. RSI in neutral zone. MACD showing consolidation pattern.'
            }
        },
        'sentiment': {
            'score': 61.68,
            'components': {
                'funding_rate': 58.2,
                'fear_greed': 65.1,
                'social_sentiment': 61.7
            },
            'interpretation': {
                'summary': 'Positive sentiment with moderate bullish bias. Funding rates neutral. Fear & Greed index showing optimism. Social sentiment moderately positive.'
            },
            'risk_level': 'MEDIUM'
        },
        'price_structure': {
            'score': 59.22,
            'components': {
                'vwap': 62.1,
                'support_resistance': 58.3,
                'trend_strength': 57.2
            },
            'interpretation': {
                'summary': 'Price structure shows consolidation near key levels. VWAP acting as dynamic support. Support/resistance levels well-defined.'
            },
            'key_levels': True
        },
        'top_influential': {
            'components': {
                'spread (orderbook)': 99.79,
                'liquidity (orderbook)': 97.63,
                'depth (orderbook)': 94.39,
                'liquidity score (orderflow)': 70.57,
                'liquidity zones (orderflow)': 60.33
            }
        }
    }
    
    print("📊 Testing Live Enhanced Confluence Analysis")
    print("-" * 50)
    
    # Test the enhanced PrettyTable formatting (what the monitor should show)
    enhanced_table = LogFormatter.format_enhanced_confluence_score_table(
        symbol=symbol,
        confluence_score=confluence_score,
        components=components,
        results=results,
        weights=weights,
        reliability=reliability,
        use_pretty_table=True
    )
    
    print("🎯 ENHANCED PRETTYTABLE OUTPUT:")
    print(enhanced_table)
    
    print("\n" + "=" * 80)
    print("📋 COMPARISON WITH CURRENT OUTPUT")
    print("=" * 80)
    
    # Show what the user currently sees vs what they should see
    print("❌ CURRENT OUTPUT (Missing sections):")
    print("-" * 40)
    print("""SEIUSDT CONFLUENCE ANALYSIS
================================================================================
Overall Score: 54.81 (NEUTRAL)
Reliability: 100% (HIGH)

Component Breakdown:
+-----------------+-------+--------+-----------------+
| Component       | Score | Impact | Gauge           |
+-----------------+-------+--------+-----------------+
| Orderbook       | 71.30 |   17.8 | ??????????····· |
| Orderflow       | 40.89 |   10.2 | ??????········· |
| Price Structure | 59.22 |    9.5 | ????????······· |
| Volume          | 46.35 |    7.4 | ??????········· |
| Technical       | 50.54 |    5.6 | ???????········ |
| Sentiment       | 61.68 |    4.3 | ?????????······ |
+-----------------+-------+--------+-----------------+

Top Influential Individual Components:
  ? spread (orderbook)                 :  99.79 ? ???????????·
  ? liquidity (orderbook)              :  97.63 ? ???????????·
  ? depth (orderbook)                  :  94.39 ? ???????????·
  ? liquidity score (orderflow)        :  70.57 ? ????????····
  ? liquidity zones (orderflow)        :  60.33 ? ???????·····

Actionable Trading Insights:
  ? NEUTRAL STANCE: Range-bound conditions likely - consider mean-reversion strategies
  ? STRENGTH: Orderbook shows strong bullish signals
  ? TIMING: Mixed signals; wait for clearer directional confirmation""")
    
    print("\n✅ NEW ENHANCED OUTPUT (All sections included):")
    print("-" * 50)
    print("(See above enhanced output)")
    
    # Analysis
    print("\n🔍 KEY IMPROVEMENTS:")
    print("-" * 20)
    print("✅ Added Market Interpretations section with detailed analysis")
    print("✅ Enhanced Actionable Trading Insights with specific recommendations")
    print("✅ Added severity indicators (🔵🟡🔴) for interpretations")
    print("✅ Improved text wrapping and formatting")
    print("✅ Added risk assessment and strategy recommendations")
    print("✅ Maintained clean PrettyTable format")
    
    # Verification
    sections_found = {
        'Component Breakdown': 'Component Breakdown:' in enhanced_table,
        'Top Influential Components': 'Top Influential Individual Components:' in enhanced_table,
        'Market Interpretations': 'Market Interpretations:' in enhanced_table,
        'Actionable Trading Insights': 'Actionable Trading Insights:' in enhanced_table
    }
    
    print(f"\n📊 SECTION VERIFICATION:")
    print("-" * 25)
    for section, found in sections_found.items():
        status = "✅ PRESENT" if found else "❌ MISSING"
        print(f"  {section}: {status}")
    
    # Check for enhanced content
    enhanced_content = {
        'Detailed interpretations': any(interp in enhanced_table for interp in [
            'Strong orderbook', 'Mixed orderflow', 'Volume patterns', 'Technical indicators'
        ]),
        'Severity indicators': '🔵' in enhanced_table,
        'Risk assessment': 'RISK ASSESSMENT' in enhanced_table or 'MEDIUM' in enhanced_table,
        'Strategy recommendations': 'STRATEGY:' in enhanced_table,
        'Key levels mentioned': 'KEY LEVELS' in enhanced_table
    }
    
    print(f"\n🎯 ENHANCED CONTENT VERIFICATION:")
    print("-" * 35)
    for content, found in enhanced_content.items():
        status = "✅ INCLUDED" if found else "❌ MISSING"
        print(f"  {content}: {status}")
    
    all_sections = all(sections_found.values())
    all_content = all(enhanced_content.values())
    
    if all_sections and all_content:
        print("\n🎉 SUCCESS: Enhanced confluence breakdown is fully functional!")
        print("   The monitor will now show complete interpretations and insights.")
        return True
    else:
        print("\n❌ Issues detected in enhanced formatting")
        return False

if __name__ == "__main__":
    success = test_live_enhanced_confluence()
    sys.exit(0 if success else 1) 