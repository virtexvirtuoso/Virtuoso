#!/usr/bin/env python3
"""Test simple text-based branding without emoji."""

import os
import sys
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def create_chart_with_simple_branding():
    """Create a chart with simple text branding like the original system."""
    
    print("=" * 60)
    print("TESTING SIMPLE TEXT BRANDING")
    print("=" * 60)
    
    # Create output directory
    os.makedirs("test_output/simple_branded_charts", exist_ok=True)
    
    # Test parameters (ENAUSDT example)
    symbol = "ENAUSDT"
    entry_price = 0.059520
    stop_loss = 0.0577
    targets = [
        {"name": "Target 1", "price": 0.0620, "size": 50},
        {"name": "Target 2", "price": 0.0640, "size": 30},
        {"name": "Target 3", "price": 0.0660, "size": 20}
    ]
    
    # Generate sample price data
    periods = 100
    timestamps = pd.date_range(end=datetime.now(), periods=periods, freq='5min')
    
    # Create realistic price movement around entry price
    base_price = entry_price
    price_volatility = 0.0003
    trend = np.linspace(0, -0.001, periods)  # Slight downtrend
    noise = np.random.normal(0, price_volatility, periods)
    prices = base_price + trend + noise
    
    # Create OHLCV data
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': prices + np.random.uniform(-0.0001, 0.0001, periods),
        'high': prices + np.random.uniform(0, 0.0002, periods),
        'low': prices - np.random.uniform(0, 0.0002, periods),
        'close': prices,
        'volume': np.random.uniform(1000000, 5000000, periods)
    })
    
    # Set up matplotlib styling for dark mode (original colors)
    plt.rcParams.update({
        "figure.facecolor": "#121212",
        "axes.facecolor": "#1E1E1E", 
        "axes.edgecolor": "#444444",
        "axes.labelcolor": "#E0E0E0",
        "xtick.color": "#E0E0E0",
        "ytick.color": "#E0E0E0",
        "text.color": "#E0E0E0",
        "savefig.facecolor": "#121212",
        "savefig.edgecolor": "#121212"
    })
    
    # Create the chart
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Plot candlestick-style chart (simplified)
    for idx, row in df.iterrows():
        color = '#22c55e' if row['close'] >= row['open'] else '#ef4444'
        # Body
        ax.plot([idx, idx], [row['open'], row['close']], color=color, linewidth=3)
        # Wicks
        ax.plot([idx, idx], [row['low'], row['high']], color=color, linewidth=1, alpha=0.5)
    
    # Add entry line (original colors)
    ax.axhline(y=entry_price, color='#4CAF50', linestyle='-', linewidth=2, 
               label=f'Entry: ${entry_price:.4f}')
    
    # Add stop loss line (original colors)
    ax.axhline(y=stop_loss, color='#ef4444', linestyle='--', linewidth=2, 
               label=f'Stop: ${stop_loss:.4f}')
    
    # Add target lines (original colors - using blues/cyans)
    target_colors = ['#03DAC6', '#018786', '#005B52']  # Teal variations
    for i, target in enumerate(targets):
        ax.axhline(y=target['price'], color=target_colors[i % len(target_colors)], 
                   linestyle='-.', linewidth=1.5, alpha=0.8,
                   label=f"{target['name']}: ${target['price']:.4f} ({target['size']}%)")
    
    # Fill between entry and stop loss
    ax.fill_between(range(len(df)), entry_price, stop_loss, 
                    color='#ef4444', alpha=0.1)
    
    # Style the chart (original styling)
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Price (USDT)', fontsize=12)
    ax.set_title(f'{symbol} Price Action - Entry: ${entry_price:.4f}', 
                 fontsize=16, pad=20)
    
    # Configure grid (original style)
    ax.grid(True, color='#333333', linestyle='-', linewidth=0.5, alpha=0.3)
    
    # Add legend (original style)
    ax.legend(loc='upper right', framealpha=0.9, fontsize=10)
    
    # Set y-axis limits to show all levels clearly
    y_min = min(stop_loss, df['low'].min()) * 0.995
    y_max = max(targets[-1]['price'], df['high'].max()) * 1.005
    ax.set_ylim(y_min, y_max)
    
    # Adjust layout (original)
    plt.subplots_adjust(left=0.1, right=0.9, top=0.92, bottom=0.15)
    
    # Add simple Virtuoso branding (like the updated code)
    fig.text(0.5, 0.02, 'VIRTUOSO', 
            fontsize=12, weight='bold', color='#E0E0E0',
            ha='center', va='bottom',
            transform=fig.transFigure,
            alpha=0.7)
    
    # Save the chart
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    chart_path = f"test_output/simple_branded_charts/{symbol}_simple_brand_{timestamp}.png"
    
    # Save with minimal padding (like the updated code)
    plt.savefig(chart_path, dpi=150, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    
    print(f"\n✅ Simple branded chart saved to: {chart_path}")
    file_size = os.path.getsize(chart_path) / 1024
    print(f"   File size: {file_size:.1f} KB")
    
    print(f"\n🎨 Reverted to original color scheme:")
    print(f"   - Entry: #4CAF50 (green)")
    print(f"   - Stop Loss: #ef4444 (red)")
    print(f"   - Targets: Teal variations")
    print(f"   - Background: #121212 / #1E1E1E")
    print(f"   - Text: #E0E0E0")
    
    print(f"\n📝 Simple branding:")
    print(f"   - Text: 'VIRTUOSO' only (no emoji)")
    print(f"   - Color: #E0E0E0 (light gray)")
    print(f"   - Size: 12pt font")
    print(f"   - Position: Bottom center")
    print(f"   - Alpha: 0.7 (subtle)")
    
    return chart_path


def main():
    """Run simple branding test."""
    
    print("\n🧪 TESTING SIMPLE VIRTUOSO BRANDING\n")
    
    # Test simple text branding
    chart_path = create_chart_with_simple_branding()
    
    print("\n" + "=" * 60)
    print("✅ SIMPLE BRANDING TEST COMPLETE")
    print("=" * 60)
    print(f"\nGenerated chart: {chart_path}")
    print("\nThe chart should now have:")
    print("  - Original color scheme restored")
    print("  - Simple 'VIRTUOSO' text at bottom")
    print("  - No emoji or fancy styling")
    print("  - Subtle and professional appearance")
    print("\nCheck test_output/simple_branded_charts/ to view the result!")


if __name__ == "__main__":
    main()