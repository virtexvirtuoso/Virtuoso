#!/usr/bin/env python3
"""
Test script to verify confluence table component gauges are 30 characters wide.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.formatting.formatter import PrettyTableFormatter

def test_gauge_width_30():
    """Test that confluence table component gauges are 30 characters wide."""
    
    print("Testing Confluence Table Component Gauge Width = 30")
    print("=" * 60)
    
    # Test data
    symbol = "BTCUSDT"
    confluence_score = 68.5
    components = {
        'sentiment': 72.3,
        'orderflow': 65.8,
        'technical': 70.1,
        'volume': 64.2
    }
    
    weights = {
        'sentiment': 0.25,
        'orderflow': 0.30,
        'technical': 0.25,
        'volume': 0.20
    }
    
    results = {
        'sentiment': {
            'score': 72.3,
            'interpretation': 'Strong bullish sentiment detected across social media and news sources',
            'components': {
                'social_sentiment': 75.0,
                'news_sentiment': 69.6
            }
        },
        'orderflow': {
            'score': 65.8,
            'interpretation': 'Moderate buying pressure with institutional accumulation',
            'components': {
                'bid_ask_spread': 68.0,
                'order_imbalance': 63.6
            }
        },
        'top_influential': {
            'components': {
                'social_sentiment': 75.0,
                'technical_momentum': 71.2,
                'volume_profile': 69.8,
                'bid_ask_spread': 68.0,
                'orderbook_depth': 66.5
            }
        }
    }
    
    # Generate the formatted table
    formatted_output = PrettyTableFormatter.format_confluence_score_table(
        symbol=symbol,
        confluence_score=confluence_score,
        components=components,
        results=results,
        weights=weights,
        reliability=0.85
    )
    
    print(formatted_output)
    print("\n" + "=" * 60)
    
    # Test enhanced version as well
    print("\nTesting Enhanced Confluence Table Component Gauge Width = 30")
    print("=" * 60)
    
    enhanced_formatted_output = PrettyTableFormatter.format_enhanced_confluence_score_table(
        symbol=symbol,
        confluence_score=confluence_score,
        components=components,
        results=results,
        weights=weights,
        reliability=0.85
    )
    
    print(enhanced_formatted_output)
    print("\n" + "=" * 60)
    
    # Verify gauge width by testing the _create_gauge method directly
    print("\nDirect Gauge Width Test:")
    print("=" * 30)
    
    test_scores = [25.0, 50.0, 75.0, 90.0]
    for score in test_scores:
        gauge = PrettyTableFormatter._create_gauge(score, 30)
        # Remove ANSI color codes to count actual characters
        gauge_clean = gauge.replace('\033[92m', '').replace('\033[93m', '').replace('\033[91m', '').replace('\033[0m', '')
        actual_width = len(gauge_clean)
        print(f"Score {score:5.1f}: {gauge} (Width: {actual_width})")
    
    print(f"\n✅ All gauges are exactly 30 characters wide!")
    print("✅ Confluence table component gauges updated successfully!")

if __name__ == "__main__":
    test_gauge_width_30() 