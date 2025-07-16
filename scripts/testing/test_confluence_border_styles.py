#!/usr/bin/env python3
"""
Test script to demonstrate different border styles for confluence tables.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.formatting.formatter import PrettyTableFormatter, LogFormatter

def test_border_styles():
    """Test different border styles for confluence tables."""
    
    print("Testing Confluence Table Border Styles")
    print("=" * 80)
    
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
    
    border_styles = [
        ("default", "DEFAULT BORDER STYLE"),
        ("single", "SINGLE BORDER STYLE"),
        ("double", "DOUBLE BORDER STYLE"),
        ("markdown", "MARKDOWN BORDER STYLE")
    ]
    
    # Test basic confluence table with different border styles
    print("\n" + "🔸" * 40)
    print("BASIC CONFLUENCE TABLE - BORDER STYLES")
    print("🔸" * 40)
    
    for border_style, title in border_styles:
        print(f"\n{'═' * 20} {title} {'═' * 20}")
        
        try:
            formatted_output = PrettyTableFormatter.format_confluence_score_table(
                symbol=symbol,
                confluence_score=confluence_score,
                components=components,
                results=results,
                weights=weights,
                reliability=0.85,
                border_style=border_style
            )
            print(formatted_output)
        except Exception as e:
            print(f"Error with {border_style} border style: {e}")
    
    # Test enhanced confluence table with different border styles
    print("\n\n" + "🔹" * 40)
    print("ENHANCED CONFLUENCE TABLE - BORDER STYLES")
    print("🔹" * 40)
    
    for border_style, title in border_styles:
        print(f"\n{'═' * 20} {title} {'═' * 20}")
        
        try:
            enhanced_formatted_output = PrettyTableFormatter.format_enhanced_confluence_score_table(
                symbol=symbol,
                confluence_score=confluence_score,
                components=components,
                results=results,
                weights=weights,
                reliability=0.85,
                border_style=border_style
            )
            print(enhanced_formatted_output)
        except Exception as e:
            print(f"Error with {border_style} border style: {e}")
    
    # Test LogFormatter integration with border styles
    print("\n\n" + "🔶" * 40)
    print("LOGFORMATTER INTEGRATION - BORDER STYLES")
    print("🔶" * 40)
    
    print(f"\n{'═' * 20} LOGFORMATTER WITH DOUBLE BORDERS {'═' * 20}")
    
    try:
        logformatter_output = LogFormatter.format_enhanced_confluence_score_table(
            symbol=symbol,
            confluence_score=confluence_score,
            components=components,
            results=results,
            weights=weights,
            reliability=0.85,
            use_pretty_table=True,
            border_style="double"
        )
        print(logformatter_output)
    except Exception as e:
        print(f"Error with LogFormatter: {e}")
    
    print(f"\n{'═' * 20} LOGFORMATTER WITH SINGLE BORDERS {'═' * 20}")
    
    try:
        logformatter_output = LogFormatter.format_confluence_score_table(
            symbol=symbol,
            confluence_score=confluence_score,
            components=components,
            results=results,
            weights=weights,
            reliability=0.85,
            use_pretty_table=True,
            border_style="single"
        )
        print(logformatter_output)
    except Exception as e:
        print(f"Error with LogFormatter: {e}")
    
    print("\n" + "✅" * 40)
    print("BORDER STYLES TEST COMPLETED!")
    print("✅" * 40)
    
    print(f"""
Summary of Available Border Styles:
• DEFAULT: Standard ASCII borders (+, -, |)
• SINGLE: Unicode single-line borders (┌, ─, ┐, ├, ┤, etc.)
• DOUBLE: Unicode double-line borders (╔, ═, ╗, ╠, ╣, etc.)
• MARKDOWN: Markdown-compatible table format

Usage Examples:
- Basic table: PrettyTableFormatter.format_confluence_score_table(..., border_style="single")
- Enhanced table: PrettyTableFormatter.format_enhanced_confluence_score_table(..., border_style="double")
- LogFormatter: LogFormatter.format_enhanced_confluence_score_table(..., border_style="double")
""")

if __name__ == "__main__":
    test_border_styles() 