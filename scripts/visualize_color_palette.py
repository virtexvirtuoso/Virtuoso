#!/usr/bin/env python3
"""
Color Palette Visualization for Bitcoin Beta Analysis

This script generates a visual representation of all available colors
in the Bitcoin Beta Analysis system.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def create_color_palette_visualization():
    """Create a comprehensive color palette visualization."""
    
    # Extended color palette from Bitcoin Beta Report
    colors = {
        # Major cryptocurrencies with brand colors
        'btc': '#FF6600',      # Bitcoin orange
        'eth': '#627EEA',      # Ethereum blue
        'sol': '#9945FF',      # Solana purple
        'avax': '#E84142',     # Avalanche red
        'xrp': '#23292F',      # XRP dark
        'ada': '#0033AD',      # Cardano blue
        'dot': '#E6007A',      # Polkadot pink
        'matic': '#8247E5',    # Polygon purple
        'doge': '#C2A633',     # Dogecoin gold
        'link': '#2A5ADA',     # Chainlink blue
        'ltc': '#BFBBBB',      # Litecoin silver
        'bnb': '#F3BA2F',      # Binance yellow
        
        # Meme coins with fun colors
        'shib': '#FFA409',     # Shiba Inu orange
        'pepe': '#4CAF50',     # Pepe green
        'floki': '#FFB800',    # Floki yellow
        'bonk': '#FF6B9D',     # Bonk pink
        'wif': '#FF4081',      # WIF magenta
        'fartcoin': '#8E24AA', # Fartcoin deep purple
        'moodeng': '#FF5722',  # Moodeng red-orange
        'soph': '#9C27B0',     # Soph purple
        'hype': '#E91E63',     # Hype pink
        'virtual': '#FF9800',  # Virtual orange
        
        # Additional trending tokens
        'sui': '#6FBCF0',      # Sui light blue
        'apt': '#32D74B',      # Aptos green
        'op': '#FF0420',       # Optimism red
        'arb': '#28A0F0',      # Arbitrum blue
        'near': '#00C08B',     # Near green
        'grt': '#6F4CFF',      # The Graph purple
        'mkr': '#1AAB9B',      # Maker teal
        'aave': '#B6509E',     # Aave purple
        'uni': '#FF007A',      # Uniswap pink
        'sushi': '#FA52A0',    # SushiSwap pink
        
        # Gaming and NFT tokens
        'sand': '#00D2FF',     # The Sandbox cyan
        'mana': '#FF2D55',     # Decentraland red
        'axs': '#0055D4',      # Axie Infinity blue
        'enj': '#624DBF',      # Enjin purple
        'gala': '#FAD776',     # Gala yellow
        
        # Additional vibrant colors
        'gradient1': '#FF6B35', # Vivid orange-red
        'gradient2': '#F7931E', # Bright orange
        'gradient3': '#FFD23F', # Golden yellow
        'gradient4': '#06FFA5', # Neon green
        'gradient5': '#4ECDC4', # Turquoise
        'gradient6': '#45B7D1', # Sky blue
        'gradient7': '#96CEB4', # Mint green
        'gradient8': '#FFEAA7', # Peach
        'gradient9': '#DDA0DD', # Plum
        'gradient10': '#FFB6C1', # Light pink
    }
    
    # Setup matplotlib with dark theme
    plt.style.use('dark_background')
    plt.rcParams.update({
        'figure.facecolor': '#0c1a2b',
        'axes.facecolor': '#0f172a', 
        'axes.edgecolor': '#1a2a40',
        'axes.labelcolor': '#e5e7eb',
        'xtick.color': '#e5e7eb',
        'ytick.color': '#e5e7eb',
        'text.color': '#e5e7eb',
        'font.size': 10,
        'font.family': 'monospace'
    })
    
    # Create figure
    fig, ax = plt.subplots(figsize=(16, 12))
    
    # Calculate grid dimensions
    cols = 8
    rows = (len(colors) + cols - 1) // cols
    
    # Create color swatches
    swatch_width = 0.8
    swatch_height = 0.6
    spacing_x = 1.0
    spacing_y = 0.8
    
    for i, (name, color) in enumerate(colors.items()):
        row = i // cols
        col = i % cols
        
        x = col * spacing_x
        y = (rows - row - 1) * spacing_y
        
        # Create color swatch
        rect = patches.Rectangle(
            (x, y), swatch_width, swatch_height,
            linewidth=1, edgecolor='#333', facecolor=color
        )
        ax.add_patch(rect)
        
        # Add token name
        ax.text(x + swatch_width/2, y + swatch_height + 0.05, 
               name.upper(), 
               ha='center', va='bottom', 
               fontsize=8, fontweight='bold',
               color='white')
        
        # Add hex code
        ax.text(x + swatch_width/2, y - 0.05, 
               color, 
               ha='center', va='top', 
               fontsize=7,
               color='#999')
    
    # Set title and labels
    ax.set_title('🎨 Bitcoin Beta Analysis - Extended Color Palette\n' +
                'Cryptocurrency Color Coding System', 
                fontsize=16, fontweight='bold', 
                color='#FF6600', pad=20)
    
    # Remove axes
    ax.set_xlim(-0.2, cols * spacing_x)
    ax.set_ylim(-0.3, rows * spacing_y)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    # Add footer
    fig.text(0.5, 0.02, 
            '🚀 Virtuoso Trading Bot - Enhanced Visual Identity for Quantitative Analysis',
            ha='center', va='bottom', 
            fontsize=10, color='#999')
    
    plt.tight_layout()
    
    # Save the visualization
    output_dir = Path('exports/bitcoin_beta_reports')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / 'color_palette_visualization.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', 
               facecolor='#0c1a2b', edgecolor='none')
    
    print(f"🎨 Color palette visualization saved to: {output_path}")
    plt.show()

if __name__ == "__main__":
    create_color_palette_visualization() 