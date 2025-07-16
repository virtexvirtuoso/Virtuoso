#!/usr/bin/env python3
"""
Test script to verify visual consistency of table borders:
- Double borders for confluence breakdown only
- Single borders for all other component score contribution breakdowns

This ensures clear visual hierarchy as requested by the user.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.formatting.formatter import LogFormatter, PrettyTableFormatter
from src.core.analysis.indicator_utils import log_score_contributions
import logging

def setup_test_logger():
    """Set up a logger for testing purposes."""
    logger = logging.getLogger('test_visual_consistency')
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger

def test_visual_consistency():
    """Test visual consistency of border styles across different table types."""
    
    print("🔍 VISUAL CONSISTENCY TEST - TABLE BORDER STYLES")
    print("=" * 80)
    print("Testing the visual hierarchy:")
    print("• Double borders (╔══╗) = Confluence breakdown only")
    print("• Single borders (┌──┐) = All other component score contribution breakdowns")
    print("=" * 80)
    
    # Test data
    symbol = "BTCUSDT"
    confluence_score = 68.5
    
    # Confluence components
    confluence_components = {
        'sentiment': 72.3,
        'orderflow': 65.8,
        'technical': 70.1,
        'volume': 64.2
    }
    
    confluence_weights = {
        'sentiment': 0.25,
        'orderflow': 0.30,
        'technical': 0.25,
        'volume': 0.20
    }
    
    # Individual component data
    sentiment_components = {
        'social_sentiment': 75.0,
        'news_sentiment': 69.6,
        'fear_greed_index': 72.8
    }
    
    sentiment_weights = {
        'social_sentiment': 0.40,
        'news_sentiment': 0.35,
        'fear_greed_index': 0.25
    }
    
    orderflow_components = {
        'cvd': 81.77,
        'trade_flow_score': 66.74,
        'imbalance_score': 69.69,
        'liquidity_score': 83.33
    }
    
    orderflow_weights = {
        'cvd': 0.25,
        'trade_flow_score': 0.20,
        'imbalance_score': 0.15,
        'liquidity_score': 0.10
    }
    
    # Mock results for confluence table
    confluence_results = {
        'sentiment': {
            'score': 72.3,
            'interpretation': 'Strong bullish sentiment detected',
            'components': sentiment_components
        },
        'orderflow': {
            'score': 65.8,
            'interpretation': 'Moderate buying pressure',
            'components': orderflow_components
        },
        'technical': {
            'score': 70.1,
            'interpretation': 'Technical indicators show bullish momentum',
            'components': {}
        },
        'volume': {
            'score': 64.2,
            'interpretation': 'Volume profile supports upward movement',
            'components': {}
        },
        'top_influential': {
            'components': {
                'social_sentiment': 75.0,
                'liquidity_score': 83.33,
                'cvd': 81.77,
                'technical_momentum': 71.2,
                'volume_profile': 69.8
            }
        }
    }
    
    print(f"\n{'🔸' * 40}")
    print("1. CONFLUENCE BREAKDOWN (Should use DOUBLE borders ╔══╗)")
    print(f"{'🔸' * 40}")
    
    try:
        confluence_table = LogFormatter.format_enhanced_confluence_score_table(
            symbol=symbol,
            confluence_score=confluence_score,
            components=confluence_components,
            results=confluence_results,
            weights=confluence_weights,
            reliability=0.85,
            use_pretty_table=True,
            border_style="double"  # Explicitly double for confluence
        )
        print(confluence_table)
    except Exception as e:
        print(f"❌ Error with confluence table: {e}")
    
    print(f"\n{'🔹' * 40}")
    print("2. SENTIMENT COMPONENT BREAKDOWN (Should use SINGLE borders ┌──┐)")
    print(f"{'🔹' * 40}")
    
    try:
        # Test individual component breakdown using the updated log_score_contributions
        logger = setup_test_logger()
        log_score_contributions(
            logger=logger,
            title="Sentiment Score Contribution Breakdown",
            component_scores=sentiment_components,
            weights=sentiment_weights,
            symbol=symbol,
            final_score=72.3
        )
    except Exception as e:
        print(f"❌ Error with sentiment breakdown: {e}")
    
    print(f"\n{'🔹' * 40}")
    print("3. ORDERFLOW COMPONENT BREAKDOWN (Should use SINGLE borders ┌──┐)")
    print(f"{'🔹' * 40}")
    
    try:
        # Test individual component breakdown using the updated log_score_contributions
        logger = setup_test_logger()
        log_score_contributions(
            logger=logger,
            title="Orderflow Score Contribution Breakdown",
            component_scores=orderflow_components,
            weights=orderflow_weights,
            symbol=symbol,
            final_score=65.8
        )
    except Exception as e:
        print(f"❌ Error with orderflow breakdown: {e}")
    
    print(f"\n{'🔶' * 40}")
    print("4. DIRECT PRETTYTABLEFORMATTER COMPARISON")
    print(f"{'🔶' * 40}")
    
    print("\n--- SINGLE BORDER STYLE (Individual Components) ---")
    
    try:
        # Create contributions for direct testing
        sentiment_contributions = []
        for component, score in sentiment_components.items():
            weight = sentiment_weights.get(component, 0)
            contribution = score * weight
            sentiment_contributions.append((component, score, weight, contribution))
        
        single_border_table = PrettyTableFormatter.format_score_contribution_section(
            title="Sentiment Score Contribution Breakdown",
            contributions=sentiment_contributions,
            symbol=symbol,
            final_score=72.3,
            border_style="single"  # Single borders for individual components
        )
        print(single_border_table)
    except Exception as e:
        print(f"❌ Error with single border table: {e}")
    
    print("\n--- DOUBLE BORDER STYLE (Confluence Only) ---")
    
    try:
        # Create contributions for direct testing
        confluence_contributions = []
        for component, score in confluence_components.items():
            weight = confluence_weights.get(component, 0)
            contribution = score * weight
            confluence_contributions.append((component, score, weight, contribution))
        
        double_border_table = PrettyTableFormatter.format_score_contribution_section(
            title="Confluence Score Contribution Breakdown",
            contributions=confluence_contributions,
            symbol=symbol,
            final_score=confluence_score,
            border_style="double"  # Double borders for confluence only
        )
        print(double_border_table)
    except Exception as e:
        print(f"❌ Error with double border table: {e}")
    
    print(f"\n{'✅' * 40}")
    print("VISUAL CONSISTENCY VERIFICATION")
    print(f"{'✅' * 40}")
    
    print("""
EXPECTED VISUAL HIERARCHY:

1. 🏆 CONFLUENCE BREAKDOWN (Most Important)
   ╔═══════════════════════════════════════════════════════════════════════════════╗
   ║ Double borders emphasize the main confluence analysis                         ║
   ╚═══════════════════════════════════════════════════════════════════════════════╝

2. 📊 INDIVIDUAL COMPONENT BREAKDOWNS (Supporting Details)
   ┌───────────────────────────────────────────────────────────────────────────────┐
   │ Single borders for supporting component analysis                              │
   └───────────────────────────────────────────────────────────────────────────────┘

BENEFITS:
• Clear visual hierarchy - confluence stands out as the primary analysis
• Consistent styling across all individual component breakdowns
• Professional appearance with appropriate emphasis levels
• Easy to scan and understand the relative importance of different sections

IMPLEMENTATION:
• LogFormatter.format_enhanced_confluence_score_table() → border_style="double"
• LogFormatter.format_score_contribution_section() → border_style="single" (default)
• Individual component breakdowns automatically use single borders
• Confluence breakdown explicitly uses double borders
""")

if __name__ == "__main__":
    test_visual_consistency() 