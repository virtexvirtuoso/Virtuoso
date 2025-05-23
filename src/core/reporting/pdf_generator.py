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
import shutil
import uuid
import re
import warnings

# Import the CustomJSONEncoder for proper serialization
from src.utils.json_encoder import CustomJSONEncoder

# Import and apply matplotlib silencing before matplotlib imports
from src.utils.matplotlib_utils import silence_matplotlib_logs

silence_matplotlib_logs()

import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend
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
import random
from matplotlib.ticker import MaxNLocator, AutoLocator
from matplotlib.lines import Line2D  # For custom legend
from matplotlib.dates import MinuteLocator, DateFormatter
from matplotlib.dates import AutoDateLocator

# Set matplotlib style for dark mode
plt.style.use("dark_background")

# Define a professional mplfinance style
VIRTUOSO_STYLE = {
    "base_mpl_style": "dark_background",
    "marketcolors": {
        "candle": {"up": "#4CAF50", "down": "#F44336"},
        "edge": {"up": "#4CAF50", "down": "#F44336"},
        "wick": {"up": "#4CAF50", "down": "#F44336"},
        "ohlc": {"up": "#4CAF50", "down": "#F44336"},
        "volume": {"up": "#2196F3", "down": "#2196F3"},
        "vcedge": {"up": "#2196F3", "down": "#2196F3"},
        "vcdopcod": False,
        "alpha": 0.8,
    },
    "mavcolors": ["#FFD700", "#00BFFF", "#FF00FF", "#00FF00"],
    "gridcolor": "#333333",
    "gridstyle": "--",
    "y_on_right": False,
    "gridaxis": "both",
    "facecolor": "#121212",
    "figcolor": "#121212",
    "edgecolor": "#444444",
    "xtick.color": "#E0E0E0",
    "ytick.color": "#E0E0E0",
    "axes.labelcolor": "#E0E0E0",
    "axes.edgecolor": "#444444",
    "axes.grid": True,
    "axes.grid.axis": "both",
    "grid.alpha": 0.3,
    "rc": {
        "axes.labelsize": 10,
        "axes.titlesize": 12,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
    },
}

# Define an enhanced version with more polish using new Virtuoso color style guide
VIRTUOSO_ENHANCED_STYLE = {
    "base_mpl_style": "dark_background",
    "marketcolors": {
        # Amber Midnight theme - Bullish: Amber, Bearish: Orange
        "candle": {"up": "#f59e0b", "down": "#f97316"},
        "edge": {"up": "#f59e0b", "down": "#f97316"},
        "wick": {"up": "#f59e0b", "down": "#f97316"},
        "ohlc": {"up": "#f59e0b", "down": "#f97316"},
        "volume": {"up": "#f59e0b", "down": "#f97316"},
        "vcedge": {"up": "#f59e0b", "down": "#f97316"},
        "vcdopcod": True,  # Volume colors depend on price change
        "alpha": 0.9,  # Slightly more opaque for better visibility
    },
    # Use the multi-series color palette from style guide
    "mavcolors": ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899"],
    "gridcolor": "#1a2a40",  # Use border color from style guide
    "gridstyle": ":",  # Dotted lines for less visual distraction
    "y_on_right": False,
    "gridaxis": "both",
    "facecolor": "#0c1a2b",  # Primary bg color from style guide
    "figcolor": "#0c1a2b",
    "edgecolor": "#1a2a40",  # Border color from style guide
    "xtick.color": "#e5e7eb",  # Text primary color
    "ytick.color": "#e5e7eb",
    "axes.labelcolor": "#e5e7eb",
    "axes.edgecolor": "#1a2a40",
    "axes.grid": True,
    "axes.grid.axis": "both",
    "grid.alpha": 0.2,
    "rc": {
        "axes.labelsize": 10,
        "axes.titlesize": 12,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "figure.facecolor": "#0c1a2b",
        "savefig.facecolor": "#0c1a2b",
    },
}


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

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        template_dir: Optional[str] = None,
        log_level: int = logging.INFO,
    ):
        """
        Initialize the ReportGenerator.
        
        Args:
            config: Optional configuration dictionary
            template_dir: Optional directory where HTML templates are stored
            log_level: Logging level
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        
        # Add cache for downsampled OHLCV data to improve performance
        self._downsample_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0

        # Initialize file handlers if not already defined
        if not self.logger.handlers:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            # Try to create file handler if log directory exists
            try:
                os.makedirs("logs", exist_ok=True)
                file_handler = logging.FileHandler("logs/pdf_generator.log")
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                self._log(f"Could not create log file: {str(e)}", logging.WARNING)

        # First try to load from central config
        config_file = os.path.join(os.getcwd(), "config", "templates_config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    config_data = json.load(f)
                    if "template_directory" in config_data and os.path.exists(
                        config_data["template_directory"]
                    ):
                        template_dir = config_data["template_directory"]
                        self.logger.info(
                            f"Using template directory from config file: {template_dir}"
                        )
            except Exception as e:
                self.logger.warning(f"Error loading template config: {str(e)}")

        # Set template directory - try several options if needed
        if template_dir:
            self.template_dir = template_dir
        elif "template_dir" in self.config:
            self.template_dir = self.config["template_dir"]
        else:
            # Try common locations
            possible_dirs = [
                os.path.join(os.getcwd(), "src", "core", "reporting", "templates"),
                os.path.join(os.getcwd(), "templates"),
                os.path.join(
                    os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    ),
                    "core",
                    "reporting",
                    "templates",
                ),
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "reporting",
                    "templates",
                ),
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "templates",
                ),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
                os.getcwd(),
            ]

            for d in possible_dirs:
                if os.path.exists(d) and os.path.isdir(d):
                    self.template_dir = d
                    break
            else:
                self.logger.warning(
                    f"No valid template directory found, using current directory: {os.getcwd()}"
                )
                self.template_dir = os.getcwd()

        # Initialize Jinja environment
        self.env = Environment(loader=FileSystemLoader(self.template_dir))

        # Add custom filters
        self.env.filters["format_number"] = self._format_number

        # Set up matplotlib styling for dark mode
        plt.rcParams.update(
            {
                "figure.facecolor": "#121212",
                "axes.facecolor": "#1E1E1E",
                "axes.edgecolor": "#444444",
                "axes.labelcolor": "#E0E0E0",
                "axes.grid": True,
                "grid.color": "#333333",
                "grid.linestyle": "--",
                "grid.alpha": 0.3,
                "xtick.color": "#E0E0E0",
                "ytick.color": "#E0E0E0",
                "text.color": "#E0E0E0",
                "savefig.facecolor": "#121212",
                "savefig.edgecolor": "#121212",
                "figure.figsize": (10, 6),
                "font.size": 10,
            }
        )

        self._log(
            f"ReportGenerator initialized with template directory: {self.template_dir}",
            logging.INFO,
        )

    async def generate_report(
        self,
        signal_data: Dict[str, Any],
        ohlcv_data: Optional[pd.DataFrame] = None,
        output_path: Optional[str] = None,
    ) -> Union[bool, Tuple[str, str]]:
        """
        Generate a PDF report for a trading signal.
        
        Args:
            signal_data: Dictionary containing signal data
            ohlcv_data: Optional DataFrame with OHLCV data for chart
            output_path: Optional output path for the report
            
        Returns:
            Tuple of (pdf_path, json_path) if successful, or False if generation failed
        """
        # Create a unique ID for this report generation process
        report_id = str(uuid.uuid4())[:8]
        symbol = signal_data.get('symbol', 'UNKNOWN')
        
        try:
            self._log(f"[PDF_GEN:{report_id}] Starting report generation for {symbol}", level=logging.INFO)
            
            # Use the generate_trading_report method to create the PDF
            self._log(f"[PDF_GEN:{report_id}] Calling generate_trading_report for {symbol}", level=logging.INFO)
            
            # If output_path is provided, ensure parent directories exist
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
            pdf_path, json_path = self.generate_trading_report(
                signal_data=signal_data,
                ohlcv_data=ohlcv_data,
                output_dir=output_path,
            )
            
            # Debug output the actual paths
            self._log(f"[PDF_GEN:{report_id}] generate_trading_report returned - PDF path: {pdf_path}, JSON path: {json_path}", level=logging.INFO)
            
            if pdf_path:
                if os.path.exists(pdf_path):
                    if os.path.isdir(pdf_path):
                        self._log(f"[PDF_GEN:{report_id}] ERROR: {pdf_path} is a directory, not a file", level=logging.ERROR)
                        return False
                        
                    # Check file extension
                    if not pdf_path.lower().endswith('.pdf'):
                        self._log(f"[PDF_GEN:{report_id}] WARNING: {pdf_path} does not have .pdf extension", level=logging.WARNING)
                        
                    # Move PDF to exports directory for easier access
                    symbol_safe = symbol.lower().replace('/', '_')
                    
                    # Get signal type (default to NEUTRAL if not available)
                    signal_type = signal_data.get("signal_type", signal_data.get("signal", "NEUTRAL")).upper()
                    
                    # Get score and round to one decimal place
                    score = signal_data.get("score", signal_data.get("confluence_score", 0))
                    score_str = f"{score:.1f}".replace('.', 'p')  # Replace decimal with 'p' for filename compatibility
                    
                    # Create a human-readable timestamp
                    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    exports_dir = os.path.join(os.getcwd(), "exports")
                    os.makedirs(exports_dir, exist_ok=True)
                    
                    # Create a descriptive filename for the exports directory
                    new_pdf_path = os.path.join(exports_dir, f"{symbol_safe}_{signal_type}_{score_str}_{timestamp_str}.pdf")
                    self._log(f"[PDF_GEN:{report_id}] Moving PDF report to {new_pdf_path}", level=logging.INFO)
                    
                    try:
                        # Copy the file instead of moving it
                        shutil.copy2(pdf_path, new_pdf_path)
                        if os.path.exists(new_pdf_path):
                            copy_size = os.path.getsize(new_pdf_path) / 1024  # Size in KB
                            self._log(f"[PDF_GEN:{report_id}] PDF report copied to {new_pdf_path}, size: {copy_size:.2f} KB", level=logging.INFO)
                            
                            # Verify file is valid
                            try:
                                with open(new_pdf_path, 'rb') as f:
                                    header = f.read(5)
                                    if header[:4] != b'%PDF':
                                        self._log(f"[PDF_GEN:{report_id}] WARNING: {new_pdf_path} is not a valid PDF file", level=logging.WARNING)
                            except Exception as e:
                                self._log(f"[PDF_GEN:{report_id}] Error verifying PDF file content: {str(e)}", level=logging.WARNING)
                        else:
                            self._log(f"[PDF_GEN:{report_id}] ERROR: PDF copy failed - {new_pdf_path} does not exist", level=logging.ERROR)
                    except Exception as e:
                        self._log(f"[PDF_GEN:{report_id}] Error copying PDF report: {str(e)}", level=logging.ERROR)
                        # If we can't copy, still return the original path
                        self._log(f"[PDF_GEN:{report_id}] Returning original PDF path: {pdf_path}", level=logging.INFO)
                        
                        # Clear the cache after report generation
                        self._clear_downsample_cache()
                        return pdf_path, json_path
                    
                    # Return path to the newly copied PDF
                    self._log(f"[PDF_GEN:{report_id}] Returning new PDF path: {new_pdf_path}", level=logging.INFO)
                    
                    # Clear the cache after report generation
                    self._clear_downsample_cache()
                    return new_pdf_path, json_path
                else:
                    self._log(f"[PDF_GEN:{report_id}] ERROR: PDF path was returned but file doesn't exist: {pdf_path}", level=logging.ERROR)
                    
                    # Clear the cache even if we had an error
                    self._clear_downsample_cache()
                    return False
            else:
                self._log(f"[PDF_GEN:{report_id}] ERROR: No PDF path was returned from generate_trading_report", level=logging.ERROR)
                
                # Clear the cache even if we had an error
                self._clear_downsample_cache()
                return False
        except Exception as e:
            self._log(f"[PDF_GEN:{report_id}] ERROR: Exception in generate_report: {str(e)}", level=logging.ERROR)
            self._log(traceback.format_exc(), level=logging.ERROR)
            
            # Clear the cache even if we had an error
            self._clear_downsample_cache()
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

    def _calculate_vwap(self, df: pd.DataFrame, periods: int) -> np.ndarray:
        """
        Calculate VWAP (Volume-Weighted Average Price) for the given period.
        
        Args:
            df: DataFrame with OHLCV data
            periods: Number of periods to look back (e.g., 1 day = ~1440 minutes)
            
        Returns:
            numpy array with VWAP values
        """
        try:
            # Calculate typical price
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            
            # Calculate VWAP using rolling window
            tp_volume = typical_price * df['volume']
            cumulative_tp_volume = tp_volume.rolling(window=periods, min_periods=1).sum()
            cumulative_volume = df['volume'].rolling(window=periods, min_periods=1).sum()
            
            # Avoid division by zero
            vwap = np.where(cumulative_volume > 0, cumulative_tp_volume / cumulative_volume, typical_price)
            
            return vwap
        except Exception as e:
            self._log(f"Error calculating VWAP: {str(e)}", logging.ERROR)
            # Return a default array of zeros with same shape as df
            return np.zeros(len(df))

    def _log(self, message: str, level: int = logging.DEBUG) -> None:
        """
        Log a message.
        
        Args:
            message: Message to log
            level: Logging level
        """
        self.logger.log(level, message)

    def _configure_axis_ticks(self, ax, max_ticks=20, axis='both'):
        """
        Configure axis ticks to prevent excessive ticks that can cause performance issues.
        
        Args:
            ax: Matplotlib axis
            max_ticks: Maximum number of ticks to allow
            axis: Which axis to configure ('x', 'y', or 'both')
        """
        try:
            from matplotlib.ticker import MaxNLocator, AutoLocator
            from matplotlib.dates import AutoDateLocator
            
            # Ensure max_ticks is reasonable
            max_ticks = min(max(max_ticks, 5), 50)  # At least 5, at most 50
            
            # Configure x-axis
            if axis in ['x', 'both']:
                # Handle date axes differently
                if hasattr(ax.xaxis, 'get_major_locator') and hasattr(ax.xaxis.get_major_locator(), 'axis') and hasattr(ax.xaxis.get_major_locator().axis, 'units') and ax.xaxis.get_major_locator().axis.units is not None:
                    # It's a date axis, use AutoDateLocator with explicit maxticks
                    date_locator = AutoDateLocator(maxticks=max_ticks)
                    ax.xaxis.set_major_locator(date_locator)
                else:
                    # Use MaxNLocator for regular numeric axis
                    ax.xaxis.set_major_locator(MaxNLocator(nbins=max_ticks, steps=[1, 2, 5, 10], prune='both'))
                
                # If still too many ticks after applying locator, force reduce them
                if len(ax.get_xticks()) > max_ticks:
                    ticks = ax.get_xticks()
                    step = max(1, len(ticks) // max_ticks)
                    ax.set_xticks(ticks[::step])
            
            # Configure y-axis
            if axis in ['y', 'both']:
                # Use MaxNLocator for y-axis with fewer bins
                ax.yaxis.set_major_locator(MaxNLocator(nbins=max_ticks//2, steps=[1, 2, 5, 10]))
                
                # If still too many ticks, force reduce them
                if len(ax.get_yticks()) > max_ticks:
                    ticks = ax.get_yticks()
                    step = max(1, len(ticks) // max_ticks)
                    ax.set_yticks(ticks[::step])
                
        except Exception as e:
            self._log(f"Error configuring axis ticks: {str(e)}", logging.WARNING)

    def _downsample_ohlcv_data(self, df, max_samples=300):
        """
        Intelligently downsample OHLCV data to reduce the number of points while preserving key features.
        Uses a caching mechanism to avoid redundant calculations.
        
        Args:
            df: DataFrame with OHLCV data
            max_samples: Maximum number of samples to keep
            
        Returns:
            Downsampled DataFrame
        """
        try:
            # If DataFrame is already small enough, return as-is
            if len(df) <= max_samples:
                return df
            
            # Generate a cache key based on dataframe content, length, and max_samples
            # Use the first and last timestamp plus length to identify the dataset
            if isinstance(df.index, pd.DatetimeIndex):
                start_ts = df.index[0].timestamp()
                end_ts = df.index[-1].timestamp()
            else:
                # If not a datetime index, use index values directly
                start_ts = df.index[0]
                end_ts = df.index[-1]
                
            df_length = len(df)
            cache_key = f"{start_ts}_{end_ts}_{df_length}_{max_samples}"
            
            # Check if we have this result cached
            if cache_key in self._downsample_cache:
                self._cache_hits += 1
                self._log(f"Cache hit for OHLCV downsampling (hits: {self._cache_hits}, misses: {self._cache_misses})", logging.INFO)
                return self._downsample_cache[cache_key]
                
            # Cache miss - need to downsample
            self._cache_misses += 1
            self._log(f"Cache miss for OHLCV downsampling (hits: {self._cache_hits}, misses: {self._cache_misses})", logging.INFO)
            self._log(f"Downsampling OHLCV data from {len(df)} to {max_samples} points", logging.INFO)
            
            # For very large datasets, use more aggressive downsampling
            if len(df) > 1000:
                max_samples = min(max_samples, 200)
                self._log(f"Using more aggressive downsampling target of {max_samples} for large dataset", logging.WARNING)
            
            # Save index type information for later restoration
            had_datetime_index = isinstance(df.index, pd.DatetimeIndex)
            original_index = df.index.copy() if had_datetime_index else None
            
            # Calculate ratio for downsampling
            ratio = len(df) / max_samples
            
            # Use different strategies depending on data size
            if ratio <= 5:  
                # For smaller datasets, use simple skip sampling
                indices = np.linspace(0, len(df) - 1, max_samples, dtype=int)
                result = df.iloc[indices].copy()
                
                # Ensure DatetimeIndex is preserved if original had one
                if had_datetime_index and not isinstance(result.index, pd.DatetimeIndex):
                    # Get corresponding datetime indices
                    new_index = original_index[indices]
                    result.index = new_index
                    
                # Cache the result before returning
                self._downsample_cache[cache_key] = result
                
                # Monitor and limit cache size
                self._monitor_cache_size()
                
                return result
            else:
                # For larger datasets, use more intelligent resampling
                # Calculate appropriate time frequency for resampling
                if isinstance(df.index, pd.DatetimeIndex):
                    # Get original frequency
                    orig_freq = pd.infer_freq(df.index)
                    if orig_freq:
                        # Calculate new frequency based on ratio
                        freq_map = {
                            'T': 'min',
                            'H': 'H',
                            'D': 'D',
                            'W': 'W',
                            'M': 'M'
                        }
                        
                        # Determine base frequency
                        base_freq = None
                        for k, v in freq_map.items():
                            if k in orig_freq:
                                base_freq = v
                                break
                        
                        if base_freq:
                            # Calculate new frequency multiplier
                            current_mult = int(re.findall(r'\d+', orig_freq)[0]) if re.findall(r'\d+', orig_freq) else 1
                            new_mult = max(1, int(current_mult * ratio))
                            rule = f"{new_mult}{base_freq}"
                            
                            try:
                                # Resample data
                                resampled = df.resample(rule).agg({
                                    'open': 'first', 
                                    'high': 'max', 
                                    'low': 'min', 
                                    'close': 'last',
                                    'volume': 'sum'
                                })
                                # If still too many points after resampling, force downsample further
                                if len(resampled) > max_samples:
                                    self._log(f"Resampling still produced too many points ({len(resampled)}), applying additional reduction", logging.WARNING)
                                    indices = np.linspace(0, len(resampled) - 1, max_samples, dtype=int)
                                    resampled = resampled.iloc[indices]
                                
                                result = resampled.dropna()
                                # Cache the result before returning
                                self._downsample_cache[cache_key] = result
                                
                                # Monitor and limit cache size
                                self._monitor_cache_size()
                                
                                return result
                            except Exception as resample_error:
                                self._log(f"Error during resampling: {str(resample_error)}, falling back to simple method", logging.WARNING)
                
                # Fallback to simple but effective method
                indices = np.linspace(0, len(df) - 1, max_samples, dtype=int)
                result = df.iloc[indices].copy()
                
                # Ensure DatetimeIndex is preserved if original had one
                if had_datetime_index and not isinstance(result.index, pd.DatetimeIndex):
                    # Get corresponding datetime indices
                    new_index = original_index[indices]
                    result.index = new_index
                
                # Cache the result before returning
                self._downsample_cache[cache_key] = result
                
                # Monitor and limit cache size
                self._monitor_cache_size()
                
                return result
                
        except Exception as e:
            self._log(f"Error downsampling data: {str(e)}", logging.ERROR)
            self._log(traceback.format_exc(), logging.DEBUG)
            # Return original data on error
            return df

    def _create_component_chart(
        self, components: Dict[str, Any], output_dir: str, max_components: int = 10
    ) -> Optional[str]:
        """
        Create a bar chart for component scores with professional styling.
        
        Args:
            components: Dictionary of components with scores and impacts
            output_dir: Directory to save the chart
            max_components: Maximum number of components to display
            
        Returns:
            Path to the saved chart file or None if chart creation failed
        """
        self._log(f"Creating component chart with {len(components)} components")

        # Validate output_dir
        if output_dir is None:
            self._log("Component chart creation failed: output_dir is None", logging.ERROR)
            return None

        try:
            # Safely handle components which may contain numpy types
            processed_components = {}
            for key, value in components.items():
                # Convert any numpy types to Python native types
                if hasattr(value, "item") and callable(getattr(value, "item")):
                    # Direct numpy value - convert to Python float and wrap in dict
                    processed_components[key] = {"score": float(value.item())}
                elif isinstance(value, (int, float)):
                    # Regular Python numeric type - wrap in dict with score
                    processed_components[key] = {"score": float(value)}
                elif isinstance(value, dict):
                    # Component is already a dict with potentially 'score' and 'impact' keys
                    processed_dict = {}
                    for k, v in value.items():
                        # Convert numpy types to native Python types
                        if hasattr(v, "item") and callable(getattr(v, "item")):
                            processed_dict[k] = float(
                                v.item()
                            )  # Convert numpy scalar to Python scalar
                        else:
                            processed_dict[k] = v
                    processed_components[key] = processed_dict
                else:
                    # Fallback for other types - use default score
                    processed_components[key] = {"score": 50.0}

            # Sort components by absolute score value
            sorted_components = sorted(
                processed_components.items(),
                key=lambda x: abs(float(x[1].get("score", 0))),
                reverse=True,
            )

            # Limit to max_components
            if len(sorted_components) > max_components:
                sorted_components = sorted_components[:max_components]

            # Extract data - ensure all values are native Python types
            labels = [str(comp[0]) for comp in sorted_components]
            scores = [float(comp[1].get("score", 0)) for comp in sorted_components]

            # Get impacts if available, or calculate from scores
            impacts = []
            for comp in sorted_components:
                if "impact" in comp[1]:
                    impacts.append(float(comp[1].get("impact", 0)))
                else:
                    # Calculate impact as deviation from neutral (50)
                    score = float(comp[1].get("score", 50))
                    impact = (
                        abs(score - 50) * 2
                    )  # Higher impact for scores far from neutral
                    impacts.append(impact)

            # Create figure with two subplots: scores and impacts
            fig, (ax1, ax2) = plt.subplots(
                2, 1, figsize=(10, 8), gridspec_kw={"height_ratios": [3, 1]}
            )

            # Apply professional styling to the figure using Virtuoso colors
            fig.patch.set_facecolor("#0c1a2b")  # Primary BG from style guide
            for ax in [ax1, ax2]:
                ax.set_facecolor("#0f172a")  # Secondary BG from style guide
                ax.spines["bottom"].set_color("#1a2a40")  # Border color
                ax.spines["top"].set_color("#1a2a40")
                ax.spines["right"].set_color("#1a2a40")
                ax.spines["left"].set_color("#1a2a40")
                ax.tick_params(colors="#e5e7eb")  # Text primary color
                ax.yaxis.label.set_color("#e5e7eb")
                ax.xaxis.label.set_color("#e5e7eb")
                ax.title.set_color("#ffbf00")  # Text secondary/accent
                ax.grid(
                    True, linestyle="--", alpha=0.3, color="#1a2a40"
                )  # Grid with border color

            # Score colors based on value - use Amber theme colors
            colors = []
            for score in scores:
                if score >= 65:
                    colors.append("#f59e0b")  # Amber for bullish
                elif score <= 35:
                    colors.append("#f97316")  # Orange for bearish
                else:
                    colors.append("#3b82f6")  # Blue for neutral

            # Plot scores with enhanced styling
            bars = ax1.barh(labels, scores, color=colors, alpha=0.8, height=0.7)
            ax1.set_title("Component Scores", color="#ffbf00", fontsize=12)
            ax1.set_xlim(0, 100)
            ax1.axvline(x=50, color="#1a2a40", linestyle="-", alpha=0.7)
            ax1.axvline(x=35, color="#f97316", linestyle="--", alpha=0.3)
            ax1.axvline(x=65, color="#f59e0b", linestyle="--", alpha=0.3)
            ax1.set_xlabel("Score", fontsize=10)

            # Add value labels with improved readability
            for bar in bars:
                width = bar.get_width()
                label_x_pos = width + 1
                ax1.text(
                    label_x_pos,
                    bar.get_y() + bar.get_height() / 2,
                    f"{width:.1f}",
                    va="center",
                    color="#e5e7eb",
                    fontsize=9,
                )

            # Plot impacts with improved styling using accent color
            impact_colors = [
                "#ff9900" if impact > 0 else "#1a2a40" for impact in impacts
            ]
            bars2 = ax2.barh(
                labels, impacts, color=impact_colors, alpha=0.8, height=0.7
            )
            ax2.set_title("Component Impact", color="#ffbf00", fontsize=12)
            ax2.set_xlabel("Impact", fontsize=10)

            # Add value labels for impacts
            for bar in bars2:
                width = bar.get_width()
                label_x_pos = width + 0.1
                ax2.text(
                    label_x_pos,
                    bar.get_y() + bar.get_height() / 2,
                    f"{width:.1f}",
                    va="center",
                    color="#e5e7eb",
                    fontsize=9,
                )

            # Tight layout and save
            plt.tight_layout()
            
            # Limit excessive ticks to avoid performance issues
            self._configure_axis_ticks(ax1, max_ticks=20)
            self._configure_axis_ticks(ax2, max_ticks=20)

            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)

            # Save figure with high quality
            chart_path = os.path.abspath(
                os.path.join(output_dir, "component_chart.png")
            )
            plt.savefig(chart_path, dpi=120, bbox_inches="tight")
            plt.close(fig)

            self._log(f"Component chart saved to {chart_path}")
            return chart_path

        except Exception as e:
            self._log(f"Error creating component chart: {str(e)}", logging.ERROR)
            self._log(traceback.format_exc(), logging.DEBUG)
            return None

    def _create_candlestick_chart(
        self,
        symbol: str,
        ohlcv_data: pd.DataFrame,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        targets: Optional[List[Dict]] = None,
        output_dir: str = None,
    ) -> Optional[str]:
        """
        Generate a candlestick chart with buy/sell zones using mplfinance.
        
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
        self._log(
            f"Creating candlestick chart for {symbol} using real OHLCV data",
            logging.INFO,
        )

        try:
            # Use temporary directory if none specified
            if output_dir is None:
                output_dir = tempfile.mkdtemp()
                self._log(f"Using temporary directory: {output_dir}")

            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Check if we have actual OHLCV data to work with
            if ohlcv_data is None or ohlcv_data.empty:
                self._log("No OHLCV data provided, falling back to simulated chart", logging.WARNING)
                return self._create_simulated_chart(
                    symbol=symbol,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    targets=targets,
                    output_dir=output_dir,
                )
                
            # Always downsample data to prevent chart rendering issues - use more conservative max samples
            # Track original length for logging purposes
            original_length = len(ohlcv_data)
            
            # Apply more aggressive downsampling for larger datasets
            max_samples = 200
            if original_length > 1000:
                max_samples = 150
            elif original_length > 500:
                max_samples = 175
                
            # Check if downsampling is needed
            if original_length > max_samples:
                self._log(f"Downsampling OHLCV data from {original_length} to max {max_samples} points to prevent chart rendering issues", logging.INFO)
                df = self._downsample_ohlcv_data(ohlcv_data, max_samples=max_samples)
                self._log(f"Downsampled to {len(df)} points", logging.INFO)
            else:
                self._log(f"No downsampling needed, using original {original_length} data points", logging.INFO)
                df = ohlcv_data.copy()

            # Ensure DataFrame has a DatetimeIndex, required by mplfinance
            if not isinstance(df.index, pd.DatetimeIndex):
                self._log("Converting DataFrame index to DatetimeIndex", logging.DEBUG)
                if 'timestamp' in df.columns:
                    # If timestamp column exists, use it as the index
                    try:
                        # Check timestamp type and convert if needed
                        if df['timestamp'].dtype == 'object':
                            # Try to parse string timestamps
                            df['timestamp'] = pd.to_datetime(df['timestamp'])
                        elif np.issubdtype(df['timestamp'].dtype, np.integer):
                            # Convert from unix timestamp (milliseconds or seconds)
                            if df['timestamp'].iloc[0] > 1e12:  # milliseconds
                                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                            else:  # seconds
                                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                        
                        # Set the timestamp as index
                        df = df.set_index('timestamp')
                        self._log("Successfully set timestamp column as DatetimeIndex", logging.DEBUG)
                    except Exception as e:
                        self._log(f"Error converting timestamp to DatetimeIndex: {str(e)}", logging.ERROR)
                        # Create a synthetic datetime index if conversion fails
                        df.index = pd.date_range(end=pd.Timestamp.now(), periods=len(df))
                        self._log("Created synthetic DatetimeIndex as fallback", logging.WARNING)
                else:
                    # If no timestamp column exists, create a synthetic datetime index
                    self._log("No timestamp column found, creating synthetic DatetimeIndex", logging.WARNING)
                    df.index = pd.date_range(end=pd.Timestamp.now(), periods=len(df))

            # Ensure required columns exist
            required_columns = ["open", "high", "low", "close"]
            if not all(col in df.columns for col in required_columns):
                self._log(
                    "Missing required OHLCV columns in candlestick chart data",
                    logging.WARNING,
                )
                # Return None instead of recursively calling _create_simulated_chart
                return None

            # Determine range of prices to display
            prices = []
            if entry_price is not None:
                prices.append(entry_price)
            if stop_loss is not None:
                prices.append(stop_loss)
            if targets:
                for target in targets:
                    if "price" in target:
                        prices.append(target["price"])
                        
            # Calculate min/max price if we have prices
            if prices:
                min_price = min(prices) * 0.95
                max_price = max(prices) * 1.05
            else:
                # Use data range if no specific prices provided
                min_price = df["low"].min() * 0.95 if "low" in df.columns else None
                max_price = df["high"].max() * 1.05 if "high" in df.columns else None
                
                # If still no valid range, return error
                if min_price is None or max_price is None:
                    self._log("Unable to determine price range for chart", logging.ERROR)
                    return None

            # Generate simulated price data with random walk - this should be skipped as we have real data
            # Instead, prepare the existing OHLCV data for plotting
            
            # Ensure required columns exist
            required_columns = ["open", "high", "low", "close"]
            if not all(col in df.columns for col in required_columns):
                self._log(
                    "Missing required OHLCV columns in candlestick chart data",
                    logging.WARNING,
                )
                # Return None instead of recursively calling _create_simulated_chart
                return None
                
            # Calculate VWAPs if volume data is available
            has_vwap = False
            if 'volume' in df.columns and len(df) > 10:  # Need reasonable amount of data for VWAP
                try:
                    # Check if we have HTF data in metadata for weekly VWAP
                    htf_data = None
                    if hasattr(ohlcv_data, 'metadata') and ohlcv_data.metadata and 'htf_data' in ohlcv_data.metadata:
                        htf_data = ohlcv_data.metadata['htf_data']
                        self._log(f"Found HTF data in metadata for weekly VWAP calculation", level=logging.DEBUG)
                    
                    # Calculate daily VWAP using LTF data (primary dataset)
                    # LTF data is more granular (e.g., 5-minute candles) which is ideal for daily VWAP
                    self._log(f"Calculating daily VWAP using LTF data", level=logging.DEBUG)
                    df['daily_vwap'] = self._calculate_vwap(df, periods=min(1440, len(df)))
                    
                    # Calculate weekly VWAP using HTF data or fall back to primary data
                    if htf_data is not None and not htf_data.empty:
                        # HTF data is higher timeframe (e.g., 4-hour candles) which is better for weekly VWAP
                        self._log(f"Calculating weekly VWAP using HTF data ({len(htf_data)} candles)", level=logging.DEBUG)
                        
                        # Copy HTF data for VWAP calculation
                        htf_df = htf_data.copy()
                        
                        # Ensure the DataFrame has all required columns
                        if all(col in htf_df.columns for col in ['high', 'low', 'close', 'volume']):
                            # Calculate VWAP on HTF data
                            htf_vwap = self._calculate_vwap(htf_df, periods=min(10080, len(htf_df)))
                            
                            # Resample HTF VWAP to match primary dataframe timestamps
                            if hasattr(htf_df, 'index') and isinstance(htf_df.index, pd.DatetimeIndex):
                                # Create a Series with HTF VWAP values
                                vwap_series = pd.Series(htf_vwap, index=htf_df.index)
                                
                                # Resample to match primary dataframe
                                if hasattr(df, 'index') and isinstance(df.index, pd.DatetimeIndex):
                                    # Reindex to match timestamps, forward filling missing values
                                    resampled_vwap = vwap_series.reindex(df.index, method='ffill')
                                    df['weekly_vwap'] = resampled_vwap.values
                                else:
                                    self._log("Primary dataframe doesn't have DatetimeIndex, can't resample HTF VWAP", level=logging.WARNING)
                                    df['weekly_vwap'] = self._calculate_vwap(df, periods=min(10080, len(df)))
                            else:
                                self._log("HTF dataframe doesn't have DatetimeIndex, can't resample VWAP", level=logging.WARNING)
                                df['weekly_vwap'] = self._calculate_vwap(df, periods=min(10080, len(df)))
                        else:
                            self._log("HTF data missing required columns, falling back to primary dataframe for weekly VWAP", level=logging.WARNING)
                            df['weekly_vwap'] = self._calculate_vwap(df, periods=min(10080, len(df)))
                    else:
                        # Fall back to calculating weekly VWAP from primary data if no HTF data available
                        self._log("No HTF data available, calculating weekly VWAP from primary dataframe", level=logging.DEBUG)
                        df['weekly_vwap'] = self._calculate_vwap(df, periods=min(10080, len(df)))
                    
                    has_vwap = True
                    self._log(f"Successfully calculated VWAP values for {symbol}", level=logging.DEBUG)
                except Exception as e:
                    self._log(f"Error calculating VWAP: {str(e)}", level=logging.ERROR)
                    traceback.print_exc()
                    has_vwap = False

            # Determine price range for y-axis scaling
            price_padding = 0.01  # 1% padding
            y_min = df["low"].min() * (1 - price_padding)
            y_max = df["high"].max() * (1 + price_padding)

            # Adjust y-axis range to include VWAP lines if they're available
            if has_vwap:
                y_min = min(y_min, df['daily_vwap'].min() * (1 - price_padding), 
                           df['weekly_vwap'].min() * (1 - price_padding))
                y_max = max(y_max, df['daily_vwap'].max() * (1 + price_padding),
                           df['weekly_vwap'].max() * (1 + price_padding))
            
            # Adjust y-axis range to include all targets and entry/stop levels
            if prices:
                y_min = min(y_min, min(prices) * 0.95)
                y_max = max(y_max, max(prices) * 1.05)

            # Prepare plot configuration with enhanced style
            kwargs = {
                "type": "candle",
                "style": VIRTUOSO_ENHANCED_STYLE,  # Use enhanced style
                "figsize": (10, 6),
                "title": f"{symbol} Price Chart",
                "panel_ratios": (4, 1),
                "volume": True if 'volume' in df.columns else False,
                "volume_panel": 1 if 'volume' in df.columns else None,
                "show_nontrading": False,
                "returnfig": True,
                "datetime_format": "%m-%d %H:%M",
                "xrotation": 0,
                "tight_layout": False,
                "ylabel": "Price",
                "ylabel_lower": "Volume" if 'volume' in df.columns else "",
                "figratio": (10, 7),
                "scale_padding": {
                    "left": 0.05,
                    "right": 0.3,
                    "top": 0.2,
                    "bottom": 0.2,
                },
                "warn_too_much_data": 1000,  # Suppress warning up to 1000 candles
            }

            # Prepare additional plots for entry, stop loss, and targets
            plots = []
            
            # Add VWAP lines if available
            if has_vwap:
                # Add daily VWAP (blue line)
                plots.append(
                    mpf.make_addplot(
                        df['daily_vwap'],
                        color='#3b82f6',  # Blue
                        width=1.2,
                        panel=0,
                        secondary_y=False,
                        linestyle='-',
                    )
                )
                
                # Add weekly VWAP (purple line)
                plots.append(
                    mpf.make_addplot(
                        df['weekly_vwap'],
                        color='#8b5cf6',  # Purple
                        width=1.2,
                        panel=0,
                        secondary_y=False,
                        linestyle='-',
                    )
                )

            # Entry price line (blue)
            if entry_price is not None:
                plots.append(
                    mpf.make_addplot(
                        [entry_price] * len(df),
                        color="#3b82f6",
                        width=1.5,
                        panel=0,
                        secondary_y=False,
                        linestyle="-",
                    )
                )

            # Stop loss line
            if stop_loss is not None:
                plots.append(
                    mpf.make_addplot(
                        [stop_loss] * len(df),
                        color="#ef4444",
                        width=1.5,
                        panel=0,
                        secondary_y=False,
                        linestyle="--",
                    )
                )

            # Target level lines with different colors
            if targets:
                target_colors = [
                    "#10b981",
                    "#8b5cf6",
                    "#f59e0b",
                    "#ec4899",
                ]  # From multi-series palette
                for i, target in enumerate(targets):
                    if "price" in target:
                        target_price = target["price"]
                        color = target_colors[i % len(target_colors)]
                        plots.append(
                            mpf.make_addplot(
                                [target_price] * len(df),
                                color=color,
                                width=1.5,
                                panel=0,
                                secondary_y=False,
                                linestyle="-.",
                                alpha=0.8,
                            )
                        )

            # Create the plot
            plot_result = mpf.plot(df, **kwargs, addplot=plots if plots else None)
            
            # Safely unpack plot result with robust error handling
            fig, axes = self._safe_plot_result_unpack(plot_result)
            
            # Get the main price axis (safely)
            ax1 = axes[0] if axes and len(axes) > 0 else None
            
            if ax1:
                # Set y-axis limits to ensure all targets are visible
                ax1.set_ylim(y_min, y_max)
                
                # Use scientific notation for large numbers
                if y_max > 10000:
                    ax1.ticklabel_format(style="plain", axis="y")
                
                # Limit ticks to avoid overflow warnings
                self._configure_axis_ticks(ax1, max_ticks=20)
                
                # Custom date formatting for x-axis - REPLACED problematic MinuteLocator
                # Use AutoDateLocator instead of MinuteLocator to prevent excessive ticks
                date_locator = AutoDateLocator(maxticks=20)
                ax1.xaxis.set_major_locator(date_locator)
                
                # Format to show more compact time format
                time_formatter = DateFormatter('%m-%d %H:%M')
                ax1.xaxis.set_major_formatter(time_formatter)
                
                # Rotate labels for better readability
                plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

                # Add custom legend for VWAP if available
                if has_vwap:
                    legend_elements = [
                        Line2D([0], [0], color='#3b82f6', lw=1.2, label='Daily VWAP (LTF)'),
                        Line2D([0], [0], color='#8b5cf6', lw=1.2, label='Weekly VWAP (HTF)')
                    ]
                    ax1.legend(handles=legend_elements, loc='upper left', fontsize=9, framealpha=0.7, facecolor='#0c1a2b')


                # Add labels with improved styling
                if entry_price is not None:
                    # Calculate normalized position for entry price
                    entry_pos = (entry_price - y_min) / (y_max - y_min)
                    
                    # Get position bounds safely - handling different return types
                    position = ax1.get_position()
                    if hasattr(position, 'bounds'):
                        # In some versions, bounds is a tuple of 4 values
                        try:
                            bounds = position.bounds
                            if isinstance(bounds, tuple) and len(bounds) == 4:
                                ax1_x_pos, ax1_y_pos, ax1_width, ax1_height = bounds
                            else:
                                self._log(f"Unexpected bounds format: {bounds}", logging.WARNING)
                                ax1_x_pos = ax1_y_pos = 0
                        except Exception as e:
                            self._log(f"Error unpacking figure bounds: {str(e)}", logging.WARNING)
                            ax1_x_pos = ax1_y_pos = 0
                    else:
                        # Fall back to direct attribute access
                        ax1_x_pos = getattr(position, 'x0', 0)
                        ax1_y_pos = getattr(position, 'y0', 0)
                        
                    ax1.annotate(
                        f"Entry: ${self._format_number(entry_price)}",
                        xy=(1.01, entry_pos),
                        xycoords=("axes fraction", "axes fraction"),
                        xytext=(1.05, entry_pos),
                        textcoords="axes fraction",
                        fontsize=9,
                        color="#3b82f6",
                        fontweight="bold",
                        bbox=dict(
                            facecolor="#0c1a2b",
                            edgecolor="#3b82f6",
                            boxstyle="round,pad=0.3",
                            alpha=0.9,
                        ),
                    )

                # Stop loss label
                if stop_loss is not None:
                    stop_pos = (stop_loss - y_min) / (y_max - y_min)
                    ax1.annotate(
                        f"Stop: ${self._format_number(stop_loss)}",
                        xy=(1.01, stop_pos),
                        xycoords=("axes fraction", "axes fraction"),
                        xytext=(1.05, stop_pos),
                        textcoords="axes fraction",
                        fontsize=9,
                        color="#ef4444",
                        fontweight="bold",
                        bbox=dict(
                            facecolor="#0c1a2b",
                            edgecolor="#ef4444",
                            boxstyle="round,pad=0.3",
                            alpha=0.9,
                        ),
                    )

                    # Shade area between entry and stop loss if both exist
                    if entry_price is not None:
                        min_idx, max_idx = 0, len(df) - 1
                        if entry_price > stop_loss:  # Long position
                            ax1.fill_between(
                                [min_idx, max_idx],
                                entry_price,
                                stop_loss,
                                color="#ef4444",
                                alpha=0.1,
                            )
                        else:  # Short position
                            ax1.fill_between(
                                [min_idx, max_idx],
                                entry_price,
                                stop_loss,
                                color="#22c55e",
                                alpha=0.1,
                            )

                # Target labels
                if targets:
                    for i, target in enumerate(targets):
                        if "price" in target:
                            target_price = target["price"]
                            target_name = target.get("name", f"Target {i+1}")
                            color = target_colors[i % len(target_colors)]

                            # Calculate profit percentage
                            profit_pct = ""
                            if entry_price and entry_price > 0:
                                pct = ((target_price / entry_price) - 1) * 100
                                profit_pct = f" ({pct:+.1f}%)"

                            # Normalize position for target
                            target_pos = (target_price - y_min) / (y_max - y_min)

                            # Add annotation for target
                            ax1.annotate(
                                f"{target_name}: ${self._format_number(target_price)}{profit_pct}",
                                xy=(1.01, target_pos),
                                xycoords=("axes fraction", "axes fraction"),
                                xytext=(1.05, target_pos),
                                textcoords="axes fraction",
                                fontsize=9,
                                color=color,
                                fontweight="bold",
                                bbox=dict(
                                    facecolor="#0c1a2b",
                                    edgecolor=color,
                                    boxstyle="round,pad=0.3",
                                    alpha=0.9,
                                ),
                            )

                            # Shade target zones
                            if entry_price is not None:
                                min_idx, max_idx = 0, len(df) - 1
                                if entry_price < target_price:  # Long position target
                                    ax1.fill_between(
                                        [min_idx, max_idx],
                                        entry_price,
                                        target_price,
                                        color=color,
                                        alpha=0.05,
                                    )
                                else:  # Short position target
                                    ax1.fill_between(
                                        [min_idx, max_idx],
                                        entry_price,
                                        target_price,
                                        color=color,
                                        alpha=0.05,
                                    )

                
                # Adjust layout with specific settings instead of tight_layout
                plt.subplots_adjust(right=0.85, left=0.1, top=0.9, bottom=0.15)

                # Create output filename for REAL data chart
                timestamp = int(time.time())
                output_file = os.path.join(
                    output_dir, f"{symbol.replace('/', '_')}_chart_{timestamp}.png"
                )

                # Save the figure
                plt.savefig(output_file, dpi=150, bbox_inches="tight")
                plt.close(fig)

                self._log(f"Real data candlestick chart saved to: {output_file}")
                return output_file

        except Exception as e:
            self._log(f"Error creating candlestick chart: {str(e)}", logging.ERROR)
            self._log(traceback.format_exc(), logging.DEBUG)
            return None

    def _export_json_data(
        self, data: Dict, filename: str, output_dir: str
    ) -> Optional[str]:
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

        # Validate output_dir and filename
        if output_dir is None:
            self._log("JSON export failed: output_dir is None", logging.ERROR)
            return None
        if filename is None:
            self._log("JSON export failed: filename is None", logging.ERROR)
            return None

        try:
            # Use reports/json directory for JSON files
            reports_base_dir = os.path.join(os.getcwd(), 'reports')
            json_dir = os.path.join(reports_base_dir, 'json')
            
            # Ensure output directories exist
            os.makedirs(json_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)

            # Import CustomJSONEncoder
            from src.utils.json_encoder import CustomJSONEncoder

            # Save to file using CustomJSONEncoder in both locations
            json_path = os.path.join(output_dir, filename)
            reports_json_path = os.path.join(json_dir, filename)
            
            json_content = json.dumps(data, indent=2, cls=CustomJSONEncoder)
            
            # Save to output_dir as requested
            with open(json_path, "w") as f:
                f.write(json_content)
                
            # Also save to reports/json directory
            with open(reports_json_path, "w") as f:
                f.write(json_content)

            self._log(f"JSON data exported to {json_path} and {reports_json_path}")
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
        elif hasattr(pd, "Timestamp") and isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32, np.float16)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient="records")
        elif isinstance(obj, pd.Series):
            return obj.to_dict()
        else:
            return obj

    def _add_watermark_to_template(
        self, html_content: str, watermark_text: str = "VIRTUOSO CRYPTO"
    ) -> str:
        """
        Add a watermark to the HTML template.
        
        Args:
            html_content: The HTML content of the template
            watermark_text: The text to use as watermark
            
        Returns:
            HTML content with watermark
        """
        self._log("Adding watermark to HTML template")

        # Define watermark styles
        watermark_styles = """
        /* Watermark styling */
        .watermark {
            position: fixed;
            top: 0;
            left: 0;
            height: 100%;
            width: 100%;
            z-index: -1;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        /* Text-based watermark */
        .text-watermark {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-45deg);
            font-size: 80px;
            color: rgba(76, 175, 80, 0.03); /* Very light green */
            font-weight: bold;
            white-space: nowrap;
            pointer-events: none;
            z-index: -1;
            width: 100%;
            text-align: center;
        }
        """

        # Define watermark div
        watermark_div = f'<div class="text-watermark">{watermark_text}</div>'

        # Add styles to the HTML head if they don't exist already
        if ".text-watermark {" not in html_content:
            html_content = html_content.replace(
                "</style>", f"{watermark_styles}\n    </style>"
            )

        # Add watermark div after body tag if it doesn't exist already
        if "text-watermark" not in html_content:
            html_content = html_content.replace(
                '<body class="crt-effect">',
                f'<body class="crt-effect">\n    {watermark_div}',
            )

        return html_content

    def generate_trading_report(
        self,
        signal_data: Dict[str, Any],
        ohlcv_data: Optional[pd.DataFrame] = None,
        output_dir: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
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
            # Create separate directories for different file types
            reports_base_dir = os.path.join(os.getcwd(), 'reports')
            html_dir = os.path.join(reports_base_dir, 'html')
            pdf_dir = os.path.join(reports_base_dir, 'pdf')
            json_dir = os.path.join(reports_base_dir, 'json')
            charts_dir = os.path.join(reports_base_dir, 'charts')
            
            # Ensure directories exist
            os.makedirs(html_dir, exist_ok=True)
            os.makedirs(pdf_dir, exist_ok=True)
            os.makedirs(json_dir, exist_ok=True)
            os.makedirs(charts_dir, exist_ok=True)
            
            # Use provided output_dir or default to pdf_dir
            if output_dir:
                # If output_dir is a complete file path with extension, use it directly
                if output_dir.lower().endswith('.pdf'):
                    pdf_path = output_dir
                    # Make sure the parent directory exists
                    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
                else:
                    # It's a directory, make sure it exists
                    os.makedirs(output_dir, exist_ok=True)
                    # Generate a filename within this directory
                    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    symbol = signal_data.get("symbol", "UNKNOWN").replace("/", "_").lower()
                    signal_type = signal_data.get("signal_type", "UNKNOWN").lower()
                    pdf_filename = f"{symbol}_{signal_type}_{timestamp_str}.pdf"
                    pdf_path = os.path.join(output_dir, pdf_filename)
            else:
                # Use default directory with generated filename
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                symbol = signal_data.get("symbol", "UNKNOWN").replace("/", "_").lower()
                signal_type = signal_data.get("signal_type", "UNKNOWN").lower()
                pdf_filename = f"{symbol}_{signal_type}_{timestamp_str}.pdf"
                pdf_path = os.path.join(pdf_dir, pdf_filename)

            # Initialize context for template rendering
            context = {}

            # Initialize image paths to None
            candlestick_chart = None
            component_chart = None
            confluence_analysis_image = None
            confluence_visualization = None

            # Extract basic signal data
            symbol = signal_data.get("symbol", "UNKNOWN")
            signal_type = signal_data.get("signal_type", "UNKNOWN")
            # CHANGED: Use confluence_score as the primary score source
            confluence_score = signal_data.get("confluence_score", signal_data.get("score", 0))
            price = signal_data.get("price", 0)
            timestamp = signal_data.get(
                "timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            reliability = signal_data.get("reliability", 0.5)

            # Add basic data to context
            context.update(
                {
                    "symbol": symbol,
                    "signal_type": signal_type,
                    "score": confluence_score,  # CHANGED: Using confluence_score instead of score
                    "price": price,
                    "timestamp": timestamp,
                    "reliability": reliability,
                }
            )

            # Create candlestick chart if OHLCV data is provided
            try:
                if ohlcv_data is not None and not ohlcv_data.empty:
                    self._log("Creating candlestick chart from OHLCV data")

                    # Get trade parameters if available
                    trade_params = signal_data.get("trade_params", {})
                    entry_price = trade_params.get("entry_price", None)
                    stop_loss = trade_params.get("stop_loss", None)
                    targets = trade_params.get("targets", None)

                    # Create chart
                    candlestick_chart = self._create_candlestick_chart(
                        symbol=symbol,
                        ohlcv_data=ohlcv_data,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        targets=targets,
                        output_dir=os.path.dirname(pdf_path),
                    )
                    
                    # If real data chart failed but we have trade params, fall back to simulated
                    if candlestick_chart is None and trade_params:
                        self._log("Real data chart failed, falling back to simulated chart", logging.WARNING)
                        candlestick_chart = self._create_simulated_chart(
                            symbol=symbol,
                            entry_price=entry_price or price,
                            stop_loss=stop_loss,
                            targets=targets,
                            output_dir=os.path.dirname(pdf_path),
                        )
                elif signal_data.get("trade_params", None):
                    self._log("Creating simulated chart from trade parameters")

                    # Get trade parameters
                    trade_params = signal_data.get("trade_params", {})
                    entry_price = trade_params.get("entry_price", price)
                    stop_loss = trade_params.get("stop_loss", None)
                    targets = trade_params.get("targets", None)

                    # Create simulated chart
                    candlestick_chart = self._create_simulated_chart(
                        symbol=symbol,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        targets=targets,
                        output_dir=os.path.dirname(pdf_path),
                    )
            except Exception as e:
                self._log(
                    f"Error creating candlestick chart: {str(e)}", level=logging.ERROR
                )

            # Add chart to template context
            context["candlestick_chart"] = candlestick_chart

            # Create component chart image
            try:
                components = signal_data.get("components", {})

                self._log(f"Components type: {type(components)}")
                self._log(
                    f"Components for chart: {list(components.keys()) if isinstance(components, dict) else 'None'}"
                )

                if components and isinstance(components, dict):
                    component_chart = self._create_component_chart(
                        components, output_dir
                    )
                    self._log(f"Component chart created: {component_chart is not None}")

                    # Add confluence visualization
                    try:
                        from src.monitoring.visualizers.confluence_visualizer import (
                            ConfluenceVisualizer,
                        )

                        # Extract component scores
                        component_scores = {}
                        component_keys = {
                            "technical": "Technical",
                            "volume": "Volume",
                            "orderbook": "Orderbook",
                            "orderflow": "Orderflow",
                            "sentiment": "Sentiment",
                            "price_structure": "Price Structure",
                        }

                        for key, display_name in component_keys.items():
                            comp_value = components.get(key, {})

                            # Handle different data types for component values
                            if isinstance(comp_value, dict):
                                score = comp_value.get("score", 50)
                            elif isinstance(comp_value, (int, float)):
                                score = float(comp_value)
                            elif hasattr(comp_value, "item") and callable(
                                getattr(comp_value, "item")
                            ):
                                # Handle numpy values
                                score = float(comp_value.item())
                            else:
                                score = 50  # Default value

                            component_scores[display_name] = score

                        overall_score = signal_data.get("score", 50)

                        # Create radar visualization
                        visualizer = ConfluenceVisualizer()
                        confluence_visualization = visualizer.generate_base64_image(
                            component_scores, overall_score
                        )

                        # Save 3D visualization for possible linking in HTML reports
                        symbol = signal_data.get("symbol", "UNKNOWN")
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        _, threed_path = visualizer.save_visualizations(
                            component_scores=component_scores,
                            overall_score=overall_score,
                            symbol=symbol,
                            timestamp=timestamp,
                        )

                        self._log(
                            f"Created confluence visualization and 3D chart at: {threed_path}"
                        )

                        # Add to template context
                        context["confluence_visualization"] = confluence_visualization
                        context["confluence_3d_link"] = os.path.abspath(threed_path)
                    except Exception as e:
                        self._log(
                            f"Error creating confluence visualization: {str(e)}",
                            level=logging.ERROR,
                        )
            except Exception as e:
                self._log(
                    f"Error creating component chart: {str(e)}", level=logging.ERROR
                )

            # Create confluence analysis image if text is provided
            try:
                confluence_text = signal_data.get("confluence_analysis", None)
                if confluence_text and isinstance(confluence_text, str):
                    self._log("Creating confluence analysis image from text")
                    confluence_analysis_image = self._create_confluence_image(
                        confluence_text,
                        output_dir,
                        symbol=symbol,
                        timestamp=timestamp,
                        signal_type=signal_type,
                    )
            except Exception as e:
                self._log(
                    f"Error creating confluence analysis image: {str(e)}",
                    level=logging.ERROR,
                )

            # Add images to template context
            context["component_chart"] = component_chart
            context["confluence_analysis"] = confluence_analysis_image

            # Prepare component data for the template
            component_data = []
            try:
                if isinstance(components, dict):
                    for name, data in components.items():
                        # Debug log the component data
                        self._log(
                            f"Processing component: {name} with data type: {type(data)}"
                        )

                        # Handle different component formats
                        if isinstance(data, dict):
                            score_value = float(data.get("score", 0))
                            impact = data.get("impact", 0)
                            interpretation = data.get("interpretation", "")
                        elif isinstance(data, (int, float)) or (
                            hasattr(data, "item") and callable(getattr(data, "item"))
                        ):
                            # Handle direct numeric value or numpy type
                            score_value = (
                                float(data)
                                if isinstance(data, (int, float))
                                else float(data.item())
                            )
                            impact = (
                                abs(score_value - 50) * 2
                            )  # Calculate impact from score
                            interpretation = ""
                        else:
                            self._log(
                                f"Warning: Component {name} has unexpected data type: {type(data)}"
                            )
                            continue

                        # Determine color class based on score
                        if score_value >= 65:
                            color_class = "high-score"
                        elif score_value <= 35:
                            color_class = "low-score"
                        else:
                            color_class = "medium-score"

                        component_data.append(
                            {
                                "name": name,
                                "score": score_value,
                                "impact": impact,
                                "interpretation": interpretation,
                                "color_class": color_class,
                            }
                        )

                    # Sort components by impact
                    component_data.sort(key=lambda x: abs(x["impact"]), reverse=True)
            except Exception as e:
                self._log(f"Error processing components: {str(e)}", logging.ERROR)

            # Format timestamp
            formatted_timestamp = ""
            try:
                if isinstance(timestamp, str):
                    try:
                        timestamp_dt = datetime.fromisoformat(timestamp)
                        formatted_timestamp = timestamp_dt.strftime(
                            "%Y-%m-%d %H:%M:%S UTC"
                        )
                    except:
                        formatted_timestamp = timestamp
                elif isinstance(timestamp, datetime):
                    formatted_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
                elif isinstance(timestamp, (int, float)):
                    # Handle timestamp as Unix time
                    timestamp_dt = datetime.fromtimestamp(
                        timestamp / 1000 if timestamp > 1e12 else timestamp
                    )
                    formatted_timestamp = timestamp_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                else:
                    formatted_timestamp = str(timestamp)
            except Exception as e:
                self._log(f"Error formatting timestamp: {str(e)}", logging.ERROR)
                formatted_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

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
                # Add debug logging for market interpretations format
                self._log(f"Processing market interpretations for {symbol}", level=logging.DEBUG)
                
                # Use market_interpretations as insights if available, otherwise fall back to insights
                insights = signal_data.get("market_interpretations", signal_data.get("insights", []))
                actionable_insights = signal_data.get("actionable_insights", [])
                
                # Debug log for insights format
                if insights:
                    if isinstance(insights, list):
                        self._log(f"Market interpretations found: {len(insights)} items", level=logging.DEBUG)
                        if len(insights) > 0:
                            self._log(f"First interpretation type: {type(insights[0]).__name__}", level=logging.DEBUG)
                            if isinstance(insights[0], dict):
                                self._log(f"First interpretation keys: {list(insights[0].keys())}", level=logging.DEBUG)
                                if 'interpretation' in insights[0]:
                                    self._log(f"Interpretation value type: {type(insights[0]['interpretation']).__name__}", level=logging.DEBUG)
                    else:
                        self._log(f"Market interpretations not in list format: {type(insights).__name__}", level=logging.DEBUG)
                else:
                    self._log("No market interpretations found", level=logging.DEBUG)
                
                # If market_interpretations are in object format (dict with 'interpretation' field), extract just the text
                if insights and isinstance(insights[0], dict) and 'interpretation' in insights[0]:
                    self._log("Converting structured interpretations to text-only format for PDF", level=logging.DEBUG)
                    insights = [item.get('interpretation', '') for item in insights]
                    self._log(f"Extracted {len(insights)} text interpretations", level=logging.DEBUG)
            except Exception as e:
                self._log(f"Error extracting insights: {str(e)}", logging.ERROR)
                self._log(traceback.format_exc(), logging.DEBUG)

            # Extract risk management details
            entry_price = price
            stop_loss = None
            stop_loss_percent = 0
            try:
                entry_price = signal_data.get("entry_price", price)
                stop_loss = signal_data.get("stop_loss", None)

                if stop_loss and entry_price:
                    if entry_price > stop_loss:  # Long position
                        stop_loss_percent = ((stop_loss / entry_price) - 1) * 100
                    else:  # Short position
                        stop_loss_percent = ((entry_price / stop_loss) - 1) * 100
            except Exception as e:
                self._log(
                    f"Error extracting risk management details: {str(e)}", logging.ERROR
                )

            # Format targets
            targets = []
            try:
                targets_data = signal_data.get("targets", {})

                if isinstance(targets_data, dict):
                    for target_name, target_data in targets_data.items():
                        if isinstance(target_data, dict) and "price" in target_data:
                            target_price = target_data.get("price", 0)
                            target_size = target_data.get("size", 0)

                            if target_price > 0:
                                target_percent = 0
                                if entry_price > 0:
                                    if target_price > entry_price:  # Long position
                                        target_percent = (
                                            (target_price / entry_price) - 1
                                        ) * 100
                                    else:  # Short position
                                        target_percent = (
                                            (entry_price / target_price) - 1
                                        ) * 100

                                targets.append(
                                    {
                                        "name": target_name,
                                        "price": target_price,
                                        "percent": target_percent,
                                        "size": target_size,
                                    }
                                )
            except Exception as e:
                self._log(f"Error formatting targets: {str(e)}", logging.ERROR)

            # Export JSON data
            json_path = None
            try:
                json_filename = (
                    f"{symbol.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                if output_dir is None:
                    self._log("Skipping JSON export: output_dir is None", logging.ERROR)
                    json_path = None
                else:
                    json_path = self._export_json_data(
                        signal_data, json_filename, output_dir
                    )
            except Exception as e:
                self._log(f"Error exporting JSON data: {str(e)}", logging.ERROR)

            # Get the relative path for JSON (for display in PDF)
            if json_path:
                json_rel_path = os.path.basename(json_path)
            else:
                json_rel_path = "Not available"

            # Prepare template context
            context = {
                "symbol": symbol,
                "score": confluence_score,  # CHANGED: Using confluence_score instead of score
                "score_width_pct": f"{min(max(confluence_score, 0), 100)}%",  # CHANGED: Using confluence_score
                "reliability": reliability * 100,  # Convert from decimal (0-1) to percentage (0-100)
                "price": price,
                "timestamp": formatted_timestamp,
                "signal_type": signal_type,
                # Map signal_type to valid CSS color values instead of using signal_type directly
                "signal_color": "#4CAF50" if signal_type == "BUY" else "#F44336" if signal_type == "SELL" else "#FFC107",  # Green for BUY, Red for SELL, Amber for NEUTRAL
                "component_data": component_data,
                "insights": insights,
                "actionable_insights": actionable_insights,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "stop_loss_percent": stop_loss_percent,
                "targets": targets,
                "hostname": hostname,
                "json_path": json_rel_path,
                "candlestick_chart": os.path.abspath(candlestick_chart)
                if candlestick_chart
                else None,
                "component_chart": os.path.abspath(component_chart)
                if component_chart
                else None,
                "confluence_analysis": confluence_analysis_image,
                "confluence_visualization": confluence_visualization,
            }

            # Render the HTML template
            try:
                template = self.env.get_template("trading_report_dark.html")

                # Fix image paths by ensuring they are absolute and using file:// protocol
                if candlestick_chart:
                    candlestick_chart = f"file://{os.path.abspath(candlestick_chart)}"
                if component_chart:
                    component_chart = f"file://{os.path.abspath(component_chart)}"
                if confluence_analysis_image:
                    confluence_analysis_image = (
                        f"file://{os.path.abspath(confluence_analysis_image)}"
                    )
                if confluence_visualization:
                    confluence_visualization = (
                        f"file://{os.path.abspath(confluence_visualization)}"
                    )

                # Update context with fixed image paths
                context.update(
                    {
                        "candlestick_chart": candlestick_chart,
                        "component_chart": component_chart,
                        "confluence_analysis": confluence_analysis_image,
                        "confluence_visualization": confluence_visualization,
                    }
                )

                # Render the template
                html_content = template.render(**context)

                # Add watermark to the rendered HTML
                watermark_text = signal_data.get("watermark_text", "VIRTUOSO CRYPTO")
                html_content = self._add_watermark_to_template(
                    html_content, watermark_text
                )

            except Exception as e:
                self._log(f"Error rendering HTML template: {str(e)}", logging.ERROR)
                return None, json_path

            # Generate PDF
            try:
                # Create a human-readable timestamp
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Get signal type (default to NEUTRAL if not available)
                signal_type = signal_data.get("signal_type", signal_data.get("signal", "NEUTRAL")).upper()
                
                # Get score and round to one decimal place
                # CHANGED: Use confluence_score as the primary score source
                confluence_score = signal_data.get("confluence_score", signal_data.get("score", 0))
                score_str = f"{confluence_score:.1f}".replace('.', 'p')  # Replace decimal with 'p' for filename compatibility
                
                # Format symbol consistently
                symbol_safe = symbol.lower().replace('/', '_')
                
                # Create a descriptive filename
                base_filename = f"{symbol_safe}_{signal_type}_{score_str}_{timestamp_str}"
                
                html_filename = f"{base_filename}.html"
                pdf_filename = f"{base_filename}.pdf"
                json_filename = f"{base_filename}.json"
                
                html_path = os.path.join(html_dir, html_filename)
                pdf_path = os.path.join(pdf_dir, pdf_filename)
                
                # Create PDF from HTML
                HTML(string=html_content).write_pdf(pdf_path)
                
                # Also save the HTML file
                with open(html_path, "w") as f:
                    f.write(html_content)

                # Export JSON data
                json_path = self._export_json_data(signal_data, json_filename, json_dir)

                self._log(f"Trading report generated: HTML: {html_path}, PDF: {pdf_path}, JSON: {json_path}")
                return pdf_path, json_path
            except Exception as e:
                self._log(f"Error generating PDF: {str(e)}", logging.ERROR)
                return None, json_path

            # Return the paths to the PDF and JSON files
            if os.path.exists(pdf_path):
                self._log(f"Successfully created PDF report: {pdf_path}")
                
                # Clear the downsampling cache to free memory
                self._clear_downsample_cache()
                
                return pdf_path, json_path
            else:
                self._log(f"Failed to create PDF report: {pdf_path}", level=logging.ERROR)
                
                # Clear the cache even if generation failed
                self._clear_downsample_cache()
                
                return None, None

        except Exception as e:
            self._log(f"Error generating trading report: {str(e)}", level=logging.ERROR)
            self._log(traceback.format_exc(), level=logging.ERROR)
            
            # Clear the cache on exception
            self._clear_downsample_cache()
            
            return None, None

    async def generate_market_report(
        self, market_data: dict, output_path: Optional[str] = None
    ) -> bool:
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
                self.logger.error(
                    f"Market data must be a dictionary, got {type(market_data)}"
                )
                try:
                    market_data = dict(market_data)
                    self.logger.info("Successfully converted market_data to dictionary")
                except (TypeError, ValueError) as e:
                    self.logger.error(
                        f"Could not convert market_data to dictionary: {str(e)}"
                    )
                    self.logger.debug(f"market_data contents: {market_data}")
                    return False

            self.logger.debug(
                f"Market data has {len(market_data)} keys: {list(market_data.keys())}"
            )

            # Create a PDF document
            self.logger.debug("Creating PDF document")
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                from reportlab.lib import colors
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.platypus import (
                    SimpleDocTemplate,
                    Paragraph,
                    Spacer,
                    Table,
                    TableStyle,
                )

                self.logger.debug("Required reportlab modules imported successfully")
            except ImportError as import_error:
                self.logger.error(
                    f"Failed to import reportlab modules: {str(import_error)}"
                )
                return False

            # Set up output path
            if not output_path:
                try:
                    timestamp = market_data.get("timestamp", int(time.time() * 1000))
                    if isinstance(timestamp, str):
                        try:
                            timestamp = int(timestamp)
                        except ValueError:
                            timestamp = int(time.time() * 1000)

                    dt = datetime.fromtimestamp(timestamp / 1000)
                    timestamp_str = dt.strftime("%Y%m%d_%H%M%S")
                    
                    # Extract report type or set a default
                    report_type = market_data.get("report_type", "MARKET").upper()
                    
                    # Format market name if available
                    market_name = market_data.get("market", "crypto").lower().replace(" ", "_")
                    
                    # Create a more descriptive filename
                    output_path = f"{market_name}_{report_type}_report_{timestamp_str}.pdf"
                    self.logger.debug(f"Generated output path: {output_path}")
                except Exception as path_error:
                    self.logger.error(
                        f"Error generating output path: {str(path_error)}"
                    )
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
                    self.logger.error(
                        f"Failed to create output directory: {str(dir_error)}"
                    )
                    # Use current directory as fallback
                    output_path = os.path.basename(output_path)
                    self.logger.info(
                        f"Using current directory for output: {output_path}"
                    )

            self.logger.debug(f"Setting up PDF document at: {output_path}")
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            elements = []

            # Set up styles
            self.logger.debug("Setting up document styles")
            try:
                styles = getSampleStyleSheet()
                title_style = styles["Title"]
                heading_style = styles["Heading1"]
                normal_style = styles["Normal"]

                # Create custom styles
                timestamp_style = ParagraphStyle(
                    "Timestamp", parent=normal_style, fontSize=8, textColor=colors.gray
                )

                section_title_style = ParagraphStyle(
                    "SectionTitle", parent=heading_style, fontSize=14, spaceAfter=6
                )

                self.logger.debug("Document styles set up successfully")
            except Exception as style_error:
                self.logger.error(
                    f"Error setting up document styles: {str(style_error)}"
                )
                # Use default styles as fallback
                styles = getSampleStyleSheet()
                title_style = styles["Title"]
                heading_style = styles["Heading1"]
                normal_style = styles["Normal"]
                timestamp_style = normal_style
                section_title_style = heading_style

            # Add title
            self.logger.debug("Adding report title")
            try:
                elements.append(Paragraph("Crypto Market Report", title_style))
                elements.append(Spacer(1, 12))

                # Add timestamp
                timestamp = market_data.get("timestamp", int(time.time() * 1000))
                try:
                    if isinstance(timestamp, str):
                        timestamp = int(timestamp)
                    dt = datetime.fromtimestamp(timestamp / 1000)
                    date_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                except (ValueError, TypeError) as timestamp_error:
                    self.logger.warning(
                        f"Error parsing timestamp: {str(timestamp_error)}"
                    )
                    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

                elements.append(Paragraph(f"Generated: {date_str}", timestamp_style))
                elements.append(Spacer(1, 20))
                self.logger.debug(f"Added title and timestamp: {date_str}")
            except Exception as title_error:
                self.logger.error(f"Error adding title: {str(title_error)}")

            # Add market overview section
            if "market_overview" in market_data:
                self.logger.debug("Adding market overview section")
                try:
                    overview = market_data["market_overview"]
                    elements.append(Paragraph("Market Overview", section_title_style))

                    if isinstance(overview, dict):
                        # Create a table for market overview
                        data = []
                        for key, value in overview.items():
                            formatted_key = key.replace("_", " ").title()
                            formatted_value = str(value)
                            data.append([formatted_key, formatted_value])

                        if data:
                            table = Table(data, colWidths=[200, 300])
                            table.setStyle(
                                TableStyle(
                                    [
                                        (
                                            "BACKGROUND",
                                            (0, 0),
                                            (0, -1),
                                            colors.lightgrey,
                                        ),
                                        ("TEXTCOLOR", (0, 0), (0, -1), colors.black),
                                        ("ALIGN", (0, 0), (0, -1), "LEFT"),
                                        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                                        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
                                        (
                                            "INNERGRID",
                                            (0, 0),
                                            (-1, -1),
                                            0.25,
                                            colors.black,
                                        ),
                                    ]
                                )
                            )
                            elements.append(table)
                        else:
                            elements.append(
                                Paragraph(
                                    "No market overview data available", normal_style
                                )
                            )
                    else:
                        elements.append(
                            Paragraph(f"Market overview: {str(overview)}", normal_style)
                        )

                    elements.append(Spacer(1, 15))
                    self.logger.debug("Market overview section added successfully")
                except Exception as overview_error:
                    self.logger.error(
                        f"Error adding market overview section: {str(overview_error)}"
                    )
                    elements.append(
                        Paragraph(
                            "Market Overview: Error processing data", normal_style
                        )
                    )
                    elements.append(Spacer(1, 15))

            # Add top performers section
            if "top_performers" in market_data:
                self.logger.debug("Adding top performers section")
                try:
                    performers = market_data["top_performers"]
                    elements.append(Paragraph("Top Performers", section_title_style))

                    if isinstance(performers, list) and performers:
                        # Create a table for top performers
                        headers = ["Symbol", "Change %", "Price", "Category"]
                        data = [headers]

                        for item in performers:
                            if isinstance(item, dict):
                                symbol = item.get("symbol", "N/A")
                                change = item.get("change_percent", "N/A")
                                if isinstance(change, (float, int)):
                                    change = f"{change:.2f}%"
                                price = item.get("price", "N/A")
                                category = item.get("category", "")

                                data.append([symbol, str(change), str(price), category])

                        if len(data) > 1:
                            table = Table(data, colWidths=[100, 100, 100, 200])
                            table.setStyle(
                                TableStyle(
                                    [
                                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                                        (
                                            "TEXTCOLOR",
                                            (0, 0),
                                            (-1, 0),
                                            colors.whitesmoke,
                                        ),
                                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                                        ("TOPPADDING", (0, 0), (-1, 0), 12),
                                        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                                        ("TOPPADDING", (0, 1), (-1, -1), 6),
                                        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
                                        (
                                            "INNERGRID",
                                            (0, 0),
                                            (-1, -1),
                                            0.25,
                                            colors.black,
                                        ),
                                    ]
                                )
                            )

                            # Add color for positive/negative changes
                            for i in range(1, len(data)):
                                change_text = data[i][1]
                                if change_text.startswith("-"):
                                    table.setStyle(
                                        TableStyle(
                                            [("TEXTCOLOR", (1, i), (1, i), colors.red),]
                                        )
                                    )
                                elif any(char.isdigit() for char in change_text):
                                    table.setStyle(
                                        TableStyle(
                                            [
                                                (
                                                    "TEXTCOLOR",
                                                    (1, i),
                                                    (1, i),
                                                    colors.green,
                                                ),
                                            ]
                                        )
                                    )

                            elements.append(table)
                        else:
                            elements.append(
                                Paragraph(
                                    "No top performers data available", normal_style
                                )
                            )
                    else:
                        elements.append(
                            Paragraph("No top performers data available", normal_style)
                        )

                    elements.append(Spacer(1, 15))
                    self.logger.debug("Top performers section added successfully")
                except Exception as performers_error:
                    self.logger.error(
                        f"Error adding top performers section: {str(performers_error)}"
                    )
                    elements.append(
                        Paragraph("Top Performers: Error processing data", normal_style)
                    )
                    elements.append(Spacer(1, 15))

            # Add market sentiment section
            if "market_sentiment" in market_data:
                self.logger.debug("Adding market sentiment section")
                try:
                    sentiment = market_data["market_sentiment"]
                    elements.append(Paragraph("Market Sentiment", section_title_style))

                    if isinstance(sentiment, dict):
                        # Create a table for market sentiment
                        data = []
                        for key, value in sentiment.items():
                            formatted_key = key.replace("_", " ").title()
                            formatted_value = str(value)
                            data.append([formatted_key, formatted_value])

                        if data:
                            table = Table(data, colWidths=[200, 300])
                            table.setStyle(
                                TableStyle(
                                    [
                                        (
                                            "BACKGROUND",
                                            (0, 0),
                                            (0, -1),
                                            colors.lightgrey,
                                        ),
                                        ("TEXTCOLOR", (0, 0), (0, -1), colors.black),
                                        ("ALIGN", (0, 0), (0, -1), "LEFT"),
                                        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                                        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
                                        (
                                            "INNERGRID",
                                            (0, 0),
                                            (-1, -1),
                                            0.25,
                                            colors.black,
                                        ),
                                    ]
                                )
                            )
                            elements.append(table)
                        else:
                            elements.append(
                                Paragraph(
                                    "No market sentiment data available", normal_style
                                )
                            )
                    else:
                        elements.append(
                            Paragraph(
                                f"Market sentiment: {str(sentiment)}", normal_style
                            )
                        )

                    elements.append(Spacer(1, 15))
                    self.logger.debug("Market sentiment section added successfully")
                except Exception as sentiment_error:
                    self.logger.error(
                        f"Error adding market sentiment section: {str(sentiment_error)}"
                    )
                    elements.append(
                        Paragraph(
                            "Market Sentiment: Error processing data", normal_style
                        )
                    )
                    elements.append(Spacer(1, 15))

            # Add trading signals section
            if "trading_signals" in market_data:
                self.logger.debug("Adding trading signals section")
                try:
                    signals = market_data["trading_signals"]
                    elements.append(Paragraph("Trading Signals", section_title_style))

                    if isinstance(signals, list) and signals:
                        # Create a table for trading signals
                        headers = ["Symbol", "Signal", "Strength", "Timeframe"]
                        data = [headers]

                        for signal in signals:
                            if isinstance(signal, dict):
                                symbol = signal.get("symbol", "N/A")
                                signal_type = signal.get("signal", "N/A")
                                strength = signal.get("strength", "N/A")
                                timeframe = signal.get("timeframe", "N/A")

                                data.append(
                                    [symbol, signal_type, str(strength), timeframe]
                                )

                        if len(data) > 1:
                            table = Table(data, colWidths=[100, 100, 100, 200])
                            table.setStyle(
                                TableStyle(
                                    [
                                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                                        (
                                            "TEXTCOLOR",
                                            (0, 0),
                                            (-1, 0),
                                            colors.whitesmoke,
                                        ),
                                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                                        ("TOPPADDING", (0, 0), (-1, 0), 12),
                                        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                                        ("TOPPADDING", (0, 1), (-1, -1), 6),
                                        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
                                        (
                                            "INNERGRID",
                                            (0, 0),
                                            (-1, -1),
                                            0.25,
                                            colors.black,
                                        ),
                                    ]
                                )
                            )

                            # Add color for buy/sell signals
                            for i in range(1, len(data)):
                                signal_type = data[i][1].lower()
                                if "buy" in signal_type or "bullish" in signal_type:
                                    table.setStyle(
                                        TableStyle(
                                            [
                                                (
                                                    "TEXTCOLOR",
                                                    (1, i),
                                                    (1, i),
                                                    colors.green,
                                                ),
                                            ]
                                        )
                                    )
                                elif "sell" in signal_type or "bearish" in signal_type:
                                    table.setStyle(
                                        TableStyle(
                                            [("TEXTCOLOR", (1, i), (1, i), colors.red),]
                                        )
                                    )

                            elements.append(table)
                        else:
                            elements.append(
                                Paragraph(
                                    "No trading signals data available", normal_style
                                )
                            )
                    else:
                        elements.append(
                            Paragraph("No trading signals data available", normal_style)
                        )

                    elements.append(Spacer(1, 15))
                    self.logger.debug("Trading signals section added successfully")
                except Exception as signals_error:
                    self.logger.error(
                        f"Error adding trading signals section: {str(signals_error)}"
                    )
                    elements.append(
                        Paragraph(
                            "Trading Signals: Error processing data", normal_style
                        )
                    )
                    elements.append(Spacer(1, 15))

            # Add notable news section
            if "notable_news" in market_data:
                self.logger.debug("Adding notable news section")
                try:
                    news = market_data["notable_news"]
                    elements.append(Paragraph("Notable News", section_title_style))

                    if isinstance(news, list) and news:
                        for item in news:
                            if isinstance(item, dict):
                                title = item.get("title", "N/A")
                                source = item.get("source", "")
                                summary = item.get("summary", "")

                                elements.append(
                                    Paragraph(f"<b>{title}</b>", normal_style)
                                )
                                if source:
                                    elements.append(
                                        Paragraph(f"Source: {source}", timestamp_style)
                                    )
                                if summary:
                                    elements.append(Paragraph(summary, normal_style))
                                elements.append(Spacer(1, 10))
                            else:
                                elements.append(Paragraph(str(item), normal_style))
                                elements.append(Spacer(1, 5))
                    else:
                        elements.append(
                            Paragraph("No notable news data available", normal_style)
                        )

                    elements.append(Spacer(1, 15))
                    self.logger.debug("Notable news section added successfully")
                except Exception as news_error:
                    self.logger.error(
                        f"Error adding notable news section: {str(news_error)}"
                    )
                    elements.append(
                        Paragraph("Notable News: Error processing data", normal_style)
                    )
                    elements.append(Spacer(1, 15))

            # Add a footer with page numbers
            self.logger.debug("Adding page footer")

            # Fixed footer callback function that doesn't rely on doc.build.current_page
            def footer(canvas, doc):
                canvas.saveState()
                canvas.setFont("Helvetica", 8)
                page_num = f"Page {doc.page}"  # Simplified page numbering
                canvas.drawRightString(letter[0] - 30, 30, page_num)
                canvas.restoreState()

            # Build the PDF
            self.logger.debug("Building PDF document")
            try:
                doc.build(elements, onFirstPage=footer, onLaterPages=footer)
                self.logger.info(
                    f"Basic market report PDF generated successfully: {output_path}"
                )
                return True
            except Exception as build_error:
                self.logger.error(f"Error building PDF document: {str(build_error)}")
                self.logger.debug(traceback.format_exc())

                # Try saving to a default location if output directory issues
                if output_dir and not os.path.exists(output_dir):
                    emergency_path = f"emergency_market_report_{int(time.time())}.pdf"
                    self.logger.warning(
                        f"Trying emergency save to current directory: {emergency_path}"
                    )

                    try:
                        doc = SimpleDocTemplate(emergency_path, pagesize=letter)
                        doc.build(elements)
                        self.logger.info(
                            f"Emergency PDF save successful: {emergency_path}"
                        )
                        return True
                    except Exception as emergency_error:
                        self.logger.error(
                            f"Emergency PDF save failed: {str(emergency_error)}"
                        )
                        return False
                return False

        except Exception as e:
            self.logger.error(f"Error in generate_market_report: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False

    async def generate_market_html_report(
        self,
        market_data: dict,
        output_path: Optional[str] = None,
        template_path: Optional[str] = None,
        generate_pdf: bool = False,
    ) -> bool:
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
            # Set up directories
            reports_base_dir = os.path.join(os.getcwd(), 'reports')
            html_dir = os.path.join(reports_base_dir, 'html')
            pdf_dir = os.path.join(reports_base_dir, 'pdf')
            
            os.makedirs(html_dir, exist_ok=True)
            os.makedirs(pdf_dir, exist_ok=True)

            # Validate market_data structure
            if market_data is None:
                self.logger.error("Market data is None, cannot generate HTML report")
                return False

            if not isinstance(market_data, dict):
                self.logger.error(
                    f"Market data must be a dictionary, got {type(market_data)}"
                )
                # Try to convert to dict if possible
                try:
                    market_data = dict(market_data)
                    self.logger.info("Successfully converted market_data to dictionary")
                except (TypeError, ValueError) as e:
                    self.logger.error(
                        f"Could not convert market_data to dictionary: {str(e)}"
                    )
                    self.logger.debug(f"market_data contents: {market_data}")
                    return False

            self.logger.debug(
                f"Market data has {len(market_data)} keys: {list(market_data.keys())}"
            )

            # Process timestamp
            timestamp = market_data.get("timestamp", int(time.time() * 1000))
            try:
                if isinstance(timestamp, str):
                    try:
                        timestamp = int(timestamp)
                    except ValueError as timestamp_error:
                        self.logger.warning(
                            f"Could not parse timestamp '{timestamp}': {str(timestamp_error)}"
                        )
                        timestamp = int(time.time() * 1000)

                dt = datetime.fromtimestamp(timestamp / 1000)
                report_date = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                # Store both timestamp and report_date for template compatibility
                market_data["report_date"] = report_date
                market_data["timestamp"] = timestamp
                self.logger.debug(f"Processed timestamp {timestamp} to {report_date}")
            except Exception as timestamp_error:
                self.logger.error(f"Error processing timestamp: {str(timestamp_error)}")
                current_time = datetime.now()
                report_date = current_time.strftime("%Y-%m-%d %H:%M:%S UTC")
                market_data["report_date"] = report_date
                market_data["timestamp"] = int(current_time.timestamp() * 1000)
                self.logger.info(f"Using current time for report date: {report_date}")

            # Process top performers - ensure it's a list
            if "top_performers" in market_data:
                performers = market_data["top_performers"]
                if isinstance(performers, dict):
                    self.logger.info(
                        "Converting top_performers from dict to list format"
                    )
                    # Convert dict format to list format
                    performers_list = []
                    for category, items in performers.items():
                        if isinstance(items, list):
                            # Add category to each item and append to main list
                            for item in items:
                                if isinstance(item, dict):
                                    item["category"] = category
                                    performers_list.append(item)
                                else:
                                    self.logger.warning(
                                        f"Skipping non-dict item in {category}: {item}"
                                    )
                        else:
                            self.logger.warning(
                                f"Unexpected format for {category} in top_performers: {items}"
                            )
                    market_data["top_performers"] = performers_list
                    self.logger.debug(
                        f"Converted top_performers to list with {len(performers_list)} items"
                    )
                elif not isinstance(performers, list):
                    self.logger.warning(
                        f"top_performers has unexpected type: {type(performers)}, setting to empty list"
                    )
                    market_data["top_performers"] = []

            # Generate the filename
            if output_path:
                html_path = output_path
                if not html_path.endswith(".html"):
                    html_path += ".html"
            else:
                # Generate a filename based on timestamp
                try:
                    timestamp = market_data.get('timestamp', int(time.time()))
                    if isinstance(timestamp, str):
                        try:
                            timestamp = int(timestamp)
                        except ValueError:
                            timestamp = int(time.time())
                    
                    html_filename = f"market_report_{timestamp}.html"
                    html_path = os.path.join(html_dir, html_filename)
                except Exception as e:
                    self.logger.error(f"Error generating timestamp string: {str(e)}")
                    html_path = os.path.join(html_dir, f"market_report_{int(time.time())}.html")

            # Check if output directory exists
            output_dir = os.path.dirname(html_path)
            if output_dir and not os.path.exists(output_dir):
                self.logger.warning(f"Output directory does not exist: {output_dir}")
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    self.logger.info(f"Created output directory: {output_dir}")
                except Exception as dir_error:
                    self.logger.error(
                        f"Failed to create output directory: {str(dir_error)}"
                    )
                    # Try to use a default path
                    html_path = f"market_report_{int(time.time())}.html"
                    self.logger.info(f"Using default path: {html_path}")

            # Check template path and load template
            template_name = "market_report_dark.html"
            template_path = os.path.join(self.template_dir, template_name)

            # Validate template path
            if not os.path.exists(template_path):
                self.logger.error(f"Template file not found: {template_path}")
                # Check if template directory exists
                if not os.path.exists(self.template_dir):
                    self.logger.error(
                        f"Template directory does not exist: {self.template_dir}"
                    )
                else:
                    self.logger.debug(f"Template directory exists, checking contents")
                    try:
                        templates = os.listdir(self.template_dir)
                        self.logger.info(f"Available templates: {templates}")
                    except Exception as list_error:
                        self.logger.error(
                            f"Error listing template directory: {str(list_error)}"
                        )

                # Fall back to basic template
                self.logger.info("Falling back to basic report generation")
                return await self.generate_market_report(market_data, output_path)

            self.logger.debug(f"Loading template: {template_path}")
            try:
                env = Environment(loader=FileSystemLoader(self.template_dir))
                # Add custom filters
                env.filters["format_with_commas"] = self._format_with_commas
                env.filters["format_number"] = self._format_number
                template = env.get_template(template_name)
                self.logger.debug("Template loaded successfully")
            except Exception as template_error:
                self.logger.error(f"Error loading template: {str(template_error)}")
                self.logger.debug(traceback.format_exc())

                # Check if we have permission to read the template
                try:
                    with open(template_path, "r") as f:
                        template_content = f.read()
                    self.logger.debug(
                        f"Template file is readable, first 100 chars: {template_content[:100]}"
                    )
                except Exception as read_error:
                    self.logger.error(f"Cannot read template file: {str(read_error)}")

                # Fall back to basic template
                self.logger.info(
                    "Falling back to basic report generation due to template error"
                )
                return await self.generate_market_report(market_data, output_path)

            # Test render each part of the template to find problematic sections
            try:
                self.logger.debug(
                    "Testing partial renders to identify problematic sections"
                )
                test_data = {"report_date": market_data.get("report_date", "Unknown")}

                # Test basic sections
                template.render(report_date=test_data["report_date"])
                self.logger.debug("Basic report_date render successful")

                # Test market overview
                if "market_overview" in market_data:
                    try:
                        overview_data = market_data["market_overview"]
                        template.render(
                            report_date=test_data["report_date"],
                            market_overview=overview_data,
                        )
                        self.logger.debug("market_overview render successful")
                    except Exception as section_error:
                        self.logger.error(
                            f"Error rendering market_overview section: {str(section_error)}"
                        )
                        # Remove problematic section
                        market_data.pop("market_overview", None)

                # Test top performers
                if "top_performers" in market_data:
                    try:
                        performers_data = market_data["top_performers"]
                        template.render(
                            report_date=test_data["report_date"],
                            top_performers=performers_data,
                        )
                        self.logger.debug("top_performers render successful")
                    except Exception as section_error:
                        self.logger.error(
                            f"Error rendering top_performers section: {str(section_error)}"
                        )
                        # Remove problematic section
                        market_data.pop("top_performers", None)

                # Test market sentiment
                if "market_sentiment" in market_data:
                    try:
                        sentiment_data = market_data["market_sentiment"]
                        template.render(
                            report_date=test_data["report_date"],
                            market_sentiment=sentiment_data,
                        )
                        self.logger.debug("market_sentiment render successful")
                    except Exception as section_error:
                        self.logger.error(
                            f"Error rendering market_sentiment section: {str(section_error)}"
                        )
                        # Remove problematic section
                        market_data.pop("market_sentiment", None)

                # Test trading signals
                if "trading_signals" in market_data:
                    try:
                        signals_data = market_data["trading_signals"]
                        template.render(
                            report_date=test_data["report_date"],
                            trading_signals=signals_data,
                        )
                        self.logger.debug("trading_signals render successful")
                    except Exception as section_error:
                        self.logger.error(
                            f"Error rendering trading_signals section: {str(section_error)}"
                        )
                        # Remove problematic section
                        market_data.pop("trading_signals", None)

                # Test notable news
                if "notable_news" in market_data:
                    try:
                        news_data = market_data["notable_news"]
                        template.render(
                            report_date=test_data["report_date"], notable_news=news_data
                        )
                        self.logger.debug("notable_news render successful")
                    except Exception as section_error:
                        self.logger.error(
                            f"Error rendering notable_news section: {str(section_error)}"
                        )
                        # Remove problematic section
                        market_data.pop("notable_news", None)

                self.logger.debug("All section renders tested")
            except Exception as test_error:
                self.logger.error(f"Error during test rendering: {str(test_error)}")

            # Render the template with market data
            try:
                self.logger.debug("Rendering full template")

                # Add required missing fields with defaults
                if "additional_sections" not in market_data:
                    market_data["additional_sections"] = {}
                
                # Ensure critical sections have at least empty structures
                market_data.setdefault("market_overview", {})
                market_data.setdefault("futures_premium", {})
                market_data.setdefault("smart_money_index", {})
                market_data.setdefault("whale_activity", {})
                market_data.setdefault("top_performers", [])
                market_data.setdefault("trading_signals", [])
                market_data.setdefault("notable_news", [])
                
                # Add comprehensive logging of data structure
                try:
                    # Use a custom encoder or fallback to simple string conversion for problem values
                    class DebugEncoder(json.JSONEncoder):
                        def default(self, obj):
                            try:
                                return super().default(obj)
                            except:
                                return str(obj)
                    
                    self.logger.debug(
                        f"Market data keys: {sorted(market_data.keys())}"
                    )
                    
                    # Log sample of each section to identify structure issues
                    for key in ["market_overview", "futures_premium", "smart_money_index", "whale_activity"]:
                        if key in market_data:
                            sample = str(market_data[key])[:200] + "..." if len(str(market_data[key])) > 200 else str(market_data[key])
                            self.logger.debug(f"{key} sample: {sample}")
                except Exception as log_error:
                    self.logger.error(f"Error logging market data structure: {str(log_error)}")

                html_content = template.render(**market_data)
                
                # Log HTML content preview
                html_preview = html_content[:500] + "..." if len(html_content) > 500 else html_content
                self.logger.debug(f"HTML content preview: {html_preview}")
                self.logger.info(f"HTML content length: {len(html_content)} characters")
                
                # Check for actual content in the HTML
                missing_content = True
                key_phrases = ["Market Overview", "Market Intelligence", "Virtuoso"]
                for phrase in key_phrases:
                    if phrase in html_content:
                        missing_content = False
                        break
                        
                if missing_content:
                    self.logger.error("HTML appears to be missing key content phrases, possible rendering issue")
                else:
                    self.logger.info(f"HTML content contains expected phrases, rendering looks ok")
                
                # Check for specific content sections
                sections = {
                    "market_overview": "Market Overview",
                    "futures_premium": "Futures Premium",
                    "smart_money_index": "Smart Money Index",
                    "whale_activity": "Whale Activity"
                }
                
                for section_key, section_title in sections.items():
                    if section_key in market_data and section_title in html_content:
                        self.logger.debug(f"Section '{section_key}' appears to be rendered correctly")
                    elif section_key in market_data:
                        self.logger.warning(f"Section '{section_key}' exists in data but doesn't appear in HTML")
                    else:
                        self.logger.debug(f"Section '{section_key}' not in market data")
                
                # For debugging, write out the HTML to a debug file
                try:
                    debug_dir = os.path.join(os.getcwd(), 'logs', 'debug')
                    os.makedirs(debug_dir, exist_ok=True)
                    debug_html_path = os.path.join(debug_dir, f"debug_html_{int(time.time())}.html")
                    with open(debug_html_path, "w") as f:
                        f.write(html_content)
                    self.logger.info(f"Wrote debug HTML to {debug_html_path}")
                except Exception as debug_error:
                    self.logger.error(f"Failed to write debug HTML: {str(debug_error)}")

                # Add watermark to the rendered HTML
                watermark_text = market_data.get("watermark_text", "VIRTUOSO CRYPTO")
                html_content = self._add_watermark_to_template(
                    html_content, watermark_text
                )

                self.logger.debug(
                    f"Template rendered successfully, content length: {len(html_content)}"
                )
            except Exception as render_error:
                self.logger.error(f"Error rendering template: {str(render_error)}")
                self.logger.debug(traceback.format_exc())

                # Try to diagnose common issues
                if "market_data" in market_data:
                    self.logger.error(
                        "Found nested 'market_data' key - this is likely a duplicate nesting error"
                    )

                self.logger.info(
                    "Falling back to basic report generation due to render error"
                )
                return await self.generate_market_report(market_data, output_path)

            # Write the HTML file
            try:
                self.logger.debug(f"Writing HTML to {html_path}")
                with open(html_path, "w") as f:
                    f.write(html_content)
                self.logger.info(f"Market report HTML generated: {html_path}")
            except Exception as write_error:
                self.logger.error(f"Error writing HTML file: {str(write_error)}")
                self.logger.debug(traceback.format_exc())

                # Try to write to a default location
                try:
                    default_path = os.path.join(html_dir, f"market_report_emergency_{int(time.time())}.html")
                    self.logger.warning(
                        f"Attempting to write to default location: {default_path}"
                    )
                    with open(default_path, "w") as f:
                        f.write(html_content)
                    self.logger.info(
                        f"Successfully wrote HTML to emergency location: {default_path}"
                    )
                    html_path = default_path
                except Exception as emergency_write_error:
                    self.logger.error(
                        f"Emergency write failed: {str(emergency_write_error)}"
                    )
                    # Fall back to basic report
                    self.logger.info(
                        "Falling back to basic report generation due to write error"
                    )
                    return await self.generate_market_report(market_data, output_path)

            # Generate PDF from HTML if requested
            if generate_pdf:
                pdf_path = os.path.join(pdf_dir, os.path.basename(html_path).replace(".html", ".pdf"))
                try:
                    pdf_success = await self.generate_pdf(html_path, pdf_path)
                    if pdf_success:
                        self.logger.info(
                            f"Successfully generated PDF from HTML: {pdf_path}"
                        )
                    else:
                        self.logger.warning(
                            f"Failed to generate PDF, but HTML was generated successfully: {html_path}"
                        )
                    return pdf_success
                except Exception as pdf_error:
                    self.logger.error(
                        f"Error generating PDF from HTML: {str(pdf_error)}"
                    )
                    self.logger.debug(traceback.format_exc())
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error generating market HTML report: {str(e)}")
            self.logger.debug(traceback.format_exc())

            # Diagnostic info
            if market_data is None:
                self.logger.critical(
                    "market_data is None - this is the root cause of the failure"
                )

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
                self.logger.error(
                    f"Error checking template permissions: {str(perm_error)}"
                )

            # Fall back to basic report generation
            self.logger.info("Falling back to basic report generation due to error")
            try:
                return await self.generate_market_report(market_data, output_path)
            except Exception as fallback_error:
                self.logger.error(
                    f"Fallback report generation failed: {str(fallback_error)}"
                )
                return False

    def _create_confluence_image(
        self,
        confluence_text: str,
        output_dir: str,
        symbol: str = "UNKNOWN",
        timestamp: Optional[Union[str, datetime, int]] = None,
        signal_type: str = "NEUTRAL",
    ) -> Optional[str]:
        """
        Create an image of the confluence analysis text output with professional styling.
        
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
                        timestamp_dt = datetime.fromisoformat(
                            timestamp.replace("Z", "+00:00")
                        )
                    elif isinstance(timestamp, datetime):
                        timestamp_dt = timestamp
                    elif isinstance(timestamp, (int, float)):
                        timestamp_dt = datetime.fromtimestamp(
                            timestamp / 1000 if timestamp > 1e12 else timestamp
                        )
                    else:
                        timestamp_dt = datetime.now()

                    timestamp_str = timestamp_dt.strftime("%Y%m%d_%H%M%S")
                except Exception as e:
                    self._log(
                        f"Error formatting timestamp for filename: {str(e)}",
                        logging.WARNING,
                    )
                    timestamp_str = str(int(time.time()))
            else:
                timestamp_str = str(int(time.time()))

            # Create filename with signal information
            signal_type_short = (
                "BUY"
                if signal_type.upper() == "BULLISH"
                else "SELL"
                if signal_type.upper() == "BEARISH"
                else "NEUT"
            )
            filename = (
                f"{symbol.lower()}_{timestamp_str}_{signal_type_short}_confluence.png"
            )

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

            # Create figure and axis with professional styling
            fig, ax = plt.subplots(figsize=(width, height))

            # Remove axes and frame
            ax.axis("off")

            # Set professional dark background
            fig.patch.set_facecolor("#121212")
            ax.set_facecolor("#121212")

            # Define padding for the text area
            padding = 0.02

            # Create a styled background for the text
            rect = plt.Rectangle(
                (padding, padding),
                1 - 2 * padding,
                1 - 2 * padding,
                transform=ax.transAxes,
                facecolor="#1E1E1E",
                edgecolor="#444444",
                linewidth=2,
                alpha=0.9,
            )
            ax.add_patch(rect)

            # Add a title for better context
            title_color = (
                "#4CAF50"
                if signal_type.upper() == "BULLISH"
                else "#F44336"
                if signal_type.upper() == "BEARISH"
                else "#FFC107"
            )
            ax.text(
                0.5,
                0.98,
                f"{symbol} Confluence Analysis",
                transform=ax.transAxes,
                fontsize=14,
                weight="bold",
                color=title_color,
                horizontalalignment="center",
                verticalalignment="top",
            )

            # Add timestamp for reference
            ax.text(
                0.02,
                0.96,
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                transform=ax.transAxes,
                fontsize=8,
                color="#888888",
                verticalalignment="top",
            )

            # Add the text with improved monospace font and styling
            ax.text(
                0.03,
                0.92,
                confluence_text,
                transform=ax.transAxes,
                fontsize=10,
                fontfamily="monospace",
                color="#E0E0E0",
                verticalalignment="top",
                horizontalalignment="left",
                linespacing=1.3,
            )

            # Add a diagonal watermark across the chart
            timestamp_str = datetime.now().strftime("%Y-%m-%d")
            fig.text(
                0.5,
                0.5,
                f"VIRTUOSO CRYPTO • {timestamp_str}",
                fontsize=20,
                color="#333333",
                ha="center",
                va="center",
                alpha=0.04,
                rotation=30,
                transform=fig.transFigure,
            )

            # Tight layout and save
            plt.tight_layout()

            # Save the figure with high quality
            image_path = os.path.join(output_dir, filename)
            plt.savefig(image_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

            self._log(f"Confluence analysis image saved to {image_path}")
            return image_path

        except Exception as e:
            self._log(
                f"Error creating confluence analysis image: {str(e)}", logging.ERROR
            )
            self._log(traceback.format_exc(), logging.ERROR)
            return None

    async def generate_pdf(self, html_path: str, pdf_path: str) -> bool:
        """Generate a PDF file from an HTML file.
        
        Args:
            html_path: Path to the HTML file
            pdf_path: Path to save the PDF file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Generating PDF from HTML: {html_path}")

            if not os.path.exists(html_path):
                self.logger.error(f"HTML file does not exist: {html_path}")
                return False

            # Create directory if it doesn't exist
            output_dir = os.path.dirname(pdf_path)
            if output_dir and not os.path.exists(output_dir):
                self.logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)

            # Set options for wkhtmltopdf
            options = {
                "page-size": "A4",
                "margin-top": "1cm",
                "margin-right": "1cm",
                "margin-bottom": "1cm",
                "margin-left": "1cm",
                "encoding": "UTF-8",
                "enable-local-file-access": None,
                "quiet": None,
            }

            # Generate PDF using pdfkit
            try:
                import pdfkit

                self.logger.debug("Using pdfkit for PDF generation")
                pdfkit.from_file(html_path, pdf_path, options=options)

                if os.path.exists(pdf_path):
                    self.logger.info(f"PDF generated successfully: {pdf_path}")
                    return True
                else:
                    self.logger.error(f"PDF file was not created: {pdf_path}")
                    return False

            except ImportError:
                self.logger.warning("pdfkit not available, trying alternative method")

                # Try using weasyprint as an alternative
                try:
                    from weasyprint import HTML

                    self.logger.debug("Using weasyprint for PDF generation")
                    HTML(filename=html_path).write_pdf(pdf_path)

                    if os.path.exists(pdf_path):
                        self.logger.info(
                            f"PDF generated successfully using weasyprint: {pdf_path}"
                        )
                        return True
                    else:
                        self.logger.error(
                            f"PDF file was not created by weasyprint: {pdf_path}"
                        )
                        return False

                except ImportError:
                    self.logger.error(
                        "Neither pdfkit nor weasyprint is available for PDF generation"
                    )
                    return False

        except Exception as e:
            self.logger.error(f"Error generating PDF: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False

    def _format_with_commas(self, value: Union[int, float]) -> str:
        """
        Format a number with commas for thousands.
        
        Args:
            value: Number to format
            
        Returns:
            Formatted number string with commas
        """
        if value is None:
            return "N/A"

        try:
            if isinstance(value, int):
                return f"{value:,d}"
            elif isinstance(value, float):
                return f"{value:,.0f}"
            else:
                return str(value)
        except Exception as e:
            self.logger.warning(f"Error formatting value with commas: {str(e)}")
            return str(value)

    def _generate_html_content(
        self,
        signal_data: Dict[str, Any],
        ohlcv_data: Optional[pd.DataFrame] = None
    ) -> str:
        """
        Generate HTML content for a trading signal report.
        
        Args:
            signal_data: Trading signal data
            ohlcv_data: OHLCV price data for charts
            
        Returns:
            HTML content string
        """
        try:
            # Get template path
            template_path = None
            if hasattr(self, 'template_dir') and self.template_dir:
                template_path = os.path.join(self.template_dir, 'signal_report.html')
                
            if not template_path or not os.path.exists(template_path):
                self._log(f"Template file not found: {template_path}", level=logging.ERROR)
                return self._generate_fallback_html(signal_data, ohlcv_data)
                
            # Read the template
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
                
            # Extract signal details
            symbol = signal_data.get('symbol', 'UNKNOWN')
            # CHANGED: Use confluence_score as primary source
            confluence_score = signal_data.get('confluence_score', signal_data.get('score', 50))
            signal_type = signal_data.get('signal', 'NEUTRAL').upper()
            reliability = signal_data.get('reliability', 1.0)
            price = signal_data.get('price', 0)
            
            # Format timestamp
            timestamp = signal_data.get('timestamp', int(time.time() * 1000))
            dt = datetime.fromtimestamp(timestamp / 1000)
            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Replace placeholders in template
            html_content = template_content
            html_content = html_content.replace('{{SYMBOL}}', symbol)
            html_content = html_content.replace('{{SCORE}}', f"{confluence_score:.2f}")  # CHANGED: Use confluence_score
            html_content = html_content.replace('{{SIGNAL_TYPE}}', signal_type)
            html_content = html_content.replace('{{RELIABILITY}}', f"{reliability * 100:.2f}")  # Convert from decimal to percentage
            html_content = html_content.replace('{{PRICE}}', f"{price:.4f}")
            html_content = html_content.replace('{{TIMESTAMP}}', timestamp_str)
            
            # Map signal types to proper CSS colors to avoid WeasyPrint warnings
            signal_color = '#4CAF50'  # Default green color
            if signal_type == 'SELL':
                signal_color = '#F44336'  # Red for sell
            elif signal_type == 'NEUTRAL':
                signal_color = '#2196F3'  # Blue for neutral
                
            html_content = html_content.replace('{{SIGNAL_COLOR}}', signal_color)
            
            # Calculate score width percentage for gauge
            score_width_pct = f"{min(max(confluence_score, 0), 100)}%"  # CHANGED: Use confluence_score
            html_content = html_content.replace('{{SCORE_WIDTH_PCT}}', score_width_pct)
            
            # Add watermark
            html_content = self._add_watermark_to_template(html_content)
            
            return html_content
            
        except Exception as e:
            self._log(f"Error generating HTML content: {str(e)}", level=logging.ERROR)
            self._log(traceback.format_exc(), level=logging.DEBUG)
            return self._generate_fallback_html(signal_data, ohlcv_data)
            
    def _generate_fallback_html(
        self,
        signal_data: Dict[str, Any],
        ohlcv_data: Optional[pd.DataFrame] = None
    ) -> str:
        """
        Generate a simple fallback HTML content when the main template fails.
        
        Args:
            signal_data: Trading signal data
            ohlcv_data: OHLCV price data for charts
            
        Returns:
            Basic HTML content string
        """
        try:
            # Extract signal details
            symbol = signal_data.get('symbol', 'UNKNOWN')
            # CHANGED: Use confluence_score as primary source
            confluence_score = signal_data.get('confluence_score', signal_data.get('score', 50))
            signal_type = signal_data.get('signal', 'NEUTRAL').upper()
            reliability = signal_data.get('reliability', 1.0)
            price = signal_data.get('price', 0)
            
            # Format timestamp
            timestamp = signal_data.get('timestamp', int(time.time() * 1000))
            dt = datetime.fromtimestamp(timestamp / 1000)
            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Generate simple HTML
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{symbol} Trading Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: #f0f0f0; padding: 10px; margin-bottom: 20px; }}
                    .content {{ padding: 10px; }}
                    .footer {{ font-size: 0.8em; text-align: center; margin-top: 30px; color: #888; }}
                    .bullish {{ color: green; }}
                    .bearish {{ color: red; }}
                    .neutral {{ color: blue; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{symbol} Trading Report</h1>
                    <p>Generated on {timestamp_str}</p>
                </div>
                <div class="content">
                    <h2>Signal Summary</h2>
                    <p><strong>Symbol:</strong> {symbol}</p>
                    <p><strong>Signal Type:</strong> <span class="{signal_type.lower()}">{signal_type}</span></p>
                    <p><strong>Score:</strong> {confluence_score:.2f}</p>
                    <p><strong>Reliability:</strong> {reliability * 100:.2f}%</p>
                    <p><strong>Price:</strong> {price:.4f}</p>
                    
                    <h2>Components</h2>
                    <ul>
            """
            
            # Add components if available
            components = signal_data.get('components', {})
            for name, value in components.items():
                if isinstance(value, (int, float)):
                    html += f"<li><strong>{name.title()}:</strong> {value:.2f}</li>\n"
                else:
                    html += f"<li><strong>{name.title()}:</strong> {value}</li>\n"
            
            html += """
                    </ul>
                    
                    <h2>Market Interpretations</h2>
                    <ul>
            """
            
            # Add market interpretations if available
            market_interpretations = signal_data.get('market_interpretations', [])
            if market_interpretations:
                for interp in market_interpretations:
                    if isinstance(interp, dict):
                        component = interp.get('display_name', interp.get('component', 'Unknown'))
                        interpretation = interp.get('interpretation', 'No interpretation')
                        if isinstance(interpretation, dict):
                            # Handle nested interpretation
                            for key, value in interpretation.items():
                                html += f"<li><strong>{component} - {key}:</strong> {value}</li>\n"
                        else:
                            html += f"<li><strong>{component}:</strong> {interpretation}</li>\n"
                    else:
                        html += f"<li>{interp}</li>\n"
            else:
                html += "<li>No interpretations available</li>\n"
            
            html += """
                    </ul>
                    
                    <h2>Actionable Insights</h2>
                    <ul>
            """
            
            # Add actionable insights if available
            actionable_insights = signal_data.get('actionable_insights', [])
            if actionable_insights:
                for insight in actionable_insights:
                    html += f"<li>{insight}</li>\n"
            else:
                html += "<li>No actionable insights available</li>\n"
            
            html += """
                    </ul>
                </div>
                <div class="footer">
                    <p>Generated by Virtuoso Trading System</p>
                </div>
            </body>
            </html>
            """
            
            return html
            
        except Exception as e:
            self._log(f"Error generating fallback HTML: {str(e)}", level=logging.ERROR)
            
            # Return absolute minimum HTML
            return f"""
            <!DOCTYPE html>
            <html>
            <head><title>Trading Report</title></head>
            <body>
                <h1>Trading Report</h1>
                <p>Symbol: {signal_data.get('symbol', 'UNKNOWN')}</p>
                <p>Score: {signal_data.get('confluence_score', signal_data.get('score', 50))}</p>
                <p>Signal: {signal_data.get('signal', 'NEUTRAL')}</p>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Error generating full report: {str(e)}</p>
            </body>
            </html>
            """

    def _create_simulated_chart(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: Optional[float] = None,
        targets: Optional[List[Dict]] = None,
        output_dir: str = None,
    ) -> Optional[str]:
        """
        Generate a simulated candlestick chart with buy/sell zones when no real OHLCV data is available.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            targets: List of target prices with format [{'price': float, 'name': str}]
            output_dir: Directory to save the chart
            
        Returns:
            Path to the saved chart file or None if chart creation failed
        """
        self._log(
            f"Creating simulated chart for {symbol} with synthetic data",
            logging.WARNING,
        )

        try:
            # Use temporary directory if none specified
            if output_dir is None:
                output_dir = tempfile.mkdtemp()
                self._log(f"Using temporary directory: {output_dir}")

            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)

            # Determine range of prices to display
            prices = [entry_price]
            if stop_loss is not None:
                prices.append(stop_loss)
            if targets:
                for target in targets:
                    if isinstance(target, dict) and "price" in target:
                        prices.append(target["price"])

            # Validate prices list
            if not prices or not all(isinstance(p, (int, float)) for p in prices):
                self._log("Invalid price values for chart creation", logging.ERROR)
                return None

            min_price = min(prices) * 0.95
            max_price = max(prices) * 1.05

            # Generate simulated price data with random walk - use fewer points to avoid rendering issues
            np.random.seed(42)  # For reproducibility
            num_points = 60  # Reduced from 100 to 60 to minimize rendering issues

            # Start with entry price and generate price fluctuations
            simulated_prices = [entry_price]
            for _ in range(num_points - 1):
                # Random price change with mean reverting tendency
                change = np.random.normal(
                    0, entry_price * 0.005
                )  # Standard deviation of 0.5%
                # Mean reversion to entry price
                mean_reversion = (entry_price - simulated_prices[-1]) * 0.1
                new_price = simulated_prices[-1] + change + mean_reversion
                simulated_prices.append(new_price)

            # Ensure the price range includes all our key levels
            simulated_prices = np.clip(simulated_prices, min_price, max_price)

            # Create a DataFrame for mplfinance
            dates = pd.date_range(end=pd.Timestamp.now(), periods=num_points)

            # Generate OHLC data from simulated prices
            df = pd.DataFrame()
            df["close"] = simulated_prices

            # Calculate open, high, low from close
            volatility = entry_price * 0.005  # 0.5% volatility
            df["open"] = df["close"].shift(1)
            # Fix the chained assignment warning by using .loc instead of direct assignment
            df.loc[0, "open"] = df["close"].iloc[0] * (1 - np.random.normal(0, 0.002))

            df["high"] = df[["open", "close"]].max(axis=1) + np.random.normal(
                0, volatility, num_points
            )
            df["low"] = df[["open", "close"]].min(axis=1) - np.random.normal(
                0, volatility, num_points
            )

            # Make sure highs and lows are sensible
            df["high"] = np.maximum(df["high"], np.maximum(df["open"], df["close"]))
            df["low"] = np.minimum(df["low"], np.minimum(df["open"], df["close"]))

            # Generate simulated volume data
            df["volume"] = np.random.gamma(shape=2.0, scale=1000, size=num_points)

            # Set datetime index
            df.index = dates

            # Ensure price range includes our key levels
            y_min = min(min_price, df["low"].min())
            y_max = max(max_price, df["high"].max())

            # If we have targets, ensure they're visible in the chart
            if targets:
                for target in targets:
                    if isinstance(target, dict) and "price" in target:
                        target_price = target["price"]
                        if target_price > y_max:
                            y_max = target_price * 1.05
                        if target_price < y_min:
                            y_min = target_price * 0.95

            # Prepare plot configuration with enhanced style
            kwargs = {
                "type": "candle",
                "style": VIRTUOSO_ENHANCED_STYLE,  # Use enhanced style
                "figsize": (10, 6),
                "title": f"{symbol} Price Chart (Simulated)",
                "panel_ratios": (4, 1),
                "volume": True,
                "volume_panel": 1,
                "show_nontrading": False,
                "returnfig": True,
                "datetime_format": "%m-%d %H:%M",
                "xrotation": 0,
                "tight_layout": False,
                "ylabel": "Price",
                "ylabel_lower": "Volume",
                "figratio": (10, 7),
                "scale_padding": {
                    "left": 0.05,
                    "right": 0.3,
                    "top": 0.2,
                    "bottom": 0.2,
                },
                "warn_too_much_data": 1000,  # Suppress warning up to 1000 candles
            }

            # Initialize VWAP availability flag
            has_vwap = False

            # Prepare additional plots for entry, stop loss, and targets
            plots = []

            # Entry price line (blue)
            if entry_price is not None:
                plots.append(
                    mpf.make_addplot(
                        [entry_price] * len(df),
                        color="#3b82f6",
                        width=1.5,
                        panel=0,
                        secondary_y=False,
                        linestyle="-",
                    )
                )

            # Stop loss line
            if stop_loss is not None:
                plots.append(
                    mpf.make_addplot(
                        [stop_loss] * len(df),
                        color="#ef4444",
                        width=1.5,
                        panel=0,
                        secondary_y=False,
                        linestyle="--",
                    )
                )

            # Target level lines with different colors
            target_colors = [
                "#10b981",
                "#8b5cf6",
                "#f59e0b",
                "#ec4899",
            ]  # From multi-series palette
            
            if targets:
                for i, target in enumerate(targets):
                    if isinstance(target, dict) and "price" in target:
                        target_price = target["price"]
                        color = target_colors[i % len(target_colors)]
                        plots.append(
                            mpf.make_addplot(
                                [target_price] * len(df),
                                color=color,
                                width=1.5,
                                panel=0,
                                secondary_y=False,
                                linestyle="-.",
                                alpha=0.8,
                            )
                        )

            # Add simulated VWAP values
            try:
                # Generate synthetic VWAP data
                df['daily_vwap'] = df['close'].rolling(window=min(30, len(df))).mean()
                df['weekly_vwap'] = df['close'].rolling(window=min(60, len(df))).mean()
                
                # Add VWAP lines
                plots.append(
                    mpf.make_addplot(
                        df['daily_vwap'],
                        color='#3b82f6',  # Blue
                        width=1.2,
                        panel=0,
                        secondary_y=False,
                        linestyle='-',
                    )
                )
                
                plots.append(
                    mpf.make_addplot(
                        df['weekly_vwap'],
                        color='#8b5cf6',  # Purple
                        width=1.2,
                        panel=0,
                        secondary_y=False,
                        linestyle='-',
                    )
                )
                
                has_vwap = True
            except Exception as e:
                self._log(f"Error creating simulated VWAP: {str(e)}", level=logging.ERROR)
                has_vwap = False

            # Create the plot
            plot_result = mpf.plot(df, **kwargs, addplot=plots if plots else None)
            
            # Safely unpack plot result with robust error handling
            fig, axes = self._safe_plot_result_unpack(plot_result)
            
            # Get the main price axis (safely)
            ax1 = axes[0] if axes and len(axes) > 0 else None
            
            if ax1:
                # Set y-axis limits to ensure all targets are visible
                ax1.set_ylim(y_min, y_max)
                
                # Use scientific notation for large numbers
                if y_max > 10000:
                    ax1.ticklabel_format(style="plain", axis="y")
                
                # Limit ticks to avoid overflow warnings
                self._configure_axis_ticks(ax1, max_ticks=20)
                
                # Custom date formatting for x-axis - REPLACED problematic MinuteLocator
                # Use AutoDateLocator instead of MinuteLocator to prevent excessive ticks
                date_locator = AutoDateLocator(maxticks=20)
                ax1.xaxis.set_major_locator(date_locator)
                
                # Format to show more compact time format
                time_formatter = DateFormatter('%m-%d %H:%M')
                ax1.xaxis.set_major_formatter(time_formatter)
                
                # Rotate labels for better readability
                plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

                # Add custom legend for VWAP if available
                if has_vwap:
                    legend_elements = [
                        Line2D([0], [0], color='#3b82f6', lw=1.2, label='Daily VWAP (Simulated)'),
                        Line2D([0], [0], color='#8b5cf6', lw=1.2, label='Weekly VWAP (Simulated)')
                    ]
                    ax1.legend(handles=legend_elements, loc='upper left', fontsize=9, framealpha=0.7, facecolor='#0c1a2b')

                # Add labels with improved styling
                if entry_price is not None:
                    # Calculate normalized position for entry price
                    entry_pos = (entry_price - y_min) / (y_max - y_min)
                    
                    # Get position bounds safely - handling different return types
                    position = ax1.get_position()
                    if hasattr(position, 'bounds'):
                        # In some versions, bounds is a tuple of 4 values
                        try:
                            bounds = position.bounds
                            if isinstance(bounds, tuple) and len(bounds) == 4:
                                ax1_x_pos, ax1_y_pos, ax1_width, ax1_height = bounds
                            else:
                                self._log(f"Unexpected bounds format: {bounds}", logging.WARNING)
                                ax1_x_pos = ax1_y_pos = 0
                        except Exception as e:
                            self._log(f"Error unpacking figure bounds: {str(e)}", logging.WARNING)
                            ax1_x_pos = ax1_y_pos = 0
                    else:
                        # Fall back to direct attribute access
                        ax1_x_pos = getattr(position, 'x0', 0)
                        ax1_y_pos = getattr(position, 'y0', 0)
                        
                    ax1.annotate(
                        f"Entry: ${self._format_number(entry_price)}",
                        xy=(1.01, entry_pos),
                        xycoords=("axes fraction", "axes fraction"),
                        xytext=(1.05, entry_pos),
                        textcoords="axes fraction",
                        fontsize=9,
                        color="#3b82f6",
                        fontweight="bold",
                        bbox=dict(
                            facecolor="#0c1a2b",
                            edgecolor="#3b82f6",
                            boxstyle="round,pad=0.3",
                            alpha=0.9,
                        ),
                    )

                # Stop loss label
                if stop_loss is not None:
                    stop_pos = (stop_loss - y_min) / (y_max - y_min)
                    ax1.annotate(
                        f"Stop: ${self._format_number(stop_loss)}",
                        xy=(1.01, stop_pos),
                        xycoords=("axes fraction", "axes fraction"),
                        xytext=(1.05, stop_pos),
                        textcoords="axes fraction",
                        fontsize=9,
                        color="#ef4444",
                        fontweight="bold",
                        bbox=dict(
                            facecolor="#0c1a2b",
                            edgecolor="#ef4444",
                            boxstyle="round,pad=0.3",
                            alpha=0.9,
                        ),
                    )

                    # Shade area between entry and stop loss if both exist
                    if entry_price is not None:
                        min_idx, max_idx = 0, len(df) - 1
                        if entry_price > stop_loss:  # Long position
                            ax1.fill_between(
                                [min_idx, max_idx],
                                entry_price,
                                stop_loss,
                                color="#ef4444",
                                alpha=0.1,
                            )
                        else:  # Short position
                            ax1.fill_between(
                                [min_idx, max_idx],
                                entry_price,
                                stop_loss,
                                color="#22c55e",
                                alpha=0.1,
                            )

                # Target labels
                if targets:
                    for i, target in enumerate(targets):
                        if isinstance(target, dict) and "price" in target:
                            target_price = target["price"]
                            target_name = target.get("name", f"Target {i+1}")
                            color = target_colors[i % len(target_colors)]

                            # Calculate profit percentage
                            profit_pct = ""
                            if entry_price and entry_price > 0:
                                pct = ((target_price / entry_price) - 1) * 100
                                profit_pct = f" ({pct:+.1f}%)"

                            # Normalize position for target
                            target_pos = (target_price - y_min) / (y_max - y_min)

                            # Add annotation for target
                            ax1.annotate(
                                f"{target_name}: ${self._format_number(target_price)}{profit_pct}",
                                xy=(1.01, target_pos),
                                xycoords=("axes fraction", "axes fraction"),
                                xytext=(1.05, target_pos),
                                textcoords="axes fraction",
                                fontsize=9,
                                color=color,
                                fontweight="bold",
                                bbox=dict(
                                    facecolor="#0c1a2b",
                                    edgecolor=color,
                                    boxstyle="round,pad=0.3",
                                    alpha=0.9,
                                ),
                            )

                            # Shade target zones
                            if entry_price is not None:
                                min_idx, max_idx = 0, len(df) - 1
                                if entry_price < target_price:  # Long position target
                                    ax1.fill_between(
                                        [min_idx, max_idx],
                                        entry_price,
                                        target_price,
                                        color=color,
                                        alpha=0.05,
                                    )
                                else:  # Short position target
                                    ax1.fill_between(
                                        [min_idx, max_idx],
                                        entry_price,
                                        target_price,
                                        color=color,
                                        alpha=0.05,
                                    )

                # Add watermark
                fig.text(
                    0.5,
                    0.5,
                    "SIMULATED",
                    fontsize=40,
                    color="#e5e7eb",
                    ha="center",
                    va="center",
                    alpha=0.1,
                    rotation=30,
                    transform=fig.transFigure,
                )
                
                # Adjust layout with specific settings instead of tight_layout
                plt.subplots_adjust(right=0.85, left=0.1, top=0.9, bottom=0.15)

                # Create output filename
                timestamp = int(time.time())
                output_file = os.path.join(
                    output_dir, f"{symbol.replace('/', '_')}_simulated_{timestamp}.png"
                )

                # Save the figure
                plt.savefig(output_file, dpi=150, bbox_inches="tight")
                plt.close(fig)

                self._log(f"Saved simulated chart: {output_file}")
                return output_file

        except Exception as e:
            self._log(f"Error creating simulated chart: {str(e)}", logging.ERROR)
            self._log(traceback.format_exc(), logging.DEBUG)
            return None

    def _clear_downsample_cache(self):
        """
        Clear the downsampling cache to free memory after report generation.
        """
        cache_size = len(self._downsample_cache)
        if cache_size > 0:
            self._log(f"Clearing downsample cache with {cache_size} entries (hits: {self._cache_hits}, misses: {self._cache_misses})", logging.INFO)
            self._downsample_cache.clear()
        else:
            self._log(f"Downsample cache already empty (hits: {self._cache_hits}, misses: {self._cache_misses})", logging.DEBUG)

    def _monitor_cache_size(self, max_entries=50):
        """
        Monitor the cache size and prune it if it grows too large.
        
        Args:
            max_entries: Maximum number of entries to keep in the cache
        """
        cache_size = len(self._downsample_cache)
        
        # If cache is under the limit, no action needed
        if cache_size <= max_entries:
            return
            
        # Log that we're pruning the cache
        self._log(f"Cache size ({cache_size}) exceeds limit ({max_entries}), pruning oldest entries", logging.WARNING)
        
        # Calculate how many entries to remove
        entries_to_remove = cache_size - max_entries
        
        # Get a list of cache keys
        cache_keys = list(self._downsample_cache.keys())
        
        # Remove the oldest entries (first entries in the dict)
        for key in cache_keys[:entries_to_remove]:
            del self._downsample_cache[key]
            
        # Log the new cache size
        self._log(f"Cache pruned, new size: {len(self._downsample_cache)}", logging.INFO)

    def _safe_plot_result_unpack(self, plot_result):
        """
        Safely unpack matplotlib plot results with fallback for different return types.
        
        Args:
            plot_result: Result from mpf.plot() which can be either a tuple or a figure
            
        Returns:
            Tuple of (fig, axes)
        """
        try:
            # First, try to unpack as a tuple (fig, axes)
            if isinstance(plot_result, tuple) and len(plot_result) == 2:
                fig, axes = plot_result
                return fig, axes
            # If it's a figure, extract axes from it
            elif hasattr(plot_result, 'get_axes'):
                fig = plot_result
                axes = fig.get_axes()
                return fig, axes
            # If it's some other format with figure attribute
            elif hasattr(plot_result, 'figure'):
                fig = plot_result.figure
                axes = fig.get_axes()
                return fig, axes
            # Last resort fallback
            else:
                self._log("Unknown plot result format, creating new figure", logging.WARNING)
                fig = plt.figure()
                axes = fig.get_axes() if hasattr(fig, 'get_axes') else []
                if not axes:
                    axes = [fig.add_subplot(111)]
                return fig, axes
        except Exception as e:
            self._log(f"Error unpacking plot result: {str(e)}", logging.ERROR)
            self._log(traceback.format_exc(), logging.DEBUG)
            # Create a new figure as fallback
            fig = plt.figure()
            axes = [fig.add_subplot(111)]
            return fig, axes


if __name__ == "__main__":
    # Example usage
    import random

    # Set up logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Create report generator
    generator = ReportGenerator()

    # Create sample data
    signal_data = {
        "symbol": "BTCUSDT",
        "score": 75.5,
        "reliability": 0.85,
        "price": 54321.98,
        "timestamp": datetime.now(),
        "components": {
            "RSI": {
                "score": 82,
                "impact": 3.2,
                "interpretation": "Overbought conditions indicating potential reversal",
            },
            "MACD": {
                "score": 71,
                "impact": 2.5,
                "interpretation": "Bullish crossover suggesting upward momentum",
            },
            "Bollinger Bands": {
                "score": 68,
                "impact": 1.8,
                "interpretation": "Price near upper band with expanding volatility",
            },
            "Volume": {
                "score": 65,
                "impact": 1.5,
                "interpretation": "Above average volume supporting the move",
            },
            "Moving Averages": {
                "score": 80,
                "impact": 3.0,
                "interpretation": "Price above all major MAs in a bullish alignment",
            },
            "Support/Resistance": {
                "score": 60,
                "impact": 1.2,
                "interpretation": "Trading above recent resistance turned support",
            },
            "Ichimoku Cloud": {
                "score": 72,
                "impact": 2.0,
                "interpretation": "Price above the cloud in a bullish trend",
            },
        },
        "insights": [
            "Strong bullish momentum supported by multiple indicators",
            "Recent breakout above key resistance level at $52,000",
            "Increased institutional buying detected in on-chain data",
            "Reduced selling pressure from miners over the past week",
        ],
        "actionable_insights": [
            "Consider entering long positions with tight stop losses",
            "Target the previous high at $58,500 for first take profit",
            "Monitor volume for confirmation of continued uptrend",
            "Watch for potential resistance at $56,000 psychological level",
        ],
        "entry_price": 54300,
        "stop_loss": 51500,
        "targets": [
            {"name": "Target 1", "price": 56800, "size": 50},
            {"name": "Target 2", "price": 58500, "size": 30},
            {"name": "Target 3", "price": 60000, "size": 20},
        ],
    }

    # Create sample OHLCV data
    periods = 50
    base_price = 50000
    dates = pd.date_range(end=datetime.now(), periods=periods)

    ohlcv_data = pd.DataFrame(
        {
            "timestamp": dates,
            "open": [
                base_price * (1 + random.uniform(-0.02, 0.02)) for _ in range(periods)
            ],
            "close": [
                base_price * (1 + random.uniform(-0.02, 0.02)) for _ in range(periods)
            ],
        }
    )

    # Add high and low values
    for i in range(periods):
        if ohlcv_data.loc[i, "open"] > ohlcv_data.loc[i, "close"]:
            ohlcv_data.loc[i, "high"] = ohlcv_data.loc[i, "open"] * (
                1 + random.uniform(0, 0.01)
            )
            ohlcv_data.loc[i, "low"] = ohlcv_data.loc[i, "close"] * (
                1 - random.uniform(0, 0.01)
            )
        else:
            ohlcv_data.loc[i, "high"] = ohlcv_data.loc[i, "close"] * (
                1 + random.uniform(0, 0.01)
            )
            ohlcv_data.loc[i, "low"] = ohlcv_data.loc[i, "open"] * (
                1 - random.uniform(0, 0.01)
            )

    # Generate random volume
    ohlcv_data["volume"] = [random.uniform(100, 1000) for _ in range(periods)]

    # Make a bull run toward the end
    for i in range(periods - 10, periods):
        ohlcv_data.loc[i, "close"] = ohlcv_data.loc[i - 1, "close"] * (
            1 + random.uniform(0.001, 0.02)
        )
        ohlcv_data.loc[i, "open"] = ohlcv_data.loc[i - 1, "close"] * (
            1 + random.uniform(-0.005, 0.01)
        )
        ohlcv_data.loc[i, "high"] = max(
            ohlcv_data.loc[i, "open"], ohlcv_data.loc[i, "close"]
        ) * (1 + random.uniform(0.001, 0.01))
        ohlcv_data.loc[i, "low"] = min(
            ohlcv_data.loc[i, "open"], ohlcv_data.loc[i, "close"]
        ) * (1 - random.uniform(0, 0.005))
        ohlcv_data.loc[i, "volume"] = ohlcv_data.loc[i - 1, "volume"] * (
            1 + random.uniform(0, 0.2)
        )

    # Set the last price to match signal data
    ohlcv_data.loc[periods - 1, "close"] = signal_data["price"]

    # Generate report
    pdf_path, json_path = generator.generate_trading_report(signal_data, ohlcv_data)

    if pdf_path:
        print(f"PDF report generated: {pdf_path}")
    if json_path:
        print(f"JSON data exported: {json_path}")
