"""
Dashboard-Styled 3D Signal Prism Demo
====================================

Demonstration of the 3D signal prism with Virtuoso Terminal dashboard styling:
- Terminal amber + navy blue color scheme
- JetBrains Mono typography
- Professional dark theme matching dashboard_v10.html
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from scripts.visualization.dashboard_styled_prism_3d import DashboardStyledPrism3D
from datetime import datetime
import numpy as np


def demo_dashboard_prism_styling():
    """Demonstrate the dashboard-styled 3D signal prism."""
    
    print("🎯 VIRTUOSO TERMINAL - Dashboard-Styled 3D Signal Prism")
    print("=" * 60)
    print("Features:")
    print("• Terminal amber + navy blue color scheme")
    print("• JetBrains Mono typography")
    print("• Professional dark theme")
    print("• Consistent with dashboard_v10.html aesthetics")
    print("• Terminal-style particle effects")
    print("• Animated rotation controls")
    print("=" * 60)
    
    # Real XRPUSDT signal data
    component_scores = {
        'technical': 44.74,
        'volume': 43.15,
        'orderbook': 60.08,
        'orderflow': 73.08,
        'sentiment': 62.10,
        'price_structure': 46.82
    }
    
    overall_score = 56.87
    confidence = 0.78
    symbol = "XRPUSDT"
    
    # Create dashboard-styled visualizer
    visualizer = DashboardStyledPrism3D()
    
    print(f"Creating dashboard-styled 3D prism for {symbol}...")
    print(f"Overall Score: {overall_score:.1f}/100")
    print(f"Confidence: {confidence*100:.0f}%")
    print()
    
    # Create the visualization
    fig = visualizer.create_dashboard_styled_prism(
        component_scores=component_scores,
        overall_score=overall_score,
        confidence=confidence,
        symbol=symbol,
        timestamp=datetime.now()
    )
    
    # Save with dashboard styling
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"signal_prism_{symbol}_{timestamp_str}"
    
    print("Saving dashboard visualization...")
    filepath = visualizer.save_dashboard_visualization(fig, filename)
    
    print(f"✅ Dashboard prism saved to: {filepath}")
    print()
    print("🎨 Dashboard Styling Features:")
    print("• Background: Terminal dark gradient (#0c1a2b → #0f172a)")
    print("• Primary text: Amber (#ffbf00)")
    print("• Secondary text: Dark amber (#b8860b)")
    print("• Accents: Orange/amber gradient (#ff9900 → #ffc107)")
    print("• Typography: JetBrains Mono monospace font")
    print("• Grid: Dark navy borders (#1a2a40)")
    print("• Particles: Adaptive amber glow effects")
    print("• Animation: Terminal-style rotation controls")
    print()
    print("🚀 Signal Analysis:")
    for component, score in component_scores.items():
        status = "🟢 STRONG" if score >= 70 else "🟡 MEDIUM" if score >= 50 else "🔴 WEAK"
        print(f"  {component.upper()}: {score:.1f}% {status}")
    
    return fig, filepath


def demo_multiple_signals():
    """Demonstrate multiple signals with different scores."""
    
    print("\n" + "=" * 60)
    print("🎯 MULTIPLE SIGNAL DEMONSTRATIONS")
    print("=" * 60)
    
    # Different signal scenarios
    scenarios = [
        {
            'name': 'STRONG_BULLISH',
            'symbol': 'BTCUSDT',
            'scores': {
                'technical': 85.2,
                'volume': 78.9,
                'orderbook': 82.1,
                'orderflow': 89.3,
                'sentiment': 76.4,
                'price_structure': 81.7
            },
            'overall': 82.3,
            'confidence': 0.92
        },
        {
            'name': 'NEUTRAL_MIXED',
            'symbol': 'ETHUSDT',
            'scores': {
                'technical': 52.1,
                'volume': 48.7,
                'orderbook': 55.3,
                'orderflow': 51.9,
                'sentiment': 49.2,
                'price_structure': 53.8
            },
            'overall': 51.8,
            'confidence': 0.65
        },
        {
            'name': 'WEAK_BEARISH',
            'symbol': 'ADAUSDT',
            'scores': {
                'technical': 28.4,
                'volume': 31.2,
                'orderbook': 25.7,
                'orderflow': 22.8,
                'sentiment': 35.1,
                'price_structure': 29.6
            },
            'overall': 28.8,
            'confidence': 0.71
        }
    ]
    
    visualizer = DashboardStyledPrism3D()
    generated_files = []
    
    for scenario in scenarios:
        print(f"\nGenerating {scenario['name']} scenario for {scenario['symbol']}...")
        
        fig = visualizer.create_dashboard_styled_prism(
            component_scores=scenario['scores'],
            overall_score=scenario['overall'],
            confidence=scenario['confidence'],
            symbol=scenario['symbol'],
            timestamp=datetime.now()
        )
        
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{scenario['name'].lower()}_{scenario['symbol']}_{timestamp_str}"
        
        filepath = visualizer.save_dashboard_visualization(fig, filename)
        generated_files.append(filepath)
        
        print(f"✅ {scenario['name']} prism saved: {os.path.basename(filepath)}")
    
    print(f"\n🎯 Generated {len(generated_files)} dashboard-styled visualizations")
    return generated_files


def demo_dashboard_color_analysis():
    """Analyze the dashboard color scheme implementation."""
    
    print("\n" + "=" * 60)
    print("🎨 DASHBOARD COLOR SCHEME ANALYSIS")
    print("=" * 60)
    
    visualizer = DashboardStyledPrism3D()
    colors = visualizer.colors
    
    print("Terminal Amber + Navy Blue Theme:")
    print(f"  Background Primary: {colors['bg_primary']} (Deep navy)")
    print(f"  Background Secondary: {colors['bg_secondary']} (Dark slate)")
    print(f"  Text Primary: {colors['text_primary']} (Bright amber)")
    print(f"  Text Secondary: {colors['text_secondary']} (Dark amber)")
    print(f"  Accent Positive: {colors['accent_positive']} (Signal amber)")
    print(f"  Accent Primary: {colors['accent_primary']} (Orange)")
    print(f"  Border Light: {colors['border_light']} (Navy border)")
    print()
    
    print("Typography Configuration:")
    typography = visualizer.typography
    print(f"  Font Family: {typography['font_family']}")
    print(f"  Title Size: {typography['title_size']}px")
    print(f"  Subtitle Size: {typography['subtitle_size']}px")
    print(f"  Label Size: {typography['label_size']}px")
    print(f"  Small Size: {typography['small_size']}px")
    print()
    
    print("Component Styling:")
    for component, info in visualizer.components.items():
        print(f"  {component.upper()}: {info['icon']} {info['color_base']} (Weight: {info['weight']*100:.1f}%)")


if __name__ == "__main__":
    # Run the dashboard prism demonstrations
    print("🚀 Starting Dashboard-Styled 3D Signal Prism Demonstrations...")
    
    # Main demo
    fig, filepath = demo_dashboard_prism_styling()
    
    # Multiple scenarios
    generated_files = demo_multiple_signals()
    
    # Color analysis
    demo_dashboard_color_analysis()
    
    print("\n" + "=" * 60)
    print("🎯 DASHBOARD PRISM DEMO COMPLETE")
    print("=" * 60)
    print(f"✅ Main visualization: {os.path.basename(filepath)}")
    print(f"✅ Additional scenarios: {len(generated_files)} files")
    print("✅ All visualizations use dashboard_v10.html styling")
    print("✅ Terminal amber + navy blue color scheme applied")
    print("✅ JetBrains Mono typography implemented")
    print("✅ Professional dark theme with terminal effects")
    print("=" * 60) 