"""
Unified Chart Generation System for Virtuoso Trading Platform
Standardizes all backend chart generation with consistent styling and performance
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server use
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import pandas as pd
import numpy as np
import io
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
import logging
from pathlib import Path

# Silence matplotlib warnings
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

class VirtuosoChartGenerator:
    """
    Unified chart generator with consistent Virtuoso theme
    Optimized for financial data visualization
    """
    
    def __init__(self):
        self.theme = self._get_theme_config()
        self._setup_matplotlib_defaults()
        self.logger = logging.getLogger(__name__)
        
        # Performance optimizations
        plt.ioff()  # Turn off interactive mode
    
    def _get_theme_config(self) -> Dict[str, Any]:
        """Get consistent theme configuration matching frontend dashboard"""
        return {
            'colors': {
                'primary': '#ffbf00',      # Amber
                'secondary': '#b8860b',    # Dark amber  
                'positive': '#4caf50',     # Green
                'negative': '#f44336',     # Red
                'warning': '#ff9900',      # Orange
                'background': '#0c1a2b',   # Navy
                'panel': '#1a2332',        # Lighter navy
                'border': '#1a2a40',       # Border color
                'text': '#ffffff',         # White text
                'text_secondary': '#b8860b', # Secondary text
                'grid': '#1a2a40'          # Grid color
            },
            'fonts': {
                'family': 'DejaVu Sans',   # Available on most systems
                'size_title': 14,
                'size_label': 11,
                'size_tick': 9,
                'weight_title': 'bold',
                'weight_label': 'normal'
            },
            'layout': {
                'figure_size': (12, 8),
                'dpi': 100,
                'tight_layout': True,
                'spine_width': 0.5
            }
        }
    
    def _setup_matplotlib_defaults(self):
        """Setup matplotlib with optimized defaults"""
        plt.rcParams.update({
            'figure.facecolor': self.theme['colors']['background'],
            'axes.facecolor': self.theme['colors']['background'],
            'axes.edgecolor': self.theme['colors']['border'],
            'axes.labelcolor': self.theme['colors']['text'],
            'axes.axisbelow': True,
            'axes.grid': True,
            'axes.linewidth': self.theme['layout']['spine_width'],
            
            'grid.color': self.theme['colors']['grid'],
            'grid.alpha': 0.3,
            'grid.linewidth': 0.5,
            
            'text.color': self.theme['colors']['text'],
            'font.family': self.theme['fonts']['family'],
            'font.size': self.theme['fonts']['size_label'],
            
            'xtick.color': self.theme['colors']['text_secondary'],
            'ytick.color': self.theme['colors']['text_secondary'],
            'xtick.labelsize': self.theme['fonts']['size_tick'],
            'ytick.labelsize': self.theme['fonts']['size_tick'],
            
            'legend.facecolor': self.theme['colors']['panel'],
            'legend.edgecolor': self.theme['colors']['border'],
            'legend.framealpha': 0.9,
            
            'figure.dpi': self.theme['layout']['dpi'],
            'savefig.dpi': self.theme['layout']['dpi'],
            'savefig.bbox': 'tight',
            'savefig.facecolor': self.theme['colors']['background'],
            'savefig.edgecolor': 'none'
        })
    
    def create_price_chart(self, 
                          data: Dict[str, Any], 
                          title: str = "Price Chart",
                          figsize: Tuple[int, int] = None,
                          save_path: Optional[str] = None) -> Union[str, bytes]:
        """
        Create standardized price chart
        
        Args:
            data: Dictionary containing 'timestamps', 'prices', 'symbol'
            title: Chart title
            figsize: Figure size tuple
            save_path: Optional path to save chart
            
        Returns:
            Base64 encoded image string or bytes if save_path provided
        """
        try:
            figsize = figsize or self.theme['layout']['figure_size']
            fig, ax = plt.subplots(figsize=figsize)
            
            # Parse data
            timestamps = pd.to_datetime(data['timestamps'])
            prices = np.array(data['prices'])
            symbol = data.get('symbol', 'UNKNOWN')
            
            # Create main price line
            line = ax.plot(timestamps, prices, 
                          color=self.theme['colors']['primary'],
                          linewidth=2, 
                          label=f'{symbol} Price',
                          alpha=0.9)[0]
            
            # Add gradient fill
            ax.fill_between(timestamps, prices, 
                           alpha=0.1, 
                           color=self.theme['colors']['primary'])
            
            # Styling
            ax.set_title(title, 
                        fontsize=self.theme['fonts']['size_title'],
                        fontweight=self.theme['fonts']['weight_title'],
                        color=self.theme['colors']['text'],
                        pad=20)
            
            ax.set_xlabel('Time', 
                         fontsize=self.theme['fonts']['size_label'],
                         color=self.theme['colors']['text'])
            
            ax.set_ylabel('Price (USD)', 
                         fontsize=self.theme['fonts']['size_label'],
                         color=self.theme['colors']['text'])
            
            # Format x-axis for time
            if len(timestamps) > 0:
                time_range = (timestamps.max() - timestamps.min()).total_seconds()
                if time_range <= 86400:  # Less than 1 day
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                elif time_range <= 604800:  # Less than 1 week  
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
                else:
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            
            # Format y-axis for price
            ax.yaxis.set_major_formatter(plt.FuncFormatter(self._format_price))
            
            # Customize legend
            legend = ax.legend(loc='upper left', 
                             frameon=True,
                             fancybox=True,
                             shadow=False)
            legend.get_frame().set_alpha(0.9)
            
            # Remove top and right spines
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            plt.tight_layout()
            
            return self._save_or_encode(fig, save_path)
            
        except Exception as e:
            self.logger.error(f"Error creating price chart: {e}")
            plt.close('all')
            return None
    
    def create_volume_chart(self,
                           data: Dict[str, Any],
                           title: str = "Volume Chart", 
                           figsize: Tuple[int, int] = None,
                           save_path: Optional[str] = None) -> Union[str, bytes]:
        """Create standardized volume chart"""
        try:
            figsize = figsize or self.theme['layout']['figure_size']
            fig, ax = plt.subplots(figsize=figsize)
            
            timestamps = pd.to_datetime(data['timestamps'])
            volumes = np.array(data['volumes'])
            prices = np.array(data.get('prices', []))
            
            # Color bars based on price direction
            colors = []
            for i, vol in enumerate(volumes):
                if i == 0 or len(prices) <= i:
                    colors.append(self.theme['colors']['text_secondary'])
                else:
                    color = (self.theme['colors']['positive'] if prices[i] >= prices[i-1] 
                            else self.theme['colors']['negative'])
                    colors.append(color)
            
            bars = ax.bar(timestamps, volumes, 
                         color=colors,
                         alpha=0.7,
                         width=0.8)
            
            # Styling
            ax.set_title(title,
                        fontsize=self.theme['fonts']['size_title'],
                        fontweight=self.theme['fonts']['weight_title'], 
                        color=self.theme['colors']['text'],
                        pad=20)
            
            ax.set_xlabel('Time',
                         fontsize=self.theme['fonts']['size_label'],
                         color=self.theme['colors']['text'])
            
            ax.set_ylabel('Volume',
                         fontsize=self.theme['fonts']['size_label'],
                         color=self.theme['colors']['text'])
            
            # Format axes
            if len(timestamps) > 0:
                time_range = (timestamps.max() - timestamps.min()).total_seconds()
                if time_range <= 86400:
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                else:
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            
            ax.yaxis.set_major_formatter(plt.FuncFormatter(self._format_volume))
            
            # Remove top and right spines
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            plt.tight_layout()
            
            return self._save_or_encode(fig, save_path)
            
        except Exception as e:
            self.logger.error(f"Error creating volume chart: {e}")
            plt.close('all')
            return None
    
    def create_confluence_indicator(self,
                                   score: float,
                                   title: str = "Confluence Score",
                                   figsize: Tuple[int, int] = (6, 6),
                                   save_path: Optional[str] = None) -> Union[str, bytes]:
        """Create standardized confluence score indicator"""
        try:
            fig, ax = plt.subplots(figsize=figsize)
            
            # Create circular progress indicator
            theta = np.linspace(0, 2*np.pi, 100)
            radius = 0.4
            
            # Background circle
            bg_x = radius * np.cos(theta)
            bg_y = radius * np.sin(theta)
            ax.plot(bg_x, bg_y, color=self.theme['colors']['border'], 
                   linewidth=8, alpha=0.3)
            
            # Score arc  
            score_theta = np.linspace(0, 2*np.pi * (score/100), int(score))
            score_x = radius * np.cos(score_theta - np.pi/2)  # Start from top
            score_y = radius * np.sin(score_theta - np.pi/2)
            
            color = self._get_score_color(score)
            ax.plot(score_x, score_y, color=color, linewidth=8)
            
            # Center text
            ax.text(0, 0, f'{score:.1f}%', 
                   ha='center', va='center',
                   fontsize=self.theme['fonts']['size_title'] + 4,
                   fontweight='bold',
                   color=self.theme['colors']['text'])
            
            # Title
            ax.set_title(title,
                        fontsize=self.theme['fonts']['size_title'],
                        fontweight=self.theme['fonts']['weight_title'],
                        color=self.theme['colors']['text'],
                        pad=20)
            
            # Remove axes and make circular
            ax.set_xlim(-0.6, 0.6)
            ax.set_ylim(-0.6, 0.6)
            ax.set_aspect('equal')
            ax.axis('off')
            
            plt.tight_layout()
            
            return self._save_or_encode(fig, save_path)
            
        except Exception as e:
            self.logger.error(f"Error creating confluence indicator: {e}")
            plt.close('all')
            return None
    
    def create_multi_symbol_comparison(self,
                                     data: Dict[str, Dict[str, Any]], 
                                     title: str = "Symbol Comparison",
                                     figsize: Tuple[int, int] = None,
                                     save_path: Optional[str] = None) -> Union[str, bytes]:
        """Create multi-symbol comparison chart"""
        try:
            figsize = figsize or (14, 8)
            fig, ax = plt.subplots(figsize=figsize)
            
            colors = [self.theme['colors']['primary'], 
                     self.theme['colors']['positive'],
                     self.theme['colors']['warning'], 
                     self.theme['colors']['negative']]
            
            for i, (symbol, symbol_data) in enumerate(data.items()):
                timestamps = pd.to_datetime(symbol_data['timestamps'])
                prices = np.array(symbol_data['prices'])
                
                # Normalize prices to percentage change
                if len(prices) > 0:
                    normalized_prices = (prices / prices[0] - 1) * 100
                    
                    color = colors[i % len(colors)]
                    ax.plot(timestamps, normalized_prices,
                           color=color, linewidth=2, 
                           label=symbol, alpha=0.8)
            
            # Styling
            ax.set_title(title,
                        fontsize=self.theme['fonts']['size_title'],
                        fontweight=self.theme['fonts']['weight_title'],
                        color=self.theme['colors']['text'],
                        pad=20)
            
            ax.set_xlabel('Time',
                         fontsize=self.theme['fonts']['size_label'],
                         color=self.theme['colors']['text'])
            
            ax.set_ylabel('Percentage Change (%)',
                         fontsize=self.theme['fonts']['size_label'],
                         color=self.theme['colors']['text'])
            
            # Add horizontal line at 0
            ax.axhline(y=0, color=self.theme['colors']['text_secondary'], 
                      linestyle='--', alpha=0.5)
            
            # Format axes
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))
            
            # Legend
            legend = ax.legend(loc='upper left', frameon=True)
            legend.get_frame().set_alpha(0.9)
            
            # Remove top and right spines
            ax.spines['top'].set_visible(False) 
            ax.spines['right'].set_visible(False)
            
            plt.tight_layout()
            
            return self._save_or_encode(fig, save_path)
            
        except Exception as e:
            self.logger.error(f"Error creating comparison chart: {e}")
            plt.close('all')
            return None
    
    # Utility methods
    def _get_score_color(self, score: float) -> str:
        """Get color based on confluence score"""
        if score >= 80:
            return self.theme['colors']['positive']
        elif score >= 60:
            return self.theme['colors']['primary']
        elif score >= 40:
            return self.theme['colors']['warning']
        else:
            return self.theme['colors']['negative']
    
    def _format_price(self, x, p):
        """Format price labels"""
        if x >= 1:
            return f'${x:.2f}'
        elif x >= 0.01:
            return f'${x:.4f}'
        else:
            return f'${x:.8f}'
    
    def _format_volume(self, x, p):
        """Format volume labels"""
        if x >= 1e9:
            return f'{x/1e9:.1f}B'
        elif x >= 1e6:
            return f'{x/1e6:.1f}M'
        elif x >= 1e3:
            return f'{x/1e3:.1f}K'
        else:
            return f'{x:.0f}'
    
    def _save_or_encode(self, fig, save_path: Optional[str]) -> Union[str, bytes]:
        """Save chart or return base64 encoded string"""
        try:
            if save_path:
                fig.savefig(save_path, 
                           facecolor=self.theme['colors']['background'],
                           edgecolor='none',
                           bbox_inches='tight',
                           dpi=self.theme['layout']['dpi'])
                plt.close(fig)
                return save_path
            else:
                buffer = io.BytesIO()
                fig.savefig(buffer, 
                           format='png',
                           facecolor=self.theme['colors']['background'],
                           edgecolor='none', 
                           bbox_inches='tight',
                           dpi=self.theme['layout']['dpi'])
                buffer.seek(0)
                image_base64 = base64.b64encode(buffer.getvalue()).decode()
                buffer.close()
                plt.close(fig)
                return f'data:image/png;base64,{image_base64}'
                
        except Exception as e:
            self.logger.error(f"Error saving/encoding chart: {e}")
            plt.close(fig)
            return None
    
    def cleanup(self):
        """Clean up matplotlib resources"""
        plt.close('all')

# Create global instance
chart_generator = VirtuosoChartGenerator()