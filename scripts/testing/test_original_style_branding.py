#!/usr/bin/env python3
"""Test with original chart style and proper Virtuoso branding."""

import os
import sys
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def create_original_style_chart():
    """Create a chart with original styling and proper branding."""
    
    print("=" * 60)
    print("TESTING ORIGINAL STYLE + PROPER BRANDING")
    print("=" * 60)
    
    # Create output directory
    os.makedirs("test_output/original_style_charts", exist_ok=True)
    
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
    
    # Create the chart with dark theme
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Set dark theme (like original)
    fig.patch.set_facecolor('#121212')
    ax.set_facecolor('#1E1E1E')
    
    # Plot candlestick-style chart (simplified)
    for idx, row in df.iterrows():
        color = '#22c55e' if row['close'] >= row['open'] else '#ef4444'
        # Body
        ax.plot([idx, idx], [row['open'], row['close']], color=color, linewidth=3)
        # Wicks
        ax.plot([idx, idx], [row['low'], row['high']], color=color, linewidth=1, alpha=0.5)
    
    # Add entry line (original green)
    ax.axhline(y=entry_price, color='#4CAF50', linestyle='-', linewidth=2, 
               label=f'Entry: ${entry_price:.4f}')
    
    # Add stop loss line (original red)
    ax.axhline(y=stop_loss, color='#ef4444', linestyle='--', linewidth=2, 
               label=f'Stop: ${stop_loss:.4f}')
    
    # Add target lines - let me check what the original target colors were
    # Based on the system, they seem to be variations of orange/yellow
    target_colors = ['#fbbf24', '#f59e0b', '#f97316']  # Orange variations
    for i, target in enumerate(targets):
        ax.axhline(y=target['price'], color=target_colors[i % len(target_colors)], 
                   linestyle='-.', linewidth=1.5, alpha=0.8,
                   label=f"{target['name']}: ${target['price']:.4f} ({target['size']}%)")
    
    # Fill between entry and stop loss (original style)
    ax.fill_between(range(len(df)), entry_price, stop_loss, 
                    color='#ef4444', alpha=0.1)
    
    # Style the chart (original colors)
    ax.set_xlabel('Time', fontsize=12, color='#E0E0E0')
    ax.set_ylabel('Price (USDT)', fontsize=12, color='#E0E0E0')
    ax.set_title(f'{symbol} Price Action - Entry: ${entry_price:.4f}', 
                 fontsize=16, color='#E0E0E0', pad=20)
    
    # Configure grid (original style)
    ax.grid(True, color='#333333', linestyle='-', linewidth=0.5, alpha=0.5)
    
    # Style axes (original colors)
    ax.spines['bottom'].set_color('#444444')
    ax.spines['top'].set_color('#444444')
    ax.spines['right'].set_color('#444444')
    ax.spines['left'].set_color('#444444')
    ax.tick_params(colors='#E0E0E0')
    
    # Add legend (original style)
    ax.legend(loc='upper right', facecolor='#1E1E1E', edgecolor='#444444', 
              fontsize=10, framealpha=0.9, labelcolor='#E0E0E0')
    
    # Set y-axis limits to show all levels clearly
    y_min = min(stop_loss, df['low'].min()) * 0.995
    y_max = max(targets[-1]['price'], df['high'].max()) * 1.005
    ax.set_ylim(y_min, y_max)
    
    # Adjust layout 
    plt.subplots_adjust(left=0.1, right=0.9, top=0.92, bottom=0.15)
    
    # Add Virtuoso branding with trending-up symbol (like the updated code)
    fig.text(0.5, 0.02, '↗ VIRTUOSO', 
            fontsize=14, weight='bold', color='#ff9900',
            ha='center', va='bottom',
            transform=fig.transFigure,
            bbox=dict(boxstyle='round,pad=0.4', 
                     facecolor='#1E1E1E', 
                     edgecolor='#ff9900',
                     alpha=0.9))
    
    # Save the chart
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    chart_path = f"test_output/original_style_charts/{symbol}_original_style_{timestamp}.png"
    
    # Save with padding for branding (like the updated code)
    plt.savefig(chart_path, dpi=150, bbox_inches='tight', pad_inches=0.2,
                facecolor='#121212', edgecolor='none')
    plt.close()
    
    print(f"\n✅ Original style chart saved to: {chart_path}")
    file_size = os.path.getsize(chart_path) / 1024
    print(f"   File size: {file_size:.1f} KB")
    
    print(f"\n🎨 Original color scheme:")
    print(f"   - Background: #121212 / #1E1E1E")
    print(f"   - Entry: #4CAF50 (green)")
    print(f"   - Stop Loss: #ef4444 (red)")
    print(f"   - Targets: Orange variations (#fbbf24, #f59e0b, #f97316)")
    print(f"   - Text: #E0E0E0")
    print(f"   - Axes: #444444")
    
    print(f"\n📈 Proper branding:")
    print(f"   - Symbol: ↗ (trending up arrow)")
    print(f"   - Text: 'VIRTUOSO'")
    print(f"   - Color: #ff9900 (orange like mobile header)")
    print(f"   - Background: Dark box with orange border")
    print(f"   - Size: 14pt font")
    
    return chart_path


def main():
    """Run original style test."""
    
    print("\n🧪 TESTING ORIGINAL STYLE WITH PROPER BRANDING\n")
    
    # Test original style with proper branding
    chart_path = create_original_style_chart()
    
    print("\n" + "=" * 60)
    print("✅ ORIGINAL STYLE TEST COMPLETE")
    print("=" * 60)
    print(f"\nGenerated chart: {chart_path}")
    print("\nThe chart should now have:")
    print("  - Original color scheme (what we had before)")
    print("  - Proper ↗ VIRTUOSO branding")
    print("  - Orange color matching mobile header")
    print("  - Professional dark box styling")
    print("\nCheck test_output/original_style_charts/ to view the result!")


if __name__ == "__main__":
    main()