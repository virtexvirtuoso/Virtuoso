#!/usr/bin/env python3
"""Test branded chart generation with Virtuoso logo."""

import os
import sys
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def create_branded_chart():
    """Create a test chart with Virtuoso branding."""
    
    print("=" * 60)
    print("TESTING BRANDED CHART GENERATION")
    print("=" * 60)
    
    # Create output directory
    os.makedirs("test_output/branded_charts", exist_ok=True)
    
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
    
    # Create the chart
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Set dark theme
    fig.patch.set_facecolor('#121212')
    ax.set_facecolor('#1E1E1E')
    
    # Plot candlestick-style chart (simplified)
    for idx, row in df.iterrows():
        color = '#22c55e' if row['close'] >= row['open'] else '#ef4444'
        # Body
        ax.plot([idx, idx], [row['open'], row['close']], color=color, linewidth=3)
        # Wicks
        ax.plot([idx, idx], [row['low'], row['high']], color=color, linewidth=1, alpha=0.5)
    
    # Add entry line
    ax.axhline(y=entry_price, color='#4CAF50', linestyle='-', linewidth=2, 
               label=f'Entry: ${entry_price:.4f}')
    
    # Add stop loss line
    ax.axhline(y=stop_loss, color='#ef4444', linestyle='--', linewidth=2, 
               label=f'Stop: ${stop_loss:.4f}')
    
    # Add target lines
    colors = ['#fbbf24', '#f59e0b', '#f97316']  # Different shades of orange
    for i, target in enumerate(targets):
        ax.axhline(y=target['price'], color=colors[i % len(colors)], 
                   linestyle='-.', linewidth=1.5, alpha=0.8,
                   label=f"{target['name']}: ${target['price']:.4f} ({target['size']}%)")
    
    # Fill between entry and stop loss
    ax.fill_between(range(len(df)), entry_price, stop_loss, 
                    color='#ef4444', alpha=0.1)
    
    # Style the chart
    ax.set_xlabel('Time', fontsize=12, color='white')
    ax.set_ylabel('Price (USDT)', fontsize=12, color='white')
    ax.set_title(f'{symbol} Price Action - Entry: ${entry_price:.4f}', 
                 fontsize=16, color='white', pad=20)
    
    # Configure grid
    ax.grid(True, color='#333333', linestyle='-', linewidth=0.5, alpha=0.5)
    
    # Style axes
    ax.spines['bottom'].set_color('white')
    ax.spines['top'].set_color('white')
    ax.spines['right'].set_color('white')
    ax.spines['left'].set_color('white')
    ax.tick_params(colors='white')
    
    # Add legend
    ax.legend(loc='upper right', facecolor='#1E1E1E', edgecolor='white', 
              fontsize=10, framealpha=0.9)
    
    # Set y-axis limits to show all levels clearly
    y_min = min(stop_loss, df['low'].min()) * 0.995
    y_max = max(targets[-1]['price'], df['high'].max()) * 1.005
    ax.set_ylim(y_min, y_max)
    
    # Adjust layout to make room for branding
    plt.subplots_adjust(left=0.1, right=0.9, top=0.92, bottom=0.15)
    
    # Add Virtuoso branding at the bottom (like in the PDF generator)
    fig.text(0.5, 0.02, '📈 VIRTUOSO', 
            fontsize=16, weight='bold', color='#ff9900',
            ha='center', va='bottom',
            transform=fig.transFigure,
            bbox=dict(boxstyle='round,pad=0.5', 
                     facecolor='#1E1E1E', 
                     edgecolor='#ff9900',
                     alpha=0.8))
    
    # Save the chart
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    chart_path = f"test_output/branded_charts/{symbol}_branded_chart_{timestamp}.png"
    
    # Save with extra padding for branding (matching PDF generator)
    plt.savefig(chart_path, dpi=150, bbox_inches='tight', pad_inches=0.3, 
                facecolor='#121212', edgecolor='none')
    plt.close()
    
    print(f"\n✅ Branded chart saved to: {chart_path}")
    file_size = os.path.getsize(chart_path) / 1024
    print(f"   File size: {file_size:.1f} KB")
    
    # Calculate and display distances
    sl_distance = ((stop_loss / entry_price) - 1) * 100
    print(f"\n   Stop Loss Distance: {sl_distance:.2f}%")
    print("   Target Distances:")
    for i, target in enumerate(targets):
        tp_distance = ((target['price'] / entry_price) - 1) * 100
        print(f"     {target['name']}: +{tp_distance:.2f}%")
    
    print(f"\n📈 Branding Details:")
    print(f"   - Logo: 📈 trending up emoji")
    print(f"   - Text: VIRTUOSO")
    print(f"   - Color: #ff9900 (orange from mobile header)")
    print(f"   - Background: Dark box with orange border")
    print(f"   - Position: Bottom center with padding")
    
    return chart_path


def test_branding_variations():
    """Test different branding styles."""
    
    print("\n" + "=" * 60)
    print("TESTING BRANDING VARIATIONS")
    print("=" * 60)
    
    # Create a simple test chart
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('#121212')
    ax.set_facecolor('#1E1E1E')
    
    # Simple price line
    x = np.linspace(0, 100, 100)
    y = 0.059 + 0.002 * np.sin(x/10) + np.random.normal(0, 0.0005, 100)
    ax.plot(x, y, color='#4CAF50', linewidth=2)
    ax.set_title('Sample Chart for Branding Test', color='white', fontsize=14)
    ax.tick_params(colors='white')
    
    # Style axes
    for spine in ax.spines.values():
        spine.set_color('white')
    
    plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.15)
    
    # Test the exact branding from the PDF generator
    fig.text(0.5, 0.02, '📈 VIRTUOSO', 
            fontsize=16, weight='bold', color='#ff9900',
            ha='center', va='bottom',
            transform=fig.transFigure,
            bbox=dict(boxstyle='round,pad=0.5', 
                     facecolor='#1E1E1E', 
                     edgecolor='#ff9900',
                     alpha=0.8))
    
    # Save test
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    test_path = f"test_output/branded_charts/branding_test_{timestamp}.png"
    plt.savefig(test_path, dpi=150, bbox_inches='tight', pad_inches=0.3,
                facecolor='#121212', edgecolor='none')
    plt.close()
    
    print(f"✅ Branding test saved to: {test_path}")
    
    return test_path


def main():
    """Run branding tests."""
    
    print("\n🧪 TESTING VIRTUOSO CHART BRANDING\n")
    
    # Test 1: Full branded chart
    chart_path = create_branded_chart()
    
    # Test 2: Simple branding test
    test_path = test_branding_variations()
    
    print("\n" + "=" * 60)
    print("✅ BRANDING TESTS COMPLETE")
    print("=" * 60)
    print("\nGenerated charts:")
    print(f"1. Full Chart: {chart_path}")
    print(f"2. Test Chart: {test_path}")
    print("\nThe charts should now have:")
    print("  - 📈 VIRTUOSO branding at the bottom")
    print("  - Orange color matching the mobile header")
    print("  - Dark background box with orange border")
    print("  - Extra padding around the entire chart")
    print("\nCheck test_output/branded_charts/ to view the results!")


if __name__ == "__main__":
    main()