#!/usr/bin/env python3
"""Test chart generation functionality in isolation."""

import os
import sys
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def create_test_chart_with_tp_sl():
    """Create a test chart similar to what the PDF generator would create."""
    
    print("=" * 60)
    print("TESTING CHART GENERATION WITH TP/SL")
    print("=" * 60)
    
    # Create output directory
    os.makedirs("test_output/charts", exist_ok=True)
    
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
    
    # Save the chart
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    chart_path = f"test_output/charts/{symbol}_chart_{timestamp}.png"
    
    plt.tight_layout()
    plt.savefig(chart_path, dpi=150, bbox_inches='tight', 
                facecolor='#121212', edgecolor='none')
    plt.close()
    
    print(f"\n✅ Chart saved to: {chart_path}")
    file_size = os.path.getsize(chart_path) / 1024
    print(f"   File size: {file_size:.1f} KB")
    
    # Calculate and display distances
    sl_distance = ((stop_loss / entry_price) - 1) * 100
    print(f"\n   Stop Loss Distance: {sl_distance:.2f}%")
    print("   Target Distances:")
    for i, target in enumerate(targets):
        tp_distance = ((target['price'] / entry_price) - 1) * 100
        print(f"     {target['name']}: +{tp_distance:.2f}%")
    
    return chart_path


def test_discord_message_with_chart():
    """Test how the Discord message would look with the chart."""
    
    print("\n" + "=" * 60)
    print("DISCORD MESSAGE PREVIEW WITH CHART")
    print("=" * 60)
    
    # Generate the chart first
    chart_path = create_test_chart_with_tp_sl()
    
    # Format the Discord message
    symbol = "ENAUSDT"
    entry_price = 0.059520
    stop_loss = 0.0577
    targets = [
        {"name": "Target 1", "price": 0.0620, "size": 50},
        {"name": "Target 2", "price": 0.0640, "size": 30},
        {"name": "Target 3", "price": 0.0660, "size": 20}
    ]
    
    # Create the message
    sl_info = f"**Stop Loss:** ${stop_loss:.4f}"
    tp_info = []
    for i, target in enumerate(targets):
        tp_info.append(f"**TP{i+1}:** ${target['price']:.4f} ({target['size']}%)")
    tp_text = "\n".join(tp_info)
    
    chart_message = f"📊 **{symbol} Price Action Chart**\n\n**Entry:** ${entry_price:.4f}\n{sl_info}\n\n{tp_text}"
    
    print("\nDiscord Message #1 (Chart with TP/SL):")
    print("-" * 40)
    print(chart_message)
    print(f"\n[Attached: {os.path.basename(chart_path)}]")
    print("-" * 40)
    
    # Signal alert message
    signal_message = f"🟢 **BUY SIGNAL: {symbol}**\n\n**Confluence Score:** 69.24/100\n**Current Price:** ${entry_price:.4f}\n**Reliability:** 85%"
    
    print("\nDiscord Message #2 (Signal Alert):")
    print("-" * 40)
    print(signal_message)
    print("-" * 40)
    
    # PDF attachment message
    pdf_message = f"📈 **{symbol} BUY Signal Report (Score: 69.2)**\nDetailed analysis report attached."
    
    print("\nDiscord Message #3 (PDF Report):")
    print("-" * 40)
    print(pdf_message)
    print("\n[Attached: enausdt_buy_69p2_20250726_150930.pdf]")
    print("-" * 40)


def main():
    """Run all tests."""
    
    print("\n🧪 TESTING CHART GENERATION FUNCTIONALITY\n")
    
    # Test chart generation
    test_discord_message_with_chart()
    
    print("\n" + "=" * 60)
    print("✅ CHART GENERATION TEST COMPLETE")
    print("=" * 60)
    print("\nCheck test_output/charts/ for the generated chart image.")
    print("The chart should show:")
    print("  - Entry price (green solid line)")
    print("  - Stop loss (red dashed line)")
    print("  - Target levels (orange dot-dash lines)")
    print("  - Price action candles")
    print("  - Dark theme matching Discord")


if __name__ == "__main__":
    main()