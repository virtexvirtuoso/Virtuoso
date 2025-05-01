#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Confluence Heatmap Visualization

This script creates both:
1. A 3D heatmap surface visualization for the 6-dimensional confluence model
2. A 2D heatmap visualization showing component relationships
3. A 3D heatmap of price, time, and volatility for trading visualization
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.mplot3d import Axes3D
import matplotlib as mpl
from matplotlib import cm
import re
import random
from datetime import datetime, timedelta

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.append(project_root)

# Configure matplotlib for high quality output
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['figure.figsize'] = (10, 8)
plt.style.use('dark_background')

# Create output directory if it doesn't exist
output_dir = os.path.join(current_dir, "confluence_viz_output")
os.makedirs(output_dir, exist_ok=True)

# Extract data from the log
def extract_confluence_data():
    """Extract confluence component data from the log"""
    # Artificial data based on the log information provided
    components = [
        "Technical", 
        "Volume", 
        "Orderbook", 
        "Orderflow", 
        "Sentiment", 
        "Price Structure"
    ]
    
    scores = {
        "Technical": 61.80,
        "Volume": 74.30,
        "Orderbook": 68.72,
        "Orderflow": 32.46,
        "Sentiment": 52.95,
        "Price Structure": 55.45
    }
    
    # Sub-components and their scores (from log analysis)
    sub_components = {
        "Technical": {
            "RSI": 65.23,
            "MACD": 58.45,
            "Bollinger": 61.72
        },
        "Volume": {
            "OBV": 76.82,
            "Volume Profile": 71.78
        },
        "Orderbook": {
            "Imbalance": 72.34,
            "Depth": 65.10
        },
        "Orderflow": {
            "Trade Flow": 28.76,
            "Large Orders": 36.15
        },
        "Sentiment": {
            "Long/Short Ratio": 52.06,
            "Social Media": 53.84
        },
        "Price Structure": {
            "Support/Resistance": 58.92,
            "Trend": 51.98
        }
    }
    
    overall_score = 55.45  # Neutral
    overall_signal = "Neutral"
    
    return components, scores, sub_components, overall_score, overall_signal

def generate_trading_price_data(symbol, days=30, volatility=None):
    """Generate realistic price and volatility data for visualization"""
    if volatility is None:
        if symbol == "BTCUSDT":
            base_price = 65000
            volatility = 0.018  # 1.8% daily volatility
        elif symbol == "ETHUSDT":
            base_price = 3500
            volatility = 0.022  # 2.2% daily volatility
        elif symbol == "XRPUSDT":
            base_price = 0.55
            volatility = 0.025  # 2.5% daily volatility
        else:
            base_price = 100
            volatility = 0.02
    else:
        if symbol == "BTCUSDT":
            base_price = 65000
        elif symbol == "ETHUSDT":
            base_price = 3500
        elif symbol == "XRPUSDT":
            base_price = 0.55
        else:
            base_price = 100
    
    np.random.seed(42)  # For reproducibility
    
    # Generate time series
    dates = [datetime.now() - timedelta(days=i) for i in range(days)]
    dates.reverse()
    
    # Generate price with random walk
    returns = np.random.normal(0.0005, volatility, days)  # slight upward bias
    price = [base_price]
    
    for ret in returns:
        price.append(price[-1] * (1 + ret))
    
    price = price[1:]  # Remove the starting base price
    
    # Calculate realized volatility (20-period rolling)
    log_returns = np.diff(np.log(price))
    realized_vol = [np.std(log_returns[max(0, i-20):i+1])*100 for i in range(len(log_returns))]
    # Pad the beginning to match length
    realized_vol = [realized_vol[0]] + realized_vol
    
    # Calculate bullish/bearish sentiment indicators
    
    # 1. Short-term price momentum (3-day)
    price_arr = np.array(price)
    momentum_st = np.zeros(len(price))
    for i in range(3, len(price)):
        momentum_st[i] = (price[i] / price[i-3] - 1) * 100  # Percent change
    
    # 2. RSI (14-period)
    diff = np.diff(price_arr)
    diff = np.insert(diff, 0, 0)  # Add zero at the beginning
    gain = np.where(diff > 0, diff, 0)
    loss = np.where(diff < 0, -diff, 0)
    
    # Initialize
    avg_gain = np.zeros(len(gain))
    avg_loss = np.zeros(len(loss))
    
    # First values are simple averages
    avg_gain[13] = np.mean(gain[0:14])
    avg_loss[13] = np.mean(loss[0:14])
    
    # Rest use smoothing formula
    for i in range(14, len(gain)):
        avg_gain[i] = (avg_gain[i-1] * 13 + gain[i]) / 14
        avg_loss[i] = (avg_loss[i-1] * 13 + loss[i]) / 14
    
    # Calculate RS and RSI
    rs = np.zeros(len(avg_gain))
    rsi = np.zeros(len(avg_gain))
    
    for i in range(13, len(rs)):
        if avg_loss[i] == 0:
            rs[i] = 100  # To avoid division by zero
        else:
            rs[i] = avg_gain[i] / avg_loss[i]
        rsi[i] = 100 - (100 / (1 + rs[i]))
    
    # Fill beginning values
    rsi[:13] = rsi[13]
    
    # 3. Moving Average Convergence/Divergence (MACD)
    # Calculate EMA-12 and EMA-26
    ema12 = np.zeros(len(price))
    ema26 = np.zeros(len(price))
    
    # Initialize
    ema12[0] = price[0]
    ema26[0] = price[0]
    
    # Calculate EMAs
    k1 = 2 / (12 + 1)
    k2 = 2 / (26 + 1)
    
    for i in range(1, len(price)):
        ema12[i] = price[i] * k1 + ema12[i-1] * (1 - k1)
        ema26[i] = price[i] * k2 + ema26[i-1] * (1 - k2)
    
    # Calculate MACD line and signal line
    macd = ema12 - ema26
    signal = np.zeros(len(macd))
    signal[0] = macd[0]
    
    k3 = 2 / (9 + 1)
    for i in range(1, len(macd)):
        signal[i] = macd[i] * k3 + signal[i-1] * (1 - k3)
    
    # MACD histogram
    histogram = macd - signal
    
    # 4. Combine indicators to create a composite bullish/bearish score
    composite_score = np.zeros(len(price))
    
    for i in range(len(price)):
        # Normalize RSI to a -1 to 1 scale (30-70 as neutral zone)
        if rsi[i] < 30:
            rsi_component = -1 + (rsi[i] / 30)
        elif rsi[i] > 70:
            rsi_component = (rsi[i] - 70) / 30
        else:
            rsi_component = 0
        
        # Normalize momentum
        momentum_component = np.clip(momentum_st[i] / 5, -1, 1)  # 5% change = full scale
        
        # Normalize MACD histogram
        if symbol == "BTCUSDT":
            macd_scale = 500
        elif symbol == "ETHUSDT":
            macd_scale = 50
        else:
            macd_scale = 0.01
        macd_component = np.clip(histogram[i] / macd_scale, -1, 1)
        
        # Combine (weighted average)
        composite_score[i] = (0.4 * momentum_component + 0.3 * rsi_component + 0.3 * macd_component)
    
    # Scale to 0-100 for visualization (-1 to 1 -> 0 to 100)
    bullish_bearish = (composite_score + 1) * 50
    
    # Create time index (0 to days-1)
    time_idx = list(range(days))
    
    return dates, price, realized_vol, bullish_bearish, time_idx

# Create a 3D surface heatmap
def create_3d_surface(components, scores):
    """Create a 3D surface heatmap for the confluence model"""
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Create a grid for the surface
    component_indices = np.arange(len(components))
    X, Y = np.meshgrid(component_indices, component_indices)
    
    # Calculate Z values - we'll create a surface where the height represents relationship strength
    Z = np.zeros((len(components), len(components)))
    
    # Fill the Z matrix with values based on component scores
    for i in range(len(components)):
        for j in range(len(components)):
            if i == j:
                Z[i, j] = scores[components[i]]
            else:
                # Create relationship values - this is a simplified model
                # In a real system, you'd calculate actual relationships
                relationship = (scores[components[i]] + scores[components[j]]) / 2
                # Add some variation
                relationship += np.random.normal(0, 5)
                # Ensure values stay in range
                Z[i, j] = max(0, min(100, relationship))
    
    # Create a custom colormap (green to red)
    colors = [(0.0, 0.0, 0.5),  # Dark blue for low values
              (0.0, 0.8, 0.8),  # Cyan for medium-low values
              (1.0, 1.0, 0.0),  # Yellow for medium values 
              (1.0, 0.5, 0.0),  # Orange for medium-high values
              (1.0, 0.0, 0.0)]  # Red for high values
    
    cmap_name = 'confluence_cmap'
    cm = LinearSegmentedColormap.from_list(cmap_name, colors)
    
    # Plot the surface
    surf = ax.plot_surface(X, Y, Z, cmap=cm, edgecolor='none', alpha=0.8)
    
    # Component labels
    ax.set_xticks(range(len(components)))
    ax.set_yticks(range(len(components)))
    ax.set_xticklabels(components, rotation=45, ha='right', fontsize=8)
    ax.set_yticklabels(components, rotation=45, ha='right', fontsize=8)
    
    # Add colorbar
    cbar = fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
    cbar.set_label('Component Score/Relationship', fontsize=10)
    
    # Set labels
    ax.set_xlabel('Components', fontsize=12)
    ax.set_ylabel('Components', fontsize=12)
    ax.set_zlabel('Score/Relationship', fontsize=12)
    
    # Set title
    plt.title('3D Surface Visualization of Confluence Model', fontsize=14)
    
    # Adjust view angle
    ax.view_init(elev=35, azim=45)
    
    # Save figure
    output_path = os.path.join(output_dir, '3d_heatmap_surface.png')
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    
    print(f"Saved visualization to {output_path}")
    return output_path

def create_2d_heatmap(components, scores):
    """Create a 2D heatmap showing component relationships"""
    plt.figure(figsize=(10, 8))
    
    # Create a grid for the heatmap
    grid = np.zeros((len(components), len(components)))
    
    # Fill the grid with values
    for i in range(len(components)):
        for j in range(len(components)):
            if i == j:
                grid[i, j] = scores[components[i]]
            else:
                # Calculate relationship as average of scores with some noise
                grid[i, j] = (scores[components[i]] + scores[components[j]]) / 2
                grid[i, j] += np.random.normal(0, 3)  # Add noise
                grid[i, j] = max(0, min(100, grid[i, j]))  # Ensure in range
    
    # Create custom colormap
    colors = [(0.0, 0.0, 0.5),  # Dark blue
              (0.0, 0.8, 0.8),  # Cyan
              (1.0, 1.0, 0.0),  # Yellow
              (1.0, 0.5, 0.0),  # Orange
              (1.0, 0.0, 0.0)]  # Red
    
    cmap_name = 'confluence_cmap'
    custom_cmap = LinearSegmentedColormap.from_list(cmap_name, colors)
    
    # Plot heatmap
    im = plt.imshow(grid, cmap=custom_cmap, interpolation='nearest')
    
    # Add colorbar
    cbar = plt.colorbar(im)
    cbar.set_label('Component Score / Relationship Strength')
    
    # Add labels
    plt.xticks(range(len(components)), components, rotation=45, ha='right')
    plt.yticks(range(len(components)), components)
    
    # Add values in cells
    for i in range(len(components)):
        for j in range(len(components)):
            text_color = 'white' if grid[i, j] < 50 else 'black'
            plt.text(j, i, f"{grid[i, j]:.1f}", ha="center", va="center", color=text_color, fontsize=9)
    
    plt.title('Component Relationship Heatmap')
    plt.tight_layout()
    
    # Save figure
    output_path = os.path.join(output_dir, '2d_component_heatmap.png')
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    
    print(f"Saved heatmap to {output_path}")
    return output_path

def create_price_volatility_heatmap():
    """Create a 3D visualization showing price, time, and volatility with bullish/bearish coloring"""
    symbols = ["BTCUSDT", "ETHUSDT", "XRPUSDT"]
    fig = plt.figure(figsize=(16, 10))
    
    # Set figure background color to dark gray for better contrast
    fig.patch.set_facecolor('#1e1e1e')
    
    # Create subplots for each symbol
    for i, symbol in enumerate(symbols):
        # Generate data
        dates, prices, volatility, sentiment, time_idx = generate_trading_price_data(symbol, days=30)
        
        # Calculate volatility momentum (rate of change) as second metric
        vol_momentum = np.zeros_like(volatility)
        vol_momentum[1:] = np.diff(volatility)
        vol_momentum_normalized = np.clip((vol_momentum - np.min(vol_momentum)) / 
                               (np.max(vol_momentum) - np.min(vol_momentum) + 1e-8), 0, 1)
        
        # Create a meshgrid for plotting
        X, Y = np.meshgrid(time_idx, np.linspace(min(prices)*0.98, max(prices)*1.02, 50))
        Z = np.zeros_like(X)
        Z_color = np.zeros_like(X)
        Z_texture = np.zeros_like(X)  # For texture/pattern intensity
        
        # Add subplot
        ax = fig.add_subplot(1, 3, i+1, projection='3d')
        
        # Configure subplot background for contrast
        ax.set_facecolor('#1e1e1e')
        
        # Add a subtle grid for better depth perception
        ax.grid(True, alpha=0.15, linestyle='--', color='white')
        
        # Add subtle floor plane for shadow effect and depth reference
        x_min, x_max = np.min(time_idx), np.max(time_idx)
        y_min, y_max = np.min(prices) * 0.98, np.max(prices) * 1.02
        floor_z = 0
        
        # Add floor with slight transparency
        xx, yy = np.meshgrid([x_min, x_max], [y_min, y_max])
        zz = np.ones_like(xx) * floor_z
        ax.plot_surface(xx, yy, zz, color='gray', alpha=0.1)
        
        # Create the 3D surface representing volatility (height) and bullish/bearish (color)
        for t_idx in range(len(time_idx)):
            vol = volatility[t_idx]
            sent = sentiment[t_idx]
            vol_mom = vol_momentum_normalized[t_idx] if t_idx < len(vol_momentum_normalized) else 0
            # Create a gaussian distribution around the price at this time point
            price = prices[t_idx]
            for p_idx in range(Z.shape[0]):
                # Distance from the current price
                dist = abs(Y[p_idx, 0] - price) / price
                # Scale Z by volatility and distance from price
                Z[p_idx, t_idx] = vol * np.exp(-dist*100)
                # Use bullish/bearish sentiment for coloring
                Z_color[p_idx, t_idx] = sent
                # Use volatility momentum for texture intensity
                Z_texture[p_idx, t_idx] = vol_mom
        
        # Create custom colormap - bearish to bullish with distinct neutral
        # More pronounced diverging colormap with clear separation at neutral point
        colors = [
            (0.7, 0.0, 0.0),    # Deep Red (very bearish)
            (0.9, 0.2, 0.2),    # Bright Red (bearish)
            (0.95, 0.5, 0.2),   # Orange (somewhat bearish)
            (0.85, 0.85, 0.85), # Light Gray (neutral) - distinctly different
            (0.2, 0.7, 0.2),    # Light Green (somewhat bullish)
            (0.0, 0.6, 0.0),    # Green (bullish)
            (0.0, 0.4, 0.0)     # Deep Green (very bullish)
        ]
        cmap_name = 'sentiment_diverging_cmap'
        custom_cmap = LinearSegmentedColormap.from_list(cmap_name, colors)
        
        # Enhance surface with lighting for better depth perception
        from matplotlib.colors import LightSource
        ls = LightSource(azdeg=315, altdeg=45)
        
        # Combine color (from sentiment) with illumination
        # Use both color for sentiment and texture (via lighting) for volatility momentum
        
        # First create the RGB values from our colormap
        rgb = custom_cmap(Z_color/100)
        
        # Now use lighting to create the illuminated version
        illuminated = ls.shade_rgb(rgb[:, :, :3], Z, blend_mode='hsv')
        
        # Adjust alpha channel based on texture (volatility momentum)
        # Higher momentum = more solid (higher alpha)
        alpha_base = 0.6  # Base alpha
        alpha_range = 0.3  # How much alpha can vary
        
        # Create a copy of illuminated with alpha channel
        illuminated_with_alpha = np.zeros((illuminated.shape[0], illuminated.shape[1], 4))
        illuminated_with_alpha[:, :, :3] = illuminated
        
        # Set alpha based on texture (volatility momentum)
        for i_row in range(illuminated.shape[0]):
            for i_col in range(illuminated.shape[1]):
                illuminated_with_alpha[i_row, i_col, 3] = alpha_base + alpha_range * Z_texture[i_row, i_col]
        
        # Plot the enhanced surface
        surf = ax.plot_surface(
            X, Y, Z, 
            facecolors=illuminated_with_alpha,
            rstride=1, cstride=1,
            linewidth=0.5, 
            antialiased=True,
            shade=False  # We're doing our own shading
        )
        
        # Create a scalar mappable for the colorbar
        sm = plt.cm.ScalarMappable(cmap=custom_cmap)
        sm.set_array(sentiment)
        
        # Plot the price line with shadow effect
        ax.plot(time_idx, prices, [0]*len(prices), color='white', linewidth=2.5)
        # Add shadow to price line on the floor for depth
        ax.plot(time_idx, prices, [floor_z]*len(prices), color='white', linewidth=1.5, alpha=0.3)
        
        # Add points with both color (sentiment) and size (volatility)
        scatter = ax.scatter(
            time_idx, 
            prices, 
            volatility, 
            c=sentiment, 
            cmap=custom_cmap, 
            s=30,  # Use fixed size for scatter points
            alpha=0.8, 
            vmin=0, 
            vmax=100,
            edgecolors='white',  # Add white outline for better visibility
            linewidths=0.5
        )
        
        # Connect points to floor with thin lines for better depth perception
        for j in range(len(time_idx)):
            ax.plot(
                [time_idx[j], time_idx[j]], 
                [prices[j], prices[j]], 
                [volatility[j], floor_z], 
                color='white', 
                alpha=0.1, 
                linewidth=0.5
            )
        
        # Set axis labels and title
        ax.set_xlabel('Time (days)', fontsize=9, labelpad=10)
        ax.set_ylabel('Price', fontsize=9, labelpad=10)
        ax.set_zlabel('Volatility (%)', fontsize=9, labelpad=10)
        ax.set_title(f'{symbol} Price & Sentiment Surface', fontsize=12, pad=10, color='white')
        
        # Customize ticks for better readability
        date_labels = [d.strftime('%m-%d') for d in dates[::5]]
        ax.set_xticks(time_idx[::5])
        ax.set_xticklabels(date_labels, rotation=45, fontsize=7)
        
        # Format price ticks based on symbol
        if symbol == "BTCUSDT" or symbol == "ETHUSDT":
            price_ticks = np.linspace(min(prices), max(prices), 5)
            ax.set_yticks(price_ticks)
            ax.set_yticklabels([f"${p:.0f}" for p in price_ticks], fontsize=7)
        else:
            price_ticks = np.linspace(min(prices), max(prices), 5)
            ax.set_yticks(price_ticks)
            ax.set_yticklabels([f"${p:.3f}" for p in price_ticks], fontsize=7)
        
        # Improved tick and label styling
        ax.tick_params(axis='x', colors='white', labelsize=7)
        ax.tick_params(axis='y', colors='white', labelsize=7)
        ax.tick_params(axis='z', colors='white', labelsize=7)
        
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.zaxis.label.set_color('white')
        
        # Add colorbar for sentiment
        if i == 2:  # Only add colorbar to the last plot to save space
            cbar = fig.colorbar(sm, ax=ax, shrink=0.5, aspect=5)
            cbar.set_label('Bullish/Bearish Sentiment', fontsize=9, color='white')
            cbar.ax.tick_params(labelsize=7, colors='white')
            cbar.set_ticks([0, 25, 50, 75, 100])
            cbar.set_ticklabels(['Very\nBearish', 'Bearish', 'Neutral', 'Bullish', 'Very\nBullish'])
            cbar.outline.set_edgecolor('white')
            
            # Add second colorbar for the opacity/texture (volatility momentum)
            # Use a simple text label instead of a second colorbar to avoid layout issues
            ax.text2D(0.88, 0.90, 'Volatility\nMomentum', transform=ax.transAxes, 
                   color='white', fontsize=9, ha='center')
            ax.text2D(0.88, 0.85, 'Low', transform=ax.transAxes, 
                   color='white', fontsize=7, ha='center')
            ax.text2D(0.88, 0.80, 'Medium', transform=ax.transAxes, 
                   color='white', fontsize=7, ha='center')
            ax.text2D(0.88, 0.75, 'High', transform=ax.transAxes, 
                   color='white', fontsize=7, ha='center')
        
        # Adjust the view
        ax.view_init(elev=30, azim=-60)
        
        # Set axis properties for better depth perception
        ax.xaxis._axinfo["grid"]['color'] = (1, 1, 1, 0.2)
        ax.yaxis._axinfo["grid"]['color'] = (1, 1, 1, 0.2)
        ax.zaxis._axinfo["grid"]['color'] = (1, 1, 1, 0.2)
        
        # Set background color for axes panes
        ax.xaxis.set_pane_color((0.1, 0.1, 0.1, 0.9))
        ax.yaxis.set_pane_color((0.1, 0.1, 0.1, 0.9))
        ax.zaxis.set_pane_color((0.1, 0.1, 0.1, 0.9))
        
        # Add custom grid lines for better depth perception - X direction
        for y in price_ticks:
            ax.plot([x_min, x_max], [y, y], [floor_z, floor_z], 
                   color='white', alpha=0.1, linestyle='-', linewidth=0.5)
            
        # Custom grid lines - Y direction
        for x in ax.get_xticks():
            if x >= x_min and x <= x_max:
                ax.plot([x, x], [y_min, y_max], [floor_z, floor_z], 
                       color='white', alpha=0.1, linestyle='-', linewidth=0.5)
                
        # Add axis labels at the end of each axis for better orientation
        # X-axis arrow and label
        arrow_len = (x_max - x_min) * 0.05
        ax.quiver(x_max + arrow_len, y_min, floor_z, 
                 arrow_len, 0, 0, color='white', alpha=0.6, 
                 arrow_length_ratio=0.3, linewidth=0.5)
        ax.text(x_max + arrow_len*2, y_min, floor_z, 'Time', 
               color='white', fontsize=8, ha='center')
        
        # Y-axis arrow and label
        arrow_len = (y_max - y_min) * 0.05
        ax.quiver(x_min, y_max + arrow_len, floor_z, 
                 0, arrow_len, 0, color='white', alpha=0.6, 
                 arrow_length_ratio=0.3, linewidth=0.5)
        ax.text(x_min, y_max + arrow_len*2, floor_z, 'Price', 
               color='white', fontsize=8, ha='center')
        
        # Z-axis arrow and label
        max_vol = max(volatility) * 1.2
        ax.quiver(x_min, y_min, max_vol, 
                 0, 0, max_vol*0.1, color='white', alpha=0.6, 
                 arrow_length_ratio=0.3, linewidth=0.5)
        ax.text(x_min, y_min, max_vol*1.2, 'Volatility', 
               color='white', fontsize=8, ha='center')
    
    plt.subplots_adjust(left=0.01, right=0.99, bottom=0.05, top=0.95, wspace=0.05)
    
    # Save figure
    output_path = os.path.join(output_dir, '3d_price_volatility_sentiment.png')
    plt.savefig(output_path, bbox_inches='tight', facecolor='#1e1e1e')
    plt.close()
    
    print(f"Saved enhanced trading visualization to {output_path}")
    return output_path

def main():
    """Main function to run the visualization"""
    # Extract data
    components, scores, sub_components, overall_score, overall_signal = extract_confluence_data()
    
    # Create visualizations
    surface_path = create_3d_surface(components, scores)
    heatmap_path = create_2d_heatmap(components, scores)
    vol_price_path = create_price_volatility_heatmap()
    
    print("Visualizations generated successfully.")

if __name__ == "__main__":
    main() 