#!/usr/bin/env python3
"""
Test script to demonstrate PrettyTable formatting for confluence analysis tables.

This script shows the difference between the old box-drawing character tables
and the new clean PrettyTable formatting.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.formatting.formatter import LogFormatter, PrettyTableFormatter

def create_sample_data():
    """Create sample data for testing table formatting."""
    
    # Sample components data
    components = {
        'orderflow': 57.63,
        'orderbook': 40.50,
        'price_structure': 54.87,
        'volume': 42.85,
        'sentiment': 73.95,
        'technical': 45.17
    }
    
    # Sample results data
    results = {
        'orderflow': {
            'score': 57.63,
            'interpretation': 'Neutral orderflow with slight buying bias. Rising open interest confirms trend strength.',
            'components': {
                'liquidity_score': 83.33,
                'open_interest_score': 69.48,
                'liquidity_zones': 67.27
            }
        },
        'orderbook': {
            'score': 40.50,
            'interpretation': 'Orderbook shows extreme ask-side dominance with high ask-side liquidity.',
            'components': {
                'liquidity': 70.20,
                'depth': 68.58,
                'spread': 45.30
            }
        },
        'sentiment': {
            'score': 73.95,
            'interpretation': 'Strongly bullish market sentiment with high risk conditions.',
            'components': {
                'funding_rate': 85.20,
                'market_activity': 78.45,
                'volatility': 62.30
            }
        },
        'top_influential': {
            'components': {
                'liquidity_score': 83.33,
                'liquidity': 70.20,
                'open_interest_score': 69.48,
                'depth': 68.58,
                'liquidity_zones': 67.27
            }
        }
    }
    
    # Sample weights
    weights = {
        'orderflow': 0.25,
        'orderbook': 0.20,
        'price_structure': 0.15,
        'volume': 0.15,
        'sentiment': 0.15,
        'technical': 0.10
    }
    
    return components, results, weights

def test_formatting():
    """Test both old and new formatting approaches."""
    
    print("=" * 100)
    print("PRETTYTABLE FORMATTING TEST")
    print("=" * 100)
    
    # Create sample data
    components, results, weights = create_sample_data()
    
    symbol = "HYPERUSDT"
    confluence_score = 50.32
    reliability = 1.0
    
    print("\n" + "=" * 50)
    print("1. ORIGINAL BOX-DRAWING CHARACTER TABLE")
    print("=" * 50)
    
    # Test original formatting
    original_table = LogFormatter.format_confluence_score_table(
        symbol=symbol,
        confluence_score=confluence_score,
        components=components,
        results=results,
        weights=weights,
        reliability=reliability,
        use_pretty_table=False
    )
    print(original_table)
    
    print("\n" + "=" * 50)
    print("2. NEW PRETTYTABLE FORMATTING")
    print("=" * 50)
    
    # Test new PrettyTable formatting
    try:
        pretty_table = PrettyTableFormatter.format_confluence_score_table(
            symbol=symbol,
            confluence_score=confluence_score,
            components=components,
            results=results,
            weights=weights,
            reliability=reliability
        )
        print(pretty_table)
    except Exception as e:
        print(f"Error with PrettyTable formatting: {e}")
        print("This might be because PrettyTable is not installed yet.")
        print("Run: pip install prettytable>=3.9.0")
    
    print("\n" + "=" * 50)
    print("3. ENHANCED FORMATTER WITH PRETTYTABLE")
    print("=" * 50)
    
    # Test enhanced formatter with PrettyTable
    try:
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
    except Exception as e:
        print(f"Error with enhanced PrettyTable formatting: {e}")
        print("This might be because PrettyTable is not installed yet.")
        print("Run: pip install prettytable>=3.9.0")

if __name__ == "__main__":
    test_formatting() 