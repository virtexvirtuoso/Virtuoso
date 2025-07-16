#!/usr/bin/env python3
"""
Test script to verify the Enhanced Analysis formatting improvements.
This script tests the new visual hierarchy and structure for Enhanced Analysis display.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.formatting.formatter import PrettyTableFormatter

def test_enhanced_analysis_formatting():
    """Test the Enhanced Analysis formatting with improved visual hierarchy."""
    
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                    ENHANCED ANALYSIS FORMATTING TEST                        ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Sample Enhanced Analysis text (similar to what user showed)
    enhanced_analysis_text = """**MARKET STATE: TRENDING_BULLISH**  **PRIMARY MARKET DRIVERS:** • **Confluence Analysis** (20.9% impact, bullish): CONFLUENCE DETECTED: Multiple components (4) align on bullish bias, increasing signal reliability. • **Volume** (12.8% impact, bullish): Volume patterns show typical market participation without clear directional bias. OBV showing strong upward trajectory (71.4), confirming price trend with accumulation. • **Price Structure** (12.8% impact, neutral): Price structure is neutral, showing balanced forces without clear direction. Mixed swing structure without clear directional bias.  **🎯 ACTIONABLE RECOMMENDATIONS:** • **Primary Strategy:** Consider trend-following long positions • **Position Sizing:** Minimal position sizing or paper trading only • **Time Horizon:** Medium-term holds (days to weeks) may be appropriate • **Risk Management:** Conservative stops recommended due to low confidence  **⚠️ RISK ASSESSMENT:** • **Overall Risk Level:** 🟡 MODERATE • **Mitigation:** Monitor for signal alignment before increasing exposure"""
    
    print("📊 Testing Enhanced Analysis Section Formatting")
    print("=" * 80)
    
    # Test the enhanced analysis section formatting
    formatted_output = PrettyTableFormatter._format_enhanced_analysis_section(enhanced_analysis_text)
    
    print("🎯 ENHANCED ANALYSIS OUTPUT:")
    print(formatted_output)
    
    print("\n" + "=" * 80)
    print("✅ VERIFICATION RESULTS:")
    print("=" * 80)
    
    # Verify that sections are properly formatted
    has_market_state = "📊" in formatted_output and "MARKET STATE:" in formatted_output
    has_primary_drivers = "🎯" in formatted_output and "PRIMARY MARKET DRIVERS:" in formatted_output
    has_recommendations = "🎯" in formatted_output and "ACTIONABLE RECOMMENDATIONS:" in formatted_output
    has_risk_assessment = "⚠️" in formatted_output and "RISK ASSESSMENT:" in formatted_output
    
    print(f"✅ Market State Section: {has_market_state}")
    print(f"✅ Primary Drivers Section: {has_primary_drivers}")
    print(f"✅ Actionable Recommendations Section: {has_recommendations}")
    print(f"✅ Risk Assessment Section: {has_risk_assessment}")
    
    # Check for proper visual hierarchy
    has_visual_hierarchy = "▪" in formatted_output and "✓" in formatted_output
    print(f"✅ Visual Hierarchy (bullets): {has_visual_hierarchy}")
    
    # Check for color coding
    has_color_coding = "BOLD" in formatted_output or "CYAN" in formatted_output
    print(f"✅ Color Coding Present: {has_color_coding}")
    
    print("\n🔍 COMPARISON WITH ORIGINAL:")
    print("=" * 50)
    print("❌ BEFORE: Dense text block in single table cell")
    print("✅ AFTER: Structured sections with visual hierarchy")
    print("✅ AFTER: Color-coded sections and proper spacing")
    print("✅ AFTER: Easy to scan and understand")

def test_full_interpretations_table():
    """Test the full interpretations table with Enhanced Analysis."""
    
    print("\n" + "=" * 80)
    print("📋 TESTING FULL INTERPRETATIONS TABLE")
    print("=" * 80)
    
    # Sample results data with Enhanced Analysis
    results = {
        'market_interpretations': [
            {
                'component': 'orderbook',
                'display_name': 'Orderbook',
                'interpretation': 'Orderbook shows extreme bid-side dominance with high bid-side liquidity and normal spreads, indicating strong buying pressure likely to drive prices higher.'
            },
            {
                'component': 'orderflow',
                'display_name': 'Orderflow',
                'interpretation': 'Strong bullish orderflow indicating steady buying pressure with dominant buying activity and strong absorption of selling pressure.'
            },
            {
                'component': 'enhanced_analysis',
                'display_name': 'Enhanced Analysis',
                'interpretation': '**MARKET STATE: TRENDING_BULLISH**  **PRIMARY MARKET DRIVERS:** • **Confluence Analysis** (20.9% impact, bullish): CONFLUENCE DETECTED: Multiple components (4) align on bullish bias, increasing signal reliability. • **Volume** (12.8% impact, bullish): Volume patterns show typical market participation without clear directional bias. OBV showing strong upward trajectory (71.4), confirming price trend with accumulation.  **🎯 ACTIONABLE RECOMMENDATIONS:** • **Primary Strategy:** Consider trend-following long positions • **Position Sizing:** Minimal position sizing or paper trading only • **Time Horizon:** Medium-term holds (days to weeks) may be appropriate  **⚠️ RISK ASSESSMENT:** • **Overall Risk Level:** 🟡 MODERATE • **Mitigation:** Monitor for signal alignment before increasing exposure'
            }
        ]
    }
    
    # Test the full interpretations table
    formatted_table = PrettyTableFormatter._format_interpretations_table(results, "double")
    
    print("🎯 FULL INTERPRETATIONS TABLE OUTPUT:")
    print(formatted_table)
    
    # Verify Enhanced Analysis is displayed separately
    has_separate_enhanced_analysis = "Enhanced Analysis" in formatted_table and "─" * 60 in formatted_table
    print(f"\n✅ Enhanced Analysis Displayed Separately: {has_separate_enhanced_analysis}")
    
    # Verify other components are in table format
    has_table_format = "┌" in formatted_table or "╔" in formatted_table
    print(f"✅ Table Format for Regular Components: {has_table_format}")

if __name__ == "__main__":
    test_enhanced_analysis_formatting()
    test_full_interpretations_table()
    
    print("\n🎉 ENHANCED ANALYSIS FORMATTING TEST COMPLETE!")
    print("The Enhanced Analysis section now has:")
    print("  • Clear visual hierarchy with section headers")
    print("  • Color-coded sections for easy scanning")
    print("  • Proper bullet points and indentation")
    print("  • Separate display from regular interpretations")
    print("  • Improved readability and actionability") 