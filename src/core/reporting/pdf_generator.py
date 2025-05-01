#!/usr/bin/env python3
"""
PDF Report Generator for Trading Signals.
Creates detailed PDF reports with charts for trading signals.
"""

import os
import json
import logging
import tempfile
import socket
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

# Import the CustomJSONEncoder for proper serialization
from src.utils.json_encoder import CustomJSONEncoder

# Import and apply matplotlib silencing before matplotlib imports
from src.utils.matplotlib_utils import silence_matplotlib_logs
silence_matplotlib_logs()

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from fpdf import FPDF
import mplfinance as mpf
from matplotlib.figure import Figure
import base64

# Set matplotlib style for dark mode
plt.style.use('dark_background')


class ReportGenerator:
    """
    Generates PDF reports for trading signals with charts.
    
    This class creates detailed PDF reports for trading signals, including:
    - Component score breakdown charts
    - Candlestick charts with buy/sell zones
    - Detailed signal information
    - JSON data export
    
    The reports use a dark-mode styling for better readability.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, template_dir: Optional[str] = None, log_level: int = logging.INFO):
        """
        Initialize the ReportGenerator.
        
        Args:
            config: Optional configuration dictionary
            template_dir: Directory containing HTML templates (overrides config)
            log_level: Logging level
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        
        # Store config
        self.config = config or {}
        
        # Set default template directory if not provided
        if template_dir is None:
            # Try to get template_dir from config
            if isinstance(self.config, dict) and 'template_dir' in self.config:
                template_dir = self.config.get('template_dir')
            
            # If still None, use default path
            if template_dir is None:
                # Get the directory of this file
                current_dir = os.path.dirname(os.path.abspath(__file__))
                # Navigate up to project root and then to templates
                template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))), 'templates')
        
        # Verify template directory exists
        if not os.path.exists(template_dir):
            self.logger.warning(f"Template directory does not exist: {template_dir}")
            # Try absolute path to templates in project root
            project_root = os.getcwd()
            template_dir = os.path.join(project_root, 'templates')
            self.logger.info(f"Trying alternate template directory: {template_dir}")
        
        # Verify the template file exists
        template_file = os.path.join(template_dir, 'trading_report_dark.html')
        if not os.path.exists(template_file):
            self.logger.warning(f"Template file not found: {template_file}")
            
        # Initialize Jinja environment
        self.env = Environment(loader=FileSystemLoader(template_dir))
        
        # Add custom filters
        self.env.filters['format_number'] = self._format_number
        
        # Set up matplotlib styling for dark mode
        plt.rcParams.update({
            'figure.facecolor': '#121212',
            'axes.facecolor': '#1E1E1E',
            'axes.edgecolor': '#444444',
            'axes.labelcolor': '#E0E0E0',
            'axes.grid': True,
            'grid.color': '#333333',
            'grid.linestyle': '--',
            'grid.alpha': 0.3,
            'xtick.color': '#E0E0E0',
            'ytick.color': '#E0E0E0',
            'text.color': '#E0E0E0',
            'savefig.facecolor': '#121212',
            'savefig.edgecolor': '#121212',
            'figure.figsize': (10, 6),
            'font.size': 10,
        })
        
        self._log(f"ReportGenerator initialized with template directory: {template_dir}", logging.INFO)
    
    async def generate_report(self, 
                           signal_data: Dict[str, Any],
                           ohlcv_data: Optional[pd.DataFrame] = None,
                           output_path: Optional[str] = None) -> bool:
        """
        Asynchronous method to generate a PDF report for a trading signal.
        
        Args:
            signal_data: Dictionary containing trading signal information
            ohlcv_data: Optional DataFrame with OHLCV data for charts
            output_path: Path where the PDF should be saved
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Determine output directory
            output_dir = os.path.dirname(output_path) if output_path else None
            
            # Generate the report (calling the synchronous method)
            pdf_path, json_path = self.generate_trading_report(
                signal_data=signal_data,
                ohlcv_data=ohlcv_data,
                output_dir=output_dir
            )
            
            # Check if PDF was generated successfully
            if pdf_path and os.path.exists(pdf_path):
                # If output_path was specified and is different from generated pdf_path
                if output_path and pdf_path != output_path:
                    import shutil
                    shutil.move(pdf_path, output_path)
                    self._log(f"PDF report moved to {output_path}", logging.INFO)
                
                return True
            else:
                self._log("Failed to generate PDF report", logging.ERROR)
                return False
                
        except Exception as e:
            self._log(f"Error in generate_report: {str(e)}", logging.ERROR)
            self._log(traceback.format_exc(), logging.ERROR)
            return False
    
    def _format_number(self, value: Union[int, float]) -> str:
        """
        Format a number for display.
        
        Args:
            value: Number to format
            
        Returns:
            Formatted number string
        """
        if value is None:
            return "N/A"
            
        if isinstance(value, int):
            return f"{value:,d}"
        
        # For float values, use different precision based on magnitude
        if abs(value) < 0.001:
            return f"{value:.6f}"
        elif abs(value) < 0.01:
            return f"{value:.5f}"
        elif abs(value) < 0.1:
            return f"{value:.4f}"
        elif abs(value) < 1:
            return f"{value:.3f}"
        elif abs(value) < 10:
            return f"{value:.2f}"
        elif abs(value) < 1000:
            return f"{value:.1f}"
        else:
            return f"{value:,.0f}"
    
    def _log(self, message: str, level: int = logging.DEBUG) -> None:
        """
        Log a message.
        
        Args:
            message: Message to log
            level: Logging level
        """
        self.logger.log(level, message)
    
    def _create_component_chart(self, 
                               components: Dict[str, Any], 
                               output_dir: str,
                               max_components: int = 10) -> Optional[str]:
        """
        Create a bar chart for component scores.
        
        Args:
            components: Dictionary of components with scores and impacts
            output_dir: Directory to save the chart
            max_components: Maximum number of components to display
            
        Returns:
            Path to the saved chart file or None if chart creation failed
        """
        self._log(f"Creating component chart with {len(components)} components")
        
        try:
            # Safely handle components which may contain numpy types
            processed_components = {}
            for key, value in components.items():
                # Convert any numpy types to Python native types
                if hasattr(value, 'item') and callable(getattr(value, 'item')):
                    # Direct numpy value - convert to Python float and wrap in dict
                    processed_components[key] = {'score': float(value.item())}
                elif isinstance(value, (int, float)):
                    # Regular Python numeric type - wrap in dict with score
                    processed_components[key] = {'score': float(value)}
                elif isinstance(value, dict):
                    # Component is already a dict with potentially 'score' and 'impact' keys
                    processed_dict = {}
                    for k, v in value.items():
                        # Convert numpy types to native Python types
                        if hasattr(v, 'item') and callable(getattr(v, 'item')):
                            processed_dict[k] = float(v.item())  # Convert numpy scalar to Python scalar
                        else:
                            processed_dict[k] = v
                    processed_components[key] = processed_dict
                else:
                    # Fallback for other types - use default score
                    processed_components[key] = {'score': 50.0}
            
            # Sort components by absolute score value
            sorted_components = sorted(
                processed_components.items(), 
                key=lambda x: abs(float(x[1].get('score', 0))), 
                reverse=True
            )
            
            # Limit to max_components
            if len(sorted_components) > max_components:
                sorted_components = sorted_components[:max_components]
            
            # Extract data - ensure all values are native Python types
            labels = [str(comp[0]) for comp in sorted_components]
            scores = [float(comp[1].get('score', 0)) for comp in sorted_components]
            
            # Get impacts if available, or calculate from scores
            impacts = []
            for comp in sorted_components:
                if 'impact' in comp[1]:
                    impacts.append(float(comp[1].get('impact', 0)))
                else:
                    # Calculate impact as deviation from neutral (50)
                    score = float(comp[1].get('score', 50))
                    impact = abs(score - 50) * 2  # Higher impact for scores far from neutral
                    impacts.append(impact)
            
            # Create figure with two subplots: scores and impacts
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1]})
            
            # Score colors based on value
            colors = []
            for score in scores:
                if score >= 65:
                    colors.append('#4CAF50')  # Green for bullish
                elif score <= 35:
                    colors.append('#F44336')  # Red for bearish
                else:
                    colors.append('#FFC107')  # Yellow for neutral
            
            # Plot scores
            bars = ax1.barh(labels, scores, color=colors)
            ax1.set_title('Component Scores', color='#E0E0E0')
            ax1.set_xlim(0, 100)
            ax1.axvline(x=50, color='#666666', linestyle='-', alpha=0.5)
            ax1.axvline(x=35, color='#F44336', linestyle='--', alpha=0.3)
            ax1.axvline(x=65, color='#4CAF50', linestyle='--', alpha=0.3)
            
            # Add value labels
            for bar in bars:
                width = bar.get_width()
                label_x_pos = width + 1
                ax1.text(label_x_pos, bar.get_y() + bar.get_height()/2, 
                         f'{width:.1f}', va='center', color='#E0E0E0')
            
            # Plot impacts
            impact_colors = ['#2196F3' if impact > 0 else '#999999' for impact in impacts]
            bars2 = ax2.barh(labels, impacts, color=impact_colors)
            ax2.set_title('Component Impact', color='#E0E0E0')
            
            # Add value labels for impacts
            for bar in bars2:
                width = bar.get_width()
                label_x_pos = width + 0.1
                ax2.text(label_x_pos, bar.get_y() + bar.get_height()/2, 
                         f'{width:.1f}', va='center', color='#E0E0E0')
            
            # Tight layout and save
            plt.tight_layout()
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Save figure
            chart_path = os.path.abspath(os.path.join(output_dir, 'component_chart.png'))
            plt.savefig(chart_path, dpi=120, bbox_inches='tight')
            plt.close(fig)
            
            self._log(f"Component chart saved to {chart_path}")
            return chart_path
            
        except Exception as e:
            self._log(f"Error creating component chart: {str(e)}", logging.ERROR)
            return None
    
    def _create_candlestick_chart(self,
                                 symbol: str,
                                 ohlcv_data: pd.DataFrame,
                                 entry_price: Optional[float] = None,
                                 stop_loss: Optional[float] = None,
                                 targets: Optional[List[Dict]] = None,
                                 output_dir: str = None) -> Optional[str]:
        """
        Generate a candlestick chart with buy/sell zones.
        
        Args:
            symbol: Trading symbol
            ohlcv_data: DataFrame with OHLCV data (columns: open, high, low, close, volume, timestamp)
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            targets: List of target prices with format [{'price': float, 'name': str}]
            output_dir: Directory to save the chart
            
        Returns:
            Path to the saved chart file or None if chart creation failed
        """
        self._log(f"Creating candlestick chart for {symbol}")
        
        try:
            # Ensure we have data
            if ohlcv_data is None or len(ohlcv_data) == 0:
                self._log("No OHLCV data provided for candlestick chart", logging.WARNING)
                if entry_price is not None:
                    # Create a simulated chart if we have an entry price
                    return self._create_simulated_chart(
                        symbol, entry_price, stop_loss, targets, output_dir
                    )
                return None
                
            # Create figure and axis
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), 
                                          gridspec_kw={'height_ratios': [3, 1]})
            
            # Ensure timestamp is in datetime format
            if 'timestamp' in ohlcv_data.columns and not pd.api.types.is_datetime64_any_dtype(ohlcv_data['timestamp']):
                ohlcv_data['timestamp'] = pd.to_datetime(ohlcv_data['timestamp'])
            
            # Get x-axis values (dates)
            if 'timestamp' in ohlcv_data.columns:
                dates = ohlcv_data['timestamp']
            else:
                dates = pd.date_range(end=datetime.now(), periods=len(ohlcv_data))
                
            # Plot candlesticks
            up = ohlcv_data[ohlcv_data['close'] >= ohlcv_data['open']]
            down = ohlcv_data[ohlcv_data['close'] < ohlcv_data['open']]
            
            # Plot up candles
            ax1.bar(up.index, up['high'] - up['low'], width=0.8, bottom=up['low'], color='#4CAF50', alpha=0.5)
            ax1.bar(up.index, up['close'] - up['open'], width=0.6, bottom=up['open'], color='#4CAF50')
            
            # Plot down candles
            ax1.bar(down.index, down['high'] - down['low'], width=0.8, bottom=down['low'], color='#F44336', alpha=0.5)
            ax1.bar(down.index, down['open'] - down['close'], width=0.6, bottom=down['close'], color='#F44336')
            
            # Plot entry, stop loss, and targets if provided
            if entry_price is not None:
                ax1.axhline(y=entry_price, color='#2196F3', linestyle='-', linewidth=1.5, 
                           label=f'Entry: ${self._format_number(entry_price)}')
                
            if stop_loss is not None:
                ax1.axhline(y=stop_loss, color='#F44336', linestyle='--', linewidth=1.5,
                           label=f'Stop: ${self._format_number(stop_loss)}')
                
                # Shade area between entry and stop loss
                if entry_price is not None:
                    min_idx, max_idx = 0, len(ohlcv_data) - 1
                    if entry_price > stop_loss:  # Long position
                        ax1.fill_between([min_idx, max_idx], entry_price, stop_loss, 
                                        color='#F44336', alpha=0.1)
                    else:  # Short position
                        ax1.fill_between([min_idx, max_idx], entry_price, stop_loss,
                                        color='#4CAF50', alpha=0.1)
            
            # Plot target levels
            if targets:
                for i, target in enumerate(targets):
                    if 'price' in target:
                        target_price = target['price']
                        target_name = target.get('name', f'Target {i+1}')
                        
                        # Different color for each target
                        target_colors = ['#00BCD4', '#9C27B0', '#FF9800', '#8BC34A']
                        color = target_colors[i % len(target_colors)]
                        
                        ax1.axhline(y=target_price, color=color, linestyle='-.', linewidth=1.5,
                                   label=f'{target_name}: ${self._format_number(target_price)}')
                        
                        # Shade target zones
                        if entry_price is not None:
                            min_idx, max_idx = 0, len(ohlcv_data) - 1
                            if entry_price < target_price:  # Long position target
                                ax1.fill_between([min_idx, max_idx], entry_price, target_price, 
                                                color=color, alpha=0.05)
                            else:  # Short position target
                                ax1.fill_between([min_idx, max_idx], entry_price, target_price,
                                                color=color, alpha=0.05)
            
            # Set title and labels
            ax1.set_title(f'{symbol} Price Chart', color='#E0E0E0')
            ax1.set_ylabel('Price', color='#E0E0E0')
            ax1.grid(True, alpha=0.3)
            
            # Plot volume
            if 'volume' in ohlcv_data.columns:
                volume = ohlcv_data['volume']
                ax2.bar(ohlcv_data.index, volume, color='#2196F3', alpha=0.5)
                ax2.set_ylabel('Volume', color='#E0E0E0')
                
                # Normalize volume to better fit the plot
                max_vol = volume.max()
                if max_vol > 0:
                    # Plot volume moving average
                    vol_ma = volume.rolling(window=5).mean()
                    ax2.plot(ohlcv_data.index, vol_ma, color='#FFC107', linewidth=1.5)
            
            # Set x-axis labels
            if len(dates) > 0:
                # Format dates on x-axis
                date_format = mdates.DateFormatter('%m-%d %H:%M')
                ax1.xaxis.set_major_formatter(date_format)
                ax2.xaxis.set_major_formatter(date_format)
                
                # Rotate date labels for better readability
                fig.autofmt_xdate()
            
            # Add legend
            ax1.legend(loc='upper left', framealpha=0.7)
            
            # Tight layout
            plt.tight_layout()
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Save figure
            chart_path = os.path.join(output_dir, f'{symbol.lower()}_chart.png')
            plt.savefig(chart_path, dpi=120, bbox_inches='tight')
            plt.close(fig)
            
            self._log(f"Candlestick chart saved to {chart_path}")
            return chart_path
            
        except Exception as e:
            self._log(f"Error creating candlestick chart: {str(e)}", logging.ERROR)
            return None
    
    def _create_simulated_chart(self,
                               symbol: str,
                               entry_price: float,
                               stop_loss: Optional[float] = None,
                               targets: Optional[List[Dict]] = None,
                               output_dir: str = None) -> Optional[str]:
        """
        Create a simulated price chart when no OHLCV data is available.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            targets: List of target prices with format [{'price': float, 'name': str}]
            output_dir: Directory to save the chart
            
        Returns:
            Path to the saved chart file or None if chart creation failed
        """
        self._log(f"Creating simulated chart for {symbol}")
        
        try:
            # Create figure and axis
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Generate some realistic-looking price data around the entry price
            periods = 50  # Number of candles to generate
            volatility = 0.02  # 2% volatility
            price_range = entry_price * volatility
            
            # Generate random walk prices centered around entry_price
            np.random.seed(42)  # For reproducibility
            price_changes = np.random.normal(0, price_range / 3, periods)
            prices = np.cumsum(price_changes) + entry_price
            
            # Ensure the last price is close to entry price
            prices[-1] = entry_price * (1 + np.random.normal(0, 0.002))
            
            # Generate OHLC data
            opens = prices[:-1]
            closes = prices[1:]
            
            # Add some randomness to highs and lows
            highs = np.maximum(opens, closes) + np.random.uniform(0, price_range / 2, periods - 1)
            lows = np.minimum(opens, closes) - np.random.uniform(0, price_range / 2, periods - 1)
            
            # Generate dates
            end_date = datetime.now()
            dates = pd.date_range(end=end_date, periods=periods)[:-1]
            
            # Create DataFrame
            ohlc_df = pd.DataFrame({
                'timestamp': dates,
                'open': opens,
                'high': highs,
                'low': lows,
                'close': closes
            })
            
            # Plot candlesticks
            up = ohlc_df[ohlc_df['close'] >= ohlc_df['open']]
            down = ohlc_df[ohlc_df['close'] < ohlc_df['open']]
            
            # Plot up candles
            ax.bar(up.index, up['high'] - up['low'], width=0.8, bottom=up['low'], 
                  color='#4CAF50', alpha=0.5)
            ax.bar(up.index, up['close'] - up['open'], width=0.6, bottom=up['open'], 
                  color='#4CAF50')
            
            # Plot down candles
            ax.bar(down.index, down['high'] - down['low'], width=0.8, bottom=down['low'], 
                  color='#F44336', alpha=0.5)
            ax.bar(down.index, down['open'] - down['close'], width=0.6, bottom=down['close'], 
                  color='#F44336')
            
            # Plot entry price
            ax.axhline(y=entry_price, color='#2196F3', linestyle='-', linewidth=1.5, 
                      label=f'Entry: ${self._format_number(entry_price)}')
            
            # Plot stop loss
            if stop_loss is not None:
                ax.axhline(y=stop_loss, color='#F44336', linestyle='--', linewidth=1.5,
                          label=f'Stop: ${self._format_number(stop_loss)}')
                
                # Shade area between entry and stop loss
                min_idx, max_idx = 0, len(ohlc_df) - 1
                if entry_price > stop_loss:  # Long position
                    ax.fill_between([min_idx, max_idx], entry_price, stop_loss, 
                                   color='#F44336', alpha=0.1)
                else:  # Short position
                    ax.fill_between([min_idx, max_idx], entry_price, stop_loss,
                                   color='#4CAF50', alpha=0.1)
            
            # Plot target levels
            if targets:
                for i, target in enumerate(targets):
                    if 'price' in target:
                        target_price = target['price']
                        target_name = target.get('name', f'Target {i+1}')
                        
                        # Different color for each target
                        target_colors = ['#00BCD4', '#9C27B0', '#FF9800', '#8BC34A']
                        color = target_colors[i % len(target_colors)]
                        
                        ax.axhline(y=target_price, color=color, linestyle='-.', linewidth=1.5,
                                  label=f'{target_name}: ${self._format_number(target_price)}')
                        
                        # Shade target zones
                        min_idx, max_idx = 0, len(ohlc_df) - 1
                        if entry_price < target_price:  # Long position target
                            ax.fill_between([min_idx, max_idx], entry_price, target_price, 
                                           color=color, alpha=0.05)
                        else:  # Short position target
                            ax.fill_between([min_idx, max_idx], entry_price, target_price,
                                           color=color, alpha=0.05)
            
            # Set title and labels
            ax.set_title(f'{symbol} Price Chart (Simulated)', color='#E0E0E0')
            ax.set_ylabel('Price', color='#E0E0E0')
            ax.set_xlabel('Time', color='#E0E0E0')
            ax.grid(True, alpha=0.3)
            
            # Add legend
            ax.legend(loc='upper left', framealpha=0.7)
            
            # Tight layout
            plt.tight_layout()
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Save figure
            chart_path = os.path.join(output_dir, f'{symbol.lower()}_chart.png')
            plt.savefig(chart_path, dpi=120, bbox_inches='tight')
            plt.close(fig)
            
            self._log(f"Simulated chart saved to {chart_path}")
            return chart_path
            
        except Exception as e:
            self._log(f"Error creating simulated chart: {str(e)}", logging.ERROR)
            return None
    
    def _export_json_data(self, data: Dict, filename: str, output_dir: str) -> Optional[str]:
        """
        Export trading signal data to JSON file.
        
        Args:
            data: Data to export
            filename: Name of the output file
            output_dir: Directory to save the file
            
        Returns:
            Path to the saved JSON file or None if export failed
        """
        self._log(f"Exporting JSON data to {filename}")
        
        try:
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Import CustomJSONEncoder
            from src.utils.json_encoder import CustomJSONEncoder
            
            # Save to file using CustomJSONEncoder
            json_path = os.path.join(output_dir, filename)
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2, cls=CustomJSONEncoder)
                
            self._log(f"JSON data exported to {json_path}")
            return json_path
            
        except Exception as e:
            self._log(f"Error exporting JSON data: {str(e)}", logging.ERROR)
            return None
    
    def _prepare_for_json(self, obj: Any) -> Any:
        """
        Convert objects to JSON serializable types.
        
        Args:
            obj: Object to convert
            
        Returns:
            JSON serializable object
        """
        if isinstance(obj, dict):
            return {k: self._prepare_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._prepare_for_json(item) for item in obj]
        elif isinstance(obj, (datetime, pd.Timestamp)):
            return obj.isoformat()
        elif hasattr(pd, 'Timestamp') and isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32, np.float16)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient='records')
        elif isinstance(obj, pd.Series):
            return obj.to_dict()
        else:
            return obj
    
    def generate_trading_report(self, 
                               signal_data: Dict[str, Any],
                               ohlcv_data: Optional[pd.DataFrame] = None,
                               output_dir: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate a PDF trading report from the provided signal data.
        
        Args:
            signal_data: Dictionary containing trading signal information
            ohlcv_data: Optional DataFrame with OHLCV data for candlestick chart
            output_dir: Directory to save the report (defaults to a temporary directory)
            
        Returns:
            Tuple of (pdf_path, json_path) or (None, None) if generation failed
        """
        try:
            # Ensure output directory exists
            output_dir = output_dir or os.path.join("reports", "pdf")
            os.makedirs(output_dir, exist_ok=True)
            
            # Initialize context for template rendering
            context = {}
            
            # Extract basic signal data
            symbol = signal_data.get('symbol', 'UNKNOWN')
            signal_type = signal_data.get('signal_type', 'UNKNOWN')
            score = signal_data.get('score', 0)
            price = signal_data.get('price', 0)
            timestamp = signal_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            reliability = signal_data.get('reliability', 0.5)
            
            # Add basic data to context
            context.update({
                'symbol': symbol,
                'signal_type': signal_type,
                'score': score,
                'price': price,
                'timestamp': timestamp,
                'reliability': reliability
            })
            
            # Create output file path
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"{symbol}_{signal_type}_{timestamp_str}.pdf"
            pdf_path = os.path.join(output_dir, pdf_filename)
            
            # Create candlestick chart if OHLCV data is provided
            candlestick_chart = None
            try:
                if ohlcv_data is not None and not ohlcv_data.empty:
                    self._log("Creating candlestick chart from OHLCV data")
                    
                    # Get trade parameters if available
                    trade_params = signal_data.get('trade_params', {})
                    entry_price = trade_params.get('entry_price', None)
                    stop_loss = trade_params.get('stop_loss', None)
                    targets = trade_params.get('targets', None)
                    
                    # Create chart
                    candlestick_chart = self._create_candlestick_chart(
                        symbol=symbol,
                        ohlcv_data=ohlcv_data,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        targets=targets,
                        output_dir=output_dir
                    )
                elif signal_data.get('trade_params', None):
                    self._log("Creating simulated chart from trade parameters")
                    
                    # Get trade parameters
                    trade_params = signal_data.get('trade_params', {})
                    entry_price = trade_params.get('entry_price', price)
                    stop_loss = trade_params.get('stop_loss', None)
                    targets = trade_params.get('targets', None)
                    
                    # Create simulated chart
                    candlestick_chart = self._create_simulated_chart(
                        symbol=symbol,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        targets=targets,
                        output_dir=output_dir
                    )
            except Exception as e:
                self._log(f"Error creating candlestick chart: {str(e)}", level=logging.ERROR)
            
            # Add chart to template context
            context['candlestick_chart'] = candlestick_chart
            
            # Create component chart image
            component_chart = None
            confluence_analysis_image = None
            
            try:
                components = signal_data.get('components', {})
                
                self._log(f"Components type: {type(components)}")
                self._log(f"Components for chart: {list(components.keys()) if isinstance(components, dict) else 'None'}")
                
                if components and isinstance(components, dict):
                    component_chart = self._create_component_chart(components, output_dir)
                    self._log(f"Component chart created: {component_chart is not None}")
                    
                    # Add confluence visualization
                    try:
                        from src.monitoring.visualizers.confluence_visualizer import ConfluenceVisualizer
                        
                        # Extract component scores
                        component_scores = {}
                        component_keys = {
                            'technical': 'Technical',
                            'volume': 'Volume',
                            'orderbook': 'Orderbook',
                            'orderflow': 'Orderflow',
                            'sentiment': 'Sentiment',
                            'price_structure': 'Price Structure'
                        }
                        
                        for key, display_name in component_keys.items():
                            comp_value = components.get(key, {})
                            
                            # Handle different data types for component values
                            if isinstance(comp_value, dict):
                                score = comp_value.get('score', 50)
                            elif isinstance(comp_value, (int, float)):
                                score = float(comp_value)
                            elif hasattr(comp_value, 'item') and callable(getattr(comp_value, 'item')):
                                # Handle numpy values
                                score = float(comp_value.item())
                            else:
                                score = 50  # Default value
                                
                            component_scores[display_name] = score
                        
                        overall_score = signal_data.get('score', 50)
                        
                        # Create radar visualization
                        visualizer = ConfluenceVisualizer()
                        confluence_visualization = visualizer.generate_base64_image(component_scores, overall_score)
                        
                        # Save 3D visualization for possible linking in HTML reports
                        symbol = signal_data.get('symbol', 'UNKNOWN')
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        _, threed_path = visualizer.save_visualizations(
                            component_scores=component_scores,
                            overall_score=overall_score,
                            symbol=symbol,
                            timestamp=timestamp
                        )
                        
                        self._log(f"Created confluence visualization and 3D chart at: {threed_path}")
                        
                        # Add to template context
                        context['confluence_visualization'] = confluence_visualization
                        context['confluence_3d_link'] = os.path.abspath(threed_path)
                    except Exception as e:
                        self._log(f"Error creating confluence visualization: {str(e)}", level=logging.ERROR)
            except Exception as e:
                self._log(f"Error creating component chart: {str(e)}", level=logging.ERROR)
            
            # Create confluence analysis image if text is provided
            try:
                confluence_text = signal_data.get('confluence_analysis', None)
                if confluence_text and isinstance(confluence_text, str):
                    self._log("Creating confluence analysis image from text")
                    confluence_analysis_image = self._create_confluence_image(
                        confluence_text, 
                        output_dir,
                        symbol=symbol,
                        timestamp=timestamp,
                        signal_type=signal_type
                    )
            except Exception as e:
                self._log(f"Error creating confluence analysis image: {str(e)}", level=logging.ERROR)
            
            # Add images to template context
            context['component_chart'] = component_chart
            context['confluence_analysis'] = confluence_analysis_image
            
            # Prepare component data for the template
            component_data = []
            try:
                if isinstance(components, dict):
                    for name, data in components.items():
                        # Debug log the component data
                        self._log(f"Processing component: {name} with data type: {type(data)}")
                        
                        # Handle different component formats
                        if isinstance(data, dict):
                            score_value = float(data.get('score', 0))
                            impact = data.get('impact', 0)
                            interpretation = data.get('interpretation', '')
                        elif isinstance(data, (int, float)) or (hasattr(data, 'item') and callable(getattr(data, 'item'))):
                            # Handle direct numeric value or numpy type
                            score_value = float(data) if isinstance(data, (int, float)) else float(data.item())
                            impact = abs(score_value - 50) * 2  # Calculate impact from score
                            interpretation = ''
                        else:
                            self._log(f"Warning: Component {name} has unexpected data type: {type(data)}")
                            continue
                        
                        # Determine color class based on score
                        if score_value >= 65:
                            color_class = "high-score"
                        elif score_value <= 35:
                            color_class = "low-score"
                        else:
                            color_class = "medium-score"
                        
                        component_data.append({
                            'name': name,
                            'score': score_value,
                            'impact': impact,
                            'interpretation': interpretation,
                            'color_class': color_class
                        })
                    
                    # Sort components by impact
                    component_data.sort(key=lambda x: abs(x['impact']), reverse=True)
            except Exception as e:
                self._log(f"Error processing components: {str(e)}", logging.ERROR)
            
            # Format timestamp
            formatted_timestamp = ""
            try:
                if isinstance(timestamp, str):
                    try:
                        timestamp_dt = datetime.fromisoformat(timestamp)
                        formatted_timestamp = timestamp_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                    except:
                        formatted_timestamp = timestamp
                elif isinstance(timestamp, datetime):
                    formatted_timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
                elif isinstance(timestamp, (int, float)):
                    # Handle timestamp as Unix time
                    timestamp_dt = datetime.fromtimestamp(timestamp / 1000 if timestamp > 1e12 else timestamp)
                    formatted_timestamp = timestamp_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                else:
                    formatted_timestamp = str(timestamp)
            except Exception as e:
                self._log(f"Error formatting timestamp: {str(e)}", logging.ERROR)
                formatted_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
            
            # Get hostname
            hostname = "unknown"
            try:
                hostname = socket.gethostname()
            except Exception as e:
                self._log(f"Error getting hostname: {str(e)}", logging.ERROR)
            
            # Extract market insights and actionable insights
            insights = []
            actionable_insights = []
            try:
                insights = signal_data.get('insights', [])
                actionable_insights = signal_data.get('actionable_insights', [])
            except Exception as e:
                self._log(f"Error extracting insights: {str(e)}", logging.ERROR)
            
            # Extract risk management details
            entry_price = price
            stop_loss = None
            stop_loss_percent = 0
            try:
                entry_price = signal_data.get('entry_price', price)
                stop_loss = signal_data.get('stop_loss', None)
                
                if stop_loss and entry_price:
                    if entry_price > stop_loss:  # Long position
                        stop_loss_percent = ((stop_loss / entry_price) - 1) * 100
                    else:  # Short position
                        stop_loss_percent = ((entry_price / stop_loss) - 1) * 100
            except Exception as e:
                self._log(f"Error extracting risk management details: {str(e)}", logging.ERROR)
            
            # Format targets
            targets = []
            try:
                targets_data = signal_data.get('targets', {})
                
                if isinstance(targets_data, dict):
                    for target_name, target_data in targets_data.items():
                        if isinstance(target_data, dict) and 'price' in target_data:
                            target_price = target_data.get("price", 0)
                            target_size = target_data.get("size", 0)
                            
                            if target_price > 0:
                                target_percent = 0
                                if entry_price > 0:
                                    if target_price > entry_price:  # Long position
                                        target_percent = ((target_price / entry_price) - 1) * 100
                                    else:  # Short position
                                        target_percent = ((entry_price / target_price) - 1) * 100
                                
                                targets.append({
                                    'name': target_name,
                                    'price': target_price,
                                    'percent': target_percent,
                                    'size': target_size
                                })
            except Exception as e:
                self._log(f"Error formatting targets: {str(e)}", logging.ERROR)
            
            # Export JSON data
            json_path = None
            try:
                json_filename = f"{symbol.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                json_path = self._export_json_data(signal_data, json_filename, output_dir)
            except Exception as e:
                self._log(f"Error exporting JSON data: {str(e)}", logging.ERROR)
            
            # Get the relative path for JSON (for display in PDF)
            if json_path:
                json_rel_path = os.path.basename(json_path)
            else:
                json_rel_path = "Not available"
            
            # Prepare template context
            context = {
                'symbol': symbol,
                'score': score,
                'reliability': reliability,
                'price': price,
                'timestamp': formatted_timestamp,
                'signal_type': signal_type,
                'signal_color': signal_type,
                'component_data': component_data,
                'insights': insights,
                'actionable_insights': actionable_insights,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'stop_loss_percent': stop_loss_percent,
                'targets': targets,
                'hostname': hostname,
                'json_path': json_rel_path,
                'candlestick_chart': os.path.abspath(candlestick_chart) if candlestick_chart else None,
                'component_chart': os.path.abspath(component_chart) if component_chart else None,
                'confluence_analysis': confluence_analysis_image,
                'confluence_visualization': confluence_visualization
            }
            
            # Render the HTML template
            try:
                template = self.env.get_template('trading_report_dark.html')
                
                # Fix image paths by ensuring they are absolute and using file:// protocol
                if candlestick_chart:
                    candlestick_chart = f"file://{os.path.abspath(candlestick_chart)}"
                if component_chart:
                    component_chart = f"file://{os.path.abspath(component_chart)}"
                if confluence_analysis_image:
                    confluence_analysis_image = f"file://{os.path.abspath(confluence_analysis_image)}"
                if confluence_visualization:
                    confluence_visualization = f"file://{os.path.abspath(confluence_visualization)}"
                
                # Update context with fixed image paths
                context.update({
                    'candlestick_chart': candlestick_chart,
                    'component_chart': component_chart,
                    'confluence_analysis': confluence_analysis_image,
                    'confluence_visualization': confluence_visualization
                })
                
                html_content = template.render(**context)
            except Exception as e:
                self._log(f"Error rendering HTML template: {str(e)}", logging.ERROR)
                return None, json_path
            
            # Generate PDF
            try:
                pdf_filename = f"{symbol.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                pdf_path = os.path.join(output_dir, pdf_filename)
                
                # Create PDF from HTML
                HTML(string=html_content).write_pdf(pdf_path)
                
                self._log(f"Trading report generated: {pdf_path}")
                return pdf_path, json_path
            except Exception as e:
                self._log(f"Error generating PDF: {str(e)}", logging.ERROR)
                return None, json_path
            
        except Exception as e:
            self._log(f"Error generating trading report: {str(e)}", logging.ERROR)
            self._log(traceback.format_exc(), logging.ERROR)
            return None, None

    async def generate_market_report(self, market_data: dict, output_path: Optional[str] = None) -> bool:
        """Generate a basic market report PDF without using HTML templates.
        This is the fallback method when HTML templating fails.
        
        Args:
            market_data: Dictionary containing market data for the report
            output_path: Optional path to save the PDF
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Input validation
            if market_data is None:
                self.logger.error("Market data is None, cannot generate report")
                return False
                
            if not isinstance(market_data, dict):
                self.logger.error(f"Market data must be a dictionary, got {type(market_data)}")
                try:
                    market_data = dict(market_data)
                    self.logger.info("Successfully converted market_data to dictionary")
                except (TypeError, ValueError) as e:
                    self.logger.error(f"Could not convert market_data to dictionary: {str(e)}")
                    self.logger.debug(f"market_data contents: {market_data}")
                    return False
            
            self.logger.debug(f"Market data has {len(market_data)} keys: {list(market_data.keys())}")
            
            # Create a PDF document
            self.logger.debug("Creating PDF document")
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                from reportlab.lib import colors
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
                
                self.logger.debug("Required reportlab modules imported successfully")
            except ImportError as import_error:
                self.logger.error(f"Failed to import reportlab modules: {str(import_error)}")
                return False
            
            # Set up output path
            if not output_path:
                try:
                    timestamp = market_data.get('timestamp', int(time.time() * 1000))
                    if isinstance(timestamp, str):
                        try:
                            timestamp = int(timestamp)
                        except ValueError:
                            timestamp = int(time.time() * 1000)
                    
                    dt = datetime.fromtimestamp(timestamp / 1000)
                    timestamp_str = dt.strftime("%Y%m%d_%H%M%S")
                    output_path = f"market_report_{timestamp_str}.pdf"
                    self.logger.debug(f"Generated output path: {output_path}")
                except Exception as path_error:
                    self.logger.error(f"Error generating output path: {str(path_error)}")
                    output_path = f"market_report_{int(time.time())}.pdf"
                    self.logger.debug(f"Using fallback output path: {output_path}")
            
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                self.logger.warning(f"Output directory does not exist: {output_dir}")
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    self.logger.info(f"Created output directory: {output_dir}")
                except Exception as dir_error:
                    self.logger.error(f"Failed to create output directory: {str(dir_error)}")
                    # Use current directory as fallback
                    output_path = os.path.basename(output_path)
                    self.logger.info(f"Using current directory for output: {output_path}")
            
            self.logger.debug(f"Setting up PDF document at: {output_path}")
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            elements = []
            
            # Set up styles
            self.logger.debug("Setting up document styles")
            try:
                styles = getSampleStyleSheet()
                title_style = styles['Title']
                heading_style = styles['Heading1']
                normal_style = styles['Normal']
                
                # Create custom styles
                timestamp_style = ParagraphStyle(
                    'Timestamp',
                    parent=normal_style,
                    fontSize=8,
                    textColor=colors.gray
                )
                
                section_title_style = ParagraphStyle(
                    'SectionTitle',
                    parent=heading_style,
                    fontSize=14,
                    spaceAfter=6
                )
                
                self.logger.debug("Document styles set up successfully")
            except Exception as style_error:
                self.logger.error(f"Error setting up document styles: {str(style_error)}")
                # Use default styles as fallback
                styles = getSampleStyleSheet()
                title_style = styles['Title']
                heading_style = styles['Heading1']
                normal_style = styles['Normal']
                timestamp_style = normal_style
                section_title_style = heading_style
            
            # Add title
            self.logger.debug("Adding report title")
            try:
                elements.append(Paragraph("Crypto Market Report", title_style))
                elements.append(Spacer(1, 12))
                
                # Add timestamp
                timestamp = market_data.get('timestamp', int(time.time() * 1000))
                try:
                    if isinstance(timestamp, str):
                        timestamp = int(timestamp)
                    dt = datetime.fromtimestamp(timestamp / 1000)
                    date_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                except (ValueError, TypeError) as timestamp_error:
                    self.logger.warning(f"Error parsing timestamp: {str(timestamp_error)}")
                    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
                
                elements.append(Paragraph(f"Generated: {date_str}", timestamp_style))
                elements.append(Spacer(1, 20))
                self.logger.debug(f"Added title and timestamp: {date_str}")
            except Exception as title_error:
                self.logger.error(f"Error adding title: {str(title_error)}")
            
            # Add market overview section
            if 'market_overview' in market_data:
                self.logger.debug("Adding market overview section")
                try:
                    overview = market_data['market_overview']
                    elements.append(Paragraph("Market Overview", section_title_style))
                    
                    if isinstance(overview, dict):
                        # Create a table for market overview
                        data = []
                        for key, value in overview.items():
                            formatted_key = key.replace('_', ' ').title()
                            formatted_value = str(value)
                            data.append([formatted_key, formatted_value])
                        
                        if data:
                            table = Table(data, colWidths=[200, 300])
                            table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                                ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                                ('TOPPADDING', (0, 0), (-1, -1), 6),
                                ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                            ]))
                            elements.append(table)
                        else:
                            elements.append(Paragraph("No market overview data available", normal_style))
                    else:
                        elements.append(Paragraph(f"Market overview: {str(overview)}", normal_style))
                    
                    elements.append(Spacer(1, 15))
                    self.logger.debug("Market overview section added successfully")
                except Exception as overview_error:
                    self.logger.error(f"Error adding market overview section: {str(overview_error)}")
                    elements.append(Paragraph("Market Overview: Error processing data", normal_style))
                    elements.append(Spacer(1, 15))
            
            # Add top performers section
            if 'top_performers' in market_data:
                self.logger.debug("Adding top performers section")
                try:
                    performers = market_data['top_performers']
                    elements.append(Paragraph("Top Performers", section_title_style))
                    
                    if isinstance(performers, list) and performers:
                        # Create a table for top performers
                        headers = ["Symbol", "Change %", "Price", "Category"]
                        data = [headers]
                        
                        for item in performers:
                            if isinstance(item, dict):
                                symbol = item.get('symbol', 'N/A')
                                change = item.get('change_percent', 'N/A')
                                if isinstance(change, (float, int)):
                                    change = f"{change:.2f}%"
                                price = item.get('price', 'N/A')
                                category = item.get('category', '')
                                
                                data.append([symbol, str(change), str(price), category])
                        
                        if len(data) > 1:
                            table = Table(data, colWidths=[100, 100, 100, 200])
                            table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                ('TOPPADDING', (0, 0), (-1, 0), 12),
                                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                                ('TOPPADDING', (0, 1), (-1, -1), 6),
                                ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                            ]))
                            
                            # Add color for positive/negative changes
                            for i in range(1, len(data)):
                                change_text = data[i][1]
                                if change_text.startswith('-'):
                                    table.setStyle(TableStyle([
                                        ('TEXTCOLOR', (1, i), (1, i), colors.red),
                                    ]))
                                elif any(char.isdigit() for char in change_text):
                                    table.setStyle(TableStyle([
                                        ('TEXTCOLOR', (1, i), (1, i), colors.green),
                                    ]))
                            
                            elements.append(table)
                        else:
                            elements.append(Paragraph("No top performers data available", normal_style))
                    else:
                        elements.append(Paragraph("No top performers data available", normal_style))
                    
                    elements.append(Spacer(1, 15))
                    self.logger.debug("Top performers section added successfully")
                except Exception as performers_error:
                    self.logger.error(f"Error adding top performers section: {str(performers_error)}")
                    elements.append(Paragraph("Top Performers: Error processing data", normal_style))
                    elements.append(Spacer(1, 15))
            
            # Add market sentiment section
            if 'market_sentiment' in market_data:
                self.logger.debug("Adding market sentiment section")
                try:
                    sentiment = market_data['market_sentiment']
                    elements.append(Paragraph("Market Sentiment", section_title_style))
                    
                    if isinstance(sentiment, dict):
                        # Create a table for market sentiment
                        data = []
                        for key, value in sentiment.items():
                            formatted_key = key.replace('_', ' ').title()
                            formatted_value = str(value)
                            data.append([formatted_key, formatted_value])
                        
                        if data:
                            table = Table(data, colWidths=[200, 300])
                            table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                                ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                                ('TOPPADDING', (0, 0), (-1, -1), 6),
                                ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                            ]))
                            elements.append(table)
                        else:
                            elements.append(Paragraph("No market sentiment data available", normal_style))
                    else:
                        elements.append(Paragraph(f"Market sentiment: {str(sentiment)}", normal_style))
                    
                    elements.append(Spacer(1, 15))
                    self.logger.debug("Market sentiment section added successfully")
                except Exception as sentiment_error:
                    self.logger.error(f"Error adding market sentiment section: {str(sentiment_error)}")
                    elements.append(Paragraph("Market Sentiment: Error processing data", normal_style))
                    elements.append(Spacer(1, 15))
            
            # Add trading signals section
            if 'trading_signals' in market_data:
                self.logger.debug("Adding trading signals section")
                try:
                    signals = market_data['trading_signals']
                    elements.append(Paragraph("Trading Signals", section_title_style))
                    
                    if isinstance(signals, list) and signals:
                        # Create a table for trading signals
                        headers = ["Symbol", "Signal", "Strength", "Timeframe"]
                        data = [headers]
                        
                        for signal in signals:
                            if isinstance(signal, dict):
                                symbol = signal.get('symbol', 'N/A')
                                signal_type = signal.get('signal', 'N/A')
                                strength = signal.get('strength', 'N/A')
                                timeframe = signal.get('timeframe', 'N/A')
                                
                                data.append([symbol, signal_type, str(strength), timeframe])
                        
                        if len(data) > 1:
                            table = Table(data, colWidths=[100, 100, 100, 200])
                            table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                ('TOPPADDING', (0, 0), (-1, 0), 12),
                                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                                ('TOPPADDING', (0, 1), (-1, -1), 6),
                                ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                            ]))
                            
                            # Add color for buy/sell signals
                            for i in range(1, len(data)):
                                signal_type = data[i][1].lower()
                                if 'buy' in signal_type or 'bullish' in signal_type:
                                    table.setStyle(TableStyle([
                                        ('TEXTCOLOR', (1, i), (1, i), colors.green),
                                    ]))
                                elif 'sell' in signal_type or 'bearish' in signal_type:
                                    table.setStyle(TableStyle([
                                        ('TEXTCOLOR', (1, i), (1, i), colors.red),
                                    ]))
                            
                            elements.append(table)
                        else:
                            elements.append(Paragraph("No trading signals data available", normal_style))
                    else:
                        elements.append(Paragraph("No trading signals data available", normal_style))
                    
                    elements.append(Spacer(1, 15))
                    self.logger.debug("Trading signals section added successfully")
                except Exception as signals_error:
                    self.logger.error(f"Error adding trading signals section: {str(signals_error)}")
                    elements.append(Paragraph("Trading Signals: Error processing data", normal_style))
                    elements.append(Spacer(1, 15))
            
            # Add notable news section
            if 'notable_news' in market_data:
                self.logger.debug("Adding notable news section")
                try:
                    news = market_data['notable_news']
                    elements.append(Paragraph("Notable News", section_title_style))
                    
                    if isinstance(news, list) and news:
                        for item in news:
                            if isinstance(item, dict):
                                title = item.get('title', 'N/A')
                                source = item.get('source', '')
                                summary = item.get('summary', '')
                                
                                elements.append(Paragraph(f"<b>{title}</b>", normal_style))
                                if source:
                                    elements.append(Paragraph(f"Source: {source}", timestamp_style))
                                if summary:
                                    elements.append(Paragraph(summary, normal_style))
                                elements.append(Spacer(1, 10))
                            else:
                                elements.append(Paragraph(str(item), normal_style))
                                elements.append(Spacer(1, 5))
                    else:
                        elements.append(Paragraph("No notable news data available", normal_style))
                    
                    elements.append(Spacer(1, 15))
                    self.logger.debug("Notable news section added successfully")
                except Exception as news_error:
                    self.logger.error(f"Error adding notable news section: {str(news_error)}")
                    elements.append(Paragraph("Notable News: Error processing data", normal_style))
                    elements.append(Spacer(1, 15))
            
            # Add a footer with page numbers
            self.logger.debug("Adding page footer")
            try:
                def footer(canvas, doc):
                    canvas.saveState()
                    canvas.setFont('Helvetica', 8)
                    page_num = f"Page {doc.page} of {doc.build.current_page}"
                    canvas.drawRightString(letter[0] - 30, 30, page_num)
                    canvas.restoreState()
                
                self.logger.debug("Footer function defined successfully")
            except Exception as footer_error:
                self.logger.error(f"Error defining footer function: {str(footer_error)}")
                footer = None
            
            # Build the PDF
            self.logger.debug("Building PDF document")
            try:
                if footer:
                    doc.build(elements, onFirstPage=footer, onLaterPages=footer)
                else:
                    doc.build(elements)
                    
                self.logger.info(f"Basic market report PDF generated successfully: {output_path}")
                return True
            except Exception as build_error:
                self.logger.error(f"Error building PDF document: {str(build_error)}")
                self.logger.debug(traceback.format_exc())
                
                # Try saving to a default location if output directory issues
                if output_dir and not os.path.exists(output_dir):
                    emergency_path = f"emergency_market_report_{int(time.time())}.pdf"
                    self.logger.warning(f"Trying emergency save to current directory: {emergency_path}")
                    
                    try:
                        doc = SimpleDocTemplate(emergency_path, pagesize=letter)
                        doc.build(elements)
                        self.logger.info(f"Emergency PDF save successful: {emergency_path}")
                        return True
                    except Exception as emergency_error:
                        self.logger.error(f"Emergency PDF save failed: {str(emergency_error)}")
                        return False
                return False
                
        except Exception as e:
            self.logger.error(f"Error in generate_market_report: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False

    async def generate_market_html_report(self, market_data: dict, output_path: Optional[str] = None, 
                                   template_path: Optional[str] = None, generate_pdf: bool = False) -> bool:
        """Generate an HTML market report using a template.
        
        Args:
            market_data: Dictionary containing market data for the report
            output_path: Optional path to save the HTML (and PDF if requested)
            template_path: Optional path to the HTML template
            generate_pdf: Whether to also generate a PDF from the HTML
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate market_data structure
            if market_data is None:
                self.logger.error("Market data is None, cannot generate HTML report")
                return False
                
            if not isinstance(market_data, dict):
                self.logger.error(f"Market data must be a dictionary, got {type(market_data)}")
                # Try to convert to dict if possible
                try:
                    market_data = dict(market_data)
                    self.logger.info("Successfully converted market_data to dictionary")
                except (TypeError, ValueError) as e:
                    self.logger.error(f"Could not convert market_data to dictionary: {str(e)}")
                    self.logger.debug(f"market_data contents: {market_data}")
                    return False
            
            self.logger.debug(f"Market data has {len(market_data)} keys: {list(market_data.keys())}")
            
            # Process timestamp
            timestamp = market_data.get('timestamp', int(time.time() * 1000))
            try:
                if isinstance(timestamp, str):
                    try:
                        timestamp = int(timestamp)
                    except ValueError as timestamp_error:
                        self.logger.warning(f"Could not parse timestamp '{timestamp}': {str(timestamp_error)}")
                        timestamp = int(time.time() * 1000)
                        
                dt = datetime.fromtimestamp(timestamp / 1000)
                report_date = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                market_data['report_date'] = report_date
                self.logger.debug(f"Processed timestamp {timestamp} to {report_date}")
            except Exception as timestamp_error:
                self.logger.error(f"Error processing timestamp: {str(timestamp_error)}")
                current_time = datetime.now()
                report_date = current_time.strftime("%Y-%m-%d %H:%M:%S UTC")
                market_data['report_date'] = report_date
                self.logger.info(f"Using current time for report date: {report_date}")
            
            # Process top performers - ensure it's a list
            if 'top_performers' in market_data:
                performers = market_data['top_performers']
                if isinstance(performers, dict):
                    self.logger.info("Converting top_performers from dict to list format")
                    # Convert dict format to list format
                    performers_list = []
                    for category, items in performers.items():
                        if isinstance(items, list):
                            # Add category to each item and append to main list
                            for item in items:
                                if isinstance(item, dict):
                                    item['category'] = category
                                    performers_list.append(item)
                                else:
                                    self.logger.warning(f"Skipping non-dict item in {category}: {item}")
                        else:
                            self.logger.warning(f"Unexpected format for {category} in top_performers: {items}")
                    market_data['top_performers'] = performers_list
                    self.logger.debug(f"Converted top_performers to list with {len(performers_list)} items")
                elif not isinstance(performers, list):
                    self.logger.warning(f"top_performers has unexpected type: {type(performers)}, setting to empty list")
                    market_data['top_performers'] = []
            
            # Generate the filename
            if output_path:
                html_path = output_path
                if not html_path.endswith('.html'):
                    html_path += '.html'
            else:
                # Generate a filename based on timestamp
                try:
                    timestamp_str = dt.strftime("%Y%m%d_%H%M%S")
                    html_path = f"market_report_{timestamp_str}.html"
                except Exception as e:
                    self.logger.error(f"Error generating timestamp string: {str(e)}")
                    html_path = f"market_report_{int(time.time())}.html"
            
            # Check if output directory exists
            output_dir = os.path.dirname(html_path)
            if output_dir and not os.path.exists(output_dir):
                self.logger.warning(f"Output directory does not exist: {output_dir}")
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    self.logger.info(f"Created output directory: {output_dir}")
                except Exception as dir_error:
                    self.logger.error(f"Failed to create output directory: {str(dir_error)}")
                    # Try to use a default path
                    html_path = f"market_report_{int(time.time())}.html"
                    self.logger.info(f"Using default path: {html_path}")
            
            # Check template path and load template
            template_name = "market_report_template.html"
            template_path = os.path.join(self.template_dir, template_name)
            
            # Validate template path
            if not os.path.exists(template_path):
                self.logger.error(f"Template file not found: {template_path}")
                # Check if template directory exists
                if not os.path.exists(self.template_dir):
                    self.logger.error(f"Template directory does not exist: {self.template_dir}")
                else:
                    self.logger.debug(f"Template directory exists, checking contents")
                    try:
                        templates = os.listdir(self.template_dir)
                        self.logger.info(f"Available templates: {templates}")
                    except Exception as list_error:
                        self.logger.error(f"Error listing template directory: {str(list_error)}")
                
                # Fall back to basic template
                self.logger.info("Falling back to basic report generation")
                return await self.generate_market_report(market_data, output_path)
            
            self.logger.debug(f"Loading template: {template_path}")
            try:
                env = Environment(loader=FileSystemLoader(self.template_dir))
                template = env.get_template(template_name)
                self.logger.debug("Template loaded successfully")
            except Exception as template_error:
                self.logger.error(f"Error loading template: {str(template_error)}")
                self.logger.debug(traceback.format_exc())
                
                # Check if we have permission to read the template
                try:
                    with open(template_path, 'r') as f:
                        template_content = f.read()
                    self.logger.debug(f"Template file is readable, first 100 chars: {template_content[:100]}")
                except Exception as read_error:
                    self.logger.error(f"Cannot read template file: {str(read_error)}")
                
                # Fall back to basic template
                self.logger.info("Falling back to basic report generation due to template error")
                return await self.generate_market_report(market_data, output_path)
            
            # Test render each part of the template to find problematic sections
            try:
                self.logger.debug("Testing partial renders to identify problematic sections")
                test_data = {'report_date': market_data.get('report_date', 'Unknown')}
                
                # Test basic sections
                template.render(report_date=test_data['report_date'])
                self.logger.debug("Basic report_date render successful")
                
                # Test market overview
                if 'market_overview' in market_data:
                    try:
                        overview_data = market_data['market_overview'] 
                        template.render(report_date=test_data['report_date'], market_overview=overview_data)
                        self.logger.debug("market_overview render successful")
                    except Exception as section_error:
                        self.logger.error(f"Error rendering market_overview section: {str(section_error)}")
                        # Remove problematic section
                        market_data.pop('market_overview', None)
                
                # Test top performers
                if 'top_performers' in market_data:
                    try:
                        performers_data = market_data['top_performers']
                        template.render(report_date=test_data['report_date'], top_performers=performers_data)
                        self.logger.debug("top_performers render successful")
                    except Exception as section_error:
                        self.logger.error(f"Error rendering top_performers section: {str(section_error)}")
                        # Remove problematic section
                        market_data.pop('top_performers', None)
                
                # Test market sentiment
                if 'market_sentiment' in market_data:
                    try:
                        sentiment_data = market_data['market_sentiment']
                        template.render(report_date=test_data['report_date'], market_sentiment=sentiment_data)
                        self.logger.debug("market_sentiment render successful")
                    except Exception as section_error:
                        self.logger.error(f"Error rendering market_sentiment section: {str(section_error)}")
                        # Remove problematic section
                        market_data.pop('market_sentiment', None)
                
                # Test trading signals
                if 'trading_signals' in market_data:
                    try:
                        signals_data = market_data['trading_signals']
                        template.render(report_date=test_data['report_date'], trading_signals=signals_data)
                        self.logger.debug("trading_signals render successful")
                    except Exception as section_error:
                        self.logger.error(f"Error rendering trading_signals section: {str(section_error)}")
                        # Remove problematic section
                        market_data.pop('trading_signals', None)
                
                # Test notable news
                if 'notable_news' in market_data:
                    try:
                        news_data = market_data['notable_news']
                        template.render(report_date=test_data['report_date'], notable_news=news_data)
                        self.logger.debug("notable_news render successful")
                    except Exception as section_error:
                        self.logger.error(f"Error rendering notable_news section: {str(section_error)}")
                        # Remove problematic section
                        market_data.pop('notable_news', None)
                
                self.logger.debug("All section renders tested")
            except Exception as test_error:
                self.logger.error(f"Error during test rendering: {str(test_error)}")
            
            # Render the template with market data
            try:
                self.logger.debug("Rendering full template")
                html_content = template.render(**market_data)
                self.logger.debug(f"Template rendered successfully, content length: {len(html_content)}")
            except Exception as render_error:
                self.logger.error(f"Error rendering template: {str(render_error)}")
                self.logger.debug(traceback.format_exc())
                
                # Try to diagnose common issues
                if 'market_data' in market_data:
                    self.logger.error("Found nested 'market_data' key - this is likely a duplicate nesting error")
                
                self.logger.info("Falling back to basic report generation due to render error")
                return await self.generate_market_report(market_data, output_path)
            
            # Write the HTML file
            try:
                self.logger.debug(f"Writing HTML to {html_path}")
                with open(html_path, 'w') as f:
                    f.write(html_content)
                self.logger.info(f"Market report HTML generated: {html_path}")
            except Exception as write_error:
                self.logger.error(f"Error writing HTML file: {str(write_error)}")
                self.logger.debug(traceback.format_exc())
                
                # Try to write to a default location
                try:
                    default_path = f"market_report_emergency_{int(time.time())}.html"
                    self.logger.warning(f"Attempting to write to default location: {default_path}")
                    with open(default_path, 'w') as f:
                        f.write(html_content)
                    self.logger.info(f"Successfully wrote HTML to emergency location: {default_path}")
                    html_path = default_path
                except Exception as emergency_write_error:
                    self.logger.error(f"Emergency write failed: {str(emergency_write_error)}")
                    # Fall back to basic report
                    self.logger.info("Falling back to basic report generation due to write error")
                    return await self.generate_market_report(market_data, output_path)
            
            # Generate PDF from HTML if requested
            if self.generate_pdf:
                try:
                    self.logger.debug("Attempting to generate PDF from HTML")
                    pdf_path = html_path.replace('.html', '.pdf')
                    
                    # Import pdfkit only when needed
                    try:
                        import pdfkit
                        
                        # Check if wkhtmltopdf is accessible
                        try:
                            config = pdfkit.configuration()
                            self.logger.debug(f"Using wkhtmltopdf at: {config.wkhtmltopdf}")
                        except Exception as config_error:
                            self.logger.warning(f"wkhtmltopdf configuration issue: {str(config_error)}")
                            config = None
                            
                        self.logger.debug(f"Converting HTML to PDF: {pdf_path}")
                        pdfkit.from_file(html_path, pdf_path, configuration=config)
                        self.logger.info(f"PDF generated: {pdf_path}")
                    except ImportError:
                        self.logger.warning("pdfkit not installed, skipping PDF generation")
                except Exception as pdf_error:
                    self.logger.error(f"Error generating PDF from HTML: {str(pdf_error)}")
                    self.logger.debug(traceback.format_exc())
                    # Continue without PDF generation
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating market HTML report: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # Diagnostic info
            if market_data is None:
                self.logger.critical("market_data is None - this is the root cause of the failure")
            
            # Check template directory permissions
            try:
                if os.path.exists(self.template_dir):
                    if os.access(self.template_dir, os.R_OK):
                        self.logger.debug("Template directory is readable")
                    else:
                        self.logger.error("No read permission for template directory")
                else:
                    self.logger.error("Template directory does not exist")
            except Exception as perm_error:
                self.logger.error(f"Error checking template permissions: {str(perm_error)}")
            
            # Fall back to basic report generation
            self.logger.info("Falling back to basic report generation due to error")
            try:
                return await self.generate_market_report(market_data, output_path)
            except Exception as fallback_error:
                self.logger.error(f"Fallback report generation failed: {str(fallback_error)}")
                return False

    def _create_confluence_image(self, confluence_text: str, output_dir: str, symbol: str = "UNKNOWN", timestamp: Optional[Union[str, datetime, int]] = None, signal_type: str = "NEUTRAL") -> Optional[str]:
        """
        Create an image of the confluence analysis text output.
        
        Args:
            confluence_text: The formatted text of the confluence analysis
            output_dir: Directory to save the image
            symbol: Trading symbol
            timestamp: Signal timestamp
            signal_type: Type of signal (BULLISH, BEARISH, NEUTRAL)
            
        Returns:
            Path to the saved image file or None if creation failed
        """
        self._log("Creating confluence analysis image")
        
        try:
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Format timestamp for filename
            timestamp_str = ""
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        timestamp_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    elif isinstance(timestamp, datetime):
                        timestamp_dt = timestamp
                    elif isinstance(timestamp, (int, float)):
                        timestamp_dt = datetime.fromtimestamp(timestamp / 1000 if timestamp > 1e12 else timestamp)
                    else:
                        timestamp_dt = datetime.now()
                    
                    timestamp_str = timestamp_dt.strftime("%Y%m%d_%H%M%S")
                except Exception as e:
                    self._log(f"Error formatting timestamp for filename: {str(e)}", logging.WARNING)
                    timestamp_str = str(int(time.time()))
            else:
                timestamp_str = str(int(time.time()))
            
            # Create filename with signal information
            signal_type_short = "BUY" if signal_type.upper() == "BULLISH" else "SELL" if signal_type.upper() == "BEARISH" else "NEUT"
            filename = f"{symbol.lower()}_{timestamp_str}_{signal_type_short}_confluence.png"
            
            # Split the text into lines for proper rendering
            lines = confluence_text.split("\n")
            
            # Calculate figure dimensions based on content
            line_count = len(lines)
            max_line_length = max(len(line) for line in lines)
            
            # Adjust figure size to accommodate the text
            # Each character is approximately 0.1 inches wide in monospace font
            # Each line is approximately 0.2 inches high
            width = max(12, max_line_length * 0.1)  # minimum width of 12 inches
            height = max(8, line_count * 0.2)  # minimum height of 8 inches
            
            # Create figure and axis
            fig, ax = plt.subplots(figsize=(width, height))
            
            # Remove axes and frame
            ax.axis('off')
            
            # Set dark background
            fig.patch.set_facecolor('#121212')
            ax.set_facecolor('#121212')
            
            # Add the text with monospace font
            ax.text(0.01, 0.99, confluence_text, 
                   transform=ax.transAxes,
                   fontsize=9,
                   fontfamily='monospace',
                   color='#E0E0E0',
                   verticalalignment='top',
                   horizontalalignment='left',
                   linespacing=1.3)
            
            # Tight layout
            plt.tight_layout()
            
            # Save the figure
            image_path = os.path.join(output_dir, filename)
            plt.savefig(image_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            
            self._log(f"Confluence analysis image saved to {image_path}")
            return image_path
            
        except Exception as e:
            self._log(f"Error creating confluence analysis image: {str(e)}", logging.ERROR)
            self._log(traceback.format_exc(), logging.ERROR)
            return None


if __name__ == "__main__":
    # Example usage
    import random
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create report generator
    generator = ReportGenerator()
    
    # Create sample data
    signal_data = {
        'symbol': 'BTCUSDT',
        'score': 75.5,
        'reliability': 0.85,
        'price': 54321.98,
        'timestamp': datetime.now(),
        'components': {
            'RSI': {'score': 82, 'impact': 3.2, 'interpretation': 'Overbought conditions indicating potential reversal'},
            'MACD': {'score': 71, 'impact': 2.5, 'interpretation': 'Bullish crossover suggesting upward momentum'},
            'Bollinger Bands': {'score': 68, 'impact': 1.8, 'interpretation': 'Price near upper band with expanding volatility'},
            'Volume': {'score': 65, 'impact': 1.5, 'interpretation': 'Above average volume supporting the move'},
            'Moving Averages': {'score': 80, 'impact': 3.0, 'interpretation': 'Price above all major MAs in a bullish alignment'},
            'Support/Resistance': {'score': 60, 'impact': 1.2, 'interpretation': 'Trading above recent resistance turned support'},
            'Ichimoku Cloud': {'score': 72, 'impact': 2.0, 'interpretation': 'Price above the cloud in a bullish trend'}
        },
        'insights': [
            'Strong bullish momentum supported by multiple indicators',
            'Recent breakout above key resistance level at $52,000',
            'Increased institutional buying detected in on-chain data',
            'Reduced selling pressure from miners over the past week'
        ],
        'actionable_insights': [
            'Consider entering long positions with tight stop losses',
            'Target the previous high at $58,500 for first take profit',
            'Monitor volume for confirmation of continued uptrend',
            'Watch for potential resistance at $56,000 psychological level'
        ],
        'entry_price': 54300,
        'stop_loss': 51500,
        'targets': [
            {'name': 'Target 1', 'price': 56800, 'size': 50},
            {'name': 'Target 2', 'price': 58500, 'size': 30},
            {'name': 'Target 3', 'price': 60000, 'size': 20}
        ]
    }
    
    # Create sample OHLCV data
    periods = 50
    base_price = 50000
    dates = pd.date_range(end=datetime.now(), periods=periods)
    
    ohlcv_data = pd.DataFrame({
        'timestamp': dates,
        'open': [base_price * (1 + random.uniform(-0.02, 0.02)) for _ in range(periods)],
        'close': [base_price * (1 + random.uniform(-0.02, 0.02)) for _ in range(periods)]
    })
    
    # Add high and low values
    for i in range(periods):
        if ohlcv_data.loc[i, 'open'] > ohlcv_data.loc[i, 'close']:
            ohlcv_data.loc[i, 'high'] = ohlcv_data.loc[i, 'open'] * (1 + random.uniform(0, 0.01))
            ohlcv_data.loc[i, 'low'] = ohlcv_data.loc[i, 'close'] * (1 - random.uniform(0, 0.01))
        else:
            ohlcv_data.loc[i, 'high'] = ohlcv_data.loc[i, 'close'] * (1 + random.uniform(0, 0.01))
            ohlcv_data.loc[i, 'low'] = ohlcv_data.loc[i, 'open'] * (1 - random.uniform(0, 0.01))
    
    # Generate random volume
    ohlcv_data['volume'] = [random.uniform(100, 1000) for _ in range(periods)]
    
    # Make a bull run toward the end
    for i in range(periods-10, periods):
        ohlcv_data.loc[i, 'close'] = ohlcv_data.loc[i-1, 'close'] * (1 + random.uniform(0.001, 0.02))
        ohlcv_data.loc[i, 'open'] = ohlcv_data.loc[i-1, 'close'] * (1 + random.uniform(-0.005, 0.01))
        ohlcv_data.loc[i, 'high'] = max(ohlcv_data.loc[i, 'open'], ohlcv_data.loc[i, 'close']) * (1 + random.uniform(0.001, 0.01))
        ohlcv_data.loc[i, 'low'] = min(ohlcv_data.loc[i, 'open'], ohlcv_data.loc[i, 'close']) * (1 - random.uniform(0, 0.005))
        ohlcv_data.loc[i, 'volume'] = ohlcv_data.loc[i-1, 'volume'] * (1 + random.uniform(0, 0.2))
    
    # Set the last price to match signal data
    ohlcv_data.loc[periods-1, 'close'] = signal_data['price']
    
    # Generate report
    pdf_path, json_path = generator.generate_trading_report(signal_data, ohlcv_data)
    
    if pdf_path:
        print(f"PDF report generated: {pdf_path}")
    if json_path:
        print(f"JSON data exported: {json_path}") 