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
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import shutil
import uuid
import re
import warnings
from enum import Enum

# Import the CustomJSONEncoder for proper serialization
try:
    from utils.json_encoder import CustomJSONEncoder
except ImportError:
    try:
        from src.utils.json_encoder import CustomJSONEncoder
    except ImportError:
        # Fallback if CustomJSONEncoder is not available
        CustomJSONEncoder = None

# Import error tracking
try:
    from src.monitoring.error_tracker import track_error, ErrorSeverity, ErrorCategory
except ImportError:
    # Fallback if error tracker is not available
    def track_error(*args, **kwargs):
        pass
    class ErrorSeverity:
        HIGH = "high"
        MEDIUM = "medium"
    class ErrorCategory:
        TEMPLATE_RENDERING = "template_rendering"
        STRING_FORMATTING = "string_formatting"

# Import our centralized interpretation system
try:
    from src.core.interpretation.interpretation_manager import InterpretationManager
except ImportError:
    try:
        from core.interpretation.interpretation_manager import InterpretationManager
    except ImportError:
        # Create dummy class if not available
        class InterpretationManager:
            def process_interpretations(self, *args, **kwargs):
                return None
            def get_formatted_interpretation(self, *args, **kwargs):
                return ""

# Import and apply matplotlib silencing before matplotlib imports
try:
    from utils.matplotlib_utils import silence_matplotlib_logs
except ImportError:
    try:
        from src.utils.matplotlib_utils import silence_matplotlib_logs
    except ImportError:
        # Fallback if matplotlib_utils is not available
        def silence_matplotlib_logs():
            pass

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

# Watermark utility for browser-quality branding
try:
    from src.utils.watermark import add_watermark, add_watermark_to_figure
    WATERMARK_AVAILABLE = True
except ImportError:
    WATERMARK_AVAILABLE = False
    add_watermark_to_figure = None
from matplotlib.dates import MinuteLocator, DateFormatter
from matplotlib.dates import AutoDateLocator

# Set matplotlib style for dark mode
plt.style.use("dark_background")


class PDFGenerationError(Exception):
    """Base exception for PDF generation errors."""
    pass


class ChartGenerationError(PDFGenerationError):
    """Exception for chart generation errors."""
    pass


class DataValidationError(PDFGenerationError):
    """Exception for data validation errors."""
    pass


class FileOperationError(PDFGenerationError):
    """Exception for file operation errors."""
    pass


class TemplateError(PDFGenerationError):
    """Exception for template processing errors."""
    pass


class ErrorSeverity(Enum):
    """Error severity levels for better error classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


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

# Create proper mplfinance style object from the dictionary
# mplfinance requires style objects created via make_mpf_style(), not raw dicts
def _create_virtuoso_style():
    """Create a proper mplfinance style object from VIRTUOSO_ENHANCED_STYLE config."""
    # Create market colors using make_marketcolors
    mc = mpf.make_marketcolors(
        up='#f59e0b',      # Amber for bullish
        down='#f97316',    # Orange for bearish
        edge={'up': '#f59e0b', 'down': '#f97316'},
        wick={'up': '#f59e0b', 'down': '#f97316'},
        volume={'up': '#f59e0b', 'down': '#f97316'},
        ohlc={'up': '#f59e0b', 'down': '#f97316'},
        inherit=True,
    )

    # Create the full style object
    style = mpf.make_mpf_style(
        base_mpf_style='nightclouds',  # Dark base style
        marketcolors=mc,
        mavcolors=['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'],
        gridcolor='#1a2a40',
        gridstyle=':',
        y_on_right=False,
        facecolor='#0c1a2b',
        figcolor='#0c1a2b',
        edgecolor='#1a2a40',
        rc={
            'axes.labelsize': 10,
            'axes.titlesize': 12,
            'xtick.labelsize': 8,
            'ytick.labelsize': 8,
            'figure.facecolor': '#0c1a2b',
            'savefig.facecolor': '#0c1a2b',
            'axes.labelcolor': '#e5e7eb',
            'xtick.color': '#e5e7eb',
            'ytick.color': '#e5e7eb',
        }
    )
    return style

# Create the style object once at module load time
VIRTUOSO_MPF_STYLE = _create_virtuoso_style()


def _create_virtuoso_light_style():
    """Create a light mode mplfinance style object with warm amber background.

    Uses Virtuoso brand colors from style.html:
    - Light BG Secondary: #f9fafb (clean, professional)
    - Light Border: #e5e7eb (subtle grid)
    - Light Text Primary: #111827
    - Light Text Secondary: #6b7280
    - Success (bullish): #10b981
    - Error (bearish): #ef4444
    - Neon Amber: #fbbf24 (accent)
    """
    # Warm light background - softer than pure white, matches Virtuoso brand
    warm_bg = '#fef7e0'  # Soft warm cream (between #fff8e0 and #f9fafb)

    # Create market colors using Virtuoso brand palette
    mc = mpf.make_marketcolors(
        up='#10b981',      # Success green (from style.html)
        down='#ef4444',    # Error red (from style.html)
        edge={'up': '#059669', 'down': '#dc2626'},  # Slightly darker edges
        wick={'up': '#10b981', 'down': '#ef4444'},
        volume={'up': '#10b981', 'down': '#ef4444'},
        ohlc={'up': '#10b981', 'down': '#ef4444'},
        inherit=True,
    )

    # Create the full style object with Virtuoso brand colors
    style = mpf.make_mpf_style(
        base_mpf_style='default',  # Light base style
        marketcolors=mc,
        mavcolors=['#3b82f6', '#8b5cf6', '#fbbf24', '#06B6D4', '#ec4899'],  # Blue, purple, amber, cyan, pink
        gridcolor='#e5e7eb',  # Light border color - subtle grid (from style.html)
        gridstyle='-',        # Solid but subtle
        y_on_right=False,
        facecolor=warm_bg,
        figcolor=warm_bg,
        edgecolor='#d1d5db',  # Slightly darker edge
        rc={
            'axes.labelsize': 11,
            'axes.titlesize': 14,
            'xtick.labelsize': 9,
            'ytick.labelsize': 9,
            'figure.facecolor': warm_bg,
            'savefig.facecolor': warm_bg,
            'axes.labelcolor': '#111827',   # Light text primary (from style.html)
            'xtick.color': '#6b7280',       # Light text secondary
            'ytick.color': '#6b7280',       # Light text secondary
            'axes.edgecolor': '#d1d5db',    # Subtle border
            'grid.alpha': 0.5,              # Softer grid
            'font.family': 'sans-serif',
            'font.size': 10,
        }
    )
    return style

# Create the light style object once at module load time
VIRTUOSO_LIGHT_MPF_STYLE = _create_virtuoso_light_style()


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
        
        # Error tracking and retry configuration
        self._error_counts = {}
        self._max_retries = self.config.get('pdf_generation', {}).get('max_retries', 3)
        self._retry_delay = self.config.get('pdf_generation', {}).get('retry_delay', 1.0)
        self._exponential_backoff = self.config.get('pdf_generation', {}).get('exponential_backoff', True)

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

        # Initialize the centralized interpretation manager
        self.interpretation_manager = InterpretationManager()

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
        Generate a PDF report for a trading signal with enhanced error handling.
        
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
        start_time = time.time()
        
        # Validate input data
        try:
            self._validate_signal_data(signal_data, report_id)
            if ohlcv_data is not None:
                self._validate_ohlcv_data(ohlcv_data, report_id)
            # Validate stop loss consistency between PDF and execution logic
            self._validate_stop_loss_consistency(signal_data, report_id)
        except DataValidationError as e:
            self._log(f"[PDF_GEN:{report_id}] Data validation failed: {str(e)}", level=logging.ERROR)
            return False
        
        # Retry logic with exponential backoff
        for attempt in range(self._max_retries):
            attempt_start = time.time()
            try:
                self._log(f"[PDF_GEN:{report_id}] Starting report generation for {symbol} (attempt {attempt + 1}/{self._max_retries})", level=logging.INFO)
                
                # Use the generate_trading_report method to create the PDF
                self._log(f"[PDF_GEN:{report_id}] Calling generate_trading_report for {symbol}", level=logging.INFO)
                
                # If output_path is provided, ensure parent directories exist
                if output_path:
                    try:
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    except OSError as e:
                        raise FileOperationError(f"Failed to create output directory: {str(e)}")
                    
                pdf_path, json_path, chart_path = self.generate_trading_report(
                    signal_data=signal_data,
                    ohlcv_data=ohlcv_data,
                    output_dir=output_path,
                )
                
                # Debug output the actual paths
                self._log(f"[PDF_GEN:{report_id}] generate_trading_report returned - PDF path: {pdf_path}, JSON path: {json_path}", level=logging.INFO)
                
                if pdf_path:
                    # Validate the generated PDF
                    try:
                        validated_path = self._validate_and_process_pdf(pdf_path, signal_data, report_id)
                        
                        # Calculate processing time
                        attempt_time = time.time() - attempt_start
                        processing_time = time.time() - start_time
                        self._log(
                            f"[PDF_GEN:{report_id}] ✅ PDF generation succeeded on attempt {attempt + 1}/{self._max_retries} "
                            f"(attempt: {attempt_time:.2f}s, total: {processing_time:.2f}s)",
                            level=logging.INFO
                        )

                        # Clear the cache after successful generation
                        self._clear_downsample_cache()
                        return validated_path, json_path
                        
                    except (FileOperationError, DataValidationError) as e:
                        self._log(f"[PDF_GEN:{report_id}] PDF validation failed: {str(e)}", level=logging.ERROR)
                        if attempt < self._max_retries - 1:
                            continue
                        else:
                            return False
                else:
                    self._log(f"[PDF_GEN:{report_id}] ERROR: No PDF path was returned from generate_trading_report", level=logging.ERROR)
                    if attempt < self._max_retries - 1:
                        continue
                    else:
                        return False
                        
            except ChartGenerationError as e:
                attempt_time = time.time() - attempt_start
                self._log(
                    f"[PDF_GEN:{report_id}] Chart generation error (attempt {attempt + 1}/{self._max_retries}, {attempt_time:.2f}s): {str(e)}",
                    level=logging.ERROR
                )
                self._track_error("chart_generation", ErrorSeverity.HIGH)

            except TemplateError as e:
                attempt_time = time.time() - attempt_start
                self._log(
                    f"[PDF_GEN:{report_id}] Template processing error (attempt {attempt + 1}/{self._max_retries}, {attempt_time:.2f}s): {str(e)}",
                    level=logging.ERROR
                )
                self._track_error("template_processing", ErrorSeverity.MEDIUM)

            except FileOperationError as e:
                attempt_time = time.time() - attempt_start
                self._log(
                    f"[PDF_GEN:{report_id}] File operation error (attempt {attempt + 1}/{self._max_retries}, {attempt_time:.2f}s): {str(e)}",
                    level=logging.ERROR
                )
                self._track_error("file_operations", ErrorSeverity.HIGH)

            except Exception as e:
                attempt_time = time.time() - attempt_start
                self._log(
                    f"[PDF_GEN:{report_id}] Unexpected error (attempt {attempt + 1}/{self._max_retries}, {attempt_time:.2f}s): {str(e)}",
                    level=logging.ERROR
                )
                self._log(f"[PDF_GEN:{report_id}] Traceback: {traceback.format_exc()}", level=logging.DEBUG)
                self._track_error("unexpected", ErrorSeverity.CRITICAL)
            
            # Wait before retry (except on last attempt)
            if attempt < self._max_retries - 1:
                delay = self._retry_delay * (2 ** attempt if self._exponential_backoff else 1)
                self._log(f"[PDF_GEN:{report_id}] Retrying in {delay:.1f}s...", level=logging.INFO)
                await asyncio.sleep(delay)
        
        # All retries failed
        total_time = time.time() - start_time
        self._log(
            f"[PDF_GEN:{report_id}] ❌ PDF generation failed after {self._max_retries} attempts in {total_time:.2f}s for {symbol}",
            level=logging.ERROR
        )
        
        # Clear the cache even if we had an error
        self._clear_downsample_cache()
        return False

    def _format_number(self, value: Union[int, float]) -> str:
        """
        Format a number for display with appropriate precision.

        For crypto assets, uses higher precision to distinguish between
        entry, stop loss, and target prices that may be close together.

        Args:
            value: Number to format

        Returns:
            Formatted number string
        """
        if value is None:
            return "N/A"

        if isinstance(value, int):
            return f"{value:,d}"

        # For float values, use higher precision for small values (crypto prices)
        # This ensures stop loss and targets are visually distinct from entry
        if abs(value) < 0.001:
            return f"{value:.6f}"
        elif abs(value) < 0.01:
            return f"{value:.5f}"
        elif abs(value) < 0.1:
            return f"{value:.5f}"  # Increased from .4f to .5f
        elif abs(value) < 1:
            return f"{value:.4f}"  # Increased from .3f to .4f for meme coins like DOGE
        elif abs(value) < 10:
            return f"{value:.3f}"  # Increased from .2f to .3f
        elif abs(value) < 100:
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
            periods: Number of periods to look back:
                     - Daily VWAP: 24 hours (1440 minutes if 1-minute data, 288 if 5-minute data)
                     - Weekly VWAP: 7 days (10080 minutes if 1-minute data, 2016 if 5-minute data)

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

    def _validate_signal_data(self, signal_data: Dict[str, Any], report_id: str) -> None:
        """
        Validate signal data for PDF generation.
        
        Args:
            signal_data: Signal data to validate
            report_id: Report ID for logging
            
        Raises:
            DataValidationError: If validation fails
        """
        if not isinstance(signal_data, dict):
            raise DataValidationError("Signal data must be a dictionary")
        
        required_fields = ['symbol']
        for field in required_fields:
            if field not in signal_data:
                raise DataValidationError(f"Missing required field: {field}")
        
        symbol = signal_data.get('symbol', '')
        if not symbol or not isinstance(symbol, str):
            raise DataValidationError("Symbol must be a non-empty string")
        
        # Validate score if present
        score = signal_data.get('score') or signal_data.get('confluence_score')
        if score is not None:
            try:
                score = float(score)
                if not 0 <= score <= 100:
                    self._log(f"[PDF_GEN:{report_id}] Warning: Score {score} is outside expected range [0-100]", level=logging.WARNING)
            except (ValueError, TypeError):
                raise DataValidationError(f"Invalid score value: {score}")
        
        self._log(f"[PDF_GEN:{report_id}] Signal data validation passed for {symbol}", level=logging.DEBUG)

    def _validate_ohlcv_data(self, ohlcv_data: pd.DataFrame, report_id: str) -> None:
        """
        Validate OHLCV data for chart generation.
        
        Args:
            ohlcv_data: OHLCV DataFrame to validate
            report_id: Report ID for logging
            
        Raises:
            DataValidationError: If validation fails
        """
        if not isinstance(ohlcv_data, pd.DataFrame):
            raise DataValidationError("OHLCV data must be a pandas DataFrame")
        
        if ohlcv_data.empty:
            raise DataValidationError("OHLCV data cannot be empty")
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in ohlcv_data.columns]
        if missing_columns:
            raise DataValidationError(f"Missing required OHLCV columns: {missing_columns}")
        
        # Check for valid numeric data
        for col in required_columns:
            if not pd.api.types.is_numeric_dtype(ohlcv_data[col]):
                raise DataValidationError(f"Column {col} must contain numeric data")
        
        # Check for reasonable data ranges
        if (ohlcv_data[['open', 'high', 'low', 'close']] <= 0).any().any():
            raise DataValidationError("Price data contains non-positive values")
        
        if (ohlcv_data['volume'] < 0).any():
            raise DataValidationError("Volume data contains negative values")
        
        self._log(f"[PDF_GEN:{report_id}] OHLCV data validation passed ({len(ohlcv_data)} rows)", level=logging.DEBUG)

    def _validate_and_process_pdf(self, pdf_path: str, signal_data: Dict[str, Any], report_id: str) -> str:
        """
        Validate and process the generated PDF file.
        
        Args:
            pdf_path: Path to the generated PDF
            signal_data: Original signal data
            report_id: Report ID for logging
            
        Returns:
            Path to the processed PDF file
            
        Raises:
            FileOperationError: If file operations fail
            DataValidationError: If PDF validation fails
        """
        if not os.path.exists(pdf_path):
            raise FileOperationError(f"PDF file does not exist: {pdf_path}")
        
        if os.path.isdir(pdf_path):
            raise FileOperationError(f"PDF path is a directory, not a file: {pdf_path}")
        
        # Check file extension
        if not pdf_path.lower().endswith('.pdf'):
            self._log(f"[PDF_GEN:{report_id}] WARNING: {pdf_path} does not have .pdf extension", level=logging.WARNING)
        
        # Validate PDF file content
        try:
            with open(pdf_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF'):
                    raise DataValidationError(f"Invalid PDF file header: {pdf_path}")
        except IOError as e:
            raise FileOperationError(f"Cannot read PDF file: {str(e)}")
        
        # Get file size
        try:
            file_size = os.path.getsize(pdf_path)
            if file_size == 0:
                raise DataValidationError("PDF file is empty")
            
            # Check for reasonable file size (between 1KB and 50MB)
            if file_size < 1024:
                self._log(f"[PDF_GEN:{report_id}] WARNING: PDF file is very small ({file_size} bytes)", level=logging.WARNING)
            elif file_size > 50 * 1024 * 1024:
                self._log(f"[PDF_GEN:{report_id}] WARNING: PDF file is very large ({file_size / 1024 / 1024:.1f} MB)", level=logging.WARNING)
            
        except OSError as e:
            raise FileOperationError(f"Cannot get PDF file size: {str(e)}")
        
        # Move PDF to exports directory for easier access
        try:
            symbol = signal_data.get('symbol', 'UNKNOWN')
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
            
            # Copy the file instead of moving it
            shutil.copy2(pdf_path, new_pdf_path)
            
            if not os.path.exists(new_pdf_path):
                raise FileOperationError(f"PDF copy failed - {new_pdf_path} does not exist")
            
            copy_size = os.path.getsize(new_pdf_path) / 1024  # Size in KB
            self._log(f"[PDF_GEN:{report_id}] PDF report copied to {new_pdf_path}, size: {copy_size:.2f} KB", level=logging.INFO)
            
            return new_pdf_path
            
        except (OSError, IOError) as e:
            # If we can't copy, still return the original path
            self._log(f"[PDF_GEN:{report_id}] Error copying PDF report: {str(e)}", level=logging.ERROR)
            self._log(f"[PDF_GEN:{report_id}] Returning original PDF path: {pdf_path}", level=logging.INFO)
            return pdf_path

    def _validate_stop_loss_consistency(self, signal_data: Dict[str, Any], report_id: str) -> None:
        """
        Validate that PDF stop loss calculations match execution parameters using the unified StopLossCalculator.

        Args:
            signal_data: Signal data dictionary
            report_id: Report ID for logging

        Raises:
            DataValidationError: If validation fails
        """
        try:
            trade_params = signal_data.get("trade_params", {})
            if not trade_params:
                self._log(f"[PDF_GEN:{report_id}] No trade_params found for validation", logging.WARNING)
                return

            pdf_stop_loss = trade_params.get("stop_loss")
            pdf_entry_price = trade_params.get("entry_price")

            if not pdf_stop_loss or not pdf_entry_price:
                self._log(f"[PDF_GEN:{report_id}] Missing stop_loss or entry_price for validation", logging.WARNING)
                return

            # Calculate PDF stop loss percentage
            if pdf_entry_price > pdf_stop_loss:  # Long position
                pdf_stop_loss_pct = abs(((pdf_stop_loss / pdf_entry_price) - 1) * 100)
            else:  # Short position
                pdf_stop_loss_pct = abs(((pdf_stop_loss / pdf_entry_price) - 1) * 100)

            # Use unified StopLossCalculator for consistency with AlertManager
            try:
                from src.core.risk.stop_loss_calculator import get_stop_loss_calculator, StopLossMethod

                # Get configuration for calculator
                config = self.config if hasattr(self, 'config') else {}

                # Initialize stop loss calculator if not already done
                try:
                    stop_calc = get_stop_loss_calculator()
                except ValueError:
                    # First initialization
                    stop_calc = get_stop_loss_calculator(config)

                # Get expected stop loss percentage using the same logic as AlertManager
                signal_type = signal_data.get("signal_type", "LONG").upper()
                confluence_score = signal_data.get("confluence_score", signal_data.get("score", 50))

                expected_stop_pct = stop_calc.calculate_stop_loss_percentage(
                    signal_type, confluence_score, StopLossMethod.CONFIDENCE_BASED
                ) * 100  # Convert to percentage

                self._log(f"[PDF_GEN:{report_id}] Using unified stop loss calculator: "
                         f"{signal_type} @ score {confluence_score} → {expected_stop_pct:.2f}%", logging.DEBUG)

            except Exception as calc_error:
                # Fallback to simple risk config if calculator fails
                self._log(f"[PDF_GEN:{report_id}] StopLossCalculator failed, using fallback: {calc_error}", logging.WARNING)
                risk_config = config.get('risk', {})
                if signal_type == 'LONG':
                    expected_stop_pct = risk_config.get('long_stop_percentage', 3.5)
                else:
                    expected_stop_pct = risk_config.get('short_stop_percentage', 3.5)

            # Allow larger tolerance for confidence-based calculations (1% instead of 0.1%)
            tolerance = 1.0
            if abs(pdf_stop_loss_pct - expected_stop_pct) > tolerance:
                error_msg = (f"Stop loss mismatch for {signal_type} signal @ confidence {confluence_score}: "
                           f"PDF shows {pdf_stop_loss_pct:.2f}% but unified calculator expects {expected_stop_pct:.2f}%")
                self._log(f"[PDF_GEN:{report_id}] {error_msg}", logging.ERROR)
                self._track_error("stop_loss_mismatch", ErrorSeverity.HIGH)
            else:
                self._log(f"[PDF_GEN:{report_id}] Stop loss validation passed: PDF {pdf_stop_loss_pct:.2f}% vs expected {expected_stop_pct:.2f}%", logging.DEBUG)

        except Exception as e:
            self._log(f"[PDF_GEN:{report_id}] Error during stop loss validation: {str(e)}", logging.ERROR)
            self._track_error("validation_error", ErrorSeverity.MEDIUM)

    def _track_error(self, error_type: str, severity: ErrorSeverity) -> None:
        """
        Track errors for monitoring and debugging.
        
        Args:
            error_type: Type of error
            severity: Error severity level
        """
        if error_type not in self._error_counts:
            self._error_counts[error_type] = {'count': 0, 'last_seen': None, 'severity': severity.value}
        
        self._error_counts[error_type]['count'] += 1
        self._error_counts[error_type]['last_seen'] = datetime.now().isoformat()
        
        # Log error statistics periodically
        total_errors = sum(error_data['count'] for error_data in self._error_counts.values())
        if total_errors % 10 == 0:  # Log every 10 errors
            self._log(f"Error statistics: {self._error_counts}", level=logging.INFO)

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
        chart_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        self._log(f"[CHART:{chart_id}] Creating component chart with {len(components)} components", logging.INFO)

        # Validate output_dir
        if output_dir is None:
            self._log(f"[CHART:{chart_id}] Component chart creation failed: output_dir is None", logging.ERROR)
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

            # Add Virtuoso branding watermark (browser-quality PNG)
            if WATERMARK_AVAILABLE and add_watermark_to_figure is not None:
                try:
                    add_watermark_to_figure(fig, position='bottom-right', zoom=0.4, padding=0.02)
                except Exception as wm_err:
                    self._log(f"Watermark failed, using fallback: {wm_err}", logging.WARNING)
                    fig.text(0.85, 0.02, 'VIRTUOSO',
                            fontsize=12, weight='bold', color='#ff9900',
                            ha='right', va='bottom',
                            transform=fig.transFigure,
                            bbox=dict(boxstyle='round,pad=0.3',
                                     facecolor='#1E1E1E',
                                     edgecolor='#ff9900',
                                     alpha=0.9))
            else:
                fig.text(0.85, 0.02, 'VIRTUOSO',
                        fontsize=12, weight='bold', color='#ff9900',
                        ha='right', va='bottom',
                        transform=fig.transFigure,
                        bbox=dict(boxstyle='round,pad=0.3',
                                 facecolor='#1E1E1E',
                                 edgecolor='#ff9900',
                                 alpha=0.9))

            # Save figure with high quality and padding for branding
            chart_path = os.path.abspath(
                os.path.join(output_dir, "component_chart.png")
            )
            plt.savefig(chart_path, dpi=120, pad_inches=0.2, facecolor=fig.get_facecolor())
            plt.close(fig)

            duration = time.time() - start_time
            self._log(f"[CHART:{chart_id}] Component chart created in {duration:.2f}s: {chart_path}", logging.INFO)
            return chart_path

        except Exception as e:
            duration = time.time() - start_time
            self._log(f"[CHART:{chart_id}] Error creating component chart after {duration:.2f}s: {str(e)}", logging.ERROR)
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
        chart_mode: str = "light",
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
            chart_mode: Chart color mode - "dark" (default) or "light" (warm amber background)

        Returns:
            Path to the saved chart file or None if chart creation failed
        """
        chart_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        self._log(f"[CHART:{chart_id}] Creating candlestick chart for {symbol}", logging.INFO)

        try:
            # Always save charts to reports/charts for easy access
            chart_dir = os.path.join(os.getcwd(), 'reports', 'charts')

            # Use provided output_dir for temp work if needed
            if output_dir is None:
                output_dir = chart_dir  # Default to charts directory
                self._log(f"[CHART:{chart_id}] Using charts directory: {output_dir}", logging.DEBUG)

            # Create directories if they don't exist
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(chart_dir, exist_ok=True)

            # Check if we have actual OHLCV data to work with
            if ohlcv_data is None or ohlcv_data.empty:
                self._log(f"[CHART-FALLBACK:{chart_id}] No OHLCV data for {symbol}, using simulated chart", logging.WARNING)
                self._track_error("simulated_chart_fallback", ErrorSeverity.LOW)
                return self._create_simulated_chart(
                    symbol=symbol,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    targets=targets,
                    output_dir=output_dir,
                    chart_mode=chart_mode,
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
                
            # Calculate VWAPs if volume data is available with timeframe detection
            has_vwap = False
            if 'volume' in df.columns and len(df) > 10:  # Need reasonable amount of data for VWAP
                try:
                    # Detect timeframe from data
                    timeframe_str = "1h"  # Default
                    daily_periods = 24  # Default for hourly data
                    weekly_periods = 168  # Default for hourly data (7 * 24)

                    if len(df) > 1 and hasattr(df, 'index') and isinstance(df.index, pd.DatetimeIndex):
                        # Calculate average time difference between candles
                        time_diffs = df.index.to_series().diff().dropna()
                        if not time_diffs.empty:
                            avg_minutes = time_diffs.mean().total_seconds() / 60

                            # Determine timeframe and periods
                            if avg_minutes < 2:
                                timeframe_str = "1m"
                                daily_periods = 1440  # 24 hours * 60 minutes
                                weekly_periods = 10080  # 7 * 24 * 60
                            elif avg_minutes < 10:
                                timeframe_str = "5m"
                                daily_periods = 288  # 24 hours * 12 (5-min candles per hour)
                                weekly_periods = 2016  # 7 * 24 * 12
                            elif avg_minutes < 20:
                                timeframe_str = "15m"
                                daily_periods = 96  # 24 hours * 4 (15-min candles per hour)
                                weekly_periods = 672  # 7 * 24 * 4
                            elif avg_minutes < 45:
                                timeframe_str = "30m"
                                daily_periods = 48  # 24 hours * 2 (30-min candles per hour)
                                weekly_periods = 336  # 7 * 24 * 2
                            elif avg_minutes < 120:
                                timeframe_str = "1h"
                                daily_periods = 24  # 24 hours
                                weekly_periods = 168  # 7 * 24
                            elif avg_minutes < 360:
                                timeframe_str = "4h"
                                daily_periods = 6  # 24 hours / 4
                                weekly_periods = 42  # 7 * 24 / 4
                            else:
                                timeframe_str = "1d"
                                daily_periods = 1  # 1 day
                                weekly_periods = 7  # 7 days

                            self._log(f"Chart timeframe: {timeframe_str} (avg {avg_minutes:.1f} min between candles)", level=logging.INFO)

                    # Check if we have HTF data in metadata for weekly VWAP
                    htf_data = None
                    if hasattr(ohlcv_data, 'metadata') and ohlcv_data.metadata and 'htf_data' in ohlcv_data.metadata:
                        htf_data = ohlcv_data.metadata['htf_data']
                        self._log(f"Found HTF data in metadata for weekly VWAP calculation", level=logging.DEBUG)

                    # Calculate daily VWAP using appropriate periods for the timeframe
                    self._log(f"Calculating daily VWAP using {min(daily_periods, len(df))} periods for {timeframe_str} data", level=logging.DEBUG)
                    df['daily_vwap'] = self._calculate_vwap(df, periods=min(daily_periods, len(df)))

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
                                    df['weekly_vwap'] = self._calculate_vwap(df, periods=min(weekly_periods, len(df)))
                            else:
                                self._log("HTF dataframe doesn't have DatetimeIndex, can't resample VWAP", level=logging.WARNING)
                                df['weekly_vwap'] = self._calculate_vwap(df, periods=min(weekly_periods, len(df)))
                        else:
                            self._log("HTF data missing required columns, falling back to primary dataframe for weekly VWAP", level=logging.WARNING)
                            df['weekly_vwap'] = self._calculate_vwap(df, periods=min(weekly_periods, len(df)))
                    else:
                        # Fall back to calculating weekly VWAP from primary data if no HTF data available
                        self._log("No HTF data available, calculating weekly VWAP from primary dataframe", level=logging.DEBUG)
                        df['weekly_vwap'] = self._calculate_vwap(df, periods=min(weekly_periods, len(df)))
                    
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
            # Ensure volume data is available and has valid values
            has_volume = 'volume' in df.columns and df['volume'].notna().any() and (df['volume'] > 0).any()
            if 'volume' in df.columns:
                self._log(f"Volume data check: has_volume={has_volume}, vol_sum={df['volume'].sum()}, vol_mean={df['volume'].mean():.2f}", level=logging.DEBUG)
            
            # Select chart style based on chart_mode parameter
            chart_style = VIRTUOSO_LIGHT_MPF_STYLE if chart_mode == "light" else VIRTUOSO_MPF_STYLE
            is_light_mode = chart_mode == "light"
            self._log(f"Using chart mode: {chart_mode}", logging.DEBUG)

            # Define label colors based on chart mode (Virtuoso brand colors from style.html)
            if is_light_mode:
                label_bg_color = '#ffffff'      # White background for labels
                label_border_alpha = 0.95
                title_color = '#111827'         # Light text primary
                watermark_color = '#fbbf24'     # Neon amber
            else:
                label_bg_color = '#0c1a2b'      # Dark background for labels
                label_border_alpha = 0.9
                title_color = '#e5e7eb'         # Dark text primary
                watermark_color = '#ff9900'     # Orange/amber

            # Build kwargs dynamically to avoid validation issues
            kwargs = {
                "type": "candle",
                "style": chart_style,  # Use proper mplfinance style object based on mode
                "figsize": (12, 7),    # Slightly wider for better label spacing
                "title": f"{symbol} Price Chart",
                "show_nontrading": False,
                "returnfig": True,
                "datetime_format": "%m/%d %H:%M",  # Include month for clarity
                "xrotation": 0,
                "tight_layout": False,
                "ylabel": "Price",
                "figratio": (12, 7),
                "scale_padding": {
                    "left": 0.12,      # Increased for Y-axis label visibility
                    "right": 0.22,     # Reduced from 0.3 for better spacing
                    "top": 0.15,       # Reduced for tighter layout
                    "bottom": 0.15,
                },
                "warn_too_much_data": 1000,  # Suppress warning up to 1000 candles
            }

            # Add volume parameter only if we have valid volume data
            if has_volume:
                kwargs["volume"] = True
                # Make volume panel 1/3 the height of price panel (was 4:1, now 3:1 for smaller volume)
                kwargs["panel_ratios"] = (3, 1)
                kwargs["volume_panel"] = 1

            # Prepare additional plots for entry, stop loss, and targets
            plots = []
            
            # Ensure targets are always available - generate defaults if none provided
            if not targets or len(targets) == 0:
                signal_type = "BULLISH"  # Default assumption for chart generation
                if stop_loss and entry_price:
                    if stop_loss > entry_price:
                        signal_type = "BEARISH"
                
                targets = self._generate_default_targets(
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    signal_type=signal_type
                )
                self._log(f"Generated {len(targets)} default targets for chart display", logging.INFO)
            
            # Add VWAP lines if available
            if has_vwap:
                # Add daily VWAP (blue line) - Swapped colors with entry price
                plots.append(
                    mpf.make_addplot(
                        df['daily_vwap'],
                        color='#3b82f6',  # Blue - swapped with entry price
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

            # Entry price line (green)
            if entry_price is not None:
                plots.append(
                    mpf.make_addplot(
                        [entry_price] * len(df),
                        color="#10b981",
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

            # CRITICAL: Resize all axes to make room for right-side annotations
            # mplfinance creates axes that span nearly the full figure width,
            # so we need to shrink them to leave space for Entry/Stop/Target labels
            for ax in axes:
                pos = ax.get_position()
                new_width = pos.width * 0.88  # Shrink to 88% to leave 12% for labels
                ax.set_position([pos.x0, pos.y0, new_width, pos.height])

            if ax1:
                # Set y-axis limits to ensure all targets are visible
                ax1.set_ylim(y_min, y_max)
                
                # Use scientific notation for large numbers
                if y_max > 10000:
                    ax1.ticklabel_format(style="plain", axis="y")
                
                # Limit ticks to avoid overflow warnings
                self._configure_axis_ticks(ax1, max_ticks=20)
                
                # Custom date formatting for x-axis - Use consistent formatting
                # Use AutoDateLocator with reasonable tick spacing
                date_locator = AutoDateLocator(maxticks=10)
                ax1.xaxis.set_major_locator(date_locator)
                
                # Format to show consistent time format matching mplfinance config
                time_formatter = DateFormatter('%m/%d %H:%M')
                ax1.xaxis.set_major_formatter(time_formatter)
                
                # Rotate labels for better readability
                plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

            # Add custom legend for VWAP if available
            if has_vwap:
                legend_elements = [
                    Line2D([0], [0], color='#3b82f6', lw=1.2, label='Daily VWAP (LTF)'),
                    Line2D([0], [0], color='#8b5cf6', lw=1.2, label='Weekly VWAP (HTF)')
                ]
                ax1.legend(handles=legend_elements, loc='upper left', fontsize=9, framealpha=0.7, facecolor=label_bg_color)

            # Always add trade overlays/labels regardless of VWAP availability
            # Add labels with improved styling
            entry_pos = None  # Initialize to prevent undefined variable error
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
            
                if entry_pos is not None:
                    ax1.annotate(
                        f"Entry: ${self._format_number(entry_price)}",
                        xy=(1.01, entry_pos),
                        xycoords=("axes fraction", "axes fraction"),
                        xytext=(1.05, entry_pos),
                        textcoords="axes fraction",
                        fontsize=9,
                        color="#10b981",
                        fontweight="bold",
                        annotation_clip=False,  # Allow annotation outside axes
                        bbox=dict(
                            facecolor=label_bg_color,
                            edgecolor="#3b82f6",
                            boxstyle="round,pad=0.3",
                            alpha=label_border_alpha,
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
                        annotation_clip=False,  # Allow annotation outside axes
                        bbox=dict(
                            facecolor=label_bg_color,
                            edgecolor="#ef4444",
                            boxstyle="round,pad=0.3",
                            alpha=label_border_alpha,
                        ),
                    )

                # Shade area between entry and stop loss if both exist
                if stop_loss is not None and entry_price is not None:
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
                                annotation_clip=False,  # Allow annotation outside axes
                                bbox=dict(
                                    facecolor=label_bg_color,
                                    edgecolor=color,
                                    boxstyle="round,pad=0.3",
                                    alpha=label_border_alpha,
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

            # Create output filename with more descriptive name
            from datetime import datetime
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            symbol_clean = symbol.replace('/', '_').replace(':', '').lower()

            # Determine signal type for filename
            signal_type = "neutral"
            if entry_price and stop_loss:
                signal_type = "buy" if entry_price > stop_loss else "sell"

            filename = f"{symbol_clean}_{signal_type}_chart_{timestamp_str}.png"
            output_file = os.path.join(output_dir, filename)

            # Add Virtuoso branding watermark (browser-quality PNG)
            if WATERMARK_AVAILABLE and add_watermark_to_figure is not None:
                try:
                    add_watermark_to_figure(fig, position='bottom-right', zoom=0.5, padding=0.02)
                except Exception as wm_err:
                    self._log(f"Watermark failed, using fallback: {wm_err}", logging.WARNING)
                    # Fallback to text watermark
                    fig.text(0.85, 0.02, 'VIRTUOSO',
                            fontsize=14, weight='bold', color='#ff9900',
                            ha='right', va='bottom',
                            transform=fig.transFigure,
                            bbox=dict(boxstyle='round,pad=0.4',
                                     facecolor='#1E1E1E',
                                     edgecolor='#ff9900',
                                     alpha=0.9))
            else:
                # Fallback to text watermark if watermark utility unavailable
                fig.text(0.85, 0.02, 'VIRTUOSO',
                        fontsize=14, weight='bold', color='#ff9900',
                        ha='right', va='bottom',
                        transform=fig.transFigure,
                        bbox=dict(boxstyle='round,pad=0.4',
                                 facecolor='#1E1E1E',
                                 edgecolor='#ff9900',
                                 alpha=0.9))

            # Save the figure - use pad_inches instead of bbox_inches='tight' to preserve watermark
            plt.savefig(output_file, dpi=150, pad_inches=0.2, facecolor=fig.get_facecolor())

            # Also save to reports/charts directory if not already there
            if output_dir != chart_dir:
                chart_file = os.path.join(chart_dir, filename)
                plt.savefig(chart_file, dpi=150, pad_inches=0.2, facecolor=fig.get_facecolor())
                self._log(f"Chart also saved to: {chart_file}")

            plt.close(fig)

            duration = time.time() - start_time
            self._log(f"[CHART:{chart_id}] Candlestick chart for {symbol} created in {duration:.2f}s: {output_file}", logging.INFO)
            return output_file

        except Exception as e:
            duration = time.time() - start_time
            self._log(f"[CHART:{chart_id}] Error creating candlestick chart for {symbol} after {duration:.2f}s: {str(e)}", logging.ERROR)
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
            
            # Pre-process data to handle circular references
            processed_data = self._prepare_for_json(data)
            json_content = json.dumps(processed_data, indent=2, cls=CustomJSONEncoder)
            
            # Save to output_dir as requested
            with open(json_path, "w") as f:
                f.write(json_content)
                
            # Also save to reports/json directory
            with open(reports_json_path, "w") as f:
                f.write(json_content)

            self._log(f"JSON data exported to {json_path} and {reports_json_path}")

            # Store signal to database if it's a trading signal (has signal_type)
            if processed_data.get('signal_type') in ['LONG', 'SHORT']:
                try:
                    from src.database.signal_storage import store_trading_signal
                    signal_id_from_db = store_trading_signal(
                        signal_data=processed_data,
                        json_path=reports_json_path
                    )

                    # Open signal tracking for performance monitoring
                    if signal_id_from_db:
                        try:
                            from src.database.signal_performance import SignalPerformanceTracker
                            from src.database.signal_tracking_helpers import (
                                determine_signal_pattern,
                                extract_orderflow_tags,
                                get_divergence_type,
                                get_validation_cohort,
                                get_trigger_component
                            )

                            tracker = SignalPerformanceTracker("data/virtuoso.db")

                            # Determine pattern classification
                            components = processed_data.get('components', {})
                            signal_type = processed_data.get('signal_type')
                            pattern = determine_signal_pattern(components, signal_type)

                            # Get additional tracking metadata
                            divergence_type = get_divergence_type(components, signal_type, pattern)
                            orderflow_tags = extract_orderflow_tags(components)
                            trigger_component = get_trigger_component(components)

                            # Get entry price (use trade_params if available, fallback to price)
                            trade_params = processed_data.get('trade_params', {})
                            confirmed_price = trade_params.get('entry_price') or processed_data.get('price')

                            # Open the signal for tracking
                            # Note: signal_id in database is a string like 'btcusdt_long_75p0_20251211_143022'
                            # We need to query the database to get this signal_id
                            from src.database.signal_storage import get_signal_by_id
                            symbol = processed_data.get('symbol', '').upper().replace('/', '')
                            score = processed_data.get('score', 0)
                            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                            score_str = f"{score:.1f}".replace('.', 'p')
                            signal_id = f"{symbol.lower()}_{signal_type}_{score_str}_{timestamp_str}"

                            success = tracker.open_signal(
                                signal_id=signal_id,
                                confirmed_price=confirmed_price,
                                signal_pattern=pattern,
                                divergence_type=divergence_type,
                                orderflow_tags=orderflow_tags,
                                is_validation_cohort=True,  # Current signals are validation cohort
                                orderflow_config=get_validation_cohort(),
                                trigger_component=trigger_component
                            )

                            if success:
                                self._log(f"Signal tracking opened for {signal_id} with pattern {pattern}")
                            else:
                                self._log(f"Warning: Failed to open signal tracking for {signal_id}", logging.WARNING)

                        except Exception as tracking_error:
                            self._log(f"Warning: Could not initialize performance tracking: {tracking_error}", logging.WARNING)

                except Exception as db_error:
                    self._log(f"Warning: Could not store signal to database: {db_error}", logging.WARNING)

            return json_path

        except Exception as e:
            self._log(f"Error exporting JSON data: {str(e)}", logging.ERROR)
            return None

    def _prepare_for_json(self, obj: Any, visited: Optional[set] = None) -> Any:
        """
        Convert objects to JSON serializable types with circular reference detection.
        
        Args:
            obj: Object to convert
            visited: Set of already visited object IDs to prevent circular references
            
        Returns:
            JSON serializable object
        """
        if visited is None:
            visited = set()
            
        # Get object ID for circular reference detection
        obj_id = id(obj)
        
        # Check for circular reference
        if obj_id in visited:
            # Return a safe representation instead of recursing
            return f"<circular_reference:{type(obj).__name__}>"
            
        # Add current object to visited set for complex types
        if isinstance(obj, (dict, list)):
            visited.add(obj_id)
            
        try:
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    try:
                        result[str(k)] = self._prepare_for_json(v, visited.copy())
                    except Exception as e:
                        # Handle problematic values gracefully
                        result[str(k)] = f"<serialization_error:{type(v).__name__}>"
                return result
            elif isinstance(obj, list):
                result = []
                for item in obj:
                    try:
                        result.append(self._prepare_for_json(item, visited.copy()))
                    except Exception as e:
                        # Handle problematic items gracefully
                        result.append(f"<serialization_error:{type(item).__name__}>")
                return result
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
            elif hasattr(obj, '__dict__') and not callable(obj) and not isinstance(obj, type):
                # Handle objects with __dict__ but avoid circular references
                try:
                    return self._prepare_for_json(obj.__dict__, visited.copy())
                except Exception as e:
                    self._log(f"[JSON_PREP] Failed to serialize object {type(obj).__name__}: {str(e)}", logging.DEBUG)
                    return f"<object:{type(obj).__name__}>"
            else:
                return obj
        except Exception as e:
            # Final fallback for any serialization issues
            return f"<unserializable:{type(obj).__name__}>"
        finally:
            # Remove from visited set when done (for this branch)
            if isinstance(obj, (dict, list)) and obj_id in visited:
                visited.discard(obj_id)

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
        template_style: str = "horizontal",
        chart_mode: str = "light",
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Generate a PDF trading report from the provided signal data.

        Args:
            signal_data: Dictionary containing trading signal information
            ohlcv_data: Optional DataFrame with OHLCV data for candlestick chart
            output_dir: Directory to save the report (defaults to a temporary directory)
            template_style: "vertical" (A4 portrait) or "horizontal" (A4 landscape)
            chart_mode: "dark" or "light" (warm amber background for charts)

        Returns:
            Tuple of (pdf_path, json_path, chart_path) or (None, None, None) if generation failed
        """
        try:
            # For horizontal template, always use light chart mode for better readability
            if template_style == "horizontal":
                chart_mode = "light"

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
                # Set output_dir for downstream functions (component chart, JSON export)
                output_dir = pdf_dir

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

            # Fix reliability percentage display bug - reliability is already in 0-1 range from signal generation
            try:
                rel_raw = float(reliability)
            except Exception as e:
                self._log(f"[RELIABILITY] Failed to parse reliability value '{reliability}': {str(e)}", logging.DEBUG)
                rel_raw = 0.5

            # Signal generator already returns reliability in 0-1 range, so just convert to percentage
            if rel_raw <= 1.0:
                # Already normalized (0-1), convert to percentage
                reliability_pct = rel_raw * 100.0
            else:
                # Already a percentage (shouldn't happen with new signal generator)
                reliability_pct = rel_raw

            # Ensure it's within valid bounds
            reliability_pct = max(0.0, min(100.0, reliability_pct))

            # Add basic data to context
            context.update(
                {
                    "symbol": symbol,
                    "signal_type": signal_type,
                    "score": confluence_score,  # CHANGED: Using confluence_score instead of score
                    "price": price,
                    "timestamp": timestamp,
                    "reliability": reliability_pct,  # Already normalized percentage for template
                    "analysis_components": signal_data.get("analysis_components", {}),  # Add interpretations
                }
            )

            # Create candlestick chart if OHLCV data is provided
            try:
                if ohlcv_data is not None and not ohlcv_data.empty:
                    self._log("Creating candlestick chart from OHLCV data")

                    # Get trade parameters if available
                    trade_params = signal_data.get("trade_params", {})
                    entry_price = (
                        trade_params.get("entry_price", None)
                        or signal_data.get("entry_price", None)
                        or signal_data.get("price", None)
                    )
                    stop_loss = trade_params.get("stop_loss", None) or signal_data.get("stop_loss", None)

                    # Calculate stop loss if missing using StopLossCalculator
                    sig_type = (signal_data.get("signal_type", "NEUTRAL") or "NEUTRAL").upper()
                    if stop_loss is None and entry_price:
                        try:
                            from src.core.risk.stop_loss_calculator import get_stop_loss_calculator, StopLossMethod

                            # Get configuration for calculator
                            config = self.config if hasattr(self, 'config') else {}

                            # Initialize stop loss calculator if not already done
                            try:
                                stop_calc = get_stop_loss_calculator()
                            except ValueError:
                                # First initialization
                                stop_calc = get_stop_loss_calculator(config)

                            # Calculate stop loss using confidence-based method
                            confluence_score = signal_data.get("confluence_score", signal_data.get("score", 50))

                            if sig_type in ["LONG", "SHORT"]:
                                stop_loss = stop_calc.calculate_stop_loss_price(
                                    entry_price=entry_price,
                                    signal_type=sig_type,
                                    confluence_score=confluence_score,
                                    method=StopLossMethod.CONFIDENCE_BASED
                                )
                                self._log(f"Chart: Calculated stop loss using StopLossCalculator: {sig_type} @ {entry_price:.6f} → {stop_loss:.6f}", logging.INFO)
                            else:
                                # Fallback for NEUTRAL or invalid signal types
                                self._log(f"Chart: Signal type {sig_type} not supported for stop loss calculation, using default 3%", logging.WARNING)
                                stop_loss = entry_price * 0.97  # Default 3% for neutral
                        except Exception as calc_error:
                            # Fallback if calculator fails
                            self._log(f"Chart: StopLossCalculator failed, using simple fallback: {calc_error}", logging.WARNING)
                            if sig_type in ["BUY", "LONG", "BULLISH"]:
                                stop_loss = entry_price * 0.97  # ~3% risk
                            elif sig_type in ["SELL", "SHORT", "BEARISH"]:
                                stop_loss = entry_price * 1.03
                    targets = trade_params.get("targets", None) or signal_data.get("targets", None)
                    
                    # Ensure targets are always available - generate defaults if none provided
                    if not targets and entry_price:
                        signal_type = signal_data.get("signal_type", "BULLISH")
                        targets = self._generate_default_targets(
                            entry_price=entry_price,
                            stop_loss=stop_loss,
                            signal_type=signal_type
                        )
                        self._log(f"Generated {len(targets)} default targets for report generation", logging.INFO)

                    # Create chart
                    candlestick_chart = self._create_candlestick_chart(
                        symbol=symbol,
                        ohlcv_data=ohlcv_data,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        targets=targets,
                        output_dir=os.path.dirname(pdf_path),
                        chart_mode=chart_mode,
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
                            chart_mode=chart_mode,
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
                        chart_mode=chart_mode,
                    )
            except Exception as e:
                self._log(
                    f"Error creating candlestick chart: {str(e)}", level=logging.ERROR
                )

            # Add chart to template context
            context["candlestick_chart"] = candlestick_chart

            # Create component chart image
            try:
                # Get components from either 'components' or 'analysis_components'
                components = signal_data.get("components", {})
                analysis_components = signal_data.get("analysis_components", {})

                # Merge analysis_components into components if they exist
                if analysis_components and isinstance(analysis_components, dict):
                    # If components is empty, use analysis_components directly
                    if not components:
                        components = analysis_components
                    else:
                        # Merge analysis_components into components
                        for key, value in analysis_components.items():
                            if key not in components:
                                components[key] = value

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
                            "range_analysis": "Range Analysis",
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
                if not confluence_text:
                    # Fallbacks to maintain confluence narrative in PDFs
                    if isinstance(signal_data.get("breakdown"), dict):
                        confluence_text = signal_data.get("breakdown", {}).get("formatted_analysis")
                    if not confluence_text:
                        confluence_text = signal_data.get("formatted_analysis")
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
                            # Calculate impact if not provided
                            impact = data.get("impact", abs(score_value - 50) * 2)
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

            # Fallback: use pre-formatted component_data from signal_data if available
            if not component_data and signal_data.get("component_data"):
                component_data = signal_data.get("component_data", [])
                self._log(f"Using pre-formatted component_data with {len(component_data)} items")

            # Calculate Top Performers - highest scoring sub-components across all categories
            top_performers = []
            try:
                results = signal_data.get("results", {})
                # Category display names and their weights
                category_info = {
                    "technical": {"name": "Technical", "weight": 0.15},
                    "volume": {"name": "Volume", "weight": 0.18},
                    "orderbook": {"name": "Orderbook", "weight": 0.20},
                    "orderflow": {"name": "Orderflow", "weight": 0.30},
                    "sentiment": {"name": "Sentiment", "weight": 0.07},
                    "price_structure": {"name": "Structure", "weight": 0.10},
                }

                all_subcomponents = []
                for category, info in category_info.items():
                    cat_data = results.get(category, {})
                    components = cat_data.get("components", {})
                    if isinstance(components, dict):
                        for sub_name, score in components.items():
                            if isinstance(score, (int, float)) and not sub_name.startswith("_"):
                                # Calculate weighted impact
                                weighted_score = score * info["weight"]
                                all_subcomponents.append({
                                    "name": sub_name.replace("_", " ").upper(),
                                    "score": round(score, 1),
                                    "category": info["name"],
                                    "weighted": round(weighted_score, 1),
                                    "color_class": "high-score" if score >= 65 else "low-score" if score <= 35 else "medium-score"
                                })

                # Sort by raw score (highest first) and take top 6
                all_subcomponents.sort(key=lambda x: x["score"], reverse=True)
                top_performers = all_subcomponents[:6]
                self._log(f"Calculated {len(top_performers)} top performers from {len(all_subcomponents)} sub-components")
            except Exception as e:
                self._log(f"Error calculating top performers: {str(e)}", logging.WARNING)

            # Format timestamp
            formatted_timestamp = ""
            try:
                if isinstance(timestamp, str):
                    try:
                        timestamp_dt = datetime.fromisoformat(timestamp)
                        formatted_timestamp = timestamp_dt.strftime(
                            "%Y-%m-%d %H:%M:%S UTC"
                        )
                    except Exception as e:
                        self._log(f"[PDF_TIMESTAMP] Failed to parse ISO timestamp '{timestamp}': {str(e)}", logging.DEBUG)
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
                
                # Process market interpretations using centralized InterpretationManager
                raw_interpretations = (
                    signal_data.get("market_interpretations")
                    or signal_data.get("insights")
                    or (signal_data.get("breakdown", {}).get("interpretations") if isinstance(signal_data.get("breakdown"), dict) else None)
                )

                # FINAL FALLBACK: derive interpretations from results dict
                # Many upstream paths populate per-component interpretations under results[component]['interpretation']
                if not raw_interpretations:
                    try:
                        results_obj = signal_data.get("results") or {}
                        if isinstance(results_obj, dict) and results_obj:
                            derived_list = []
                            for comp_name, comp_data in results_obj.items():
                                if isinstance(comp_data, dict):
                                    interp = comp_data.get("interpretation") or comp_data.get("summary") or comp_data.get("text")
                                    if interp:
                                        display = comp_name.replace('_', ' ').title()
                                        derived_list.append({
                                            "component": comp_name,
                                            "display_name": display,
                                            "interpretation": interp,
                                        })
                            if derived_list:
                                raw_interpretations = derived_list
                                self._log(f"Derived {len(derived_list)} interpretations from results for PDF", level=logging.DEBUG)
                    except Exception as e:
                        self._log(f"Error deriving interpretations from results: {e}", level=logging.WARNING)
                raw_actionable = signal_data.get("actionable_insights", [])
                # Strip emojis from actionable insights (using Lucide icons in template instead)
                import re
                emoji_pattern = re.compile(
                    '['
                    '\U0001F600-\U0001F64F'  # emoticons
                    '\U0001F300-\U0001F5FF'  # symbols & pictographs
                    '\U0001F680-\U0001F6FF'  # transport & map
                    '\U0001F1E0-\U0001F1FF'  # flags
                    '\U00002702-\U000027B0'  # dingbats
                    '\U0001F900-\U0001F9FF'  # supplemental symbols
                    '\U00002600-\U000026FF'  # misc symbols
                    ']+', re.UNICODE
                )
                actionable_insights = [emoji_pattern.sub('', str(item)).strip() for item in raw_actionable]

                # Use InterpretationManager to process and standardize interpretations
                insights = []
                try:
                    if raw_interpretations:
                        self._log(f"Processing {len(raw_interpretations) if isinstance(raw_interpretations, list) else 1} interpretations with InterpretationManager", level=logging.DEBUG)
                        
                        # Process interpretations through centralized manager
                        interpretation_set = self.interpretation_manager.process_interpretations(
                            raw_interpretations, 
                            f"pdf_{symbol}",
                            market_data=None,
                            timestamp=datetime.now()
                        )
                        
                        # Format interpretations for PDF (text-only format)
                        formatted_for_pdf = self.interpretation_manager.get_formatted_interpretation(
                            interpretation_set, 'pdf'
                        )
                        
                        # Extract text-only interpretations for PDF template
                        insights = []
                        for interpretation in interpretation_set.interpretations:
                            component_name = interpretation.component_name.replace('_', ' ').title()
                            # No emoji prefix - using Lucide icons in template instead
                            insights.append(f"{component_name}: {interpretation.interpretation_text}")
                        
                        self._log(f"Processed {len(insights)} interpretations for PDF", level=logging.DEBUG)
                    else:
                        self._log("No market interpretations found", level=logging.DEBUG)
                        # Last-resort: derive brief insights from formatted analysis text
                        fa_text = signal_data.get("formatted_analysis")
                        if not fa_text and isinstance(signal_data.get("breakdown"), dict):
                            fa_text = signal_data.get("breakdown", {}).get("formatted_analysis")
                        if isinstance(fa_text, str) and fa_text:
                            for line in fa_text.splitlines():
                                s = line.strip()
                                if s.startswith("•") or s.startswith("-"):
                                    insights.append(s.lstrip("•-").strip())
                                    if len(insights) >= 6:
                                        break
                
                except Exception as e:
                    self._log(f"Error processing interpretations with InterpretationManager: {e}", level=logging.ERROR)
                    # Fallback to original processing
                    insights = raw_interpretations if isinstance(raw_interpretations, list) else []
                
                # Normalize insights to a list of plain strings for the template
                try:
                    if insights:
                        normalized_insights = []
                        for item in insights:
                            if isinstance(item, str):
                                if item.strip():
                                    normalized_insights.append(item.strip())
                                continue
                            if isinstance(item, dict):
                                text = (
                                    item.get('interpretation')
                                    or item.get('interpretation_text')
                                    or item.get('text')
                                    or item.get('summary')
                                )
                                comp = (
                                    item.get('display_name')
                                    or item.get('component_name')
                                    or item.get('component')
                                )
                                if text:
                                    normalized_insights.append(f"{comp + ': ' if comp else ''}{text}")
                                continue
                            # Fallback for objects with attributes
                            text = getattr(item, 'interpretation_text', None) or getattr(item, 'text', None)
                            comp = getattr(item, 'component_name', None)
                            if text:
                                normalized_insights.append(f"{(comp + ': ') if comp else ''}{text}")

                        # Replace only if we built something useful
                        if normalized_insights:
                            insights = normalized_insights
                except Exception:
                    pass
            except Exception as e:
                self._log(f"Error extracting insights: {str(e)}", logging.ERROR)
                self._log(traceback.format_exc(), logging.DEBUG)

            # Merge interpretations into component_data for template rendering
            # This ensures component_data has interpretation text for the header-style display
            try:
                if insights and component_data:
                    # Build a mapping of component names to their insights
                    insight_map = {}
                    for insight in insights:
                        if isinstance(insight, str) and ':' in insight:
                            # Parse "Component Name: interpretation text" format
                            parts = insight.split(':', 1)
                            if len(parts) == 2:
                                comp_name = parts[0].strip().lower().replace(' ', '_')
                                insight_text = parts[1].strip()
                                insight_map[comp_name] = insight_text

                    # Update component_data with interpretations
                    for comp in component_data:
                        comp_name = comp.get('name', '').lower().replace(' ', '_')
                        if comp_name in insight_map and not comp.get('interpretation'):
                            comp['interpretation'] = insight_map[comp_name]

                    self._log(f"Merged {len(insight_map)} interpretations into component_data", level=logging.DEBUG)
            except Exception as e:
                self._log(f"Error merging interpretations into component_data: {e}", logging.WARNING)

            # Extract risk management details with comprehensive validation
            entry_price = price
            stop_loss = None
            stop_loss_percent = 0
            try:
                # Check trade_params first, then fall back to signal_data
                trade_params = signal_data.get("trade_params", {})
                entry_price = trade_params.get("entry_price", None) or signal_data.get("entry_price", price)
                stop_loss = trade_params.get("stop_loss", None) or signal_data.get("stop_loss", None)

                # Calculate stop loss if missing using StopLossCalculator
                if stop_loss is None and entry_price:
                    try:
                        from src.core.risk.stop_loss_calculator import get_stop_loss_calculator, StopLossMethod

                        # Get configuration for calculator
                        config = self.config if hasattr(self, 'config') else {}

                        # Initialize stop loss calculator if not already done
                        try:
                            stop_calc = get_stop_loss_calculator()
                        except ValueError:
                            # First initialization
                            stop_calc = get_stop_loss_calculator(config)

                        # Calculate stop loss using confidence-based method
                        sig_type = (signal_data.get("signal_type", "NEUTRAL") or "NEUTRAL").upper()
                        confluence_score = signal_data.get("confluence_score", signal_data.get("score", 50))

                        if sig_type in ["LONG", "SHORT"]:
                            stop_loss = stop_calc.calculate_stop_loss_price(
                                entry_price=entry_price,
                                signal_type=sig_type,
                                confluence_score=confluence_score,
                                method=StopLossMethod.CONFIDENCE_BASED
                            )
                            self._log(f"Calculated stop loss using StopLossCalculator: {sig_type} @ {entry_price:.6f} → {stop_loss:.6f}", logging.INFO)
                        else:
                            # Fallback for NEUTRAL or invalid signal types
                            self._log(f"Signal type {sig_type} not supported for stop loss calculation, using default 3%", logging.WARNING)
                            stop_loss = entry_price * 0.97  # Default 3% for neutral
                    except Exception as calc_error:
                        # Fallback if calculator fails
                        self._log(f"StopLossCalculator failed, using simple fallback: {calc_error}", logging.WARNING)
                        sig_type = (signal_data.get("signal_type", "NEUTRAL") or "NEUTRAL").upper()
                        if sig_type in ["LONG", "BULLISH"]:
                            stop_loss = entry_price * 0.97  # ~3% risk
                        elif sig_type in ["SHORT", "BEARISH"]:
                            stop_loss = entry_price * 1.03
                        else:
                            stop_loss = entry_price * 0.97  # Default for neutral

                # Comprehensive boundary checking and validation
                if stop_loss and entry_price:
                    # Validate numeric types
                    if not isinstance(entry_price, (int, float)) or not isinstance(stop_loss, (int, float)):
                        self._log(f"Invalid price types: entry_price={type(entry_price)}, stop_loss={type(stop_loss)}", logging.ERROR)
                        entry_price, stop_loss = price, None

                    # Validate positive values
                    elif entry_price <= 0 or stop_loss <= 0:
                        self._log(f"Invalid negative prices: entry_price={entry_price}, stop_loss={stop_loss}", logging.ERROR)
                        entry_price, stop_loss = price, None

                    # Validate reasonable price ranges (not more than 1000x difference)
                    elif abs(entry_price / stop_loss) > 1000 or abs(stop_loss / entry_price) > 1000:
                        self._log(f"Unrealistic price ratio: entry_price={entry_price}, stop_loss={stop_loss}", logging.ERROR)
                        entry_price, stop_loss = price, None

                    else:
                        # Calculate stop loss percentage with proper validation
                        if entry_price > stop_loss:  # Long position
                            stop_loss_percent = ((stop_loss / entry_price) - 1) * 100
                        else:  # Short position
                            stop_loss_percent = ((stop_loss / entry_price) - 1) * 100

                        # Validate calculated percentage is reasonable (0.1% to 50%)
                        abs_percent = abs(stop_loss_percent)
                        if abs_percent < 0.1 or abs_percent > 50:
                            self._log(f"Unrealistic stop loss percentage: {stop_loss_percent:.2f}%", logging.WARNING)
                            # Don't reset to None, but log the concern

                        # Ensure percentage is displayed as positive value
                        stop_loss_percent = abs(stop_loss_percent)

            except (ZeroDivisionError, ValueError, TypeError) as e:
                self._log(f"Calculation error in risk management details: {str(e)}", logging.ERROR)
                entry_price, stop_loss, stop_loss_percent = price, None, 0
            except Exception as e:
                self._log(f"Unexpected error extracting risk management details: {str(e)}", logging.ERROR)
                entry_price, stop_loss, stop_loss_percent = price, None, 0

            # Format targets
            targets = []
            try:
                # Check trade_params first, then fall back to signal_data
                trade_params = signal_data.get("trade_params", {})
                targets_data = trade_params.get("targets", None) or signal_data.get("targets", {})

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
                elif isinstance(targets_data, list):
                    # Handle list format (from generated targets)
                    for target_data in targets_data:
                        if isinstance(target_data, dict) and "price" in target_data:
                            target_price = target_data.get("price", 0)
                            target_size = target_data.get("size", 0)
                            target_name = target_data.get("name", f"Target {len(targets) + 1}")

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
                
                # If no targets found, generate defaults
                if not targets and entry_price:
                    signal_type = signal_data.get("signal_type", "BULLISH")
                    default_targets = self._generate_default_targets(
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        signal_type=signal_type
                    )
                    targets = default_targets
                    self._log(f"Generated {len(targets)} default targets for PDF display", logging.INFO)
                    
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
                "reliability": reliability_pct,  # Use normalized percentage for template display
                "price": price,
                "timestamp": formatted_timestamp,
                "signal_type": signal_type,
                # Map signal_type to valid CSS color values instead of using signal_type directly
                "signal_color": "#4CAF50" if signal_type == "LONG" else "#F44336" if signal_type == "SHORT" else "#FFC107",  # Green for LONG, Red for SHORT, Amber for NEUTRAL
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
                # Top performers - highest scoring sub-components
                "top_performers": top_performers,
            }

            # Render the HTML template
            try:
                # Select template based on template_style parameter
                if template_style == "horizontal":
                    template_name = "trading_report_horizontal.html"
                else:
                    template_name = "trading_report_dark.html"
                template = self.env.get_template(template_name)

                # Preserve raw chart path for return values before converting for HTML
                raw_candlestick_chart_path = candlestick_chart

                # Fix image paths - use web-accessible /exports/ URLs for charts in exports directory
                # This allows HTML reports to display charts when viewed via the web server
                if candlestick_chart:
                    abs_path = os.path.abspath(candlestick_chart)
                    if '/exports/' in abs_path:
                        # Use web-accessible path for exports
                        candlestick_chart = f"/exports/{os.path.basename(abs_path)}"
                    else:
                        # Fallback to file:// for other locations
                        candlestick_chart = f"file://{abs_path}"
                if component_chart:
                    abs_path = os.path.abspath(component_chart)
                    if '/exports/' in abs_path:
                        component_chart = f"/exports/{os.path.basename(abs_path)}"
                    else:
                        component_chart = f"file://{abs_path}"
                if confluence_analysis_image:
                    abs_path = os.path.abspath(confluence_analysis_image)
                    if '/exports/' in abs_path:
                        confluence_analysis_image = f"/exports/{os.path.basename(abs_path)}"
                    else:
                        confluence_analysis_image = f"file://{abs_path}"
                # NOTE: confluence_visualization is already base64 data from visualizer.generate_base64_image()
                # The template uses data:image/png;base64,{{ confluence_visualization }} so we don't convert it

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

                # Save the HTML file first (needed for Chrome renderer)
                with open(html_path, "w") as f:
                    f.write(html_content)

                # Try Chrome Headless first (full CSS support: gradients, shadows, etc.)
                # Falls back to WeasyPrint if Chrome is unavailable
                chrome_success = self._render_pdf_with_chrome(html_content, pdf_path, html_path)

                if not chrome_success:
                    self._log("Falling back to WeasyPrint for PDF generation", logging.INFO)
                    HTML(string=html_content).write_pdf(pdf_path)

                # Export JSON data
                json_path = self._export_json_data(signal_data, json_filename, json_dir)

                self._log(f"Trading report generated: HTML: {html_path}, PDF: {pdf_path}, JSON: {json_path}")
                
                # Store filesystem chart path (not file:// URI) so Discord can attach it
                chart_path = raw_candlestick_chart_path if raw_candlestick_chart_path else None
                return pdf_path, json_path, chart_path
            except Exception as e:
                self._log(f"Error generating PDF: {str(e)}", logging.ERROR)
                return None, json_path, None

            # Return the paths to the PDF and JSON files
            if os.path.exists(pdf_path):
                self._log(f"Successfully created PDF report: {pdf_path}")
                
                # Clear the downsampling cache to free memory
                self._clear_downsample_cache()
                
                # Return with chart path (stored earlier)
                chart_path = candlestick_chart if 'candlestick_chart' in locals() else None
                return pdf_path, json_path, chart_path
            else:
                self._log(f"Failed to create PDF report: {pdf_path}", level=logging.ERROR)
                
                # Clear the cache even if generation failed
                self._clear_downsample_cache()
                
                return None, None, None

        except Exception as e:
            self._log(f"Error generating trading report: {str(e)}", level=logging.ERROR)
            self._log(traceback.format_exc(), level=logging.ERROR)
            
            # Clear the cache on exception
            self._clear_downsample_cache()
            
            return None, None, None

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

                    # Smart timestamp conversion - detect if timestamp is in seconds or milliseconds
                    # Timestamps after year 2001 in milliseconds are > 1e12
                    # Timestamps after year 2001 in seconds are > 1e9 but < 1e12
                    if timestamp > 1e12:
                        # Already in milliseconds
                        dt = datetime.fromtimestamp(timestamp / 1000)
                    elif timestamp > 1e9:
                        # In seconds, convert to milliseconds first
                        self.logger.debug(f"Converting timestamp from seconds to milliseconds for filename: {timestamp}")
                        timestamp = timestamp * 1000
                        dt = datetime.fromtimestamp(timestamp / 1000)
                    else:
                        # Very small timestamp, likely an error - use current time
                        self.logger.warning(f"Invalid timestamp value for filename: {timestamp}, using current time")
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
                    
                    # Smart timestamp conversion - detect if timestamp is in seconds or milliseconds
                    # Timestamps after year 2001 in milliseconds are > 1e12
                    # Timestamps after year 2001 in seconds are > 1e9 but < 1e12
                    if timestamp > 1e12:
                        # Already in milliseconds
                        dt = datetime.fromtimestamp(timestamp / 1000)
                    elif timestamp > 1e9:
                        # In seconds, convert to milliseconds first
                        self.logger.debug(f"Converting timestamp from seconds to milliseconds in market report: {timestamp}")
                        timestamp = timestamp * 1000
                        dt = datetime.fromtimestamp(timestamp / 1000)
                    else:
                        # Very small timestamp, likely an error - use current time
                        self.logger.warning(f"Invalid timestamp value in market report: {timestamp}, using current time")
                        timestamp = int(time.time() * 1000)
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

            # Add futures premium section if available
            if "futures_premium" in market_data:
                self.logger.debug("Adding futures premium section")
                try:
                    elements.append(Paragraph("Futures Premium Analysis", section_title_style))
                    elements.append(Spacer(1, 12))
                    
                    futures_premium = market_data["futures_premium"]
                    
                    # Create futures premium chart
                    chart_path = self._create_futures_premium_chart(futures_premium, output_dir or ".")
                    if chart_path and os.path.exists(chart_path):
                        from reportlab.platypus import Image
                        img = Image(chart_path, width=500, height=300)
                        elements.append(img)
                        elements.append(Spacer(1, 12))
                    
                    # Create term structure chart
                    term_chart_path = self._create_term_structure_chart(futures_premium, output_dir or ".")
                    if term_chart_path and os.path.exists(term_chart_path):
                        from reportlab.platypus import Image
                        img = Image(term_chart_path, width=500, height=350)
                        elements.append(img)
                        elements.append(Spacer(1, 12))
                    
                    # Add summary table
                    market_status = futures_premium.get('market_status', 'NEUTRAL')
                    average_premium = futures_premium.get('average_premium', 0.0)
                    
                    summary_data = [
                        ['Market Status', market_status],
                        ['Average Premium', f"{average_premium:.2f}%"],
                        ['Analysis Time', datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")]
                    ]
                    
                    summary_table = Table(summary_data, colWidths=[150, 200])
                    summary_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    
                    elements.append(summary_table)
                    elements.append(Spacer(1, 20))
                    
                except Exception as futures_error:
                    self.logger.error(f"Error adding futures premium section: {str(futures_error)}")

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

                # Smart timestamp conversion - detect if timestamp is in seconds or milliseconds
                # Timestamps after year 2001 in milliseconds are > 1e12
                # Timestamps after year 2001 in seconds are > 1e9 but < 1e12
                current_time_ms = int(time.time() * 1000)
                
                if timestamp > 1e12:
                    # Already in milliseconds
                    dt = datetime.fromtimestamp(timestamp / 1000)
                elif timestamp > 1e9:
                    # In seconds, convert to milliseconds first
                    self.logger.debug(f"Converting timestamp from seconds to milliseconds: {timestamp}")
                    timestamp = timestamp * 1000
                    dt = datetime.fromtimestamp(timestamp / 1000)
                else:
                    # Very small timestamp, likely an error - use current time
                    self.logger.warning(f"Invalid timestamp value: {timestamp}, using current time")
                    timestamp = current_time_ms
                    dt = datetime.fromtimestamp(timestamp / 1000)
                
                report_date = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                # Store both timestamp (in milliseconds) and report_date for template compatibility
                market_data["report_date"] = report_date
                market_data["timestamp"] = timestamp
                market_data["generated_at"] = report_date  # Add this line to fix template variable error
                self.logger.debug(f"Processed timestamp {timestamp} to {report_date}")
            except Exception as timestamp_error:
                self.logger.error(f"Error processing timestamp: {str(timestamp_error)}")
                current_time = datetime.now()
                report_date = current_time.strftime("%Y-%m-%d %H:%M:%S UTC")
                market_data["report_date"] = report_date
                market_data["timestamp"] = int(current_time.timestamp() * 1000)
                market_data["generated_at"] = report_date  # Add this line to fix template variable error
                self.logger.info(f"Using current time for report date: {report_date}")

            # Process top performers - ensure it's in the correct format for the template
            if "top_performers" in market_data:
                performers = market_data["top_performers"]
                if isinstance(performers, dict):
                    # Check if it's already in the correct format (gainers/losers structure)
                    if "gainers" in performers and "losers" in performers:
                        self.logger.debug("top_performers already in correct dict format with gainers/losers")
                        # Ensure gainers and losers are lists
                        if not isinstance(performers.get("gainers"), list):
                            performers["gainers"] = []
                        if not isinstance(performers.get("losers"), list):
                            performers["losers"] = []
                    else:
                        # Legacy format - convert to gainers/losers structure
                        self.logger.info("Converting top_performers from legacy dict format to gainers/losers structure")
                        gainers = []
                        losers = []
                        for category, items in performers.items():
                            if isinstance(items, list):
                                for item in items:
                                    if isinstance(item, dict):
                                        # Determine if it's a gainer or loser based on change
                                        change = item.get("change_percent", 0)
                                        if isinstance(change, str):
                                            try:
                                                change = float(change.replace("%", ""))
                                            except Exception as e:
                                                self._log(f"[TOP_PERF] Failed to parse change_percent '{change}': {str(e)}", logging.DEBUG)
                                                change = 0
                                        
                                        if change > 0:
                                            gainers.append(item)
                                        else:
                                            losers.append(item)
                            else:
                                self.logger.warning(f"Unexpected format for {category} in top_performers: {items}")
                        
                        market_data["top_performers"] = {
                            "gainers": gainers,
                            "losers": losers,
                            "total_analyzed": performers.get("total_analyzed", len(gainers) + len(losers)),
                            "failed_symbols": performers.get("failed_symbols", 0),
                            "timestamp": performers.get("timestamp", int(time.time() * 1000))
                        }
                        self.logger.debug(f"Converted to gainers/losers format: {len(gainers)} gainers, {len(losers)} losers")
                elif isinstance(performers, list):
                    # Convert list format to gainers/losers structure
                    self.logger.info("Converting top_performers from list format to gainers/losers structure")
                    gainers = []
                    losers = []
                    for item in performers:
                        if isinstance(item, dict):
                            change = item.get("change_percent", 0)
                            if isinstance(change, str):
                                try:
                                    change = float(change.replace("%", ""))
                                except Exception as e:
                                    self._log(f"[TOP_PERF] Failed to parse change_percent '{change}': {str(e)}", logging.DEBUG)
                                    change = 0
                            
                            if change > 0:
                                gainers.append(item)
                            else:
                                losers.append(item)
                    
                    market_data["top_performers"] = {
                        "gainers": gainers,
                        "losers": losers,
                        "total_analyzed": len(performers),
                        "failed_symbols": 0,
                        "timestamp": int(time.time() * 1000)
                    }
                    self.logger.debug(f"Converted list to gainers/losers format: {len(gainers)} gainers, {len(losers)} losers")
                else:
                    self.logger.warning(f"top_performers has unexpected type: {type(performers)}, setting to default structure")
                    market_data["top_performers"] = {
                        "gainers": [],
                        "losers": [],
                        "total_analyzed": 0,
                        "failed_symbols": 0,
                        "timestamp": int(time.time() * 1000)
                    }

            # Generate the filename
            if output_path:
                html_path = output_path
                if not html_path.endswith(".html"):
                    html_path += ".html"
            else:
                # Generate a filename based on timestamp
                try:
                    # Use the timestamp from market_data which is now guaranteed to be in milliseconds
                    timestamp = market_data.get('timestamp', int(time.time() * 1000))
                    if isinstance(timestamp, str):
                        try:
                            timestamp = int(timestamp)
                        except ValueError:
                            timestamp = int(time.time() * 1000)
                    
                    html_filename = f"market_report_{timestamp}.html"
                    html_path = os.path.join(html_dir, html_filename)
                except Exception as e:
                    self.logger.error(f"Error generating timestamp string: {str(e)}")
                    html_path = os.path.join(html_dir, f"market_report_{int(time.time() * 1000)}.html")

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
                
                # Generate futures premium charts if data is available
                if market_data.get("futures_premium") and isinstance(market_data["futures_premium"], dict):
                    futures_premium = market_data["futures_premium"]
                    
                    # Create charts for HTML report
                    chart_path = self._create_futures_premium_chart(futures_premium, output_dir or ".")
                    term_chart_path = self._create_term_structure_chart(futures_premium, output_dir or ".")
                    
                    # Add chart paths to market data for template
                    if chart_path:
                        market_data["futures_premium"]["chart_path"] = os.path.basename(chart_path)
                    if term_chart_path:
                        market_data["futures_premium"]["term_structure_chart_path"] = os.path.basename(term_chart_path)
                
                # Add comprehensive logging of data structure
                try:
                    # Use a custom encoder or fallback to simple string conversion for problem values
                    class DebugEncoder(json.JSONEncoder):
                        def default(self, obj):
                            try:
                                return super().default(obj)
                            except Exception as e:
                                self._log(f"[DEBUG_ENCODER] Failed to serialize {type(obj).__name__}: {str(e)}", logging.DEBUG)
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
                error_msg = str(render_error)
                self.logger.error(f"Error rendering template: {error_msg}")
                self.logger.debug(traceback.format_exc())
                
                # Track template rendering errors
                track_error(
                    error_type="template_rendering_error",
                    message=error_msg,
                    component="pdf_generator",
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.TEMPLATE_RENDERING,
                    details={"template_path": template_path, "error_details": error_msg}
                )

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
                "LONG"
                if signal_type.upper() in ["LONG", "BULLISH"]
                else "SHORT"
                if signal_type.upper() in ["SHORT", "BEARISH"]
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
                
                # Enhanced options for better CSS support in wkhtmltopdf
                options = {
                    "page-size": "A4",
                    "margin-top": "1cm",
                    "margin-right": "1cm", 
                    "margin-bottom": "1cm",
                    "margin-left": "1cm",
                    "encoding": "UTF-8",
                    "enable-local-file-access": None,
                    "print-media-type": None,
                    "disable-smart-shrinking": None,
                    "zoom": 1.0,
                    "dpi": 96,
                    "image-dpi": 96,
                    "image-quality": 94,
                    "quiet": None,
                    # Enhanced options for better CSS support
                    "load-error-handling": "ignore",
                    "load-media-error-handling": "ignore",
                    "javascript-delay": 1000,
                    "no-stop-slow-scripts": None,
                    "debug-javascript": None,
                    "enable-javascript": None,
                }

                # Preprocess HTML to improve PDF compatibility
                processed_html_path = self._preprocess_html_for_pdf(html_path)
                
                pdfkit.from_file(processed_html_path, pdf_path, options=options)

                # Clean up temporary file if created
                if processed_html_path != html_path and os.path.exists(processed_html_path):
                    os.remove(processed_html_path)

                if os.path.exists(pdf_path):
                    self.logger.info(f"PDF generated successfully using pdfkit: {pdf_path}")
                    return True
                else:
                    self.logger.error(f"PDF file was not created by pdfkit: {pdf_path}")
                    return False

            except ImportError:
                self.logger.warning("pdfkit not available, trying weasyprint")

                # Fall back to weasyprint if pdfkit is not available
                try:
                    from weasyprint import HTML, CSS
                    from weasyprint.css import get_all_computed_styles
                    from weasyprint.css.targets import TargetCollector

                    self.logger.debug("Using weasyprint for PDF generation")
                    
                    # Read and clean HTML content for WeasyPrint compatibility
                    with open(html_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    # Remove problematic CSS that WeasyPrint doesn't support
                    html_content = self._clean_html_for_weasyprint(html_content)
                    
                    # Create HTML document from string instead of file to avoid encoding issues
                    html_doc = HTML(string=html_content, base_url=f"file://{os.path.dirname(html_path)}/")
                    
                    # Generate PDF with error handling
                    try:
                        html_doc.write_pdf(pdf_path)
                    except Exception as weasy_error:
                        self.logger.error(f"WeasyPrint PDF generation failed: {str(weasy_error)}")
                        # Try with simplified HTML
                        simplified_html = self._create_simplified_html(html_content)
                        html_doc = HTML(string=simplified_html)
                        html_doc.write_pdf(pdf_path)

                    if os.path.exists(pdf_path):
                        self.logger.info(f"PDF generated successfully using weasyprint: {pdf_path}")
                        return True
                    else:
                        self.logger.error(f"PDF file was not created by weasyprint: {pdf_path}")
                        return False

                except ImportError:
                    self.logger.error("Neither pdfkit nor weasyprint is available for PDF generation")
                    return False

        except Exception as e:
            self.logger.error(f"Error generating PDF: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False

    def _clean_html_for_weasyprint(self, html_content: str) -> str:
        """
        Clean HTML content to be compatible with WeasyPrint.
        
        Args:
            html_content: Original HTML content
            
        Returns:
            Cleaned HTML content
        """
        import re
        
        # Remove problematic CSS properties that WeasyPrint doesn't support
        problematic_properties = [
            r'box-shadow:[^;]+;',
            r'text-shadow:[^;]+;',
            r'@keyframes[^}]+}[^}]*}',
            r'animation:[^;]+;',
            r'transform:[^;]+;',
            r'transition:[^;]+;'
        ]
        
        for pattern in problematic_properties:
            html_content = re.sub(pattern, '', html_content, flags=re.IGNORECASE | re.DOTALL)
        
        # Fix media queries
        html_content = re.sub(r'@media\s+\([^)]+\)', '@media screen', html_content)
        
        return html_content
    
    def _create_simplified_html(self, original_html: str) -> str:
        """
        Create a simplified HTML version as fallback.
        
        Args:
            original_html: Original HTML content
            
        Returns:
            Simplified HTML content
        """
        import re
        
        # Extract title and basic content
        title_match = re.search(r'<title>([^<]+)</title>', original_html, re.IGNORECASE)
        title = title_match.group(1) if title_match else "Market Report"
        
        # Extract body content (remove complex styling)
        body_match = re.search(r'<body[^>]*>(.*?)</body>', original_html, re.IGNORECASE | re.DOTALL)
        body_content = body_match.group(1) if body_match else "Report content unavailable"
        
        # Remove complex CSS classes and inline styles
        body_content = re.sub(r'class="[^"]*"', '', body_content)
        body_content = re.sub(r'style="[^"]*"', '', body_content)
        
        simplified_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 20px; 
                    line-height: 1.6;
                    color: #333;
                }}
                h1, h2, h3 {{ color: #2c3e50; }}
                .header {{ 
                    background-color: #f8f9fa; 
                    padding: 15px; 
                    margin-bottom: 20px; 
                    border: 1px solid #dee2e6;
                }}
                .content {{ padding: 10px; }}
                table {{ 
                    width: 100%; 
                    border-collapse: collapse; 
                    margin: 10px 0;
                }}
                th, td {{ 
                    border: 1px solid #ddd; 
                    padding: 8px; 
                    text-align: left;
                }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            {body_content}
        </body>
        </html>
        """
        
        return simplified_html

    def _render_pdf_with_chrome(self, html_content: str, pdf_path: str, html_path: Optional[str] = None) -> bool:
        """
        Render PDF using Chrome Headless for full CSS support (gradients, shadows, etc.).

        Chrome Headless provides complete CSS rendering including:
        - Linear/radial gradients
        - Box shadows and text shadows
        - CSS transforms and animations (rendered statically)
        - Modern flexbox and grid layouts

        Args:
            html_content: HTML string to render
            pdf_path: Output path for PDF file
            html_path: Optional existing HTML file path (avoids temp file creation)

        Returns:
            True if successful, False otherwise
        """
        import subprocess
        import platform

        # Find Chrome executable based on platform
        chrome_paths = []
        if platform.system() == "Darwin":  # macOS
            chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            ]
        elif platform.system() == "Linux":
            chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/snap/bin/chromium",
            ]
        else:  # Windows
            chrome_paths = [
                "C:/Program Files/Google/Chrome/Application/chrome.exe",
                "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
            ]

        chrome_exe = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_exe = path
                break

        if not chrome_exe:
            self._log("Chrome not found, falling back to WeasyPrint", logging.WARNING)
            return False

        temp_html = None
        try:
            # If we don't have an HTML file, create a temp one
            if html_path and os.path.exists(html_path):
                source_html = html_path
            else:
                # Write content to temp file
                temp_html = tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.html',
                    delete=False,
                    encoding='utf-8'
                )
                temp_html.write(html_content)
                temp_html.close()
                source_html = temp_html.name

            # Build Chrome headless command for PDF generation
            # Using file:// protocol for local file access
            file_url = f"file://{os.path.abspath(source_html)}"

            cmd = [
                chrome_exe,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                f"--print-to-pdf={pdf_path}",
                "--no-pdf-header-footer",
                "--print-to-pdf-no-header",
                # A4 Landscape dimensions
                "--print-to-pdf-width=297mm",
                "--print-to-pdf-height=210mm",
                "--virtual-time-budget=3000",  # Wait for rendering
                file_url
            ]

            self._log(f"Running Chrome headless for PDF generation: {pdf_path}", logging.DEBUG)

            # Execute Chrome
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )

            if result.returncode != 0:
                self._log(f"Chrome PDF generation returned non-zero: {result.stderr}", logging.WARNING)
                # Don't return False yet - check if PDF was created anyway

            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                self._log(f"PDF generated successfully using Chrome Headless: {pdf_path}")
                return True
            else:
                self._log("Chrome did not produce PDF output", logging.WARNING)
                return False

        except subprocess.TimeoutExpired:
            self._log("Chrome PDF generation timed out", logging.WARNING)
            return False
        except Exception as e:
            self._log(f"Chrome PDF generation failed: {str(e)}", logging.WARNING)
            return False
        finally:
            # Clean up temp file
            if temp_html and os.path.exists(temp_html.name):
                try:
                    os.remove(temp_html.name)
                except Exception as e:
                    self._log(f"[CLEANUP] Failed to remove temp HTML file {temp_html.name}: {str(e)}", logging.DEBUG)

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
            try:
                rel_raw = float(reliability)
            except Exception:
                rel_raw = 1.0

            # Fix reliability display - signal generator returns 0-1 range
            if rel_raw <= 1.0:
                rel_norm = rel_raw  # Already normalized
            else:
                rel_norm = rel_raw / 100.0  # Convert percentage to 0-1
            if rel_norm < 0.0:
                rel_norm = 0.0
            if rel_norm > 1.0:
                rel_norm = 1.0
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
            html_content = html_content.replace('{{RELIABILITY}}', f"{rel_norm * 100:.2f}")
            html_content = html_content.replace('{{PRICE}}', f"{price:.4f}")
            html_content = html_content.replace('{{TIMESTAMP}}', timestamp_str)
            
            # Map signal types to proper CSS colors to avoid WeasyPrint warnings
            signal_color = '#4CAF50'  # Default green color
            if signal_type == 'SHORT':
                signal_color = '#F44336'  # Red for short
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
            try:
                rel_raw = float(reliability)
            except Exception:
                rel_raw = 1.0

            # Fix reliability display - signal generator returns 0-1 range
            if rel_raw <= 1.0:
                rel_norm = rel_raw  # Already normalized
            else:
                rel_norm = rel_raw / 100.0  # Convert percentage to 0-1
            if rel_norm < 0.0:
                rel_norm = 0.0
            if rel_norm > 1.0:
                rel_norm = 1.0
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
                    <p><strong>Reliability:</strong> {rel_norm * 100:.2f}%</p>
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
            
            # Process market interpretations using centralized InterpretationManager
            raw_interpretations = signal_data.get('market_interpretations', [])
            try:
                if raw_interpretations:
                    # Process interpretations through centralized manager
                    interpretation_set = self.interpretation_manager.process_interpretations(
                        raw_interpretations, 
                        f"fallback_pdf_{signal_data.get('symbol', 'UNKNOWN')}",
                        market_data=None,
                        timestamp=datetime.now()
                    )
                    
                    # Add standardized interpretations to HTML
                    for interpretation in interpretation_set.interpretations:
                        component_name = interpretation.component_name.replace('_', ' ').title()
                        severity_indicator = "🔴" if interpretation.severity.value == "critical" else "🟡" if interpretation.severity.value == "warning" else "🟢"
                        html += f"<li>{severity_indicator} <strong>{component_name}:</strong> {interpretation.interpretation_text}</li>\n"
                else:
                    html += "<li>No interpretations available</li>\n"
                    
            except Exception as e:
                self._log(f"Error processing interpretations in fallback HTML: {e}", level=logging.ERROR)
                # Fallback to original processing
                if raw_interpretations:
                    for interp in raw_interpretations:
                        if isinstance(interp, dict):
                            component = interp.get('display_name', interp.get('component', 'Unknown'))
                            interpretation = interp.get('interpretation', 'No interpretation')
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
        chart_mode: str = "light",
    ) -> Optional[str]:
        """
        Generate a simulated candlestick chart with buy/sell zones when no real OHLCV data is available.

        Args:
            symbol: Trading symbol
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            targets: List of target prices with format [{'price': float, 'name': str}]
            output_dir: Directory to save the chart
            chart_mode: "dark" or "light" (warm amber background)

        Returns:
            Path to the saved chart file or None if chart creation failed
        """
        self._log(
            f"Creating simulated chart for {symbol} with synthetic data",
            logging.WARNING,
        )

        try:
            # Always save charts to reports/charts for easy access
            chart_dir = os.path.join(os.getcwd(), 'reports', 'charts')

            # Use provided output_dir for temp work if needed
            if output_dir is None:
                output_dir = chart_dir  # Default to charts directory
                self._log(f"Using charts directory: {output_dir}")

            # Create directories if they don't exist
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(chart_dir, exist_ok=True)

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

            # Select chart style based on chart_mode
            chart_style = VIRTUOSO_LIGHT_MPF_STYLE if chart_mode == "light" else VIRTUOSO_MPF_STYLE

            # Prepare plot configuration with enhanced style
            kwargs = {
                "type": "candle",
                "style": chart_style,  # Use light or dark style based on chart_mode
                "figsize": (12, 9),  # Standard chart size for landscape PDF
                "title": f"{symbol} Price Chart ⚠️ SIMULATED DATA ⚠️",
                "panel_ratios": (4, 1),  # More space for price, less for volume
                "volume": True,
                "volume_panel": 1,
                "show_nontrading": False,
                "returnfig": True,
                "datetime_format": "%d %H:%M",
                "xrotation": 0,
                "tight_layout": False,
                "ylabel": "Price",
                "ylabel_lower": "Volume",
                "figratio": (12, 9),  # Match figsize ratio
                "scale_padding": {
                    "left": 0.12,      # Increased for Y-axis label visibility
                    "right": 0.3,
                    "top": 0.2,
                    "bottom": 0.2,
                },
                "warn_too_much_data": 1000,  # Suppress warning up to 1000 candles
            }

            # Define label colors based on chart_mode
            if chart_mode == "light":
                label_bg_color = '#fef3c7'      # Light amber background for labels
                label_border_alpha = 0.95
            else:
                label_bg_color = '#0c1a2b'      # Dark background for labels
                label_border_alpha = 0.9

            # Initialize VWAP availability flag
            has_vwap = False

            # Prepare additional plots for entry, stop loss, and targets
            plots = []

            # Ensure targets are always available - generate defaults if none provided
            if not targets or len(targets) == 0:
                signal_type = "BULLISH"  # Default assumption for simulated chart
                if stop_loss and entry_price:
                    if stop_loss > entry_price:
                        signal_type = "BEARISH"
                
                targets = self._generate_default_targets(
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    signal_type=signal_type
                )
                self._log(f"Generated {len(targets)} default targets for simulated chart", logging.INFO)

            # Entry price line (green)
            if entry_price is not None:
                plots.append(
                    mpf.make_addplot(
                        [entry_price] * len(df),
                        color="#10b981",
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
                        color='#3b82f6',  # Blue - swapped with entry price
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

            # CRITICAL: Resize all axes to make room for right-side annotations
            # mplfinance creates axes that span nearly the full figure width,
            # so we need to shrink them to leave space for Entry/Stop/Target labels
            for ax in axes:
                pos = ax.get_position()
                new_width = pos.width * 0.88  # Shrink to 88% to leave 12% for labels
                ax.set_position([pos.x0, pos.y0, new_width, pos.height])

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
                
                # Format to show more compact time format with month
                time_formatter = DateFormatter('%m/%d %H:%M')
                ax1.xaxis.set_major_formatter(time_formatter)
                
                # Rotate labels for better readability
                plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

                # Add custom legend for VWAP if available
                if has_vwap:
                    legend_elements = [
                        Line2D([0], [0], color='#3b82f6', lw=1.2, label='Daily VWAP (Simulated)'),
                        Line2D([0], [0], color='#8b5cf6', lw=1.2, label='Weekly VWAP (Simulated)')
                    ]
                    ax1.legend(handles=legend_elements, loc='upper left', fontsize=9, framealpha=0.7, facecolor=label_bg_color)

                # Add labels with improved styling
                entry_pos = None  # Initialize to prevent undefined variable error
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
                        
                    if entry_pos is not None:
                        ax1.annotate(
                            f"Entry: ${self._format_number(entry_price)}",
                            xy=(1.01, entry_pos),
                            xycoords=("axes fraction", "axes fraction"),
                            xytext=(1.05, entry_pos),
                            textcoords="axes fraction",
                            fontsize=9,
                            color="#3b82f6",
                            fontweight="bold",
                            annotation_clip=False,  # Allow annotation outside axes
                            bbox=dict(
                                facecolor=label_bg_color,
                                edgecolor="#3b82f6",
                                boxstyle="round,pad=0.3",
                                alpha=label_border_alpha,
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
                        annotation_clip=False,  # Allow annotation outside axes
                        bbox=dict(
                            facecolor=label_bg_color,
                            edgecolor="#ef4444",
                            boxstyle="round,pad=0.3",
                            alpha=label_border_alpha,
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
                                annotation_clip=False,  # Allow annotation outside axes
                                bbox=dict(
                                    facecolor=label_bg_color,
                                    edgecolor=color,
                                    boxstyle="round,pad=0.3",
                                    alpha=label_border_alpha,
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

                # Add multiple prominent watermarks for simulated charts
                self._add_simulated_watermarks(fig, ax1)

                # Adjust layout with specific settings instead of tight_layout
                plt.subplots_adjust(right=0.85, left=0.1, top=0.9, bottom=0.15)

                # Create output filename with more descriptive name
                from datetime import datetime
                timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                symbol_clean = symbol.replace('/', '_').replace(':', '').lower()

                # Determine signal type for filename
                signal_type = "neutral"
                if entry_price and stop_loss:
                    signal_type = "buy" if entry_price > stop_loss else "sell"

                filename = f"{symbol_clean}_{signal_type}_simulated_{timestamp_str}.png"
                output_file = os.path.join(output_dir, filename)

                # Add Virtuoso branding watermark (browser-quality PNG)
                if WATERMARK_AVAILABLE and add_watermark_to_figure is not None:
                    try:
                        add_watermark_to_figure(fig, position='bottom-right', zoom=0.5, padding=0.02)
                    except Exception as wm_err:
                        self._log(f"Watermark failed, using fallback: {wm_err}", logging.WARNING)
                        # Fallback to text watermark
                        fig.text(0.85, 0.02, 'VIRTUOSO',
                                fontsize=14, weight='bold', color='#ff9900',
                                ha='right', va='bottom',
                                transform=fig.transFigure,
                                bbox=dict(boxstyle='round,pad=0.4',
                                         facecolor='#1E1E1E',
                                         edgecolor='#ff9900',
                                         alpha=0.9))
                else:
                    # Fallback to text watermark if watermark utility unavailable
                    fig.text(0.85, 0.02, 'VIRTUOSO',
                            fontsize=14, weight='bold', color='#ff9900',
                            ha='right', va='bottom',
                            transform=fig.transFigure,
                            bbox=dict(boxstyle='round,pad=0.4',
                                     facecolor='#1E1E1E',
                                     edgecolor='#ff9900',
                                     alpha=0.9))

                # Save the figure - use pad_inches instead of bbox_inches='tight' to preserve watermark
                plt.savefig(output_file, dpi=150, pad_inches=0.2, facecolor=fig.get_facecolor())

                # Also save to reports/charts directory if not already there
                if output_dir != chart_dir:
                    chart_file = os.path.join(chart_dir, filename)
                    plt.savefig(chart_file, dpi=150, pad_inches=0.2, facecolor=fig.get_facecolor())
                    self._log(f"Simulated chart also saved to: {chart_file}")

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

    def _preprocess_html_for_pdf(self, html_path):
        """
        Preprocess HTML for better PDF compatibility by converting CSS variables to actual values.
        
        Args:
            html_path: Path to the HTML file
            
        Returns:
            Path to the preprocessed HTML file
        """
        try:
            self.logger.info(f"Preprocessing HTML for PDF compatibility: {html_path}")
            # Read the HTML content
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Convert CSS variables to actual values
            processed_content = self._convert_css_variables(html_content)
            self.logger.info("CSS variables converted to actual values for PDF compatibility")
            
            # Create a temporary file for the processed HTML
            import tempfile
            temp_fd, temp_path = tempfile.mkstemp(suffix='.html', prefix='processed_')
            
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as temp_file:
                temp_file.write(processed_content)
            
            return temp_path
            
        except Exception as e:
            self.logger.warning(f"Failed to preprocess HTML for PDF: {str(e)}")
            return html_path
    
    def _convert_css_variables(self, html_content):
        """
        Convert CSS variables to actual values for better PDF compatibility.
        
        Args:
            html_content: HTML content with CSS variables
            
        Returns:
            HTML content with CSS variables replaced by actual values
        """
        import re
        
        # Define the CSS variable mappings from the dark theme
        css_variables = {
            '--primary-bg': '#0c1a2b',
            '--secondary-bg': '#1e1e2e',
            '--border-color': '#1a2a40',
            '--text-primary': '#e0e0e0',
            '--text-secondary': '#aaaaaa',
            '--bullish': '#4caf50',
            '--bearish': '#f44336',
            '--neutral': '#ff9800',
            '--highlight': '#ffbf00',
            '--accent': '#3b82f6',
            '--card-bg': '#252535',
            '--hover-bg': '#2a2a3a',
        }
        
        # Replace CSS variable declarations in :root
        for var_name, var_value in css_variables.items():
            # Replace var() usage
            pattern = rf'var\({re.escape(var_name)}\)'
            html_content = re.sub(pattern, var_value, html_content)
        
        # Remove the :root variable declarations since they're not needed anymore
        root_pattern = r':root\s*\{[^}]*\}'
        html_content = re.sub(root_pattern, '', html_content, flags=re.DOTALL)
        
        # Simplify complex CSS that PDF generators struggle with
        simplifications = [
            # Remove complex animations and transitions
            (r'animation:[^;]+;', ''),
            (r'transition:[^;]+;', ''),
            (r'@keyframes[^}]+\}[^}]*\}', ''),
            # Simplify complex gradients
            (r'background:\s*linear-gradient\([^)]+\);', 'background: #252535;'),
            # Remove transform effects
            (r'transform:[^;]+;', ''),
            # Simplify box-shadows
            (r'box-shadow:[^;]+;', 'border: 1px solid #444;'),
            # Remove text-shadow
            (r'text-shadow:[^;]+;', ''),
        ]
        
        for pattern, replacement in simplifications:
            html_content = re.sub(pattern, replacement, html_content, flags=re.IGNORECASE)
        
        return html_content

    def _create_futures_premium_chart(
        self, futures_premium_data: Dict[str, Any], output_dir: str
    ) -> Optional[str]:
        """Create futures premium analysis chart showing contango/backwardation."""
        try:
            if not futures_premium_data or not isinstance(futures_premium_data, dict):
                self.logger.warning("No futures premium data available for chart")
                return None
            
            premiums = futures_premium_data.get('premiums', {})
            if not premiums:
                self.logger.warning("No premium data found in futures premium data")
                return None
            
            # Prepare data for visualization
            symbols = []
            premium_values = []
            colors = []
            
            for symbol, data in premiums.items():
                if isinstance(data, dict) and 'premium_value' in data:
                    symbols.append(symbol.replace('USDT', ''))  # Clean symbol names
                    premium_value = data['premium_value']
                    premium_values.append(premium_value)
                    
                    # Color coding: green for contango, red for backwardation
                    if premium_value > 2.0:
                        colors.append('#00ff00')  # Bright green for strong contango
                    elif premium_value > 0:
                        colors.append('#90EE90')  # Light green for contango
                    elif premium_value < -2.0:
                        colors.append('#ff0000')  # Bright red for strong backwardation
                    elif premium_value < 0:
                        colors.append('#FFA07A')  # Light red for backwardation
                    else:
                        colors.append('#808080')  # Gray for neutral
            
            if not symbols:
                self.logger.warning("No valid premium data found for chart")
                return None
            
            # Create the chart
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # Create horizontal bar chart
            bars = ax.barh(symbols, premium_values, color=colors, alpha=0.8, edgecolor='white', linewidth=0.5)
            
            # Customize the chart
            ax.set_xlabel('Premium (%)', fontsize=12, color='white')
            ax.set_ylabel('Symbols', fontsize=12, color='white')
            ax.set_title('Futures Premium Analysis - Contango vs Backwardation', 
                        fontsize=16, fontweight='bold', color='white', pad=20)
            
            # Add zero line
            ax.axvline(x=0, color='white', linestyle='-', alpha=0.3, linewidth=1)
            
            # Add grid
            ax.grid(True, alpha=0.3, color='white')
            
            # Add value labels on bars
            for i, (bar, value) in enumerate(zip(bars, premium_values)):
                if value >= 0:
                    ax.text(value + 0.1, bar.get_y() + bar.get_height()/2, 
                           f'{value:.2f}%', va='center', ha='left', 
                           color='white', fontsize=10, fontweight='bold')
                else:
                    ax.text(value - 0.1, bar.get_y() + bar.get_height()/2, 
                           f'{value:.2f}%', va='center', ha='right', 
                           color='white', fontsize=10, fontweight='bold')
            
            # Add legend
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor='#00ff00', label='Strong Contango (>2%)'),
                Patch(facecolor='#90EE90', label='Contango (0-2%)'),
                Patch(facecolor='#808080', label='Neutral (~0%)'),
                Patch(facecolor='#FFA07A', label='Backwardation (0 to -2%)'),
                Patch(facecolor='#ff0000', label='Strong Backwardation (<-2%)')
            ]
            ax.legend(handles=legend_elements, loc='upper right', 
                     facecolor='black', edgecolor='white', fontsize=10)
            
            # Add market status text
            market_status = futures_premium_data.get('market_status', 'NEUTRAL')
            average_premium = futures_premium_data.get('average_premium', 0.0)
            
            # Extract numeric value from percentage string if needed
            if isinstance(average_premium, str):
                try:
                    average_premium = float(average_premium.replace('%', ''))
                except (ValueError, TypeError):
                    average_premium = 0.0
            
            status_text = f"Market Status: {market_status}\nAverage Premium: {average_premium:.2f}%"
            ax.text(0.02, 0.98, status_text, transform=ax.transAxes, 
                   fontsize=12, verticalalignment='top', 
                   bbox=dict(boxstyle='round', facecolor='black', alpha=0.8, edgecolor='white'),
                   color='white', fontweight='bold')
            
            # Style the axes
            ax.tick_params(colors='white', labelsize=10)
            ax.spines['bottom'].set_color('white')
            ax.spines['top'].set_color('white')
            ax.spines['right'].set_color('white')
            ax.spines['left'].set_color('white')
            
            plt.tight_layout()
            
            # Save the chart
            chart_filename = f"futures_premium_analysis_{int(time.time())}.png"
            chart_path = os.path.join(output_dir, chart_filename)
            
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', 
                       facecolor='black', edgecolor='white')
            plt.close()
            
            self.logger.info(f"Futures premium chart saved to: {chart_path}")
            return chart_path
            
        except Exception as e:
            self.logger.error(f"Error creating futures premium chart: {str(e)}")
            return None

    def _create_term_structure_chart(
        self, futures_premium_data: Dict[str, Any], output_dir: str
    ) -> Optional[str]:
        """Create term structure chart showing quarterly futures basis."""
        try:
            if not futures_premium_data or not isinstance(futures_premium_data, dict):
                self.logger.warning("No futures premium data available for term structure chart")
                return None
            
            quarterly_futures = futures_premium_data.get('quarterly_futures', {})
            if not quarterly_futures:
                self.logger.warning("No quarterly futures data found")
                return None
            
            # Create the chart
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(14, 10))
            
            colors = ['#00ff00', '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57']
            color_idx = 0
            
            # Plot term structure for each symbol
            for symbol, contracts in quarterly_futures.items():
                if not isinstance(contracts, list) or len(contracts) < 2:
                    continue
                
                # Sort contracts by expiry
                sorted_contracts = sorted(contracts, key=lambda x: x.get('months_to_expiry', 12))
                
                months_to_expiry = []
                basis_values = []
                
                for contract in sorted_contracts:
                    months = contract.get('months_to_expiry', 0)
                    basis_str = contract.get('basis', '0%')
                    try:
                        basis = float(basis_str.replace('%', ''))
                        months_to_expiry.append(months)
                        basis_values.append(basis)
                    except (ValueError, AttributeError):
                        continue
                
                if len(months_to_expiry) >= 2:
                    # Plot the term structure
                    color = colors[color_idx % len(colors)]
                    ax.plot(months_to_expiry, basis_values, 
                           marker='o', linewidth=2, markersize=8, 
                           color=color, label=symbol.replace('USDT', ''), alpha=0.8)
                    
                    # Add value labels
                    for x, y in zip(months_to_expiry, basis_values):
                        ax.annotate(f'{y:.2f}%', (x, y), 
                                   textcoords="offset points", xytext=(0,10), 
                                   ha='center', fontsize=9, color='white', 
                                   fontweight='bold')
                    
                    color_idx += 1
            
            # Customize the chart
            ax.set_xlabel('Months to Expiry', fontsize=12, color='white')
            ax.set_ylabel('Basis (%)', fontsize=12, color='white')
            ax.set_title('Quarterly Futures Term Structure', 
                        fontsize=16, fontweight='bold', color='white', pad=20)
            
            # Add zero line
            ax.axhline(y=0, color='white', linestyle='-', alpha=0.3, linewidth=1)
            
            # Add grid
            ax.grid(True, alpha=0.3, color='white')
            
            # Add legend
            ax.legend(loc='upper left', facecolor='black', edgecolor='white', 
                     fontsize=10, framealpha=0.8)
            
            # Add interpretation text
            interpretation = "Term Structure Analysis:\n"
            interpretation += "• Upward sloping = Contango (normal)\n"
            interpretation += "• Downward sloping = Backwardation (supply shortage)\n"
            interpretation += "• Flat = Neutral market conditions"
            
            ax.text(0.98, 0.02, interpretation, transform=ax.transAxes, 
                   fontsize=10, verticalalignment='bottom', horizontalalignment='right',
                   bbox=dict(boxstyle='round', facecolor='black', alpha=0.8, edgecolor='white'),
                   color='white')
            
            # Style the axes
            ax.tick_params(colors='white', labelsize=10)
            ax.spines['bottom'].set_color('white')
            ax.spines['top'].set_color('white')
            ax.spines['right'].set_color('white')
            ax.spines['left'].set_color('white')
            
            plt.tight_layout()
            
            # Save the chart
            chart_filename = f"term_structure_analysis_{int(time.time())}.png"
            chart_path = os.path.join(output_dir, chart_filename)
            
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', 
                       facecolor='black', edgecolor='white')
            plt.close()
            
            self.logger.info(f"Term structure chart saved to: {chart_path}")
            return chart_path
            
        except Exception as e:
            self.logger.error(f"Error creating term structure chart: {str(e)}")
            return None

    def _generate_default_targets(self, entry_price: float, stop_loss: Optional[float] = None, signal_type: str = "BULLISH") -> List[Dict]:
        """Generate default targets when none are provided in signal data."""
        if not entry_price or entry_price <= 0:
            return []
            
        targets = []
        
        # Calculate risk distance for target calculation
        if stop_loss and stop_loss > 0:
            risk_distance = abs(entry_price - stop_loss)
        else:
            # Use default 3% risk if no stop loss provided
            risk_distance = entry_price * 0.03
            
        # Generate targets based on signal type
        if signal_type.upper() in ['BULLISH', 'LONG', 'BUY']:
            # Long position targets
            targets = [
                {
                    "name": "Target 1",
                    "price": entry_price + (risk_distance * 1.5),  # 1.5:1 R:R
                    "size": 50,
                    "percent": ((entry_price + (risk_distance * 1.5)) / entry_price - 1) * 100
                },
                {
                    "name": "Target 2", 
                    "price": entry_price + (risk_distance * 2.5),  # 2.5:1 R:R
                    "size": 30,
                    "percent": ((entry_price + (risk_distance * 2.5)) / entry_price - 1) * 100
                },
                {
                    "name": "Target 3",
                    "price": entry_price + (risk_distance * 4.0),  # 4:1 R:R
                    "size": 20,
                    "percent": ((entry_price + (risk_distance * 4.0)) / entry_price - 1) * 100
                }
            ]
        elif signal_type.upper() in ['BEARISH', 'SHORT', 'SELL']:
            # Short position targets
            targets = [
                {
                    "name": "Target 1",
                    "price": entry_price - (risk_distance * 1.5),  # 1.5:1 R:R
                    "size": 50,
                    "percent": ((entry_price - (risk_distance * 1.5)) / entry_price - 1) * 100
                },
                {
                    "name": "Target 2",
                    "price": entry_price - (risk_distance * 2.5),  # 2.5:1 R:R
                    "size": 30,
                    "percent": ((entry_price - (risk_distance * 2.5)) / entry_price - 1) * 100
                },
                {
                    "name": "Target 3",
                    "price": entry_price - (risk_distance * 4.0),  # 4:1 R:R
                    "size": 20,
                    "percent": ((entry_price - (risk_distance * 4.0)) / entry_price - 1) * 100
                }
            ]
        else:
            # Neutral - generate symmetric targets
            targets = [
                {
                    "name": "Target 1",
                    "price": entry_price + (risk_distance * 1.0),
                    "size": 50,
                    "percent": ((entry_price + (risk_distance * 1.0)) / entry_price - 1) * 100
                },
                {
                    "name": "Target 2",
                    "price": entry_price + (risk_distance * 2.0),
                    "size": 30,
                    "percent": ((entry_price + (risk_distance * 2.0)) / entry_price - 1) * 100
                }
            ]
            
        # Ensure all target prices are positive
        targets = [target for target in targets if target["price"] > 0]
        
        self._log(f"Generated {len(targets)} default targets for {signal_type} signal", logging.INFO)
        return targets

    def _add_simulated_watermarks(self, fig, ax):
        """
        Add prominent watermarks to simulated charts to clearly indicate synthetic data.
        
        Args:
            fig: Matplotlib figure object
            ax: Matplotlib axis object
        """
        # Large diagonal watermark across the entire chart
        fig.text(
            0.5,
            0.5,
            "SIMULATED DATA",
            fontsize=50,
            color="#ff6b6b",
            ha="center",
            va="center",
            alpha=0.25,
            rotation=30,
            weight="bold",
            transform=fig.transFigure,
        )
        
        # Secondary diagonal watermark for emphasis
        fig.text(
            0.5,
            0.5,
            "NOT REAL MARKET DATA",
            fontsize=24,
            color="#ffa500",
            ha="center",
            va="center",
            alpha=0.4,
            rotation=30,
            weight="bold",
            transform=fig.transFigure,
        )

        # Top-right corner indicator
        ax.text(
            0.98,
            0.98,
            "⚠️ SIMULATED",
            fontsize=14,
            color="#ff4444",
            ha="right",
            va="top",
            alpha=0.8,
            weight="bold",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="#1a1a1a",
                edgecolor="#ff4444",
                alpha=0.9
            ),
            transform=ax.transAxes,
        )

        # Bottom-left corner indicator
        ax.text(
            0.02,
            0.02,
            "⚠️ SYNTHETIC DATA",
            fontsize=12,
            color="#ff6b6b",
            ha="left",
            va="bottom",
            alpha=0.8,
            weight="bold",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="#1a1a1a",
                edgecolor="#ff6b6b",
                alpha=0.9
            ),
            transform=ax.transAxes,
        )

        # Top-left corner indicator
        ax.text(
            0.02,
            0.98,
            "DEMO ONLY",
            fontsize=12,
            color="#ffa500",
            ha="left",
            va="top",
            alpha=0.8,
            weight="bold",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="#1a1a1a",
                edgecolor="#ffa500",
                alpha=0.9
            ),
            transform=ax.transAxes,
        )
        
        # Add warning text in chart title area
        fig.text(
            0.5,
            0.95,
            "⚠️ WARNING: This chart contains simulated data for demonstration purposes only ⚠️",
            fontsize=12,
            color="#ff4444",
            ha="center",
            va="top",
            alpha=0.9,
            weight="bold",
            transform=fig.transFigure,
        )


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


# Alias for backward compatibility with code expecting PDFGenerator
PDFGenerator = ReportGenerator
