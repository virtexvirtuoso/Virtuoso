#!/usr/bin/env python3
"""
Bitcoin Beta 7-Day Analysis Report Generator

This module generates comprehensive Bitcoin beta analysis reports for the last 7 days,
showing how different cryptocurrencies correlate with Bitcoin across multiple timeframes.

Features:
- 7-day focused multi-timeframe beta analysis (4h, 1h, 15m, 5m)
- Date-specific analysis with clear time boundaries
- Dynamic symbol selection from current market monitoring
- Statistical measures relevant to short-term traders
- Professional PDF reports with charts including date ranges
- Weekly analysis perfect for trading reviews
"""

import os
import asyncio
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import traceback
from pathlib import Path
import base64
from io import BytesIO
import gc

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# SVG and image processing
try:
    from PIL import Image as PILImage, ImageDraw
    from cairosvg import svg2png
    PIL_AVAILABLE = True
    CAIRO_AVAILABLE = True
except ImportError:
    try:
        from PIL import Image as PILImage, ImageDraw
        PIL_AVAILABLE = True
        CAIRO_AVAILABLE = False
    except ImportError:
        PIL_AVAILABLE = False
        CAIRO_AVAILABLE = False
        PILImage = None
        ImageDraw = None
        svg2png = None

# HTML template engine
try:
    from jinja2 import Environment, FileSystemLoader, Template
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

# PDF generation from HTML
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False
    
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

# Import alpha detector for divergence analysis
from .bitcoin_beta_alpha_detector import BitcoinBetaAlphaDetector, AlphaOpportunity

logger = logging.getLogger(__name__)

class BitcoinBeta7DayReportConfig:
    """Configuration class for Bitcoin Beta 7-Day Report with customizable parameters."""
    
    def __init__(self, **kwargs):
        # Data fetching configuration
        self.symbols = kwargs.get('symbols', [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT',
            'SOL/USDT', 'DOGE/USDT', 'DOT/USDT', 'AVAX/USDT', 'MATIC/USDT'
        ])
        
        # Timeframe configuration
        self.timeframes = kwargs.get('timeframes', {
            'htf': '4h',    # High timeframe
            'mtf': '1h',    # Medium timeframe  
            'ltf': '15m',   # Low timeframe
            'base': '5m'    # Base timeframe
        })
        
        # Period configuration (number of candles to fetch)
        self.periods = kwargs.get('periods', {
            'htf': 42,      # 7 days * 6 periods per day
            'mtf': 168,     # 7 days * 24 periods per day
            'ltf': 672,     # 7 days * 96 periods per day
            'base': 2016    # 7 days * 288 periods per day
        })
        
        # Analysis configuration
        self.min_data_points = kwargs.get('min_data_points', 20)
        self.correlation_threshold = kwargs.get('correlation_threshold', 0.3)
        self.beta_significance_level = kwargs.get('beta_significance_level', 0.05)
        
        # Chart configuration
        self.chart_style = kwargs.get('chart_style', 'dark_background')
        self.figure_size = kwargs.get('figure_size', (20, 12))
        self.dpi = kwargs.get('dpi', 1200)
        self.color_palette = kwargs.get('color_palette', 'viridis')
        
        # Watermark configuration
        self.watermark_enabled = kwargs.get('watermark_enabled', True)
        self.watermark_opacity = kwargs.get('watermark_opacity', 0.15)
        self.watermark_size = kwargs.get('watermark_size', 0.3)
        self.watermark_position = kwargs.get('watermark_position', 'auto')
        
        # Output configuration
        self.output_formats = kwargs.get('output_formats', ['pdf', 'html', 'png'])
        self.png_high_res = kwargs.get('png_high_res', True)
        self.include_raw_data = kwargs.get('include_raw_data', False)
        
        # Performance configuration
        self.enable_caching = kwargs.get('enable_caching', True)
        self.cache_duration_hours = kwargs.get('cache_duration_hours', 1)
        self.parallel_processing = kwargs.get('parallel_processing', True)
        self.max_concurrent_requests = kwargs.get('max_concurrent_requests', 5)
        
        # Enhanced analytics configuration
        self.enable_enhanced_analytics = kwargs.get('enable_enhanced_analytics', True)
        self.volatility_analysis = kwargs.get('volatility_analysis', True)
        self.momentum_indicators = kwargs.get('momentum_indicators', True)
        self.market_regime_detection = kwargs.get('market_regime_detection', True)
        self.risk_metrics = kwargs.get('risk_metrics', True)
        self.performance_attribution = kwargs.get('performance_attribution', True)
        
        # Risk management configuration
        self.var_confidence_levels = kwargs.get('var_confidence_levels', [0.95, 0.99])
        self.volatility_window = kwargs.get('volatility_window', 20)
        self.correlation_window = kwargs.get('correlation_window', 30)
        
        # Report customization
        self.report_title = kwargs.get('report_title', 'Bitcoin Beta Analysis - 7-Day Report')
        self.include_executive_summary = kwargs.get('include_executive_summary', True)
        self.include_methodology = kwargs.get('include_methodology', True)
        self.include_disclaimers = kwargs.get('include_disclaimers', True)
        
        # Validation
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration parameters."""
        # Validate symbols
        if not self.symbols or not isinstance(self.symbols, list):
            raise ValueError("Symbols must be a non-empty list")
        
        if 'BTC/USDT' not in self.symbols:
            self.symbols.insert(0, 'BTC/USDT')  # Ensure BTC is included
        
        # Validate timeframes
        valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d']
        for tf in self.timeframes.values():
            if tf not in valid_timeframes:
                raise ValueError(f"Invalid timeframe: {tf}")
        
        # Validate periods
        for tf_name, period in self.periods.items():
            if tf_name in self.timeframes and period < 10:
                raise ValueError(f"Period for {tf_name} must be at least 10")
        
        # Validate thresholds
        if not 0 <= self.correlation_threshold <= 1:
            raise ValueError("Correlation threshold must be between 0 and 1")
        
        if not 0 < self.beta_significance_level < 1:
            raise ValueError("Beta significance level must be between 0 and 1")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            attr: getattr(self, attr) 
            for attr in dir(self) 
            if not attr.startswith('_') and not callable(getattr(self, attr))
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BitcoinBeta7DayReportConfig':
        """Create configuration from dictionary."""
        return cls(**config_dict)
    
    @classmethod
    def load_from_file(cls, config_path: str) -> 'BitcoinBeta7DayReportConfig':
        """Load configuration from JSON file."""
        import json
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)
    
    def save_to_file(self, config_path: str):
        """Save configuration to JSON file."""
        import json
        with open(config_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


class BitcoinBeta7DayReport:
    """
    Enhanced Bitcoin Beta 7-Day Report Generator with comprehensive optimizations.
    
    This class generates detailed Bitcoin beta analysis reports with:
    - High-performance parallel data fetching with caching
    - Advanced analytics including volatility, momentum, and regime analysis
    - Customizable configuration system
    - Multiple output formats (PDF, HTML, PNG)
    - Professional watermarked charts
    - Risk metrics and performance attribution
    """
    
    def __init__(self, exchange_manager, config: Optional[BitcoinBeta7DayReportConfig] = None):
        """
        Initialize the Bitcoin Beta 7-Day Report generator.
        
        Args:
            exchange_manager: Exchange manager instance
            config: Optional configuration object
        """
        self.exchange_manager = exchange_manager
        self.config = config or BitcoinBeta7DayReportConfig()
        
        # Use configuration values
        self.symbols = self.config.symbols
        self.timeframes = self.config.timeframes
        self.periods = self.config.periods
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Calculate date range (7 days)
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=7)
        
        # Create output directory
        self.output_dir = Path('exports/bitcoin_beta_7day_reports')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize enhanced analytics if enabled
        self.enhanced_analytics = None
        
        # Initialize alpha detector and other managers (optional)
        self.alpha_detector = None
        self.logger.debug("Alpha detector disabled for optimized demo")
        
        # Initialize optional managers
        self.top_symbols_manager = None
        self.alert_manager = None
        
        self.logger.info(f"Initialized Bitcoin Beta 7-Day Report Generator")
        self.logger.info(f"Analysis period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        self.logger.info(f"Symbols: {len(self.symbols)} assets")
        self.logger.info(f"Timeframes: {list(self.timeframes.keys())}")
        self.logger.info(f"Configuration: {len(self.config.to_dict())} parameters")

    def _setup_matplotlib(self):
        """Setup matplotlib for high-quality chart generation."""
        plt.style.use('dark_background')
        plt.rcParams.update({
            'figure.facecolor': '#0c1a2b',
            'axes.facecolor': '#0c1a2b',
            'savefig.facecolor': '#0c1a2b',
            'text.color': 'white',
            'axes.labelcolor': 'white',
            'xtick.color': 'white',
            'ytick.color': 'white',
            'axes.edgecolor': 'white',
            'figure.edgecolor': 'white',
            'axes.linewidth': 0.8,
            'grid.color': '#2a3f5f',
            'grid.alpha': 0.3,
            'font.size': 10,
            'axes.titlesize': 12,
            'axes.labelsize': 10,
            'xtick.labelsize': 9,
            'ytick.labelsize': 9,
            'legend.fontsize': 9,
            'figure.titlesize': 14
        })

    def _add_watermark(self, fig, ax=None, position='bottom-right', size=0.08, alpha=0.15):
        """
        Add optimized transparent amber trending-up Lucide icon watermark to matplotlib figure.
        
        Args:
            fig: Matplotlib figure object
            ax: Matplotlib axes object (optional, uses current axes if None)
            position: Position of watermark ('bottom-right', 'bottom-left', 'top-right', 'top-left', 'center', 'auto')
            size: Size of watermark relative to figure (0.0 to 1.0)
            alpha: Transparency level (0.0 to 1.0)
        """
        try:
            if not PIL_AVAILABLE:
                self.logger.debug("PIL not available - skipping watermark")
                return
            
            # Optimized SVG with better stroke width and cleaner paths
            trending_up_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 24 24" fill="none" stroke="#FFC107" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M16 7h6v6"/>
                <path d="m22 7-8.5 8.5-5-5L2 17"/>
            </svg>'''
            
            # Convert SVG to PNG with optimized settings
            if CAIRO_AVAILABLE:
                try:
                    # Higher resolution for better quality at small sizes
                    png_data = svg2png(bytestring=trending_up_svg.encode('utf-8'), 
                                     output_width=200, output_height=200,
                                     background_color='transparent')
                    watermark_img = PILImage.open(BytesIO(png_data)).convert("RGBA")
                except Exception as e:
                    self.logger.debug(f"SVG conversion failed, using fallback: {e}")
                    watermark_img = self._create_optimized_fallback_watermark()
            else:
                watermark_img = self._create_optimized_fallback_watermark()
            
            # Smart sizing based on figure dimensions and content
            fig_width_px = fig.get_figwidth() * fig.dpi
            fig_height_px = fig.get_figheight() * fig.dpi
            
            # Adaptive size calculation - smaller for busy charts, larger for simple ones
            base_size = min(fig_width_px, fig_height_px)
            
            # Adjust size based on chart type (detected from figure size ratio)
            aspect_ratio = fig_width_px / fig_height_px
            if aspect_ratio > 2.0:  # Wide charts (like multi-timeframe)
                size_multiplier = 0.8
            elif aspect_ratio < 0.8:  # Tall charts
                size_multiplier = 1.2
            else:  # Square-ish charts
                size_multiplier = 1.0
            
            watermark_size = int(base_size * size * size_multiplier)
            watermark_size = max(40, min(watermark_size, 150))  # Clamp between 40-150px
            
            # High-quality resize with anti-aliasing
            watermark_img = watermark_img.resize((watermark_size, watermark_size), 
                                                PILImage.Resampling.LANCZOS)
            
            # Optimized transparency application
            if watermark_img.mode != 'RGBA':
                watermark_img = watermark_img.convert('RGBA')
            
            # Smart alpha adjustment based on background
            adjusted_alpha = self._calculate_adaptive_alpha(alpha, fig)
            
            # Apply transparency more efficiently
            alpha_layer = watermark_img.split()[-1]
            alpha_array = np.array(alpha_layer, dtype=np.float32)
            alpha_array = (alpha_array * adjusted_alpha).astype(np.uint8)
            watermark_img.putalpha(PILImage.fromarray(alpha_array))
            
            # Smart positioning with collision detection
            optimal_position = self._find_optimal_position(fig, ax, position, size)
            
            # Add watermark with optimized settings
            self._apply_watermark_to_figure(fig, watermark_img, optimal_position)
            
        except Exception as e:
            self.logger.debug(f"Watermark application failed: {e}")
            # Fail silently to not interrupt report generation

    def _create_optimized_fallback_watermark(self):
        """Create an optimized fallback watermark with better visual quality."""
        try:
            # Create higher resolution fallback
            img = PILImage.new('RGBA', (200, 200), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Optimized amber color with better visibility
            amber_color = (255, 193, 7, 220)  # Slightly more opaque
            
            # Draw smoother trending arrow with anti-aliasing effect
            # Main trend line
            draw.line([(40, 160), (160, 40)], fill=amber_color, width=6)
            
            # Arrow head with better proportions
            draw.line([(160, 40), (140, 50)], fill=amber_color, width=6)
            draw.line([(160, 40), (150, 60)], fill=amber_color, width=6)
            
            # Additional trend indicators for better recognition
            draw.line([(50, 140), (80, 110), (110, 90), (140, 60)], fill=amber_color, width=4)
            
            # Small accent dots for visual interest
            for i, (x, y) in enumerate([(60, 130), (90, 100), (120, 80)]):
                dot_size = 4 - i
                draw.ellipse([x-dot_size, y-dot_size, x+dot_size, y+dot_size], fill=amber_color)
            
            return img
            
        except Exception as e:
            self.logger.debug(f"Fallback watermark creation failed: {e}")
            # Return minimal transparent image
            return PILImage.new('RGBA', (200, 200), (0, 0, 0, 0))

    def _calculate_adaptive_alpha(self, base_alpha, fig):
        """Calculate adaptive alpha based on figure background and content."""
        try:
            # Check figure background color
            bg_color = fig.get_facecolor()
            
            # For dark backgrounds, slightly increase alpha for better visibility
            if isinstance(bg_color, str) and bg_color.startswith('#'):
                # Convert hex to RGB
                bg_rgb = tuple(int(bg_color[i:i+2], 16) for i in (1, 3, 5))
                brightness = sum(bg_rgb) / (3 * 255)
                
                if brightness < 0.3:  # Dark background
                    return min(base_alpha * 1.3, 0.25)
                elif brightness > 0.7:  # Light background
                    return base_alpha * 0.8
            
            return base_alpha
            
        except Exception:
            return base_alpha

    def _find_optimal_position(self, fig, ax, requested_position, size):
        """Find optimal watermark position to avoid overlapping with important chart elements."""
        try:
            # Default positions with better spacing
            positions = {
                'bottom-right': (0.96 - size, 0.04),
                'bottom-left': (0.04, 0.04),
                'top-right': (0.96 - size, 0.96 - size),
                'top-left': (0.04, 0.96 - size),
                'center': (0.5 - size/2, 0.5 - size/2)
            }
            
            if requested_position == 'auto':
                # Smart positioning logic
                if ax is not None:
                    # Check if there are legends or text elements
                    legend = ax.get_legend()
                    if legend:
                        legend_pos = legend.get_window_extent()
                        # Avoid legend area - use opposite corner
                        return positions['bottom-left']
                
                # Default to bottom-right for auto
                return positions['bottom-right']
            
            return positions.get(requested_position, positions['bottom-right'])
            
        except Exception:
            return (0.96 - size, 0.04)  # Safe default

    def _apply_watermark_to_figure(self, fig, watermark_img, position):
        """Apply watermark to figure with optimized rendering."""
        try:
            from matplotlib.offsetbox import OffsetImage, AnnotationBbox
            
            # Convert PIL image to matplotlib format efficiently
            watermark_array = np.array(watermark_img)
            
            # Create OffsetImage with optimized settings
            imagebox = OffsetImage(watermark_array, zoom=1.0, alpha=1.0)
            
            # Create annotation box with better positioning
            x_pos, y_pos = position
            ab = AnnotationBbox(imagebox, (x_pos, y_pos), 
                              xycoords='figure fraction',
                              frameon=False,
                              box_alignment=(0, 0),
                              pad=0)
            
            # Add to figure with z-order control
            ab.set_zorder(1000)  # Ensure watermark is on top
            fig.add_artist(ab)
            
        except Exception as e:
            self.logger.debug(f"Watermark application to figure failed: {e}")

    async def generate_report(self) -> Optional[str]:
        """
        Generate a comprehensive Bitcoin beta 7-day analysis report.
        
        Returns:
            str: Path to generated PDF report, or None if failed
        """
        try:
            self.logger.info(f"Starting Bitcoin Beta 7-Day Analysis Report generation for {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
            
            # Get current dynamic symbols
            symbols = await self._get_dynamic_symbols()
            if not symbols:
                self.logger.error("No symbols available for analysis")
                return None
                
            self.logger.info(f"Analyzing {len(symbols)} symbols: {symbols}")
            
            # Fetch market data for all timeframes
            market_data = await self._fetch_all_market_data(symbols)
            if not market_data:
                self.logger.error("Failed to fetch market data")
                return None
                
            # Calculate beta statistics for all timeframes
            beta_analysis = self._calculate_multi_timeframe_beta(market_data)
            
            # Calculate enhanced analytics if enabled
            if self.config.enable_enhanced_analytics:
                self.logger.info("Calculating enhanced analytics...")
                self.enhanced_analytics = self._calculate_enhanced_analytics(market_data, beta_analysis)
            
            # Detect alpha generation opportunities
            alpha_opportunities = []
            if self.alpha_detector:
                try:
                    alpha_opportunities = self.alpha_detector.detect_alpha_opportunities(beta_analysis)
                except Exception as e:
                    self.logger.warning(f"Alpha detection failed: {e}")
                    alpha_opportunities = []
            
            # Send alpha opportunity alerts if alert manager is available and opportunities are found
            if self.alert_manager and alpha_opportunities:
                await self._send_alpha_opportunity_alerts(alpha_opportunities, market_data)
            
            # Generate charts
            chart_paths = await self._generate_charts(market_data, beta_analysis)
            
            # Create HTML report first (using the dark template)
            html_path = await self._create_html_report(beta_analysis, chart_paths, symbols, alpha_opportunities)
            
            # Generate PDF from the styled HTML
            pdf_path = None
            if html_path:
                pdf_path = await self._convert_html_to_pdf(html_path)
                
            # Fallback to ReportLab if HTML-to-PDF conversion fails
            if not pdf_path:
                self.logger.warning("HTML-to-PDF conversion failed, falling back to ReportLab")
                pdf_path = await self._create_pdf_report_fallback(beta_analysis, chart_paths, symbols, alpha_opportunities)
            
            if pdf_path:
                self.logger.info(f"Bitcoin Beta Report generated successfully: {pdf_path}")
                if html_path:
                    self.logger.info(f"HTML Bitcoin Beta Report generated: {html_path}")
                return pdf_path
            else:
                self.logger.error("Failed to generate PDF report")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating Bitcoin Beta Report: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None
            
    async def _get_dynamic_symbols(self) -> List[str]:
        """Get the current dynamic symbols being analyzed."""
        try:
            # Use configured symbols if top_symbols_manager is not available
            if not self.top_symbols_manager:
                self.logger.info("Using configured symbols (no top_symbols_manager)")
                return self.symbols
            
            # Get symbols from top symbols manager
            symbols = await self.top_symbols_manager.get_symbols()
            
            if not symbols:
                self.logger.warning("No dynamic symbols found, using configured symbols")
                return self.symbols
                
            # Ensure BTCUSDT is included (our reference asset)
            symbol_list = list(symbols) if isinstance(symbols, (list, tuple, set)) else [symbols]
            
            # Convert to list of strings if needed
            clean_symbols = []
            for symbol in symbol_list:
                if isinstance(symbol, dict) and 'symbol' in symbol:
                    clean_symbols.append(symbol['symbol'])
                elif isinstance(symbol, str):
                    clean_symbols.append(symbol)
                    
            # Ensure BTCUSDT is first (reference asset)
            if 'BTCUSDT' in clean_symbols:
                clean_symbols.remove('BTCUSDT')
                clean_symbols.insert(0, 'BTCUSDT')
            elif clean_symbols:
                # If no BTCUSDT, add it as reference
                clean_symbols.insert(0, 'BTCUSDT')
                
            return clean_symbols[:10]  # Limit to 10 symbols for readability
            
        except Exception as e:
            self.logger.error(f"Error getting dynamic symbols: {str(e)}")
            # Return configured symbols as fallback
            return self.symbols
            
    async def _fetch_all_market_data(self, symbols: List[str]) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Fetch OHLCV data for all symbols and timeframes with optimizations.
        
        Args:
            symbols: List of symbol strings to fetch
            
        Returns:
            Dict with structure: {symbol: {timeframe: DataFrame}}
        """
        try:
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            import hashlib
            import pickle
            
            # Create cache directory
            cache_dir = self.output_dir / 'cache'
            cache_dir.mkdir(exist_ok=True)
            
            # Generate cache key based on symbols, timeframes, and date range
            cache_key = hashlib.md5(
                f"{sorted(symbols)}_{self.timeframes}_{self.start_date}_{self.end_date}".encode()
            ).hexdigest()
            cache_file = cache_dir / f"market_data_{cache_key}.pkl"
            
            # Try to load from cache first (if less than 1 hour old)
            if cache_file.exists():
                cache_age = datetime.now().timestamp() - cache_file.stat().st_mtime
                if cache_age < 3600:  # 1 hour cache
                    try:
                        with open(cache_file, 'rb') as f:
                            cached_data = pickle.load(f)
                        self.logger.info(f"Loaded market data from cache (age: {cache_age/60:.1f} minutes)")
                        return cached_data
                    except Exception as e:
                        self.logger.warning(f"Cache load failed: {e}")
            
            market_data = {}
            
            # Handle both ExchangeManager and direct exchange instances
            if hasattr(self.exchange_manager, 'get_primary_exchange'):
                exchange = await self.exchange_manager.get_primary_exchange()
            else:
                exchange = self.exchange_manager
            
            if not exchange:
                self.logger.error("No primary exchange available")
                return {}
            
            # Parallel data fetching with semaphore for rate limiting
            semaphore = asyncio.Semaphore(5)  # Limit concurrent requests
            
            async def fetch_symbol_data(symbol: str) -> Tuple[str, Dict[str, pd.DataFrame]]:
                """Fetch data for a single symbol across all timeframes."""
                async with semaphore:
                    symbol_data = {}
                    
                    for tf_name, tf_interval in self.timeframes.items():
                        try:
                            limit = self.periods[tf_name]
                            
                            # Add retry logic
                            for attempt in range(3):
                                try:
                                    ohlcv = await exchange.fetch_ohlcv(
                                        symbol=symbol,
                                        timeframe=tf_interval,
                                        limit=limit
                                    )
                                    break
                                except Exception as e:
                                    if attempt == 2:
                                        raise e
                                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                            
                            if ohlcv and len(ohlcv) > 50:
                                # Optimized DataFrame creation
                                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                                df.set_index('timestamp', inplace=True)
                                
                                # Filter to exact 7-day range
                                df = df[(df.index >= self.start_date) & (df.index <= self.end_date)]
                                
                                if len(df) > 10:  # Minimum data requirement
                                    # Vectorized calculations
                                    df['returns'] = df['close'].pct_change()
                                    df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
                                    
                                    symbol_data[tf_name] = df
                                    self.logger.debug(f"Fetched {len(df)} candles for {symbol} {tf_name}")
                                else:
                                    self.logger.warning(f"Insufficient data after filtering for {symbol} {tf_name}")
                            else:
                                self.logger.warning(f"Insufficient raw data for {symbol} {tf_name}")
                                
                        except Exception as e:
                            self.logger.error(f"Error fetching {symbol} {tf_name}: {str(e)}")
                            continue
                    
                    # Small delay to respect rate limits
                    await asyncio.sleep(0.05)
                    return symbol, symbol_data
            
            # Execute parallel fetching
            self.logger.info(f"Fetching data for {len(symbols)} symbols in parallel...")
            tasks = [fetch_symbol_data(symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    self.logger.error(f"Symbol fetch failed: {result}")
                    continue
                symbol, symbol_data = result
                if symbol_data:
                    market_data[symbol] = symbol_data
            
            # Cache the results
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(market_data, f)
                self.logger.info(f"Cached market data for future use")
            except Exception as e:
                self.logger.warning(f"Failed to cache data: {e}")
            
            self.logger.info(f"Successfully fetched data for {len(market_data)} symbols")
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error fetching market data: {str(e)}")
            return {}

    def _calculate_multi_timeframe_beta(self, market_data: Dict[str, Dict[str, pd.DataFrame]]) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        Calculate beta statistics for all symbols across all timeframes.
        
        Args:
            market_data: Market data dictionary
            
        Returns:
            Dict with structure: {timeframe: {symbol: {stat_name: value}}}
        """
        try:
            beta_analysis = {}
            
            # Bitcoin is our reference asset
            btc_symbol = 'BTCUSDT'
            
            for tf_name in self.timeframes.keys():
                beta_analysis[tf_name] = {}
                
                # Get Bitcoin data for this timeframe
                if btc_symbol not in market_data or tf_name not in market_data[btc_symbol]:
                    self.logger.warning(f"No Bitcoin data for {tf_name}")
                    continue
                    
                btc_data = market_data[btc_symbol][tf_name]
                btc_returns = btc_data['returns'].dropna()
                
                if len(btc_returns) < 30:  # Minimum for statistical significance
                    self.logger.warning(f"Insufficient Bitcoin data for {tf_name}")
                    continue
                    
                for symbol in market_data.keys():
                    if symbol == btc_symbol:
                        # Bitcoin vs itself
                        beta_analysis[tf_name][symbol] = {
                            'beta': 1.0,
                            'correlation': 1.0,
                            'r_squared': 1.0,
                            'volatility_ratio': 1.0,
                            'alpha': 0.0,
                            'sharpe_ratio': self._calculate_sharpe_ratio(btc_returns),
                            'max_drawdown': self._calculate_max_drawdown(btc_data['close']),
                            'volatility': btc_returns.std() * np.sqrt(252),  # Annualized
                            'rolling_beta_30': 1.0
                        }
                        continue
                        
                    if tf_name not in market_data[symbol]:
                        continue
                        
                    asset_data = market_data[symbol][tf_name]
                    asset_returns = asset_data['returns'].dropna()
                    
                    # Align data (same time periods)
                    aligned_data = pd.concat([btc_returns, asset_returns], axis=1, join='inner')
                    aligned_data.columns = ['btc_returns', 'asset_returns']
                    aligned_data = aligned_data.dropna()
                    
                    if len(aligned_data) < 30:
                        continue
                        
                    btc_aligned = aligned_data['btc_returns']
                    asset_aligned = aligned_data['asset_returns']
                    
                    # Calculate beta and related statistics
                    covariance = np.cov(asset_aligned, btc_aligned)[0, 1]
                    btc_variance = np.var(btc_aligned)
                    
                    beta = covariance / btc_variance if btc_variance > 0 else 0
                    correlation = np.corrcoef(asset_aligned, btc_aligned)[0, 1]
                    r_squared = correlation ** 2
                    
                    # Volatility ratio
                    asset_vol = asset_aligned.std()
                    btc_vol = btc_aligned.std()
                    volatility_ratio = asset_vol / btc_vol if btc_vol > 0 else 0
                    
                    # Alpha (intercept from regression)
                    alpha = asset_aligned.mean() - beta * btc_aligned.mean()
                    
                    # Rolling beta (30-period)
                    rolling_beta = self._calculate_rolling_beta(aligned_data, window=30)
                    
                    beta_analysis[tf_name][symbol] = {
                        'beta': beta,
                        'correlation': correlation,
                        'r_squared': r_squared,
                        'volatility_ratio': volatility_ratio,
                        'alpha': alpha * 252,  # Annualized
                        'sharpe_ratio': self._calculate_sharpe_ratio(asset_aligned),
                        'max_drawdown': self._calculate_max_drawdown(asset_data['close']),
                        'volatility': asset_aligned.std() * np.sqrt(252),  # Annualized
                        'rolling_beta_30': rolling_beta
                    }
                    
            return beta_analysis
            
        except Exception as e:
            self.logger.error(f"Error calculating beta statistics: {str(e)}")
            return {}
            
    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        if returns.empty or returns.std() == 0:
            return 0.0
        excess_returns = returns.mean() * 252 - risk_free_rate  # Annualized
        return excess_returns / (returns.std() * np.sqrt(252))
        
    def _calculate_max_drawdown(self, prices: pd.Series) -> float:
        """Calculate maximum drawdown."""
        if prices.empty:
            return 0.0
        peak = prices.expanding().max()
        drawdown = (prices - peak) / peak
        return drawdown.min()
        
    def _calculate_rolling_beta(self, aligned_data: pd.DataFrame, window: int = 30) -> float:
        """Calculate the most recent rolling beta."""
        if len(aligned_data) < window:
            return 0.0
            
        recent_data = aligned_data.tail(window)
        btc_returns = recent_data['btc_returns']
        asset_returns = recent_data['asset_returns']
        
        covariance = np.cov(asset_returns, btc_returns)[0, 1]
        btc_variance = np.var(btc_returns)
        
        return covariance / btc_variance if btc_variance > 0 else 0.0
        
    async def _generate_charts(self, market_data: Dict[str, Dict[str, pd.DataFrame]], 
                              beta_analysis: Dict[str, Dict[str, Dict[str, float]]]) -> Dict[str, str]:
        """
        Generate all charts for the report.
        
        Args:
            market_data: Market data dictionary
            beta_analysis: Beta analysis results
            
        Returns:
            Dict mapping chart names to file paths
        """
        try:
            chart_paths = {}
            
            # Generate main performance comparison chart
            main_chart = await self._create_performance_chart(market_data, 'htf', beta_analysis)
            if main_chart:
                chart_paths['performance'] = main_chart
                
            # Generate beta comparison chart
            beta_chart = await self._create_beta_comparison_chart(beta_analysis)
            if beta_chart:
                chart_paths['beta_comparison'] = beta_chart
                
            # Generate correlation heatmap
            correlation_chart = await self._create_correlation_heatmap(beta_analysis)
            if correlation_chart:
                chart_paths['correlation'] = correlation_chart
                
            # Generate high-resolution PNG exports for each section
            await self._generate_high_res_png_exports(market_data, beta_analysis, chart_paths)
                
            return chart_paths
            
        except Exception as e:
            self.logger.error(f"Error generating charts: {str(e)}")
            return {}

    async def _generate_high_res_png_exports(self, market_data: Dict[str, Dict[str, pd.DataFrame]], 
                                           beta_analysis: Dict[str, Dict[str, Dict[str, float]]],
                                           chart_paths: Dict[str, str]) -> Dict[str, str]:
        """
        Generate high-resolution PNG exports for each report section with parallel processing.
        
        Args:
            market_data: Market data dictionary
            beta_analysis: Beta analysis results
            chart_paths: Existing chart paths
            
        Returns:
            Dict mapping section names to PNG file paths
        """
        try:
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            import gc
            
            timestamp = int(datetime.now().timestamp())
            png_exports = {}
            
            # Create PNG exports directory
            png_dir = self.output_dir / 'png_exports'
            png_dir.mkdir(exist_ok=True)
            
            self.logger.info("Generating high-resolution PNG exports with parallel processing...")
            
            # Define chart generation tasks
            chart_tasks = []
            
            # 1. Performance Charts for Each Timeframe (parallel)
            for tf_key, tf_display in [('htf', '4H'), ('mtf', '1H'), ('ltf', '15M'), ('base', '5M')]:
                if tf_key in self.timeframes:
                    output_path = png_dir / f'performance_{tf_display.lower()}_{timestamp}.png'
                    chart_tasks.append({
                        'name': f'performance_{tf_display.lower()}',
                        'func': self._create_performance_chart_png,
                        'args': (market_data, tf_key, beta_analysis, output_path),
                        'priority': 1  # High priority
                    })
            
            # 2. Other charts
            chart_tasks.extend([
                {
                    'name': 'beta_comparison',
                    'func': self._create_beta_comparison_png,
                    'args': (beta_analysis, png_dir / f'beta_comparison_{timestamp}.png'),
                    'priority': 2
                },
                {
                    'name': 'correlation_heatmap',
                    'func': self._create_correlation_heatmap_png,
                    'args': (beta_analysis, png_dir / f'correlation_heatmap_{timestamp}.png'),
                    'priority': 2
                },
                {
                    'name': 'individual_beta_analysis',
                    'func': self._create_individual_beta_analysis_png,
                    'args': (beta_analysis, png_dir / f'individual_beta_analysis_{timestamp}.png'),
                    'priority': 3
                },
                {
                    'name': 'summary_statistics',
                    'func': self._create_summary_statistics_png,
                    'args': (beta_analysis, png_dir / f'summary_statistics_{timestamp}.png'),
                    'priority': 3
                }
            ])
            
            # Sort by priority (higher priority first)
            chart_tasks.sort(key=lambda x: x['priority'])
            
            # Execute charts in batches to manage memory
            batch_size = 3  # Process 3 charts at a time
            
            for i in range(0, len(chart_tasks), batch_size):
                batch = chart_tasks[i:i + batch_size]
                
                # Create tasks for this batch
                batch_coroutines = []
                for task in batch:
                    batch_coroutines.append(self._execute_chart_task(task))
                
                # Execute batch in parallel
                batch_results = await asyncio.gather(*batch_coroutines, return_exceptions=True)
                
                # Process batch results
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Chart generation failed for {batch[j]['name']}: {result}")
                    elif result:
                        png_exports[batch[j]['name']] = result
                        
                # Force garbage collection between batches
                gc.collect()
                
                # Small delay between batches
                if i + batch_size < len(chart_tasks):
                    await asyncio.sleep(0.5)
            
            # Log the generated PNG exports with file sizes
            self.logger.info(f"Generated {len(png_exports)} high-resolution PNG exports:")
            total_size = 0
            for section, path in png_exports.items():
                try:
                    file_size = Path(path).stat().st_size / (1024 * 1024)  # MB
                    total_size += file_size
                    self.logger.info(f"  • {section}: {Path(path).name} ({file_size:.1f} MB)")
                except Exception:
                    self.logger.info(f"  • {section}: {Path(path).name}")
            
            self.logger.info(f"Total PNG export size: {total_size:.1f} MB")
            
            return png_exports
            
        except Exception as e:
            self.logger.error(f"Error generating PNG exports: {str(e)}")
            return {}
    
    async def _execute_chart_task(self, task: Dict) -> Optional[str]:
        """Execute a single chart generation task with error handling."""
        try:
            func = task['func']
            args = task['args']
            
            # Execute the chart generation function
            result = await func(*args)
            
            if result:
                self.logger.debug(f"Successfully generated {task['name']}")
                return result
            else:
                self.logger.warning(f"Failed to generate {task['name']}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error executing chart task {task['name']}: {str(e)}")
            return None

    async def _create_performance_chart_png(self, market_data: Dict[str, Dict[str, pd.DataFrame]], 
                                          timeframe: str, 
                                          beta_analysis: Dict[str, Dict[str, Dict[str, float]]],
                                          output_path: Path) -> Optional[str]:
        """Create high-resolution performance chart PNG for specific timeframe."""
        try:
            # Create ultra-high-resolution figure
            fig, ax = plt.subplots(figsize=(20, 12))
            fig.patch.set_facecolor('#0c1a2b')
            
            btc_symbol = 'BTCUSDT'
            
            # Get symbols and sort by beta
            symbols_to_plot = []
            for symbol in market_data.keys():
                if timeframe in market_data[symbol]:
                    symbols_to_plot.append(symbol)
            
            # Sort symbols by beta if available
            if beta_analysis and timeframe in beta_analysis:
                symbol_beta_pairs = []
                for symbol in symbols_to_plot:
                    if symbol == btc_symbol:
                        continue
                    if symbol in beta_analysis[timeframe]:
                        beta_value = beta_analysis[timeframe][symbol]['beta']
                        symbol_beta_pairs.append((symbol, beta_value))
                
                symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)
                sorted_symbols = [btc_symbol] + [pair[0] for pair in symbol_beta_pairs]
            else:
                sorted_symbols = symbols_to_plot
            
            # Plot symbols
            for symbol in sorted_symbols:
                if timeframe not in market_data[symbol]:
                    continue
                    
                df = market_data[symbol][timeframe]
                normalized_prices = (df['close'] / df['close'].iloc[0]) * 100
                color = self._get_symbol_color(symbol)
                linewidth = 6 if symbol == btc_symbol else 3
                alpha = 1.0 if symbol == btc_symbol else 0.85
                
                if beta_analysis and timeframe in beta_analysis and symbol in beta_analysis[timeframe]:
                    beta_value = beta_analysis[timeframe][symbol]['beta']
                    if symbol == btc_symbol:
                        label = f"{symbol} (β=1.000)"
                    else:
                        label = f"{symbol} (β={beta_value:.3f})"
                else:
                    label = symbol
                
                ax.plot(normalized_prices.index, normalized_prices.values, 
                       color=color, linewidth=linewidth, alpha=alpha, label=label)
            
            # Styling with 7-day date range
            timeframe_names = {'htf': '4H', 'mtf': '1H', 'ltf': '15M', 'base': '5M'}
            tf_display = timeframe_names.get(timeframe, timeframe.upper())
            date_range = f"{self.start_date.strftime('%m/%d')} - {self.end_date.strftime('%m/%d/%Y')}"
            
            ax.set_title(f'7-Day Normalized Price Performance - {tf_display} Timeframe\n{date_range} | Ranked by Beta Coefficient', 
                        fontweight='bold', pad=25, fontsize=20, color='white')
            ax.set_xlabel('Date', fontsize=16, color='white')
            ax.set_ylabel('Normalized Price (Start = 100)', fontsize=16, color='white')
            ax.grid(False)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=14)
            
            ax.set_facecolor('#0c1a2b')
            ax.tick_params(colors='white', labelsize=14)
            for spine in ax.spines.values():
                spine.set_color('white')
            
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # Add optimized watermark
            self._add_watermark(fig, ax, position='auto', size=0.05, alpha=0.12)
            
            # Save with ultra-high resolution
            plt.savefig(output_path, 
                       dpi=1200,  # Ultra-high DPI
                       bbox_inches='tight', 
                       facecolor='#0c1a2b',
                       edgecolor='none',
                       transparent=False,
                       pad_inches=0.3)
            plt.close()
            
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Error creating performance chart PNG: {str(e)}")
            return None

    async def _create_beta_comparison_png(self, beta_analysis: Dict[str, Dict[str, Dict[str, float]]],
                                        output_path: Path) -> Optional[str]:
        """Create high-resolution beta comparison PNG."""
        try:
            fig, axes = plt.subplots(2, 2, figsize=(24, 18))
            fig.patch.set_facecolor('#0c1a2b')
            axes = axes.flatten()
            
            timeframe_names = {'htf': '4H', 'mtf': '1H', 'ltf': '15M', 'base': '5M'}
            date_range = f"{self.start_date.strftime('%m/%d')} - {self.end_date.strftime('%m/%d/%Y')}"
            
            for i, (tf_name, tf_display) in enumerate(timeframe_names.items()):
                if tf_name not in beta_analysis:
                    continue
                    
                ax = axes[i]
                
                # Get symbols and their betas, excluding Bitcoin
                symbol_beta_pairs = []
                for symbol, stats in beta_analysis[tf_name].items():
                    if symbol == 'BTCUSDT':
                        continue
                    symbol_beta_pairs.append((symbol, stats['beta']))
                
                symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)
                
                if symbol_beta_pairs:
                    symbols = [pair[0].replace('USDT', '') for pair in symbol_beta_pairs]
                    betas = [pair[1] for pair in symbol_beta_pairs]
                    colors_list = [self._get_symbol_color(pair[0]) for pair in symbol_beta_pairs]
                    
                    bars = ax.bar(symbols, betas, color=colors_list, alpha=0.8, width=0.7)
                    
                    # Add value labels
                    for bar, beta in zip(bars, betas):
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                               f'{beta:.2f}', ha='center', va='bottom', fontsize=14, 
                               color='white', fontweight='bold')
                    
                    ax.axhline(y=1.0, color='#FF6600', linestyle='--', alpha=0.8, 
                              label='Bitcoin (β=1.0)', linewidth=3)
                    ax.set_title(f'7-Day Beta vs Bitcoin - {tf_display}\n{date_range} | Ranked by Beta Value', 
                                fontweight='bold', fontsize=16, color='white', pad=20)
                    ax.set_ylabel('Beta Coefficient', fontsize=14, color='white')
                    ax.set_ylim(0, max(max(betas) * 1.2, 1.5))
                    ax.grid(False)
                    
                    ax.set_facecolor('#0c1a2b')
                    ax.tick_params(colors='white', labelsize=12)
                    for spine in ax.spines.values():
                        spine.set_color('white')
                    plt.setp(ax.get_xticklabels(), rotation=45, color='white')
            
            plt.suptitle(f'7-Day Bitcoin Beta Analysis Across All Timeframes\n{date_range}', 
                        fontsize=22, fontweight='bold', color='white', y=0.98)
            plt.tight_layout()
            
            # Add optimized watermark
            self._add_watermark(fig, position='auto', size=0.04, alpha=0.12)
            
            plt.savefig(output_path, 
                       dpi=1200,
                       bbox_inches='tight', 
                       facecolor='#0c1a2b',
                       edgecolor='none',
                       transparent=False,
                       pad_inches=0.3)
            plt.close()
            
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Error creating beta comparison PNG: {str(e)}")
            return None

    async def _create_correlation_heatmap_png(self, beta_analysis: Dict[str, Dict[str, Dict[str, float]]],
                                            output_path: Path) -> Optional[str]:
        """Create high-resolution correlation heatmap PNG."""
        try:
            timeframes = ['htf', 'mtf', 'ltf', 'base'] 
            
            # Get symbols and sort by HTF beta
            symbols = set()
            for tf_data in beta_analysis.values():
                symbols.update(tf_data.keys())
            symbols.discard('BTCUSDT')
            
            if 'htf' in beta_analysis:
                symbol_beta_pairs = []
                for symbol in symbols:
                    if symbol in beta_analysis['htf']:
                        beta_value = beta_analysis['htf'][symbol]['beta']
                        symbol_beta_pairs.append((symbol, beta_value))
                
                symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)
                sorted_symbols = [pair[0] for pair in symbol_beta_pairs]
            else:
                sorted_symbols = sorted(list(symbols))
            
            # Create correlation matrix
            correlation_data = []
            for symbol in sorted_symbols:
                row = []
                for tf in timeframes:
                    if tf in beta_analysis and symbol in beta_analysis[tf]:
                        correlation = beta_analysis[tf][symbol]['correlation']
                        row.append(correlation)
                    else:
                        row.append(0.0)
                correlation_data.append(row)
                
            if not correlation_data:
                return None
                
            fig, ax = plt.subplots(figsize=(16, 12))
            fig.patch.set_facecolor('#0c1a2b')
            
            im = ax.imshow(correlation_data, cmap='RdYlBu_r', aspect='auto', vmin=-1, vmax=1, 
                          interpolation='nearest')
            
            ax.set_xticks(range(len(timeframes)))
            ax.set_xticklabels(['4H', '1H', '15M', '5M'])
            ax.set_yticks(range(len(sorted_symbols)))
            ax.set_yticklabels([s.replace('USDT', '') for s in sorted_symbols])
            
            # Add correlation values
            for i in range(len(sorted_symbols)):
                for j in range(len(timeframes)):
                    text = ax.text(j, i, f'{correlation_data[i][j]:.2f}',
                                 ha="center", va="center", 
                                 color="white" if abs(correlation_data[i][j]) > 0.5 else "black",
                                 fontsize=13, fontweight='bold')
            
            date_range = f"{self.start_date.strftime('%m/%d')} - {self.end_date.strftime('%m/%d/%Y')}"                     
            ax.set_title(f'7-Day Correlation with Bitcoin Across Timeframes\n{date_range} | Ranked by 4H Beta Values', 
                        fontweight='bold', pad=25, fontsize=18, color='white')
            ax.set_xlabel('Timeframe', fontsize=16, color='white')
            ax.set_ylabel('Assets (Ranked by Beta)', fontsize=16, color='white')
            
            ax.set_facecolor('#0c1a2b')
            ax.tick_params(colors='white', labelsize=14)
            
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label('Correlation Coefficient', rotation=270, labelpad=25, 
                          fontsize=14, color='white')
            cbar.ax.tick_params(colors='white', labelsize=12)
            
            plt.tight_layout()
            
            # Add optimized watermark
            self._add_watermark(fig, ax, position='auto', size=0.05, alpha=0.12)
            
            plt.savefig(output_path, 
                       dpi=1200,
                       bbox_inches='tight', 
                       facecolor='#0c1a2b',
                       edgecolor='none',
                       transparent=False,
                       pad_inches=0.3)
            plt.close()
            
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Error creating correlation heatmap PNG: {str(e)}")
            return None

    async def _create_individual_beta_analysis_png(self, beta_analysis: Dict[str, Dict[str, Dict[str, float]]],
                                                 output_path: Path) -> Optional[str]:
        """Create individual symbol beta analysis chart."""
        try:
            # Get all symbols (excluding Bitcoin)
            all_symbols = set()
            for tf_data in beta_analysis.values():
                all_symbols.update(tf_data.keys())
            all_symbols.discard('BTCUSDT')
            
            if not all_symbols:
                return None
            
            # Sort symbols by HTF beta
            if 'htf' in beta_analysis:
                symbol_beta_pairs = []
                for symbol in all_symbols:
                    if symbol in beta_analysis['htf']:
                        beta_value = beta_analysis['htf'][symbol]['beta']
                        symbol_beta_pairs.append((symbol, beta_value))
                
                symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)
                sorted_symbols = [pair[0] for pair in symbol_beta_pairs]
            else:
                sorted_symbols = sorted(list(all_symbols))
            
            # Create subplots for top symbols
            n_symbols = min(len(sorted_symbols), 12)  # Show top 12 symbols
            cols = 4
            rows = (n_symbols + cols - 1) // cols
            
            fig, axes = plt.subplots(rows, cols, figsize=(24, 6*rows))
            fig.patch.set_facecolor('#0c1a2b')
            
            if rows == 1:
                axes = [axes] if n_symbols == 1 else axes
            else:
                axes = axes.flatten()
            
            timeframes = ['htf', 'mtf', 'ltf', 'base']
            timeframe_names = ['4H', '1H', '15M', '5M']
            
            for i, symbol in enumerate(sorted_symbols[:n_symbols]):
                ax = axes[i]
                
                # Get beta values for this symbol across timeframes
                betas = []
                for tf in timeframes:
                    if tf in beta_analysis and symbol in beta_analysis[tf]:
                        betas.append(beta_analysis[tf][symbol]['beta'])
                    else:
                        betas.append(0.0)
                
                color = self._get_symbol_color(symbol)
                bars = ax.bar(timeframe_names, betas, color=color, alpha=0.8)
                
                # Add value labels
                for bar, beta in zip(bars, betas):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                           f'{beta:.2f}', ha='center', va='bottom', fontsize=11, 
                           color='white', fontweight='bold')
                
                ax.axhline(y=1.0, color='#FF6600', linestyle='--', alpha=0.7, linewidth=2)
                ax.set_title(f'{symbol.replace("USDT", "")}', fontweight='bold', fontsize=14, color='white')
                ax.set_ylabel('Beta', fontsize=12, color='white')
                ax.set_ylim(0, max(max(betas) * 1.2, 1.5))
                ax.grid(False)
                
                ax.set_facecolor('#0c1a2b')
                ax.tick_params(colors='white', labelsize=10)
                for spine in ax.spines.values():
                    spine.set_color('white')
            
            # Hide unused subplots
            for i in range(n_symbols, len(axes)):
                axes[i].set_visible(False)
            
            # Add main title with better spacing and date range
            date_range = f"{self.start_date.strftime('%m/%d')} - {self.end_date.strftime('%m/%d/%Y')}"
            plt.suptitle(f'7-Day Individual Symbol Beta Analysis\n{date_range} | Across All Timeframes', 
                        fontsize=22, fontweight='bold', color='white', y=0.95)
            
            # Adjust layout with more space for the title
            plt.tight_layout(rect=[0, 0, 1, 0.92])
            
            # Add optimized watermark
            self._add_watermark(fig, position='auto', size=0.04, alpha=0.12)
            
            plt.savefig(output_path, 
                       dpi=1200,
                       bbox_inches='tight', 
                       facecolor='#0c1a2b',
                       edgecolor='none',
                       transparent=False,
                       pad_inches=0.4)
            plt.close()
            
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Error creating individual beta analysis PNG: {str(e)}")
            return None

    async def _create_summary_statistics_png(self, beta_analysis: Dict[str, Dict[str, Dict[str, float]]],
                                           output_path: Path) -> Optional[str]:
        """Create summary statistics table as PNG."""
        try:
            # Prepare data for table
            symbols = set()
            for tf_data in beta_analysis.values():
                symbols.update(tf_data.keys())
            symbols.discard('BTCUSDT')
            
            if not symbols:
                return None
            
            # Sort symbols by HTF beta
            if 'htf' in beta_analysis:
                symbol_beta_pairs = []
                for symbol in symbols:
                    if symbol in beta_analysis['htf']:
                        beta_value = beta_analysis['htf'][symbol]['beta']
                        symbol_beta_pairs.append((symbol, beta_value))
                
                symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)
                sorted_symbols = [pair[0] for pair in symbol_beta_pairs]
            else:
                sorted_symbols = sorted(list(symbols))
            
            # Create table data for 7-day analysis
            table_data = []
            headers = ['Symbol', '4H Beta', '4H Corr', '1H Beta', '1H Corr', '15M Beta', '15M Corr', '5M Beta', '5M Corr']
            
            for symbol in sorted_symbols[:15]:  # Top 15 symbols
                row = [symbol.replace('USDT', '')]
                
                for tf in ['htf', 'mtf', 'ltf', 'base']:
                    if tf in beta_analysis and symbol in beta_analysis[tf]:
                        beta = beta_analysis[tf][symbol]['beta']
                        corr = beta_analysis[tf][symbol]['correlation']
                        row.extend([f'{beta:.3f}', f'{corr:.3f}'])
                    else:
                        row.extend(['N/A', 'N/A'])
                
                table_data.append(row)
            
            # Create figure for table
            fig, ax = plt.subplots(figsize=(20, 12))
            fig.patch.set_facecolor('#0c1a2b')
            ax.axis('tight')
            ax.axis('off')
            
            # Create table
            table = ax.table(cellText=table_data, colLabels=headers, 
                           cellLoc='center', loc='center')
            
            # Style the table
            table.auto_set_font_size(False)
            table.set_fontsize(12)
            table.scale(1.2, 2)
            
            # Header styling
            for i in range(len(headers)):
                table[(0, i)].set_facecolor('#FF6600')
                table[(0, i)].set_text_props(weight='bold', color='white')
                table[(0, i)].set_height(0.08)
            
            # Data cell styling
            for i in range(1, len(table_data) + 1):
                for j in range(len(headers)):
                    if j == 0:  # Symbol column
                        table[(i, j)].set_facecolor('#1a2332')
                        table[(i, j)].set_text_props(weight='bold', color='white')
                    else:
                        # Alternate row colors
                        if i % 2 == 0:
                            table[(i, j)].set_facecolor('#2a3442')
                        else:
                            table[(i, j)].set_facecolor('#1a2332')
                        table[(i, j)].set_text_props(color='white')
                    table[(i, j)].set_height(0.06)
            
            date_range = f"{self.start_date.strftime('%m/%d')} - {self.end_date.strftime('%m/%d/%Y')}"
            ax.set_title(f'7-Day Bitcoin Beta Analysis - Summary Statistics\n{date_range} | Ranked by 4H Beta Values', 
                        fontweight='bold', fontsize=18, color='white', pad=30)
            
            plt.tight_layout()
            
            # Add optimized watermark
            self._add_watermark(fig, ax, position='auto', size=0.05, alpha=0.12)
            
            plt.savefig(output_path, 
                       dpi=1200,
                       bbox_inches='tight', 
                       facecolor='#0c1a2b',
                       edgecolor='none',
                       transparent=False,
                       pad_inches=0.3)
            plt.close()
            
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Error creating summary statistics PNG: {str(e)}")
            return None

    async def _create_html_report(self, beta_analysis: Dict[str, Dict[str, Dict[str, float]]], 
                                 chart_paths: Dict[str, str], symbols: List[str], 
                                 alpha_opportunities: List[AlphaOpportunity] = None) -> Optional[str]:
        """Create comprehensive HTML report using dark template."""
        try:
            if not self.jinja_env:
                self.logger.warning("Jinja2 not available or template directory not found - skipping HTML report")
                return None
                
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            html_path = self.output_dir / f'bitcoin_beta_7day_report_{timestamp}.html'
            
            # Prepare template data with 7-day specifics
            template_data = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
                'symbols_count': len(symbols),
                'hostname': 'Virtuoso Trading System',
                'analysis_period': '7-Day Analysis',
                'start_date': self.start_date.strftime('%Y-%m-%d %H:%M'),
                'end_date': self.end_date.strftime('%Y-%m-%d %H:%M'),
                'date_range': f"{self.start_date.strftime('%m/%d')} - {self.end_date.strftime('%m/%d/%Y')}"
            }
            
            # Calculate summary statistics
            if 'htf' in beta_analysis:
                htf_betas = [stats['beta'] for symbol, stats in beta_analysis['htf'].items() if symbol != 'BTCUSDT']
                if htf_betas:
                    avg_beta = sum(htf_betas) / len(htf_betas)
                    template_data['avg_beta_htf'] = avg_beta
                    
                    # Beta gauge data
                    beta_gauge_width = min(avg_beta / 2.0 * 100, 100)  # Scale to 2.0 max
                    if avg_beta >= 1.2:
                        beta_gauge_color = '#F44336'  # Red for high beta
                    elif avg_beta <= 0.8:
                        beta_gauge_color = '#4CAF50'  # Green for low beta
                    else:
                        beta_gauge_color = '#FFC107'  # Yellow for medium beta
                        
                    template_data['beta_gauge_width'] = beta_gauge_width
                    template_data['beta_gauge_color'] = beta_gauge_color
                else:
                    template_data['avg_beta_htf'] = 1.0
                    template_data['beta_gauge_width'] = 50
                    template_data['beta_gauge_color'] = '#FFC107'
            else:
                template_data['avg_beta_htf'] = 1.0
                template_data['beta_gauge_width'] = 50
                template_data['beta_gauge_color'] = '#FFC107'
                
            # Alpha opportunities count
            template_data['alpha_count'] = len(alpha_opportunities) if alpha_opportunities else 0
            
            # Market interpretation for 7-day period
            if template_data['avg_beta_htf'] >= 1.3:
                template_data['market_interpretation'] = f"High 7-day correlation detected ({template_data['date_range']}). Portfolio shows amplified Bitcoin exposure with elevated short-term volatility risk."
            elif template_data['avg_beta_htf'] <= 0.7:
                template_data['market_interpretation'] = f"Low 7-day correlation detected ({template_data['date_range']}). Portfolio offers good short-term diversification benefits with reduced Bitcoin exposure."
            else:
                template_data['market_interpretation'] = f"Moderate 7-day correlation detected ({template_data['date_range']}). Portfolio shows balanced exposure to Bitcoin movements over the past week."
                
            # Chart paths (use absolute paths for PDF conversion compatibility)
            if chart_paths:
                for chart_type, path in chart_paths.items():
                    if path and os.path.exists(path):
                        # Use absolute path for better PDF conversion compatibility
                        abs_path = os.path.abspath(path)
                        template_data[f'{chart_type}_chart'] = f"file://{abs_path}"
                        
            # HTF data for table (sorted by beta)
            if 'htf' in beta_analysis:
                # Sort symbols by beta (highest to lowest)
                symbol_beta_pairs = []
                for symbol, stats in beta_analysis['htf'].items():
                    if symbol == 'BTCUSDT':
                        continue
                    symbol_beta_pairs.append((symbol, stats))
                
                # Sort by beta value (highest to lowest)
                symbol_beta_pairs.sort(key=lambda x: x[1]['beta'], reverse=True)
                
                htf_data = []
                for symbol, stats in symbol_beta_pairs:
                    htf_data.append({
                        'symbol': symbol.replace('USDT', ''),
                        'beta': stats['beta'],
                        'correlation': stats['correlation'],
                        'r_squared': stats['r_squared'],
                        'volatility_ratio': stats['volatility_ratio'],
                        'sharpe_ratio': stats['sharpe_ratio'],
                        'max_drawdown': stats['max_drawdown']
                    })
                template_data['htf_data'] = htf_data
                
            # Alpha opportunities data
            if alpha_opportunities:
                alpha_data = []
                for opp in alpha_opportunities[:5]:  # Top 5
                    alpha_data.append({
                        'symbol': opp.symbol.replace('USDT', ''),
                        'pattern': opp.divergence_type.value.replace('_', ' ').title(),
                        'insight': opp.trading_insight,
                        'confidence': opp.confidence,
                        'potential': opp.alpha_potential
                    })
                template_data['alpha_opportunities'] = alpha_data
                
            # Trading insights
            insights = self._generate_insights(beta_analysis, alpha_opportunities)
            template_data['insights'] = insights
            
            # Risk assessment data
            if 'htf' in beta_analysis and htf_betas:
                template_data['portfolio_beta'] = template_data['avg_beta_htf']
                template_data['diversification_score'] = 1.0 - (sum(abs(b - 1.0) for b in htf_betas) / len(htf_betas))
                template_data['btc_exposure'] = min(template_data['avg_beta_htf'] / 1.5, 1.0)
                
                # Risk level assessment
                if template_data['avg_beta_htf'] >= 1.4:
                    template_data['risk_level'] = 'HIGH'
                    template_data['risk_level_class'] = 'risk-high'
                elif template_data['avg_beta_htf'] <= 0.6:
                    template_data['risk_level'] = 'LOW'
                    template_data['risk_level_class'] = 'risk-low'
                else:
                    template_data['risk_level'] = 'MEDIUM'
                    template_data['risk_level_class'] = 'risk-medium'
            else:
                template_data['portfolio_beta'] = 1.0
                template_data['diversification_score'] = 0.5
                template_data['btc_exposure'] = 0.5
                template_data['risk_level'] = 'MEDIUM'
                template_data['risk_level_class'] = 'risk-medium'
                
            # Load and render template
            template = self.jinja_env.get_template('bitcoin_beta_dark.html')
            html_content = template.render(**template_data)
            
            # Write HTML file
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            self.logger.info(f"HTML report created: {html_path}")
            return str(html_path)
            
        except Exception as e:
            self.logger.error(f"Error creating HTML report: {str(e)}")
            return None
        
    def schedule_report(self):
        """Schedule the report to run every 6 hours starting at 00:00 UTC."""
        # This would be implemented with asyncio or a task scheduler
        # For now, returning the method to call
        return self.generate_report

    async def _send_alpha_opportunity_alerts(self, alpha_opportunities: List[AlphaOpportunity], market_data: Dict[str, Dict[str, pd.DataFrame]]):
        """
        Send individual alerts for detected alpha opportunities.
        
        Args:
            alpha_opportunities: List of detected alpha opportunities
            market_data: Market data for current price context
        """
        try:
            # Get configuration for alert thresholds
            alpha_config = self.config.get('bitcoin_beta_analysis', {}).get('alpha_detection', {})
            min_confidence = alpha_config.get('alerts', {}).get('min_confidence', 0.70)
            
            self.logger.info(f"Processing {len(alpha_opportunities)} alpha opportunities for alerts")
            
            sent_alerts = 0
            for opportunity in alpha_opportunities:
                try:
                    # Only send alerts for high-confidence opportunities
                    if opportunity.confidence < min_confidence:
                        self.logger.debug(f"Skipping {opportunity.symbol} alpha alert: confidence {opportunity.confidence:.1%} below threshold {min_confidence:.1%}")
                        continue
                    
                    # Get current price for context
                    current_price = None
                    if opportunity.symbol in market_data:
                        # Try to get the most recent price from base timeframe (1m)
                        for timeframe in ['base', 'ltf', 'mtf', 'htf']:
                            if timeframe in market_data[opportunity.symbol]:
                                df = market_data[opportunity.symbol][timeframe]
                                if not df.empty:
                                    current_price = float(df['close'].iloc[-1])
                                    break
                    
                    # Create market data context
                    market_context = {
                        'asset': {'price': current_price} if current_price else {},
                        'bitcoin': {},
                        'timeframe_signals': opportunity.timeframe_signals,
                        'analysis_timestamp': datetime.now().isoformat()
                    }
                    
                    # Get Bitcoin price for context if available
                    if 'BTCUSDT' in market_data:
                        for timeframe in ['base', 'ltf', 'mtf', 'htf']:
                            if timeframe in market_data['BTCUSDT']:
                                btc_df = market_data['BTCUSDT'][timeframe]
                                if not btc_df.empty:
                                    market_context['bitcoin']['price'] = float(btc_df['close'].iloc[-1])
                                    break
                    
                    # Send the alpha opportunity alert
                    await self.alert_manager.send_alpha_opportunity_alert(
                        symbol=opportunity.symbol,
                        alpha_estimate=opportunity.alpha_potential,
                        confidence_score=opportunity.confidence,
                        divergence_type=opportunity.divergence_type.value,  # Convert enum to string
                        risk_level=opportunity.risk_level,
                        trading_insight=opportunity.trading_insight,
                        market_data=market_context
                    )
                    
                    sent_alerts += 1
                    self.logger.info(f"Sent alpha opportunity alert for {opportunity.symbol}: {opportunity.alpha_potential:.1%} alpha, {opportunity.confidence:.1%} confidence")
                    
                    # Small delay between alerts to avoid rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    self.logger.error(f"Error sending alpha alert for {opportunity.symbol}: {str(e)}")
                    continue
            
            self.logger.info(f"Successfully sent {sent_alerts}/{len(alpha_opportunities)} alpha opportunity alerts")
            
        except Exception as e:
            self.logger.error(f"Error in _send_alpha_opportunity_alerts: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _create_performance_chart(self, market_data: Dict[str, Dict[str, pd.DataFrame]], 
                                       timeframe: str = 'htf', 
                                       beta_analysis: Dict[str, Dict[str, Dict[str, float]]] = None) -> Optional[str]:
        """Create normalized performance comparison chart with beta-ranked legend."""
        try:
            # Create high-resolution figure with optimized size
            fig, ax = plt.subplots(figsize=(16, 10))
            fig.patch.set_facecolor('#0c1a2b')  # Set figure background
            
            btc_symbol = 'BTCUSDT'
            
            # Get symbols and sort by beta if beta_analysis is available
            symbols_to_plot = []
            for symbol in market_data.keys():
                if timeframe in market_data[symbol]:
                    symbols_to_plot.append(symbol)
            
            # Sort symbols by beta (highest to lowest) if beta analysis is available
            if beta_analysis and timeframe in beta_analysis:
                # Create list of (symbol, beta) tuples, excluding Bitcoin
                symbol_beta_pairs = []
                for symbol in symbols_to_plot:
                    if symbol == btc_symbol:
                        continue  # We'll add Bitcoin first
                    if symbol in beta_analysis[timeframe]:
                        beta_value = beta_analysis[timeframe][symbol]['beta']
                        symbol_beta_pairs.append((symbol, beta_value))
                
                # Sort by beta (highest to lowest)
                symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)
                
                # Create final sorted symbol list: Bitcoin first, then sorted by beta
                sorted_symbols = [btc_symbol] + [pair[0] for pair in symbol_beta_pairs]
            else:
                # No beta analysis available, use original order
                sorted_symbols = symbols_to_plot
            
            # Plot symbols in beta-ranked order
            for symbol in sorted_symbols:
                if timeframe not in market_data[symbol]:
                    continue
                    
                df = market_data[symbol][timeframe]
                
                # Normalize to start at 100
                normalized_prices = (df['close'] / df['close'].iloc[0]) * 100
                
                # Get color for symbol
                color = self._get_symbol_color(symbol)
                
                # Plot with much thicker line for Bitcoin to make it stand out
                linewidth = 5 if symbol == btc_symbol else 2
                alpha = 1.0 if symbol == btc_symbol else 0.8
                
                # Create label with beta value if available
                if beta_analysis and timeframe in beta_analysis and symbol in beta_analysis[timeframe]:
                    beta_value = beta_analysis[timeframe][symbol]['beta']
                    if symbol == btc_symbol:
                        label = f"{symbol} (β=1.000)"
                    else:
                        label = f"{symbol} (β={beta_value:.3f})"
                else:
                    label = symbol
                
                ax.plot(normalized_prices.index, normalized_prices.values, 
                       color=color, linewidth=linewidth, alpha=alpha, label=label)
                
            date_range = f"{self.start_date.strftime('%m/%d')} - {self.end_date.strftime('%m/%d/%Y')}"
            timeframe_display = {'htf': '4H', 'mtf': '1H', 'ltf': '15M', 'base': '5M'}.get(timeframe, timeframe.upper())
            ax.set_title(f'7-Day Normalized Price Performance - {timeframe_display} Timeframe\n{date_range} | Ranked by Beta Coefficient', 
                        fontweight='bold', pad=20, fontsize=16, color='white')
            ax.set_xlabel('Date', fontsize=14, color='white')
            ax.set_ylabel('Normalized Price (Start = 100)', fontsize=14, color='white')
            # Remove grid lines for cleaner appearance
            ax.grid(False)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=12)
            
            # Set dark background and improve text visibility
            ax.set_facecolor('#0c1a2b')
            ax.tick_params(colors='white', labelsize=12)
            ax.spines['bottom'].set_color('white')
            ax.spines['top'].set_color('white')
            ax.spines['right'].set_color('white')
            ax.spines['left'].set_color('white')
            
            # Format x-axis dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # Add optimized watermark
            self._add_watermark(fig, ax, position='auto', size=0.06, alpha=0.15)
            
            # Save chart with ultra-high resolution and quality
            chart_path = self.output_dir / f'performance_chart_{int(datetime.now().timestamp())}.png'
            plt.savefig(chart_path, 
                       dpi=600,  # Ultra-high DPI for crisp resolution
                       bbox_inches='tight', 
                       facecolor='#0c1a2b',
                       edgecolor='none',
                       transparent=False,
                       pad_inches=0.2)
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            self.logger.error(f"Error creating performance chart: {str(e)}")
            return None

    async def _create_beta_comparison_chart(self, beta_analysis: Dict[str, Dict[str, Dict[str, float]]]) -> Optional[str]:
        """Create beta comparison chart across timeframes with beta-ranked symbols."""
        try:
            # Create high-resolution figure with optimized size
            fig, axes = plt.subplots(2, 2, figsize=(20, 16))
            fig.patch.set_facecolor('#0c1a2b')  # Set figure background
            axes = axes.flatten()
            
            timeframe_names = {'htf': '4H', 'mtf': '1H', 'ltf': '15M', 'base': '5M'}
            date_range = f"{self.start_date.strftime('%m/%d')} - {self.end_date.strftime('%m/%d/%Y')}"
            
            for i, (tf_name, tf_display) in enumerate(timeframe_names.items()):
                if tf_name not in beta_analysis:
                    continue
                    
                ax = axes[i]
                
                # Get symbols and their betas, excluding Bitcoin
                symbol_beta_pairs = []
                for symbol, stats in beta_analysis[tf_name].items():
                    if symbol == 'BTCUSDT':  # Skip Bitcoin (always beta = 1)
                        continue
                    symbol_beta_pairs.append((symbol, stats['beta']))
                
                # Sort by beta (highest to lowest)
                symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)
                
                if symbol_beta_pairs:
                    symbols = [pair[0].replace('USDT', '') for pair in symbol_beta_pairs]
                    betas = [pair[1] for pair in symbol_beta_pairs]
                    colors_list = [self._get_symbol_color(pair[0]) for pair in symbol_beta_pairs]
                    
                    bars = ax.bar(symbols, betas, color=colors_list, alpha=0.8)
                    
                    # Add value labels on bars with better formatting
                    for bar, beta in zip(bars, betas):
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                               f'{beta:.2f}', ha='center', va='bottom', fontsize=12, 
                               color='white', fontweight='bold')
                    
                    ax.axhline(y=1.0, color='#FF6600', linestyle='--', alpha=0.7, 
                              label='Bitcoin (β=1.0)', linewidth=2)
                    ax.set_title(f'7-Day Beta vs Bitcoin - {tf_display}\n{date_range} | Ranked by Beta Value', 
                                fontweight='bold', fontsize=14, color='white', pad=15)
                    ax.set_ylabel('Beta Coefficient', fontsize=12, color='white')
                    ax.set_ylim(0, max(max(betas) * 1.2, 1.5))
                    # Remove grid lines for cleaner appearance
                    ax.grid(False)
                    
                    # Improve styling
                    ax.set_facecolor('#0c1a2b')
                    ax.tick_params(colors='white', labelsize=10)
                    ax.spines['bottom'].set_color('white')
                    ax.spines['top'].set_color('white')
                    ax.spines['right'].set_color('white')
                    ax.spines['left'].set_color('white')
                    plt.setp(ax.get_xticklabels(), rotation=45, color='white')
            
            plt.tight_layout()
            
            # Add optimized watermark
            self._add_watermark(fig, position='auto', size=0.05, alpha=0.15)
            
            # Save chart with ultra-high resolution and quality
            chart_path = self.output_dir / f'beta_comparison_{int(datetime.now().timestamp())}.png'
            plt.savefig(chart_path, 
                       dpi=600,  # Ultra-high DPI for crisp resolution
                       bbox_inches='tight', 
                       facecolor='#0c1a2b',
                       edgecolor='none',
                       transparent=False,
                       pad_inches=0.2)
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            self.logger.error(f"Error creating beta comparison chart: {str(e)}")
            return None

    async def _create_correlation_heatmap(self, beta_analysis: Dict[str, Dict[str, Dict[str, float]]]) -> Optional[str]:
        """Create correlation heatmap showing relationships across timeframes with beta-ranked symbols."""
        try:
            # Prepare data for heatmap
            timeframes = ['htf', 'mtf', 'ltf', 'base'] 
            
            # Get symbols and sort by HTF beta (excluding Bitcoin)
            symbols = set()
            for tf_data in beta_analysis.values():
                symbols.update(tf_data.keys())
            symbols.discard('BTCUSDT')  # Remove Bitcoin
            
            # Sort symbols by HTF beta (highest to lowest) if available
            if 'htf' in beta_analysis:
                symbol_beta_pairs = []
                for symbol in symbols:
                    if symbol in beta_analysis['htf']:
                        beta_value = beta_analysis['htf'][symbol]['beta']
                        symbol_beta_pairs.append((symbol, beta_value))
                
                # Sort by beta (highest to lowest)
                symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)
                sorted_symbols = [pair[0] for pair in symbol_beta_pairs]
            else:
                sorted_symbols = sorted(list(symbols))
            
            # Create correlation matrix
            correlation_data = []
            for symbol in sorted_symbols:
                row = []
                for tf in timeframes:
                    if tf in beta_analysis and symbol in beta_analysis[tf]:
                        correlation = beta_analysis[tf][symbol]['correlation']
                        row.append(correlation)
                    else:
                        row.append(0.0)
                correlation_data.append(row)
                
            if not correlation_data:
                return None
                
            # Create high-resolution heatmap
            fig, ax = plt.subplots(figsize=(14, 10))
            fig.patch.set_facecolor('#0c1a2b')  # Set figure background
            
            im = ax.imshow(correlation_data, cmap='RdYlBu_r', aspect='auto', vmin=-1, vmax=1, 
                          interpolation='nearest')  # Crisp pixel rendering
            
            # Set ticks and labels
            ax.set_xticks(range(len(timeframes)))
            ax.set_xticklabels(['4H', '1H', '15M', '5M'])
            ax.set_yticks(range(len(sorted_symbols)))
            ax.set_yticklabels([s.replace('USDT', '') for s in sorted_symbols])
            
            # Add correlation values with better formatting
            for i in range(len(sorted_symbols)):
                for j in range(len(timeframes)):
                    text = ax.text(j, i, f'{correlation_data[i][j]:.2f}',
                                 ha="center", va="center", 
                                 color="white" if abs(correlation_data[i][j]) > 0.5 else "black",
                                 fontsize=11, fontweight='bold')
            
            date_range = f"{self.start_date.strftime('%m/%d')} - {self.end_date.strftime('%m/%d/%Y')}"                     
            ax.set_title(f'7-Day Correlation with Bitcoin Across Timeframes\n{date_range} | Ranked by 4H Beta Values', 
                        fontweight='bold', pad=20, fontsize=16, color='white')
            ax.set_xlabel('Timeframe', fontsize=14, color='white')
            ax.set_ylabel('Assets (Ranked by Beta)', fontsize=14, color='white')
            
            # Improve styling
            ax.set_facecolor('#0c1a2b')
            ax.tick_params(colors='white', labelsize=12)
            
            # Add colorbar with better styling
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label('Correlation Coefficient', rotation=270, labelpad=20, 
                          fontsize=12, color='white')
            cbar.ax.tick_params(colors='white', labelsize=10)
            
            plt.tight_layout()
            
            # Add optimized watermark
            self._add_watermark(fig, ax, position='auto', size=0.06, alpha=0.15)
            
            # Save chart with ultra-high resolution and quality
            chart_path = self.output_dir / f'correlation_heatmap_{int(datetime.now().timestamp())}.png'
            plt.savefig(chart_path, 
                       dpi=600,  # Ultra-high DPI for crisp resolution
                       bbox_inches='tight', 
                       facecolor='#0c1a2b',
                       edgecolor='none',
                       transparent=False,
                       pad_inches=0.2)
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            self.logger.error(f"Error creating correlation heatmap: {str(e)}")
            return None

    def _get_symbol_color(self, symbol: str) -> str:
        """Get color for a symbol with intelligent fallback."""
        # Clean symbol (remove USDT, BUSD, etc.)
        symbol_base = symbol.replace('USDT', '').replace('BUSD', '').replace('USDC', '').lower()
        
        # Handle special cases for tokens with numbers
        if symbol_base.startswith('1000'):
            symbol_base = symbol_base[4:]  # Remove '1000' prefix
            
        # Try to get color from our expanded palette
        if symbol_base in self.colors:
            return self.colors[symbol_base]
            
        # Fallback to gradient colors based on hash
        gradient_colors = [
            '#FF6B35', '#F7931E', '#FFD23F', '#06FFA5', '#4ECDC4',
            '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#FFB6C1',
            '#20B2AA', '#87CEEB', '#DEB887', '#5F9EA0', '#D2691E',
            '#FF69B4', '#32CD32', '#FF4500', '#1E90FF', '#FFD700',
            '#FF1493', '#00CED1', '#FF8C00', '#9370DB', '#00FA9A'
        ]
        
        # Use hash of symbol to consistently assign colors
        color_index = hash(symbol_base) % len(gradient_colors)
        return gradient_colors[color_index]

    async def _convert_html_to_pdf(self, html_path: str) -> Optional[str]:
        """
        Convert the styled HTML report to PDF using the dark theme.
        
        Args:
            html_path: Path to the HTML file to convert
            
        Returns:
            str: Path to generated PDF, or None if failed
        """
        try:
            # Generate PDF filename based on HTML filename
            html_file = Path(html_path)
            pdf_path = html_file.with_suffix('.pdf')
            
            self.logger.info(f"Converting HTML to PDF: {html_path} -> {pdf_path}")
            
            # Try pdfkit first (wkhtmltopdf)
            if PDFKIT_AVAILABLE:
                try:
                    options = {
                        'page-size': 'A4',
                        'margin-top': '1cm',
                        'margin-right': '1cm',
                        'margin-bottom': '1cm',
                        'margin-left': '1cm',
                        'encoding': 'UTF-8',
                        'enable-local-file-access': None,
                        'print-media-type': None,
                        'disable-smart-shrinking': None,
                        'zoom': 1.0,
                        'dpi': 96,
                        'image-dpi': 96,
                        'image-quality': 94,
                        'quiet': None,
                        'no-outline': None,
                        'disable-javascript': None,
                    }
                    
                    pdfkit.from_file(str(html_path), str(pdf_path), options=options)
                    
                    if pdf_path.exists() and pdf_path.stat().st_size > 1000:  # At least 1KB
                        self.logger.info(f"PDF generated successfully using pdfkit: {pdf_path}")
                        return str(pdf_path)
                    else:
                        self.logger.warning("pdfkit generated empty or invalid PDF")
                        
                except Exception as e:
                    self.logger.warning(f"pdfkit conversion failed: {str(e)}")
            
            # Try weasyprint as fallback
            if WEASYPRINT_AVAILABLE:
                try:
                    # Read HTML content and clean it for WeasyPrint
                    with open(html_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    # Clean HTML for WeasyPrint compatibility
                    html_content = self._clean_html_for_weasyprint(html_content)
                    
                    # Generate PDF with WeasyPrint
                    html_doc = HTML(string=html_content, base_url=f"file://{html_file.parent}/")
                    html_doc.write_pdf(str(pdf_path))
                    
                    if pdf_path.exists() and pdf_path.stat().st_size > 1000:  # At least 1KB
                        self.logger.info(f"PDF generated successfully using weasyprint: {pdf_path}")
                        return str(pdf_path)
                    else:
                        self.logger.warning("weasyprint generated empty or invalid PDF")
                        
                except Exception as e:
                    self.logger.warning(f"weasyprint conversion failed: {str(e)}")
            
            self.logger.error("Both pdfkit and weasyprint failed to generate PDF")
            return None
            
        except Exception as e:
            self.logger.error(f"Error converting HTML to PDF: {str(e)}")
            return None

    def _clean_html_for_weasyprint(self, html_content: str) -> str:
        """
        Clean HTML content for WeasyPrint compatibility.
        
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
            r'transition:[^;]+;',
            r'cursor:[^;]+;',
        ]
        
        for pattern in problematic_properties:
            html_content = re.sub(pattern, '', html_content, flags=re.IGNORECASE | re.DOTALL)
        
        # Fix media queries for print
        html_content = re.sub(r'@media\s+\([^)]+\)', '@media print', html_content)
        
        # Remove JavaScript
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        return html_content

    async def _create_pdf_report_fallback(self, beta_analysis: Dict[str, Dict[str, Dict[str, float]]], 
                                chart_paths: Dict[str, str], symbols: List[str], 
                                alpha_opportunities: List[AlphaOpportunity] = None) -> Optional[str]:
        """Create comprehensive PDF report."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_path = self.output_dir / f'bitcoin_beta_7day_report_{timestamp}.pdf'
            
            doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                textColor=colors.HexColor('#ffbf00'),
                alignment=1  # Center
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                textColor=colors.HexColor('#e5e7eb')
            )
            
            # Build content
            content = []
            
            # Title with 7-day specifics
            content.append(Paragraph("Bitcoin Beta 7-Day Analysis Report", title_style))
            content.append(Paragraph(f"Analysis Period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}", styles['Normal']))
            content.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}", styles['Normal']))
            content.append(Spacer(1, 20))
            
            # Executive Summary
            content.append(Paragraph("Executive Summary", heading_style))
            summary_text = f"""
            This report analyzes the 7-day correlation (beta) between Bitcoin and {len(symbols)-1} other cryptocurrencies 
            from {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')} across multiple timeframes 
import talib
            (4H, 1H, 15M, 5M). Beta measures how much an asset moves relative to Bitcoin's price movements over this 
            7-day period. A beta of 1.0 means the asset moved exactly with Bitcoin, while beta > 1.0 indicates 
            higher volatility and beta < 1.0 indicates lower volatility relative to Bitcoin during this week.
            """
            content.append(Paragraph(summary_text, styles['Normal']))
            content.append(Spacer(1, 20))
            
            # Beta Summary Table
            content.append(Paragraph("Beta Summary - 4H Timeframe (Ranked by Beta)", heading_style))
            
            if 'htf' in beta_analysis:
                table_data = [['Asset', 'Beta', 'Correlation', 'R²', 'Volatility Ratio', 'Max Drawdown']]
                
                # Sort symbols by beta (highest to lowest)
                symbol_beta_pairs = []
                for symbol, stats in beta_analysis['htf'].items():
                    if symbol == 'BTCUSDT':
                        continue
                    symbol_beta_pairs.append((symbol, stats))
                
                # Sort by beta value (highest to lowest)
                symbol_beta_pairs.sort(key=lambda x: x[1]['beta'], reverse=True)
                
                for symbol, stats in symbol_beta_pairs:
                    table_data.append([
                        symbol.replace('USDT', ''),
                        f"{stats['beta']:.3f}",
                        f"{stats['correlation']:.3f}",
                        f"{stats['r_squared']:.3f}",
                        f"{stats['volatility_ratio']:.3f}",
                        f"{stats['max_drawdown']:.1%}"
                    ])
                
                table = Table(table_data, colWidths=[1*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1*inch, 1*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a2a40')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                content.append(table)
                content.append(Spacer(1, 20))
            
            # Add charts
            if 'performance' in chart_paths and os.path.exists(chart_paths['performance']):
                content.append(Paragraph("Normalized Price Performance", heading_style))
                img = Image(chart_paths['performance'], width=7*inch, height=4*inch)
                content.append(img)
                content.append(Spacer(1, 20))
            
            if 'beta_comparison' in chart_paths and os.path.exists(chart_paths['beta_comparison']):
                content.append(Paragraph("Beta Comparison Across Timeframes", heading_style))
                img = Image(chart_paths['beta_comparison'], width=7*inch, height=5*inch)
                content.append(img)
                content.append(Spacer(1, 20))
                
            if 'correlation' in chart_paths and os.path.exists(chart_paths['correlation']):
                content.append(Paragraph("Correlation Heatmap", heading_style))
                img = Image(chart_paths['correlation'], width=6*inch, height=4*inch)
                content.append(img)
                content.append(Spacer(1, 20))
            
            # Alpha Generation Opportunities
            if alpha_opportunities:
                content.append(Paragraph("Alpha Generation Opportunities", heading_style))
                
                # Add alpha opportunities table
                alpha_table_data = [['Symbol', 'Pattern', 'Confidence', 'Alpha Potential', 'Recommendation']]
                
                for opp in alpha_opportunities[:5]:  # Top 5 opportunities
                    alpha_table_data.append([
                        opp.symbol.replace('USDT', ''),
                        opp.divergence_type.value.replace('_', ' ').title(),
                        f"{opp.confidence:.0%}",
                        f"{opp.alpha_potential:.1%}",
                        opp.recommended_action[:30] + "..." if len(opp.recommended_action) > 30 else opp.recommended_action
                    ])
                
                alpha_table = Table(alpha_table_data, colWidths=[0.8*inch, 1.2*inch, 0.8*inch, 0.8*inch, 2*inch])
                alpha_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a2a40')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                content.append(alpha_table)
                content.append(Spacer(1, 20))
                
                # Add detailed alpha insights
                for opp in alpha_opportunities[:3]:  # Top 3 detailed
                    content.append(Paragraph(f"🎯 {opp.symbol.replace('USDT', '')} - {opp.divergence_type.value.replace('_', ' ').title()}", styles['Normal']))
                    content.append(Paragraph(f"   {opp.trading_insight}", styles['Normal']))
                    content.append(Paragraph(f"   Action: {opp.recommended_action}", styles['Normal']))
                    content.append(Spacer(1, 10))
            
            # Key Insights
            content.append(Paragraph("Key Trading Insights", heading_style))
            insights = self._generate_insights(beta_analysis, alpha_opportunities)
            for insight in insights:
                content.append(Paragraph(f"• {insight}", styles['Normal']))
            
            # Build PDF
            doc.build(content)
            
            self.logger.info(f"PDF report created: {pdf_path}")
            return str(pdf_path)
            
        except Exception as e:
            self.logger.error(f"Error creating PDF report: {str(e)}")
            return None

    def _generate_insights(self, beta_analysis: Dict[str, Dict[str, Dict[str, float]]], 
                          alpha_opportunities: List[AlphaOpportunity] = None) -> List[str]:
        """Generate trading insights from beta analysis."""
        insights = []
        
        try:
            if 'htf' in beta_analysis:
                # Find highest and lowest beta assets
                betas = {symbol: stats['beta'] for symbol, stats in beta_analysis['htf'].items() 
                        if symbol != 'BTCUSDT'}
                
                if betas:
                    highest_beta = max(betas, key=betas.get)
                    lowest_beta = min(betas, key=betas.get)
                    
                    insights.append(f"{highest_beta.replace('USDT', '')} shows the highest beta ({betas[highest_beta]:.2f}), making it most sensitive to Bitcoin movements")
                    insights.append(f"{lowest_beta.replace('USDT', '')} shows the lowest beta ({betas[lowest_beta]:.2f}), offering potential diversification benefits")
                    
                # Find best correlated assets
                correlations = {symbol: stats['correlation'] for symbol, stats in beta_analysis['htf'].items() 
                               if symbol != 'BTCUSDT'}
                               
                if correlations:
                    best_corr = max(correlations, key=correlations.get)
                    insights.append(f"{best_corr.replace('USDT', '')} has the strongest correlation with Bitcoin ({correlations[best_corr]:.2f})")
                    
                # Volatility insights
                vol_ratios = {symbol: stats['volatility_ratio'] for symbol, stats in beta_analysis['htf'].items() 
                             if symbol != 'BTCUSDT'}
                             
                if vol_ratios:
                    high_vol = max(vol_ratios, key=vol_ratios.get)
                    insights.append(f"{high_vol.replace('USDT', '')} is {vol_ratios[high_vol]:.1f}x more volatile than Bitcoin")
                    
            # Add alpha generation insights
            if alpha_opportunities:
                high_confidence_opps = [opp for opp in alpha_opportunities if opp.confidence > 0.8]
                if high_confidence_opps:
                    insights.append(f"{len(high_confidence_opps)} high-confidence alpha opportunities identified")
                    
                for opp in alpha_opportunities[:2]:  # Top 2 opportunities
                    insights.append(f"{opp.symbol.replace('USDT', '')} {opp.divergence_type.value.replace('_', ' ')}: {opp.trading_insight}")
                    
        except Exception as e:
            self.logger.error(f"Error generating insights: {str(e)}")
            insights.append("Analysis completed successfully - see charts and tables for detailed correlations")
            
        return insights

    def _calculate_enhanced_analytics(self, market_data: Dict[str, Dict[str, pd.DataFrame]], 
                                    beta_analysis: Dict[str, Dict[str, Dict[str, float]]]) -> Dict[str, Any]:
        """
        Calculate enhanced analytics including volatility, momentum, and market regime analysis.
        
        Args:
            market_data: Market data dictionary
            beta_analysis: Beta analysis results
            
        Returns:
            Dict containing enhanced analytics
        """
        try:
            analytics = {
                'volatility_analysis': {},
                'momentum_indicators': {},
                'market_regime': {},
                'risk_metrics': {},
                'correlation_stability': {},
                'performance_attribution': {}
            }
            
            # Get Bitcoin data for reference
            btc_data = market_data.get('BTC/USDT', {})
            
            for tf_name, tf_data in btc_data.items():
                if tf_data is None or len(tf_data) < 20:
                    continue
                    
                # 1. Volatility Analysis
                analytics['volatility_analysis'][tf_name] = self._calculate_volatility_metrics(tf_data)
                
                # 2. Market Regime Detection
                analytics['market_regime'][tf_name] = self._detect_market_regime(tf_data)
            
            # 3. Cross-asset momentum analysis
            analytics['momentum_indicators'] = self._calculate_momentum_indicators(market_data)
            
            # 4. Risk metrics across all assets
            analytics['risk_metrics'] = self._calculate_risk_metrics(market_data, beta_analysis)
            
            # 5. Correlation stability analysis
            analytics['correlation_stability'] = self._analyze_correlation_stability(market_data)
            
            # 6. Performance attribution
            analytics['performance_attribution'] = self._calculate_performance_attribution(market_data, beta_analysis)
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error calculating enhanced analytics: {str(e)}")
            return {}
    
    def _calculate_volatility_metrics(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive volatility metrics."""
        try:
            returns = data['returns'].dropna()
            
            # Annualization factor based on timeframe frequency
            periods_per_year = {
                '4h': 365 * 6,    # 6 periods per day
                '1h': 365 * 24,   # 24 periods per day  
                '15m': 365 * 96,  # 96 periods per day
                '5m': 365 * 288   # 288 periods per day
            }
            
            # Estimate annualization factor (default to daily if unknown)
            ann_factor = 365
            for tf, factor in periods_per_year.items():
                if tf in str(data.index.freq).lower():
                    ann_factor = factor
                    break
            
            metrics = {
                'realized_volatility': returns.std() * np.sqrt(ann_factor),
                'garch_volatility': self._calculate_garch_volatility(returns),
                'volatility_of_volatility': self._calculate_vol_of_vol(returns),
                'skewness': returns.skew(),
                'kurtosis': returns.kurtosis(),
                'var_95': returns.quantile(0.05),
                'var_99': returns.quantile(0.01),
                'max_drawdown': self._calculate_max_drawdown(data['close']),
                'volatility_regime': 'High' if returns.std() > returns.rolling(50).std().mean() else 'Low'
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility metrics: {str(e)}")
            return {}
    
    def _calculate_garch_volatility(self, returns: pd.Series) -> float:
        """Calculate GARCH(1,1) volatility estimate."""
        try:
            # Simple GARCH(1,1) approximation
            # In production, use arch library for proper GARCH estimation
            
            # Rolling volatility as proxy
            rolling_vol = pd.Series(talib.STDDEV(returns.values.astype(float), timeperiod=20), index=returns.index)
            
            # EWMA volatility (lambda = 0.94, common for daily data)
            ewma_vol = returns.ewm(alpha=0.06).std().iloc[-1] if len(returns) > 1 else returns.std()
            
            return float(ewma_vol * np.sqrt(365))  # Annualized
            
        except Exception:
            return float(returns.std() * np.sqrt(365))
    
    def _calculate_vol_of_vol(self, returns: pd.Series, window: int = 20) -> float:
        """Calculate volatility of volatility."""
        try:
            rolling_vol = returns.rolling(window=window).std()
            vol_of_vol = rolling_vol.std()
            return float(vol_of_vol) if not np.isnan(vol_of_vol) else 0.0
        except Exception:
            return 0.0
    
    def _calculate_max_drawdown(self, prices: pd.Series) -> float:
        """Calculate maximum drawdown."""
        try:
            cumulative = (1 + prices.pct_change()).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            return float(drawdown.min())
        except Exception:
            return 0.0
    
    def _detect_market_regime(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Detect current market regime using multiple indicators."""
        try:
            returns = data['returns'].dropna()
            prices = data['close']
            
            # 1. Trend detection using moving averages
            ma_short = prices.rolling(10).mean()
            ma_long = prices.rolling(30).mean()
            trend = 'Bullish' if ma_short.iloc[-1] > ma_long.iloc[-1] else 'Bearish'
            
            # 2. Volatility regime
            current_vol = returns.tail(10).std()
            avg_vol = returns.std()
            vol_regime = 'High Vol' if current_vol > avg_vol * 1.2 else 'Low Vol'
            
            # 3. Momentum regime
            momentum = (prices.iloc[-1] / prices.iloc[-20] - 1) * 100 if len(prices) >= 20 else 0
            momentum_regime = 'Strong' if abs(momentum) > 5 else 'Weak'
            
            # 4. Mean reversion tendency
            # Calculate how often price reverts to mean
            deviations = (prices - prices.rolling(20).mean()) / prices.rolling(20).std()
            mean_reversion_score = (deviations.abs() > 1).sum() / len(deviations)
            
            regime = {
                'trend': trend,
                'volatility': vol_regime,
                'momentum': momentum_regime,
                'momentum_pct': float(momentum),
                'mean_reversion_score': float(mean_reversion_score),
                'regime_confidence': self._calculate_regime_confidence(returns, prices)
            }
            
            return regime
            
        except Exception as e:
            self.logger.error(f"Error detecting market regime: {str(e)}")
            return {}
    
    def _calculate_regime_confidence(self, returns: pd.Series, prices: pd.Series) -> float:
        """Calculate confidence in regime detection."""
        try:
            # Simple confidence based on consistency of signals
            vol_consistency = 1 - (returns.rolling(5).std().std() / returns.std())
            trend_consistency = (prices.rolling(5).mean().diff() > 0).sum() / len(prices.rolling(5).mean().diff())
            
            confidence = (vol_consistency + abs(trend_consistency - 0.5) * 2) / 2
            return float(np.clip(confidence, 0, 1))
            
        except Exception:
            return 0.5
    
    def _calculate_momentum_indicators(self, market_data: Dict[str, Dict[str, pd.DataFrame]]) -> Dict[str, Any]:
        """Calculate momentum indicators across all assets."""
        try:
            momentum_data = {}
            
            for symbol, timeframes in market_data.items():
                momentum_data[symbol] = {}
                
                for tf_name, df in timeframes.items():
                    if df is None or len(df) < 20:
                        continue
                        
                    prices = df['close']
                    
                    # Calculate various momentum indicators
                    momentum_data[symbol][tf_name] = {
                        'rsi': self._calculate_rsi(prices),
                        'momentum_1d': (prices.iloc[-1] / prices.iloc[-2] - 1) * 100 if len(prices) >= 2 else 0,
                        'momentum_7d': (prices.iloc[-1] / prices.iloc[-min(len(prices), 7)] - 1) * 100,
                        'price_position': (prices.iloc[-1] - prices.min()) / (prices.max() - prices.min()) if prices.max() != prices.min() else 0.5
                    }
            
            return momentum_data
            
        except Exception as e:
            self.logger.error(f"Error calculating momentum indicators: {str(e)}")
            return {}
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> float:
        """Calculate RSI indicator."""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50.0
            
        except Exception:
            return 50.0
    
    def _calculate_risk_metrics(self, market_data: Dict[str, Dict[str, pd.DataFrame]], 
                              beta_analysis: Dict[str, Dict[str, Dict[str, float]]]) -> Dict[str, Any]:
        """Calculate comprehensive risk metrics."""
        try:
            risk_metrics = {
                'portfolio_risk': {},
                'individual_risk': {},
                'correlation_risk': {},
                'tail_risk': {}
            }
            
            # Calculate portfolio-level risk metrics
            all_returns = []
            symbols = []
            
            for symbol, timeframes in market_data.items():
                if 'base' in timeframes and timeframes['base'] is not None:
                    returns = timeframes['base']['returns'].dropna()
                    if len(returns) > 10:
                        all_returns.append(returns)
                        symbols.append(symbol)
            
            if all_returns:
                # Create returns matrix
                returns_df = pd.concat(all_returns, axis=1, keys=symbols).dropna()
                
                if len(returns_df) > 10:
                    # Portfolio risk metrics
                    risk_metrics['portfolio_risk'] = {
                        'avg_correlation': returns_df.corr().values[np.triu_indices_from(returns_df.corr().values, k=1)].mean(),
                        'max_correlation': returns_df.corr().values[np.triu_indices_from(returns_df.corr().values, k=1)].max(),
                        'min_correlation': returns_df.corr().values[np.triu_indices_from(returns_df.corr().values, k=1)].min(),
                        'portfolio_volatility': np.sqrt(np.diag(returns_df.cov()).mean()),
                        'diversification_ratio': len(symbols) / (1 + risk_metrics['portfolio_risk'].get('avg_correlation', 0) * (len(symbols) - 1))
                    }
            
            return risk_metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {str(e)}")
            return {}
    
    def _analyze_correlation_stability(self, market_data: Dict[str, Dict[str, pd.DataFrame]]) -> Dict[str, Any]:
        """Analyze stability of correlations over time."""
        try:
            stability_metrics = {}
            
            # Get Bitcoin returns for reference
            btc_data = market_data.get('BTC/USDT', {})
            
            for tf_name, btc_df in btc_data.items():
                if btc_df is None or len(btc_df) < 50:
                    continue
                    
                btc_returns = btc_df['returns'].dropna()
                correlations_over_time = []
                
                # Calculate rolling correlations with other assets
                for symbol, timeframes in market_data.items():
                    if symbol == 'BTC/USDT' or tf_name not in timeframes:
                        continue
                        
                    asset_df = timeframes[tf_name]
                    if asset_df is None or len(asset_df) < 50:
                        continue
                        
                    asset_returns = asset_df['returns'].dropna()
                    
                    # Align the series
                    aligned_data = pd.concat([btc_returns, asset_returns], axis=1, keys=['BTC', symbol]).dropna()
                    
                    if len(aligned_data) >= 30:
                        # Calculate rolling correlation
                        rolling_corr = aligned_data['BTC'].rolling(window=20).corr(aligned_data[symbol])
                        correlations_over_time.extend(rolling_corr.dropna().tolist())
                
                if correlations_over_time:
                    stability_metrics[tf_name] = {
                        'correlation_volatility': np.std(correlations_over_time),
                        'correlation_trend': np.polyfit(range(len(correlations_over_time)), correlations_over_time, 1)[0],
                        'correlation_stability_score': 1 - np.std(correlations_over_time)  # Higher = more stable
                    }
            
            return stability_metrics
            
        except Exception as e:
            self.logger.error(f"Error analyzing correlation stability: {str(e)}")
            return {}
    
    def _calculate_performance_attribution(self, market_data: Dict[str, Dict[str, pd.DataFrame]], 
                                         beta_analysis: Dict[str, Dict[str, Dict[str, float]]]) -> Dict[str, Any]:
        """Calculate performance attribution analysis."""
        try:
            attribution = {}
            
            for symbol, timeframes in market_data.items():
                if symbol == 'BTC/USDT':
                    continue
                    
                attribution[symbol] = {}
                
                for tf_name, df in timeframes.items():
                    if df is None or len(df) < 20:
                        continue
                        
                    # Get beta for this symbol/timeframe
                    beta = beta_analysis.get(symbol, {}).get(tf_name, {}).get('beta', 0)
                    
                    # Calculate returns
                    asset_returns = df['returns'].dropna()
                    
                    # Get Bitcoin returns for same period
                    btc_data = market_data.get('BTC/USDT', {}).get(tf_name)
                    if btc_data is None:
                        continue
                        
                    btc_returns = btc_data['returns'].dropna()
                    
                    # Align returns
                    aligned_data = pd.concat([asset_returns, btc_returns], axis=1, keys=[symbol, 'BTC']).dropna()
                    
                    if len(aligned_data) >= 10:
                        asset_ret = aligned_data[symbol]
                        btc_ret = aligned_data['BTC']
                        
                        # Performance attribution
                        systematic_return = beta * btc_ret.mean()  # Return explained by Bitcoin
                        idiosyncratic_return = asset_ret.mean() - systematic_return  # Asset-specific return
                        
                        attribution[symbol][tf_name] = {
                            'total_return': float(asset_ret.mean()),
                            'systematic_return': float(systematic_return),
                            'idiosyncratic_return': float(idiosyncratic_return),
                            'systematic_percentage': float(systematic_return / asset_ret.mean() * 100) if asset_ret.mean() != 0 else 0,
                            'tracking_error': float((asset_ret - beta * btc_ret).std()),
                            'information_ratio': float(idiosyncratic_return / (asset_ret - beta * btc_ret).std()) if (asset_ret - beta * btc_ret).std() != 0 else 0
                        }
            
            return attribution
            
        except Exception as e:
            self.logger.error(f"Error calculating performance attribution: {str(e)}")
            return {}

async def main():
    """Test the Bitcoin Beta Report generator."""
    # This would be called with proper exchange_manager and top_symbols_manager
    pass

if __name__ == "__main__":
    asyncio.run(main()) 