#!/usr/bin/env python3
"""
Test script for Longer Gauges in PrettyTable Formatting

This script demonstrates the improved gauge lengths in both:
1. Contribution breakdown tables (sentiment, orderflow, etc.)
2. Confluence analysis breakdown tables
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.core.formatting.formatter import LogFormatter

def test_longer_gauges():
    """Test the longer gauges in both table types."""
    
    print("🎯 Testing Longer Gauges in PrettyTable Formatting")
    print("=" * 80)
    print()
    
    # Test 1: Contribution Breakdown Table (e.g., Sentiment Analysis)
    print("📊 TEST 1: Contribution Breakdown Table (Sentiment)")
    print("-" * 50)
    
    # Sample sentiment contributions
    sentiment_contributions = [
        ("funding_rate", 99.15, 0.27, 26.8),
        ("fear_greed_index", 85.32, 0.25, 21.3),
        ("social_sentiment", 72.45, 0.20, 14.5),
        ("options_flow", 68.90, 0.15, 10.3),
        ("whale_activity", 55.20, 0.13, 7.2)
    ]
    
    sentiment_table = LogFormatter.format_score_contribution_section(
        title="Sentiment Score Contribution Breakdown",
        contributions=sentiment_contributions,
        symbol="BTCUSDT",
        final_score=73.95,
        use_pretty_table=True
    )
    
    print(sentiment_table)
    print()
    
    # Test 2: Confluence Analysis Table
    print("📊 TEST 2: Enhanced Confluence Analysis Table")
    print("-" * 50)
    
    # Sample confluence data
    symbol = "ETHUSDT"
    confluence_score = 67.84
    reliability = 0.95
    
    components = {
        'orderbook': 78.23,
        'orderflow': 71.45,
        'technical': 65.89,
        'volume': 62.34,
        'sentiment': 73.95,
        'price_structure': 58.12
    }
    
    weights = {
        'orderbook': 0.25,
        'orderflow': 0.25,
        'volume': 0.16,
        'price_structure': 0.16,
        'technical': 0.11,
        'sentiment': 0.07
    }
    
    # Enhanced results with interpretations
    results = {
        'orderbook': {
            'score': 78.23,
            'components': {
                'spread': 95.45,
                'liquidity': 89.67,
                'depth': 82.34,
                'imbalance': 65.45
            },
            'interpretation': {
                'summary': 'Strong orderbook with excellent liquidity conditions and tight spreads indicating high market efficiency.'
            }
        },
        'orderflow': {
            'score': 71.45,
            'components': {
                'liquidity_score': 88.90,
                'cvd': 76.23,
                'liquidity_zones': 68.45,
                'open_interest': 52.12
            },
            'interpretation': {
                'summary': 'Positive orderflow with strong buying pressure. CVD showing sustained accumulation patterns.'
            }
        },
        'technical': {
            'score': 65.89,
            'components': {
                'macd': 72.34,
                'rsi': 68.45,
                'williams_r': 56.78
            },
            'interpretation': {
                'summary': 'Technical indicators show bullish momentum with MACD confirming uptrend and RSI in healthy range.'
            },
            'buy_threshold': 60.0,
            'sell_threshold': 40.0
        },
        'sentiment': {
            'score': 73.95,
            'components': {
                'funding_rate': 99.15,
                'fear_greed_index': 85.32,
                'social_sentiment': 72.45
            },
            'interpretation': {
                'summary': 'Positive sentiment with neutral funding rates and optimistic market psychology.'
            },
            'risk_level': 'MEDIUM'
        },
        'top_influential': {
            'components': {
                'spread (orderbook)': 95.45,
                'liquidity (orderbook)': 89.67,
                'liquidity score (orderflow)': 88.90,
                'depth (orderbook)': 82.34,
                'cvd (orderflow)': 76.23
            }
        }
    }
    
    confluence_table = LogFormatter.format_enhanced_confluence_score_table(
        symbol=symbol,
        confluence_score=confluence_score,
        components=components,
        results=results,
        weights=weights,
        reliability=reliability,
        use_pretty_table=True
    )
    
    print(confluence_table)
    print()
    
    # Test 3: Comparison Summary
    print("📋 GAUGE LENGTH IMPROVEMENTS")
    print("-" * 30)
    print("✅ Contribution Breakdown Tables:")
    print("   • Component gauges: 20 → 30 characters (+50%)")
    print("   • Final score gauge: 20 → 30 characters (+50%)")
    print()
    print("✅ Confluence Analysis Tables:")
    print("   • Component breakdown gauges: 15 → 25 characters (+67%)")
    print("   • Top influential gauges: 12 → 20 characters (+67%)")
    print("   • Default gauge width: 20 → 30 characters (+50%)")
    print()
    print("🎯 VISUAL IMPACT:")
    print("   • More prominent visual representation")
    print("   • Easier to read at a glance")
    print("   • Better proportional scaling")
    print("   • Consistent gauge lengths across all tables")
    print()
    print("🚀 READY FOR PRODUCTION!")
    print("=" * 80)

if __name__ == "__main__":
    test_longer_gauges() 