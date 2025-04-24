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
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

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
            import traceback
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
                               components: Dict[str, Dict], 
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
            # Sort components by absolute score value
            sorted_components = sorted(
                components.items(), 
                key=lambda x: abs(float(x[1].get('score', 0))), 
                reverse=True
            )
            
            # Limit to max_components
            if len(sorted_components) > max_components:
                sorted_components = sorted_components[:max_components]
            
            # Extract data
            labels = [comp[0] for comp in sorted_components]
            scores = [float(comp[1].get('score', 0)) for comp in sorted_components]
            impacts = [float(comp[1].get('impact', 0)) for comp in sorted_components]
            
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
            chart_path = os.path.join(output_dir, 'component_chart.png')
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
            
            # Prepare data for JSON serialization
            json_data = self._prepare_for_json(data)
            
            # Save to file
            json_path = os.path.join(output_dir, filename)
            with open(json_path, 'w') as f:
                json.dump(json_data, f, indent=2)
                
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
            # Create a temporary directory if output_dir is not provided
            if output_dir is None:
                output_dir = tempfile.mkdtemp(prefix='trading_report_')
                self._log(f"Created temporary directory for report: {output_dir}")
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Debug log the signal data type
            self._log(f"Signal data type: {type(signal_data)}")
            
            # Check if signal_data is a dictionary
            if not isinstance(signal_data, dict):
                self._log(f"Error: signal_data is not a dictionary, it's a {type(signal_data)}", logging.ERROR)
                return None, None
                
            try:
                # Extract basic information
                symbol = signal_data.get('symbol', 'UNKNOWN')
                score = signal_data.get('score', 50)
                reliability = signal_data.get('reliability', 0) * 100  # Convert to percentage
                price = signal_data.get('price', 0)
                timestamp = signal_data.get('timestamp', datetime.now().isoformat())
                
                self._log(f"Extracted basic info - symbol: {symbol}, score: {score}, reliability: {reliability}, price: {price}, timestamp: {timestamp}")
            except Exception as e:
                self._log(f"Error extracting basic information: {str(e)}", logging.ERROR)
                return None, None
            
            try:
                # Determine signal type and color
                if score >= 65:
                    signal_type = "BULLISH"
                    signal_color = "#4CAF50"  # Green
                elif score <= 35:
                    signal_type = "BEARISH"
                    signal_color = "#F44336"  # Red
                else:
                    signal_type = "NEUTRAL"
                    signal_color = "#FFC107"  # Yellow
            except Exception as e:
                self._log(f"Error determining signal type: {str(e)}", logging.ERROR)
                signal_type = "NEUTRAL"
                signal_color = "#FFC107"
            
            # Create candlestick chart if OHLCV data is provided
            candlestick_chart = None
            try:
                if ohlcv_data is not None:
                    entry_price = signal_data.get('entry_price', price)
                    stop_loss = signal_data.get('stop_loss', None)
                    
                    # Special handling for targets
                    targets = []
                    targets_data = signal_data.get('targets', None)
                    
                    if targets_data:
                        self._log(f"Targets data type: {type(targets_data)}")
                        
                        if isinstance(targets_data, dict):
                            # Convert dict to list of dicts with name
                            for name, target_info in targets_data.items():
                                if isinstance(target_info, dict) and 'price' in target_info:
                                    target_dict = target_info.copy()
                                    target_dict['name'] = name
                                    targets.append(target_dict)
                        elif isinstance(targets_data, list):
                            targets = targets_data
                    
                    self._log(f"Attempting to create candlestick chart with entry_price: {entry_price}, stop_loss: {stop_loss}")
                    
                    candlestick_chart = self._create_candlestick_chart(
                        symbol, ohlcv_data, entry_price, stop_loss, targets, output_dir
                    )
            except Exception as e:
                self._log(f"Error creating candlestick chart: {str(e)}", logging.ERROR)
            
            # Create component chart if components are provided
            component_chart = None
            components = {}
            try:
                components = signal_data.get('components', {})
                
                self._log(f"Components type: {type(components)}")
                self._log(f"Components for chart: {list(components.keys()) if isinstance(components, dict) else 'None'}")
                
                if components and isinstance(components, dict):
                    component_chart = self._create_component_chart(components, output_dir)
            except Exception as e:
                self._log(f"Error creating component chart: {str(e)}", logging.ERROR)
            
            # Prepare component data for the template
            component_data = []
            try:
                if isinstance(components, dict):
                    for name, data in components.items():
                        # Debug log the component data
                        self._log(f"Processing component: {name} with data type: {type(data)}")
                        
                        if not isinstance(data, dict):
                            self._log(f"Warning: Component {name} has non-dict data: {type(data)}")
                            continue
                            
                        score_value = float(data.get('score', 0))
                        
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
                            'impact': data.get('impact', 0),
                            'interpretation': data.get('interpretation', ''),
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
                'signal_color': signal_color,
                'component_data': component_data,
                'insights': insights,
                'actionable_insights': actionable_insights,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'stop_loss_percent': stop_loss_percent,
                'targets': targets,
                'hostname': hostname,
                'json_path': json_rel_path,
                'candlestick_chart': candlestick_chart if candlestick_chart else None,
                'component_chart': component_chart if component_chart else None
            }
            
            # Render the HTML template
            try:
                template = self.env.get_template('trading_report_dark.html')
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
            import traceback
            self._log(traceback.format_exc(), logging.ERROR)
            return None, None


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