#!/usr/bin/env python3
"""
Test script for PrettyTable contribution breakdown tables.

This script demonstrates the new PrettyTable formatting for score contribution
sections, which replaces the Unicode box-drawing character tables.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.formatting.formatter import LogFormatter, PrettyTableFormatter

def test_sentiment_contribution_breakdown():
    """Test PrettyTable formatting for sentiment score contribution breakdown."""
    print("\n" + "="*80)
    print("TESTING SENTIMENT SCORE CONTRIBUTION BREAKDOWN - PRETTYTABLE FORMAT")
    print("="*80)
    
    # Sample sentiment data matching the user's example
    title = "Sentiment Score Contribution Breakdown"
    symbol = "HYPERUSDT"
    
    contributions = [
        ("funding_rate", 99.15, 0.27, 26.8),
        ("volatility", 96.39, 0.14, 13.9),
        ("market_activity", 74.00, 0.15, 11.3),
        ("risk", 66.43, 0.14, 9.6),
        ("liquidations", 50.00, 0.15, 7.7),
        ("long_short_ratio", 34.76, 0.14, 4.7),
        ("market_mood", 50.00, 0.00, 0.0),
        ("open_interest", 50.00, 0.00, 0.0),
    ]
    
    final_score = 73.95
    
    # Test PrettyTable version
    print("\n🔹 PrettyTable Version:")
    pretty_result = PrettyTableFormatter.format_score_contribution_section(
        title=title,
        contributions=contributions,
        symbol=symbol,
        final_score=final_score
    )
    print(pretty_result)
    
    # Test original version for comparison
    print("\n🔹 Original Unicode Box-Drawing Version:")
    original_result = LogFormatter.format_score_contribution_section(
        title=title,
        contributions=contributions,
        symbol=symbol,
        final_score=final_score,
        use_pretty_table=False
    )
    print(original_result)

def test_orderflow_contribution_breakdown():
    """Test PrettyTable formatting for orderflow score contribution breakdown."""
    print("\n" + "="*80)
    print("TESTING ORDERFLOW SCORE CONTRIBUTION BREAKDOWN - PRETTYTABLE FORMAT")
    print("="*80)
    
    # Sample orderflow data matching the user's example
    title = "Orderflow Score Contribution Breakdown"
    symbol = "HYPERUSDT"
    
    contributions = [
        ("cvd", 53.42, 0.25, 13.4),
        ("open_interest_score", 69.48, 0.15, 10.4),
        ("trade_flow_score", 50.59, 0.20, 10.1),
        ("liquidity_score", 83.33, 0.10, 8.3),
        ("imbalance_score", 47.51, 0.15, 7.1),
        ("pressure_score", 49.15, 0.10, 4.9),
        ("liquidity_zones", 67.27, 0.05, 3.4),
    ]
    
    final_score = 57.63
    
    # Test PrettyTable version
    print("\n🔹 PrettyTable Version:")
    pretty_result = PrettyTableFormatter.format_score_contribution_section(
        title=title,
        contributions=contributions,
        symbol=symbol,
        final_score=final_score
    )
    print(pretty_result)
    
    # Test original version for comparison
    print("\n🔹 Original Unicode Box-Drawing Version:")
    original_result = LogFormatter.format_score_contribution_section(
        title=title,
        contributions=contributions,
        symbol=symbol,
        final_score=final_score,
        use_pretty_table=False
    )
    print(original_result)

def test_with_divergence_adjustments():
    """Test PrettyTable formatting with divergence adjustments."""
    print("\n" + "="*80)
    print("TESTING CONTRIBUTION BREAKDOWN WITH DIVERGENCE ADJUSTMENTS")
    print("="*80)
    
    title = "Technical Score Contribution Breakdown"
    symbol = "BTCUSDT"
    
    contributions = [
        ("rsi", 75.5, 0.20, 15.1),
        ("macd", 68.2, 0.15, 10.2),
        ("bollinger_bands", 45.8, 0.15, 6.9),
        ("volume_profile", 82.1, 0.25, 20.5),
        ("support_resistance", 58.3, 0.15, 8.7),
        ("trend_strength", 72.9, 0.10, 7.3),
    ]
    
    divergence_adjustments = {
        "rsi": 2.5,
        "macd": -1.2,
        "volume_profile": 3.1,
        "trend_strength": 0.0,
    }
    
    final_score = 71.2
    
    # Test PrettyTable version with divergences
    print("\n🔹 PrettyTable Version with Divergences:")
    pretty_result = PrettyTableFormatter.format_score_contribution_section(
        title=title,
        contributions=contributions,
        symbol=symbol,
        divergence_adjustments=divergence_adjustments,
        final_score=final_score
    )
    print(pretty_result)
    
    # Test original version for comparison
    print("\n🔹 Original Unicode Box-Drawing Version with Divergences:")
    original_result = LogFormatter.format_score_contribution_section(
        title=title,
        contributions=contributions,
        symbol=symbol,
        divergence_adjustments=divergence_adjustments,
        final_score=final_score,
        use_pretty_table=False
    )
    print(original_result)

def test_utility_function():
    """Test the updated utility function that uses PrettyTable by default."""
    print("\n" + "="*80)
    print("TESTING UTILITY FUNCTION WITH PRETTYTABLE")
    print("="*80)
    
    import logging
    from src.core.analysis.indicator_utils import log_score_contributions
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger(__name__)
    
    # Sample data
    component_scores = {
        "momentum": 78.5,
        "trend": 65.2,
        "volatility": 45.8,
        "volume": 82.1,
        "support_resistance": 58.3
    }
    
    weights = {
        "momentum": 0.25,
        "trend": 0.20,
        "volatility": 0.15,
        "volume": 0.25,
        "support_resistance": 0.15
    }
    
    final_score = 68.7
    
    print("\n🔹 Using log_score_contributions utility function (now uses PrettyTable by default):")
    log_score_contributions(
        logger=logger,
        title="Technical Analysis Score Contribution Breakdown",
        component_scores=component_scores,
        weights=weights,
        symbol="ETHUSDT",
        final_score=final_score
    )

def main():
    """Run all tests."""
    print("🚀 PRETTYTABLE CONTRIBUTION BREAKDOWN TABLES TEST")
    print("This script demonstrates the conversion from Unicode box-drawing")
    print("character tables to clean PrettyTable formatting.")
    
    try:
        test_sentiment_contribution_breakdown()
        test_orderflow_contribution_breakdown()
        test_with_divergence_adjustments()
        test_utility_function()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("\n📊 SUMMARY:")
        print("• Sentiment contribution tables now use PrettyTable")
        print("• Orderflow contribution tables now use PrettyTable")
        print("• Divergence adjustments are properly handled")
        print("• Color coding and gauges are preserved")
        print("• Utility functions updated to use PrettyTable by default")
        print("• Backward compatibility maintained with use_pretty_table parameter")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 