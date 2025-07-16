#!/usr/bin/env python3
"""
Simple 3D Prism Example
=======================

A standalone example showing how to create 3D signal prism visualizations
from your confluence analysis data. This example uses the actual data
from your log output to create a realistic visualization.

Run this script to generate interactive 3D prisms that you can open in your browser.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from scripts.visualization.signal_prism_3d import SignalPrism3D


def create_prism_from_log_data():
    """Create a 3D prism using the actual data from your confluence analysis logs."""
    
    print("🎯 Creating 3D Signal Prism from Your Confluence Analysis Data")
    print("=" * 65)
    
    # Data extracted from your actual log output
    component_scores = {
        'technical': 44.74,      # Technical analysis score
        'volume': 43.15,         # Volume analysis score  
        'orderbook': 60.08,      # Orderbook analysis score
        'orderflow': 73.08,      # Orderflow analysis score (strongest)
        'sentiment': 62.10,      # Sentiment analysis score
        'price_structure': 46.82 # Price structure analysis score
    }
    
    # Overall confluence metrics
    overall_score = 56.87  # Overall confluence score
    confidence = 0.78      # Confidence level (78%)
    symbol = "XRPUSDT"     # Trading pair
    
    print(f"📊 Analyzing {symbol}")
    print(f"   Overall Score: {overall_score:.1f}/100")
    print(f"   Confidence: {confidence*100:.0f}%")
    print(f"   Strongest Component: Orderflow ({component_scores['orderflow']:.1f})")
    print(f"   Weakest Component: Volume ({component_scores['volume']:.1f})")
    
    # Create the visualizer
    visualizer = SignalPrism3D()
    
    # Generate the interactive 3D prism
    print("\n🔨 Building 3D prism visualization...")
    fig = visualizer.create_interactive_visualization(
        component_scores=component_scores,
        overall_score=overall_score,
        confidence=confidence,
        symbol=symbol,
        timestamp=datetime.now()
    )
    
    # Add rotation animation controls
    fig = visualizer.add_animation_controls(fig)
    
    # Save the visualization
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = visualizer.save_visualization(
        fig, 
        f"confluence_prism_{symbol}_{timestamp_str}"
    )
    
    print(f"✅ 3D Prism saved to: {filepath}")
    
    # Create a dashboard view with multiple angles
    print("\n🎛️  Creating dashboard view...")
    dashboard_fig = visualizer.create_dashboard_view(
        component_scores, overall_score, confidence, symbol
    )
    
    dashboard_path = visualizer.save_visualization(
        dashboard_fig,
        f"confluence_dashboard_{symbol}_{timestamp_str}"
    )
    
    print(f"✅ Dashboard saved to: {dashboard_path}")
    
    # Provide interpretation
    print("\n🎯 Signal Interpretation:")
    print("-" * 25)
    
    if overall_score >= 65:
        signal_type = "🟢 BULLISH"
        action = "Consider LONG positions"
    elif overall_score <= 35:
        signal_type = "🔴 BEARISH" 
        action = "Consider SHORT positions"
    else:
        signal_type = "🟡 NEUTRAL"
        action = "Wait for clearer signals"
    
    if confidence >= 0.8:
        confidence_level = "🟢 HIGH"
        risk = "Low Risk"
    elif confidence >= 0.6:
        confidence_level = "🟡 MEDIUM"
        risk = "Medium Risk"
    else:
        confidence_level = "🔴 LOW"
        risk = "High Risk"
    
    print(f"   Signal Type: {signal_type}")
    print(f"   Confidence: {confidence_level} ({confidence*100:.0f}%)")
    print(f"   Risk Level: {risk}")
    print(f"   Recommended Action: {action}")
    
    # Component analysis
    print(f"\n📈 Component Analysis:")
    print("-" * 22)
    for component, score in component_scores.items():
        if score >= 60:
            status = "🟢 Bullish"
        elif score <= 40:
            status = "🔴 Bearish"
        else:
            status = "🟡 Neutral"
        
        print(f"   {component.title():<15}: {score:>5.1f} {status}")
    
    return filepath, dashboard_path


def create_comparison_prisms():
    """Create multiple prisms showing different market scenarios for comparison."""
    
    print("\n" + "=" * 65)
    print("📊 Creating Comparison Prisms for Different Market Scenarios")
    print("=" * 65)
    
    visualizer = SignalPrism3D()
    
    # Define different market scenarios
    scenarios = {
        'strong_bullish': {
            'scores': {
                'technical': 85, 'volume': 80, 'orderbook': 75,
                'orderflow': 90, 'sentiment': 85, 'price_structure': 80
            },
            'overall': 82.5,
            'confidence': 0.9,
            'symbol': 'BULL_SIGNAL',
            'description': 'Strong Bullish Market'
        },
        'strong_bearish': {
            'scores': {
                'technical': 15, 'volume': 20, 'orderbook': 25,
                'orderflow': 10, 'sentiment': 15, 'price_structure': 20
            },
            'overall': 17.5,
            'confidence': 0.85,
            'symbol': 'BEAR_SIGNAL',
            'description': 'Strong Bearish Market'
        },
        'mixed_signals': {
            'scores': {
                'technical': 70, 'volume': 30, 'orderbook': 60,
                'orderflow': 40, 'sentiment': 80, 'price_structure': 35
            },
            'overall': 52.5,
            'confidence': 0.4,
            'symbol': 'MIXED_SIGNAL',
            'description': 'Mixed/Conflicting Signals'
        }
    }
    
    saved_files = []
    
    for scenario_name, data in scenarios.items():
        print(f"\n🎯 Creating {data['description']}...")
        
        # Create prism
        fig = visualizer.create_interactive_visualization(
            component_scores=data['scores'],
            overall_score=data['overall'],
            confidence=data['confidence'],
            symbol=data['symbol'],
            timestamp=datetime.now()
        )
        
        # Add animation
        fig = visualizer.add_animation_controls(fig)
        
        # Save
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = visualizer.save_visualization(
            fig,
            f"scenario_{scenario_name}_{timestamp_str}"
        )
        
        saved_files.append((data['description'], filepath))
        print(f"   ✅ Saved: {os.path.basename(filepath)}")
    
    return saved_files


def main():
    """Main function to run all examples."""
    
    print("🚀 3D Signal Prism Visualization Examples")
    print("=" * 45)
    print("This script creates interactive 3D visualizations of your trading signals.")
    print("The prisms will be saved as HTML files that you can open in your browser.")
    print()
    
    try:
        # Create prism from your actual confluence data
        main_prism, dashboard = create_prism_from_log_data()
        
        # Create comparison scenarios
        comparison_files = create_comparison_prisms()
        
        # Summary
        print("\n" + "=" * 65)
        print("🎉 ALL VISUALIZATIONS CREATED SUCCESSFULLY!")
        print("=" * 65)
        
        print(f"\n📁 Files created in: examples/demo/3d_viz_output/")
        print(f"   🎯 Main Prism: {os.path.basename(main_prism)}")
        print(f"   🎛️  Dashboard: {os.path.basename(dashboard)}")
        
        print(f"\n📊 Comparison Scenarios:")
        for description, filepath in comparison_files:
            print(f"   • {description}: {os.path.basename(filepath)}")
        
        print(f"\n🌐 How to View:")
        print(f"   1. Navigate to the examples/demo/3d_viz_output/ directory")
        print(f"   2. Double-click any .html file to open in your browser")
        print(f"   3. Use mouse to rotate and examine the 3D prisms")
        print(f"   4. Click the ▶️ Rotate button for auto-rotation")
        print(f"   5. Hover over prism faces for detailed information")
        
        print(f"\n💡 Tips:")
        print(f"   • Green faces = Bullish signals")
        print(f"   • Red faces = Bearish signals") 
        print(f"   • Orange faces = Neutral signals")
        print(f"   • Taller prisms = Stronger overall signals")
        print(f"   • More opaque = Higher confidence")
        
    except Exception as e:
        print(f"\n❌ Error creating visualizations: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 