#!/usr/bin/env python3
"""
Test script to demonstrate PrettyTable optimizations for:
1. Top Influential Individual Components
2. Market Interpretations

This script shows the improvements in formatting and readability.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.formatting.formatter import PrettyTableFormatter

def create_mock_results():
    """Create comprehensive mock results to test PrettyTable formatting."""
    return {
        'top_influential': {
            'components': {
                'spread': 99.98,
                'liquidity': 99.72,
                'depth': 95.28,
                'liquidity_score': 83.33,
                'cvd': 75.80,
                'price_impact': 88.45,
                'support_resistance': 91.20
            }
        },
        'orderbook': {
            'score': 69.53,
            'components': {
                'spread': 99.98,
                'liquidity': 99.72,
                'depth': 95.28,
                'price_impact': 88.45,
                'support_resistance': 91.20
            },
            'interpretation': {
                'summary': 'Orderbook shows Strong bid-side dominance with high bid-side liquidity and tight spreads, suggesting buyers controlling price action, providing strong price support below current level, and indicating high market efficiency and low execution costs.'
            }
        },
        'orderflow': {
            'score': 68.00,
            'components': {
                'liquidity_score': 83.33,
                'cvd': 75.80,
                'trade_flow_score': 72.15,
                'imbalance_score': 68.90
            },
            'interpretation': {
                'summary': 'Strong bullish orderflow indicating steady buying pressure. Strong positive cumulative volume delta showing dominant buying activity. Large trades predominantly executed on the buy side with strong absorption of selling pressure.'
            }
        },
        'price_structure': {
            'score': 52.40,
            'components': {
                'vwap_relation': 61.3,
                'price_oscillation': 45.2,
                'equilibrium_distance': 48.7
            },
            'interpretation': {
                'summary': 'Price structure is neutral, showing balanced forces without clear directional bias. Price oscillating near VWAP indicating equilibrium between buyers and sellers.'
            }
        },
        'volume': {
            'score': 33.39,
            'components': {
                'volume_trend': 28.5,
                'volume_spike': 35.8,
                'volume_consistency': 31.2
            },
            'interpretation': {
                'summary': 'Volume patterns show typical market participation without clear directional bias, indicating neutral conditions or potential consolidation phase.'
            }
        },
        'technical': {
            'score': 39.76,
            'components': {
                'rsi': 42.8,
                'macd': 38.5,
                'momentum': 41.2
            },
            'interpretation': {
                'summary': 'Technical indicators show slight bearish bias within overall neutrality. MACD shows neutral trend conditions. RSI in neutral territory.'
            }
        },
        'sentiment': {
            'score': 59.45,
            'components': {
                'funding_rate': 62.3,
                'open_interest': 58.1,
                'volatility': 57.9
            },
            'interpretation': {
                'summary': 'Moderately bullish market sentiment with high risk conditions and neutral funding rates, suggesting potential for sharp reversals, indicating balanced buy/sell positioning.'
            }
        },
        'market_interpretations': [
            {
                'component': 'overall_analysis',
                'display_name': 'Overall Analysis',
                'interpretation': 'PENGUUSDT shows neutral sentiment with confluence score of 56.6. Price is in consolidation with no clear directional bias.'
            },
            {
                'component': 'technical',
                'display_name': 'Technical',
                'interpretation': 'Technical indicators show slight bearish bias within overall neutrality. MACD shows neutral trend conditions (50.0). RSI in neutral territory (42.8).'
            },
            {
                'component': 'volume',
                'display_name': 'Volume',
                'interpretation': 'Volume patterns show typical market participation without clear directional bias, indicating neutral conditions or potential consolidation phase.'
            },
            {
                'component': 'orderbook',
                'display_name': 'Orderbook',
                'interpretation': 'Orderbook shows Strong bid-side dominance with high bid-side liquidity and tight spreads, suggesting buyers controlling price action, providing strong price support below current level.'
            },
            {
                'component': 'orderflow',
                'display_name': 'Orderflow',
                'interpretation': 'Strong bullish orderflow indicating steady buying pressure. Strong positive cumulative volume delta showing dominant buying activity.'
            },
            {
                'component': 'sentiment',
                'display_name': 'Sentiment',
                'interpretation': 'Moderately bullish market sentiment with high risk conditions and neutral funding rates, suggesting potential for sharp reversals.'
            },
            {
                'component': 'price_structure',
                'display_name': 'Price Structure',
                'interpretation': 'Price structure is neutral, showing balanced forces without clear directional bias. Price oscillating near VWAP indicating equilibrium between buyers and sellers.'
            }
        ]
    }

def test_top_components_optimization():
    """Test the optimized Top Influential Individual Components with PrettyTable."""
    print("=" * 80)
    print("🚀 TESTING TOP INFLUENTIAL INDIVIDUAL COMPONENTS - PRETTYTABLE OPTIMIZATION")
    print("=" * 80)
    
    mock_results = create_mock_results()
    
    print("\n📊 BEFORE: Simple text formatting (current implementation)")
    print("-" * 60)
    
    # Show what the old implementation would look like
    top_components = PrettyTableFormatter._extract_top_components(mock_results)
    if top_components:
        print(f"{PrettyTableFormatter.BOLD}Top Influential Individual Components:{PrettyTableFormatter.RESET}")
        for comp_name, comp_score in top_components[:5]:
            gauge = PrettyTableFormatter._create_gauge(comp_score, 30)
            trend = PrettyTableFormatter._get_trend_indicator(comp_score)
            score_color = PrettyTableFormatter._get_score_color(comp_score)
            print(f"  • {comp_name:<35}: {score_color}{comp_score:>6.2f}{PrettyTableFormatter.RESET} {trend} {gauge}")
    
    print("\n✨ AFTER: PrettyTable optimization (new implementation)")
    print("-" * 60)
    
    # Show the optimized PrettyTable version
    optimized_table = PrettyTableFormatter._format_top_components_table(mock_results, "double")
    print(optimized_table)
    
    print("🎯 IMPROVEMENTS:")
    print("   ✓ Clean tabular format with proper column alignment")
    print("   ✓ Consistent spacing and borders")
    print("   ✓ Parent component information clearly displayed")
    print("   ✓ Better readability with structured layout")
    print("   ✓ Professional appearance")

def test_market_interpretations_optimization():
    """Test the optimized Market Interpretations with PrettyTable."""
    print("\n" + "=" * 80)
    print("🧠 TESTING MARKET INTERPRETATIONS - PRETTYTABLE OPTIMIZATION")
    print("=" * 80)
    
    mock_results = create_mock_results()
    
    print("\n📝 BEFORE: Manual border formatting (current implementation)")
    print("-" * 60)
    
    # Show what the old manual border implementation would look like
    enhanced_interpretations = PrettyTableFormatter._format_enhanced_interpretations(mock_results)
    if enhanced_interpretations:
        interpretation_width = 80
        top_border = "╔" + "═" * (interpretation_width - 2) + "╗"
        bottom_border = "╚" + "═" * (interpretation_width - 2) + "╝"
        side_border = "║"
        
        print(top_border)
        header = f"{PrettyTableFormatter.BOLD}Market Interpretations{PrettyTableFormatter.RESET}"
        header_padding = interpretation_width - len("Market Interpretations") - 4
        print(f"{side_border} {header}{' ' * header_padding} {side_border}")
        
        separator_line = "╠" + "═" * (interpretation_width - 2) + "╣"
        print(separator_line)
        
        for interpretation in enhanced_interpretations[:3]:  # Show first 3 for demo
            if interpretation.strip():
                max_content_width = interpretation_width - 4
                clean_interp = interpretation.strip()
                
                import textwrap
                wrapped_lines = textwrap.fill(clean_interp, width=max_content_width).split('\n')
                
                for line in wrapped_lines:
                    line_padding = max_content_width - len(line)
                    print(f"{side_border} {line}{' ' * line_padding} {side_border}")
        
        print(bottom_border)
    
    print("\n✨ AFTER: PrettyTable optimization (new implementation)")
    print("-" * 60)
    
    # Show the optimized PrettyTable version
    optimized_table = PrettyTableFormatter._format_interpretations_table(mock_results, "double")
    print(optimized_table)
    
    print("🎯 IMPROVEMENTS:")
    print("   ✓ Clean two-column table format")
    print("   ✓ Component names clearly separated from interpretations")
    print("   ✓ Automatic text wrapping within table cells")
    print("   ✓ Consistent alignment and spacing")
    print("   ✓ Easier to scan and read")
    print("   ✓ Professional table appearance")

def test_different_border_styles():
    """Test different border styles available with PrettyTable."""
    print("\n" + "=" * 80)
    print("🎨 TESTING DIFFERENT BORDER STYLES")
    print("=" * 80)
    
    mock_results = create_mock_results()
    border_styles = ["double", "single", "markdown", "default"]
    
    for style in border_styles:
        print(f"\n📋 {style.upper()} BORDER STYLE:")
        print("-" * 40)
        
        # Test with top components table
        table = PrettyTableFormatter._format_top_components_table(mock_results, style)
        if table:
            # Show just the first few lines for demo
            lines = table.split('\n')
            for line in lines[:8]:  # Show header and a couple rows
                print(line)
            if len(lines) > 8:
                print("... (truncated for demo)")

def main():
    """Run all optimization tests."""
    print("🔬 PRETTYTABLE OPTIMIZATION TESTING SUITE")
    print("Testing improvements to Top Influential Components and Market Interpretations")
    
    # Test individual optimizations
    test_top_components_optimization()
    test_market_interpretations_optimization()
    test_different_border_styles()
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 80)
    print("\n🚀 SUMMARY OF OPTIMIZATIONS:")
    print("   • Top Influential Components: Converted to clean tabular format")
    print("   • Market Interpretations: Converted to structured two-column table")
    print("   • Both sections now use PrettyTable for consistent, professional formatting")
    print("   • Improved readability, alignment, and visual appeal")
    print("   • Multiple border styles supported (double, single, markdown, default)")
    print("\n💡 These optimizations provide:")
    print("   ✓ Better data organization and presentation")
    print("   ✓ Consistent formatting across all sections")
    print("   ✓ Enhanced user experience")
    print("   ✓ Professional appearance")
    print("   ✓ Easier maintenance and updates")

if __name__ == "__main__":
    main() 