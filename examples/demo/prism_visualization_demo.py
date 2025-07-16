#!/usr/bin/env python3
"""
3D Signal Prism Visualization Demo
=================================

This demo shows how to create stunning 3D prism visualizations from your
confluence analysis data. The prism provides a physical representation of
trading signals that makes complex data intuitive for traders.

Features demonstrated:
- Real-time signal prism generation
- Interactive 3D visualization
- Trading recommendations
- Dashboard views
- Animation controls
"""

import sys
import os
from pathlib import Path
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

from scripts.visualization.signal_prism_3d import SignalPrism3D
from scripts.visualization.confluence_prism_integration import ConfluencePrismIntegration


def create_sample_market_data(symbol: str = "BTCUSDT", trend: str = "bullish") -> dict:
    """Create realistic sample market data for demonstration."""
    
    # Base price
    base_price = 45000.0 if symbol == "BTCUSDT" else 0.01055
    
    # Generate price movement based on trend
    if trend == "bullish":
        price_multiplier = np.linspace(1.0, 1.02, 100)  # 2% uptrend
        volume_multiplier = np.linspace(1.0, 1.5, 100)  # Increasing volume
    elif trend == "bearish":
        price_multiplier = np.linspace(1.0, 0.98, 100)  # 2% downtrend
        volume_multiplier = np.linspace(1.0, 1.3, 100)  # Increasing volume
    else:  # neutral
        price_multiplier = 1.0 + 0.005 * np.sin(np.linspace(0, 4*np.pi, 100))  # Sideways
        volume_multiplier = np.ones(100)
    
    # Generate OHLCV data
    prices = base_price * price_multiplier
    volumes = 1000000 * volume_multiplier
    
    ohlcv_data = {
        'open': prices,
        'high': prices * 1.001,
        'low': prices * 0.999,
        'close': prices,
        'volume': volumes
    }
    
    # Create DataFrames for different timeframes
    market_data = {
        'ohlcv': {
            '1m': pd.DataFrame(ohlcv_data),
            '5m': pd.DataFrame({k: v[::5] for k, v in ohlcv_data.items()}),
            '15m': pd.DataFrame({k: v[::15] for k, v in ohlcv_data.items()}),
            '1h': pd.DataFrame({k: v[::60] for k, v in ohlcv_data.items()})
        },
        'orderbook': {
            'bids': [[base_price * 0.999, 1000000], [base_price * 0.998, 2000000]],
            'asks': [[base_price * 1.001, 1000000], [base_price * 1.002, 2000000]]
        },
        'trades': []
    }
    
    # Generate trade data
    for i in range(500):
        side = 'buy' if np.random.random() > 0.5 else 'sell'
        price = base_price * (1 + np.random.normal(0, 0.001))
        size = np.random.exponential(1000)
        
        market_data['trades'].append({
            'price': price,
            'size': size,
            'side': side,
            'timestamp': int(datetime.now().timestamp() * 1000) + i * 1000,
            'id': f"trade_{i}"
        })
    
    return market_data


async def demo_basic_prism():
    """Demonstrate basic 3D prism creation."""
    
    print("\n" + "="*60)
    print("🎯 BASIC 3D SIGNAL PRISM DEMO")
    print("="*60)
    
    # Sample component scores (from your log data)
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
    
    # Create visualizer
    visualizer = SignalPrism3D()
    
    # Create interactive visualization
    print("Creating 3D prism visualization...")
    fig = visualizer.create_interactive_visualization(
        component_scores=component_scores,
        overall_score=overall_score,
        confidence=confidence,
        symbol=symbol,
        timestamp=datetime.now()
    )
    
    # Add animation controls
    fig = visualizer.add_animation_controls(fig)
    
    # Save visualization
    filepath = visualizer.save_visualization(
        fig, 
        f"demo_basic_prism_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    print(f"✅ Basic prism saved to: {filepath}")
    
    # Create dashboard view
    print("Creating dashboard view...")
    dashboard_fig = visualizer.create_dashboard_view(
        component_scores, overall_score, confidence, symbol
    )
    
    dashboard_path = visualizer.save_visualization(
        dashboard_fig, 
        f"demo_dashboard_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    print(f"✅ Dashboard saved to: {dashboard_path}")
    
    return fig, dashboard_fig


async def demo_integrated_analysis():
    """Demonstrate full integration with confluence analysis."""
    
    print("\n" + "="*60)
    print("🚀 INTEGRATED CONFLUENCE ANALYSIS DEMO")
    print("="*60)
    
    # Create sample market data for different scenarios
    scenarios = [
        ("BTCUSDT", "bullish", "Strong bullish trend"),
        ("ETHUSDT", "bearish", "Strong bearish trend"),
        ("XRPUSDT", "neutral", "Sideways consolidation")
    ]
    
    # Initialize integration
    integration = ConfluencePrismIntegration({
        'auto_save': True,
        'auto_rotate': True,
        'output_dir': 'examples/demo/3d_viz_output'
    })
    
    results = []
    
    for symbol, trend, description in scenarios:
        print(f"\n📊 Analyzing {symbol} - {description}")
        print("-" * 40)
        
        # Create market data
        market_data = create_sample_market_data(symbol, trend)
        
        # Run analysis and visualization
        result = await integration.analyze_and_visualize(market_data, symbol)
        
        if result.get('success'):
            print(f"✅ Analysis complete for {symbol}")
            print(f"   Overall Score: {result['overall_score']:.1f}/100")
            print(f"   Confidence: {result['confidence']*100:.0f}%")
            
            # Show trading recommendation
            rec = result['trading_recommendation']
            print(f"   Signal: {rec['primary_signal']} ({rec['signal_strength']})")
            print(f"   Risk Level: {rec['risk_level']}")
            
            results.append(result)
        else:
            print(f"❌ Analysis failed for {symbol}: {result.get('error')}")
    
    return results


async def demo_live_simulation():
    """Simulate live trading signal updates."""
    
    print("\n" + "="*60)
    print("📡 LIVE SIGNAL SIMULATION DEMO")
    print("="*60)
    
    # Create visualizer
    visualizer = SignalPrism3D()
    
    # Simulate changing market conditions
    base_scores = {
        'technical': 50.0,
        'volume': 50.0,
        'orderbook': 50.0,
        'orderflow': 50.0,
        'sentiment': 50.0,
        'price_structure': 50.0
    }
    
    print("Simulating live signal updates...")
    
    for i in range(5):
        # Simulate score changes
        component_scores = {}
        for component, base_score in base_scores.items():
            # Add some random movement
            change = np.random.normal(0, 10)
            new_score = max(0, min(100, base_score + change))
            component_scores[component] = new_score
            base_scores[component] = new_score  # Update base for next iteration
        
        # Calculate overall score
        weights = {
            'technical': 0.20,
            'volume': 0.10,
            'orderbook': 0.20,
            'orderflow': 0.25,
            'sentiment': 0.15,
            'price_structure': 0.10
        }
        
        overall_score = sum(score * weights[comp] for comp, score in component_scores.items())
        confidence = 0.6 + 0.3 * np.random.random()  # Random confidence
        
        print(f"\n⏱️  Update {i+1}/5 - Overall Score: {overall_score:.1f}, Confidence: {confidence:.2f}")
        
        # Create visualization
        fig = visualizer.create_interactive_visualization(
            component_scores=component_scores,
            overall_score=overall_score,
            confidence=confidence,
            symbol="LIVE_SIM",
            timestamp=datetime.now()
        )
        
        # Save with timestamp
        filepath = visualizer.save_visualization(
            fig, 
            f"live_sim_update_{i+1}_{datetime.now().strftime('%H%M%S')}"
        )
        
        print(f"   📊 Prism saved: {os.path.basename(filepath)}")
        
        # Brief pause to simulate real-time updates
        await asyncio.sleep(1)
    
    print("\n✅ Live simulation complete!")


def demo_static_examples():
    """Create static examples showing different signal types."""
    
    print("\n" + "="*60)
    print("📈 STATIC SIGNAL EXAMPLES")
    print("="*60)
    
    visualizer = SignalPrism3D()
    
    # Define different signal scenarios
    scenarios = {
        'strong_bullish': {
            'scores': {'technical': 85, 'volume': 80, 'orderbook': 75, 
                      'orderflow': 90, 'sentiment': 85, 'price_structure': 80},
            'overall': 82.5,
            'confidence': 0.9,
            'description': 'Strong Bullish Signal'
        },
        'strong_bearish': {
            'scores': {'technical': 15, 'volume': 20, 'orderbook': 25, 
                      'orderflow': 10, 'sentiment': 15, 'price_structure': 20},
            'overall': 17.5,
            'confidence': 0.85,
            'description': 'Strong Bearish Signal'
        },
        'mixed_signals': {
            'scores': {'technical': 70, 'volume': 30, 'orderbook': 60, 
                      'orderflow': 40, 'sentiment': 80, 'price_structure': 35},
            'overall': 52.5,
            'confidence': 0.4,
            'description': 'Mixed/Conflicting Signals'
        },
        'neutral_low_confidence': {
            'scores': {'technical': 48, 'volume': 52, 'orderbook': 49, 
                      'orderflow': 51, 'sentiment': 50, 'price_structure': 50},
            'overall': 50.0,
            'confidence': 0.3,
            'description': 'Neutral with Low Confidence'
        }
    }
    
    saved_files = []
    
    for scenario_name, scenario_data in scenarios.items():
        print(f"\n📊 Creating {scenario_data['description']}...")
        
        fig = visualizer.create_interactive_visualization(
            component_scores=scenario_data['scores'],
            overall_score=scenario_data['overall'],
            confidence=scenario_data['confidence'],
            symbol=f"DEMO_{scenario_name.upper()}",
            timestamp=datetime.now()
        )
        
        # Add animation
        fig = visualizer.add_animation_controls(fig)
        
        # Save
        filepath = visualizer.save_visualization(
            fig, 
            f"example_{scenario_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        saved_files.append((scenario_data['description'], filepath))
        print(f"   ✅ Saved: {os.path.basename(filepath)}")
    
    print(f"\n📁 All examples saved to: examples/demo/3d_viz_output/")
    return saved_files


async def main():
    """Run all demonstrations."""
    
    print("🎯 3D SIGNAL PRISM VISUALIZATION DEMO")
    print("=" * 60)
    print("This demo showcases the 3D prism visualization system")
    print("that transforms confluence analysis into intuitive visual signals.")
    print()
    
    try:
        # Run basic demo
        await demo_basic_prism()
        
        # Run static examples
        demo_static_examples()
        
        # Run integrated analysis demo
        await demo_integrated_analysis()
        
        # Run live simulation
        await demo_live_simulation()
        
        print("\n" + "="*60)
        print("🎉 ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("📁 Check the 'examples/demo/3d_viz_output/' directory for all generated visualizations.")
        print("🌐 Open the HTML files in your browser to interact with the 3D prisms.")
        print("🎮 Use the rotation controls to examine signals from all angles.")
        print("💡 Hover over prism faces to see detailed component information.")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 