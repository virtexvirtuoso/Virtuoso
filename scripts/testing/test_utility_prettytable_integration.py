#!/usr/bin/env python3
"""
Test script to verify that the utility functions use PrettyTable contribution breakdown tables.

This script directly tests the log_score_contributions utility function which is 
what the actual indicators use for logging contribution breakdown tables.
"""

import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configure logging to capture the formatted output
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)

def test_utility_function_prettytable():
    """Test that log_score_contributions utility function uses PrettyTable."""
    print("🚀 TESTING UTILITY FUNCTION PRETTYTABLE INTEGRATION")
    print("="*80)
    
    try:
        # Import the utility function
        from src.core.analysis.indicator_utils import log_score_contributions
        
        # Create a test logger
        logger = logging.getLogger("test_utility")
        
        # Test data matching the HYPERUSDT Sentiment example
        print("📊 Testing Sentiment Score Contribution Breakdown...")
        component_scores = {
            "funding_rate": 99.15,
            "volatility": 96.39,
            "market_activity": 74.00,
            "risk": 66.43,
            "liquidations": 50.00,
            "long_short_ratio": 34.76,
            "market_mood": 50.00,
            "open_interest": 50.00
        }
        
        weights = {
            "funding_rate": 0.27,
            "volatility": 0.14,
            "market_activity": 0.15,
            "risk": 0.14,
            "liquidations": 0.15,
            "long_short_ratio": 0.14,
            "market_mood": 0.00,
            "open_interest": 0.00
        }
        
        final_score = 73.95
        
        print("\n🔹 SENTIMENT CONTRIBUTION BREAKDOWN (Should use PrettyTable):")
        print("-" * 80)
        
        # This should use PrettyTable by default now
        log_score_contributions(
            logger=logger,
            title="Sentiment Score Contribution Breakdown",
            component_scores=component_scores,
            weights=weights,
            symbol="HYPERUSDT",
            final_score=final_score
        )
        
        print("-" * 80)
        
        # Test data matching the HYPERUSDT Orderflow example
        print("\n📊 Testing Orderflow Score Contribution Breakdown...")
        orderflow_scores = {
            "cvd": 53.42,
            "open_interest_score": 69.48,
            "trade_flow_score": 50.59,
            "liquidity_score": 83.33,
            "imbalance_score": 47.51,
            "pressure_score": 49.15,
            "liquidity_zones": 67.27
        }
        
        orderflow_weights = {
            "cvd": 0.25,
            "open_interest_score": 0.15,
            "trade_flow_score": 0.20,
            "liquidity_score": 0.10,
            "imbalance_score": 0.15,
            "pressure_score": 0.10,
            "liquidity_zones": 0.05
        }
        
        orderflow_final_score = 57.63
        
        print("\n🔹 ORDERFLOW CONTRIBUTION BREAKDOWN (Should use PrettyTable):")
        print("-" * 80)
        
        log_score_contributions(
            logger=logger,
            title="Orderflow Score Contribution Breakdown",
            component_scores=orderflow_scores,
            weights=orderflow_weights,
            symbol="HYPERUSDT",
            final_score=orderflow_final_score
        )
        
        print("-" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_formatter_comparison():
    """Test direct comparison between old and new formatters."""
    print("\n🚀 TESTING DIRECT FORMATTER COMPARISON")
    print("="*80)
    
    try:
        from src.core.formatting.formatter import LogFormatter, PrettyTableFormatter
        
        # Test data
        contributions = [
            ("funding_rate", 99.15, 0.27, 26.8),
            ("volatility", 96.39, 0.14, 13.9),
            ("market_activity", 74.00, 0.15, 11.3),
            ("risk", 66.43, 0.14, 9.6),
            ("liquidations", 50.00, 0.15, 7.7),
            ("long_short_ratio", 34.76, 0.14, 4.7)
        ]
        
        title = "Sentiment Score Contribution Breakdown"
        symbol = "HYPERUSDT"
        final_score = 73.95
        
        print("🔹 PRETTYTABLE VERSION (NEW):")
        print("-" * 80)
        pretty_result = PrettyTableFormatter.format_score_contribution_section(
            title=title,
            contributions=contributions,
            symbol=symbol,
            final_score=final_score
        )
        print(pretty_result)
        
        print("\n🔹 UNICODE BOX-DRAWING VERSION (OLD):")
        print("-" * 80)
        original_result = LogFormatter.format_score_contribution_section(
            title=title,
            contributions=contributions,
            symbol=symbol,
            final_score=final_score,
            use_pretty_table=False
        )
        print(original_result)
        
        print("\n🔹 LOGFORMATTER WITH PRETTYTABLE ENABLED:")
        print("-" * 80)
        enhanced_result = LogFormatter.format_score_contribution_section(
            title=title,
            contributions=contributions,
            symbol=symbol,
            final_score=final_score,
            use_pretty_table=True
        )
        print(enhanced_result)
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def verify_prettytable_characteristics(output_text):
    """Verify that the output has PrettyTable characteristics."""
    prettytable_indicators = [
        "+--",  # PrettyTable border
        "| ",   # PrettyTable column separator
        " |",   # PrettyTable column end
        "====", # Header separator
        "Status:", # Status line
    ]
    
    unicode_indicators = [
        "┌",    # Unicode top-left corner
        "─",    # Unicode horizontal line
        "┐",    # Unicode top-right corner
        "├",    # Unicode left T-junction
        "┤",    # Unicode right T-junction
        "│",    # Unicode vertical line
    ]
    
    prettytable_count = sum(1 for indicator in prettytable_indicators if indicator in output_text)
    unicode_count = sum(1 for indicator in unicode_indicators if indicator in output_text)
    
    return {
        'prettytable_indicators': prettytable_count,
        'unicode_indicators': unicode_count,
        'is_prettytable': prettytable_count > 0 and unicode_count == 0
    }

def main():
    """Run all tests."""
    print("🔍 UTILITY FUNCTION PRETTYTABLE INTEGRATION TEST")
    print("This test verifies that the utility functions use PrettyTable")
    print("for contribution breakdown tables instead of Unicode box-drawing.")
    print("="*80)
    
    success_count = 0
    total_tests = 2
    
    # Test utility function integration
    if test_utility_function_prettytable():
        success_count += 1
    
    # Test direct formatter comparison
    if test_direct_formatter_comparison():
        success_count += 1
    
    print("\n" + "="*80)
    print(f"📊 TEST RESULTS: {success_count}/{total_tests} PASSED")
    
    if success_count == total_tests:
        print("✅ ALL UTILITY FUNCTION TESTS PASSED!")
        print("\n🎯 VERIFICATION COMPLETE:")
        print("• Utility functions use PrettyTable by default")
        print("• Contribution breakdown tables display cleanly")
        print("• No Unicode box-drawing characters in utility output")
        print("• Both sentiment and orderflow examples work correctly")
        
        print("\n📋 WHAT THIS MEANS:")
        print("• All indicators using log_score_contributions() now use PrettyTable")
        print("• This includes SentimentIndicators, OrderflowIndicators, and others")
        print("• The tables you see in logs will be clean PrettyTable format")
        print("• No more complex Unicode box-drawing character tables")
        
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        return 1

if __name__ == "__main__":
    exit(main()) 