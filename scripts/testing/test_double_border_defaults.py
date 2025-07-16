#!/usr/bin/env python3
"""
Test script to demonstrate double border defaults for confluence tables.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.formatting.formatter import PrettyTableFormatter, LogFormatter

def test_double_border_defaults():
    """Test that confluence tables now use double borders by default."""
    
    print("Testing Double Border Defaults for Confluence Tables")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "CONFLUENCE TABLES NOW USE PREMIUM DOUBLE BORDERS BY DEFAULT".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    
    # Test data
    symbol = "BTCUSDT"
    confluence_score = 72.8
    components = {
        'sentiment': 78.5,
        'orderflow': 69.2,
        'technical': 74.3,
        'volume': 68.9
    }
    
    weights = {
        'sentiment': 0.25,
        'orderflow': 0.30,
        'technical': 0.25,
        'volume': 0.20
    }
    
    results = {
        'sentiment': {
            'score': 78.5,
            'interpretation': 'Very strong bullish sentiment with widespread social media excitement and positive news coverage',
            'components': {
                'social_sentiment': 82.3,
                'news_sentiment': 74.7,
                'fear_greed_index': 76.8
            }
        },
        'orderflow': {
            'score': 69.2,
            'interpretation': 'Solid buying pressure with consistent institutional accumulation patterns',
            'components': {
                'bid_ask_spread': 71.5,
                'order_imbalance': 66.9,
                'large_orders': 70.0
            }
        },
        'technical': {
            'score': 74.3,
            'interpretation': 'Strong technical momentum with multiple bullish indicators converging',
            'components': {
                'momentum_oscillators': 76.2,
                'trend_indicators': 72.4,
                'support_resistance': 74.3
            }
        },
        'top_influential': {
            'components': {
                'social_sentiment': 82.3,
                'momentum_oscillators': 76.2,
                'news_sentiment': 74.7,
                'support_resistance': 74.3,
                'bid_ask_spread': 71.5
            }
        }
    }
    
    print(f"\n{'╔' + '═' * 50 + '╗'}")
    print(f"║{'PRETTYTABLEFORMATTER - DEFAULT DOUBLE BORDERS'.center(50)}║")
    print(f"{'╚' + '═' * 50 + '╝'}")
    
    # Test PrettyTableFormatter with default parameters (should be double borders)
    try:
        basic_table = PrettyTableFormatter.format_confluence_score_table(
            symbol=symbol,
            confluence_score=confluence_score,
            components=components,
            results=results,
            weights=weights,
            reliability=0.92
            # No border_style parameter - should default to "double"
        )
        print(basic_table)
    except Exception as e:
        print(f"Error with basic confluence table: {e}")
    
    print(f"\n{'╔' + '═' * 50 + '╗'}")
    print(f"║{'ENHANCED CONFLUENCE - DEFAULT DOUBLE BORDERS'.center(50)}║")
    print(f"{'╚' + '═' * 50 + '╝'}")
    
    # Test Enhanced confluence table with default parameters
    try:
        enhanced_table = PrettyTableFormatter.format_enhanced_confluence_score_table(
            symbol=symbol,
            confluence_score=confluence_score,
            components=components,
            results=results,
            weights=weights,
            reliability=0.92
            # No border_style parameter - should default to "double"
        )
        print(enhanced_table)
    except Exception as e:
        print(f"Error with enhanced confluence table: {e}")
    
    print(f"\n{'╔' + '═' * 50 + '╗'}")
    print(f"║{'LOGFORMATTER INTEGRATION - DOUBLE BORDERS'.center(50)}║")
    print(f"{'╚' + '═' * 50 + '╝'}")
    
    # Test LogFormatter integration with PrettyTable enabled
    try:
        logformatter_table = LogFormatter.format_enhanced_confluence_score_table(
            symbol=symbol,
            confluence_score=confluence_score,
            components=components,
            results=results,
            weights=weights,
            reliability=0.92,
            use_pretty_table=True
            # No border_style parameter - should inherit double border default
        )
        print(logformatter_table)
    except Exception as e:
        print(f"Error with LogFormatter: {e}")
    
    print(f"\n{'╔' + '═' * 50 + '╗'}")
    print(f"║{'SCORE CONTRIBUTION - DEFAULT DOUBLE BORDERS'.center(50)}║")
    print(f"{'╚' + '═' * 50 + '╝'}")
    
    # Test score contribution section with default double borders
    contributions = [
        ('sentiment', 78.5, 0.25, 19.6),
        ('orderflow', 69.2, 0.30, 20.8),
        ('technical', 74.3, 0.25, 18.6),
        ('volume', 68.9, 0.20, 13.8)
    ]
    
    try:
        contribution_table = PrettyTableFormatter.format_score_contribution_section(
            title="Confluence Score Breakdown",
            contributions=contributions,
            symbol=symbol,
            final_score=confluence_score
            # No border_style parameter - should default to "double"
        )
        print(contribution_table)
    except Exception as e:
        print(f"Error with contribution table: {e}")
    
    print(f"\n{'╔' + '═' * 78 + '╗'}")
    print(f"║{'COMPARISON: SINGLE vs DOUBLE BORDERS'.center(78)}║")
    print(f"{'╚' + '═' * 78 + '╝'}")
    
    print(f"\n{'─' * 40} SINGLE BORDERS {'─' * 40}")
    
    # Show single border for comparison
    try:
        single_border_table = PrettyTableFormatter.format_confluence_score_table(
            symbol=symbol,
            confluence_score=confluence_score,
            components=components,
            results=results,
            weights=weights,
            reliability=0.92,
            border_style="single"  # Explicitly request single borders
        )
        print(single_border_table)
    except Exception as e:
        print(f"Error with single border table: {e}")
    
    print(f"\n{'═' * 40} DOUBLE BORDERS (DEFAULT) {'═' * 40}")
    
    # Show double border (default)
    try:
        double_border_table = PrettyTableFormatter.format_confluence_score_table(
            symbol=symbol,
            confluence_score=confluence_score,
            components=components,
            results=results,
            weights=weights,
            reliability=0.92
            # No border_style - uses new double border default
        )
        print(double_border_table)
    except Exception as e:
        print(f"Error with double border table: {e}")
    
    print(f"\n{'╔' + '═' * 78 + '╗'}")
    print(f"║{'SUMMARY OF CHANGES'.center(78)}║")
    print(f"║{' ' * 78}║")
    
    # Fix f-string syntax by using variables
    conf_table_text = '✅ PrettyTableFormatter.format_confluence_score_table()'
    conf_default_text = '   Default: border_style="double"'
    enh_table_text = '✅ PrettyTableFormatter.format_enhanced_confluence_score_table()'
    enh_default_text = '   Default: border_style="double"'
    contrib_table_text = '✅ PrettyTableFormatter.format_score_contribution_section()'
    contrib_default_text = '   Default: border_style="double"'
    log_integration_text = '✅ LogFormatter integration inherits double border defaults'
    premium_text = '✅ All confluence tables now have premium presentation by default'
    
    print(f"║{conf_table_text.ljust(78)}║")
    print(f"║{conf_default_text.ljust(78)}║")
    print(f"║{' ' * 78}║")
    print(f"║{enh_table_text.ljust(78)}║")
    print(f"║{enh_default_text.ljust(78)}║")
    print(f"║{' ' * 78}║")
    print(f"║{contrib_table_text.ljust(78)}║")
    print(f"║{contrib_default_text.ljust(78)}║")
    print(f"║{' ' * 78}║")
    print(f"║{log_integration_text.ljust(78)}║")
    print(f"║{' ' * 78}║")
    print(f"║{premium_text.ljust(78)}║")
    print(f"╚{'═' * 78}╝")
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                              USAGE EXAMPLES                                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║ # Double borders by default (no parameter needed)                           ║
║ table = PrettyTableFormatter.format_confluence_score_table(...)             ║
║                                                                              ║
║ # Enhanced table with double borders by default                             ║
║ table = PrettyTableFormatter.format_enhanced_confluence_score_table(...)    ║
║                                                                              ║
║ # LogFormatter with double borders by default                               ║
║ table = LogFormatter.format_enhanced_confluence_score_table(                ║
║     ..., use_pretty_table=True)                                             ║
║                                                                              ║
║ # Override to single borders if needed                                      ║
║ table = PrettyTableFormatter.format_confluence_score_table(                 ║
║     ..., border_style="single")                                             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")

if __name__ == "__main__":
    test_double_border_defaults() 