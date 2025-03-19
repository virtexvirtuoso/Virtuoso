import logging
from typing import Any, Dict, List, Tuple, Optional, Union
import numpy as np
import pandas as pd
from pandas import Series
from src.utils.helpers import TimeframeUtils
from scipy.stats import gaussian_kde
from scipy.signal import find_peaks
import traceback
from src.utils.error_handling import handle_indicator_error
import time
from sklearn.mixture import GaussianMixture
from sklearn.cluster import DBSCAN
from collections import defaultdict
from .base_indicator import BaseIndicator, debug_method, DebugLevel, DebugMetrics
from ..core.logger import Logger
import talib
from sklearn.cluster import KMeans
from scipy.signal import argrelextrema

logger = logging.getLogger('PriceStructureIndicators')

class PriceStructureIndicators(BaseIndicator):
    """Price-based trading indicators that analyze market structure and price action.
    
    The Market Prism Concept - Price Structure Analysis Face:
    Analyzes market structure and price action to identify key levels, trends, and potential 
    reversal points. This refers to market structure/price action, not actual trading positions.
    
    Note: This class has been refactored to consolidate redundant methods. The main entry point
    for all price structure analysis is the `calculate` method, which provides comprehensive
    analysis results including component scores, signals, and interpretation.
    
    Components and weights:
    1. Support/Resistance levels (20%)
       - Identifies key price levels where market has shown significant reaction
       - Uses historical price action to map support and resistance zones
       - Incorporates volume profile for level validation
       
    2. Order blocks and supply/demand zones (20%)
       - Maps significant supply and demand areas
       - Identifies institutional order blocks
       - Tracks zone reaction strength and validity
       
    3. Trend position relative to key moving averages (20%)
       - Analyzes price position relative to major MAs
       - Tracks MA crossovers and alignments
       - Measures trend strength and momentum
       
    4. Volume analysis including profile and VWAP (20%)
       - Volume Profile analysis for price acceptance/rejection
       - VWAP deviation analysis
       - Volume node identification
       
    5. Market structure including swing points (20%)
       - Tracks higher highs/lows or lower highs/lows
       - Identifies swing points and pivots
       - Analyzes structural breaks and continuations
    
    Timeframe weights:
    - Base (1m): 40%
    - LTF (5m): 30%
    - MTF (30m): 20%
    - HTF (4h): 10%
    """

    # Define validation requirements
    validation_requirements = {
        'ohlcv': {
            'required': True,
            'columns': ['open', 'high', 'low', 'close', 'volume'],
            'min_data_points': 100
        },
        'timeframes': {
            'required': ['base', 'ltf', 'mtf', 'htf'],
            'min_candles': {
                'base': 100,
                'ltf': 50,
                'mtf': 50,
                'htf': 50
            }
        }
    }

    def __init__(self, config: Dict[str, Any], logger: Optional[Logger] = None):
        """Initialize PriceStructureIndicators.
        
        Args:
            config: Configuration dictionary
            logger: Optional logger instance
        """
        # Set indicator type before calling super().__init__
        self.indicator_type = 'price_structure'
        
        # Default component weights
        default_weights = {
            'order_block': 0.20,
            'volume_profile': 0.20,
            'vwap': 0.15,
            'composite_value': 0.15,
            'support_resistance': 0.15,
            'market_structure': 0.15
        }
        
        # Component name mapping to handle inconsistencies between config and internal names
        self.component_mapping = {
            # Config name -> Internal calculation name
            'order_block': 'order_blocks',
            'volume_profile': 'volume_profile',
            'vwap': 'vwap',
            'composite_value': 'composite_value',
            'support_resistance': 'support_resistance',
            # Internal calculation name -> Config name
            'order_blocks': 'order_block',
            'volume_analysis': 'volume_profile',
            'trend_position': 'vwap',
            'market_structure': 'market_structure'  # Map market_structure to itself
        }
        
        # Get price structure specific config
        price_structure_config = config.get('analysis', {}).get('indicators', {}).get('price_structure', {})
        
        # Read component weights from config if available
        components_config = price_structure_config.get('components', {})
        self.component_weights = {}
        
        # Use weights from config or fall back to defaults
        for component, default_weight in default_weights.items():
            config_weight = components_config.get(component, {}).get('weight', default_weight)
            self.component_weights[component] = config_weight
        
        # Setup required timeframes
        self.required_timeframes = ['base', 'ltf', 'mtf', 'htf']
        
        # Set timeframe weights
        self.timeframe_weights = {
            'base': 0.4,
            'ltf': 0.3,
            'mtf': 0.2,
            'htf': 0.1
        }
        
        # Call parent class constructor
        super().__init__(config, logger)
        
        # Initialize parameters
        self.order_block_lookback = price_structure_config.get('parameters', {}).get('order_block', {}).get('lookback', 20)
        self.volume_profile_bins = price_structure_config.get('parameters', {}).get('volume_profile', {}).get('bins', 100)
        self.value_area_volume = price_structure_config.get('parameters', {}).get('volume_profile', {}).get('value_area', 0.7)
        
        # Timeframe mapping from config
        self.timeframe_map = {
            tf: str(self.config['timeframes'][tf]['interval'])
            for tf in ['base', 'ltf', 'mtf', 'htf']
            if tf in self.config.get('timeframes', {})
        }
        
        # Fallback timeframe mapping if config is missing
        if not self.timeframe_map or len(self.timeframe_map) < 4:
            self.logger.warning("Missing timeframe configuration, using defaults")
            self.timeframe_map = {
                'base': '1',
                'ltf': '5',
                'mtf': '30',
                'htf': '240'
            }
        
        # Validate weights
        self._validate_weights()

    @debug_method(DebugLevel.DETAILED)
    async def _calculate_component_scores(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate individual scores for each position component."""
        try:
            if not self._validate_input(data):
                raise ValueError("Invalid input data structure")

            ohlcv_data = data['ohlcv']
            
            scores = {
                'support_resistance': self._analyze_sr_levels(ohlcv_data),
                'order_blocks': self._analyze_orderblock_zones(ohlcv_data),
                'trend_position': self._analyze_trend_position(ohlcv_data),
                'volume_analysis': self._analyze_volume(ohlcv_data),
                'market_structure': self._analyze_market_structure(ohlcv_data)
            }
            
            if not all(comp in scores for comp in self.component_weights):
                raise ValueError("Missing component scores")
                
            return scores
            
        except Exception as e:
            self.logger.error(f"Error calculating component scores: {str(e)}")
            return {comp: 50.0 for comp in self.component_weights}

    def _validate_input(self, market_data: Dict[str, Any]) -> bool:
        """Validate input data structure.
        
        Checks if the market data contains the required OHLCV data and timeframes.
        Adjusts timeframe weights if some timeframes are missing.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            self.logger.debug("\n=== Validating Position Indicator Input ===")
            
            if not isinstance(market_data, dict):
                self.logger.error("Market data must be a dictionary")
                return False
                
            # Check if ohlcv exists and is a dictionary
            if 'ohlcv' not in market_data:
                self.logger.error("Missing 'ohlcv' data in market_data")
                return False
                
            ohlcv = market_data.get('ohlcv', {})
            if not isinstance(ohlcv, dict):
                self.logger.error(f"OHLCV data must be a dictionary, got {type(ohlcv)}")
                return False
            
            # Check for missing timeframes
            missing_timeframes = []
            for tf_name in self.required_timeframes:
                # Try direct match with timeframe name
                if tf_name not in ohlcv:
                    # Try match with timeframe map
                    tf_key = self.timeframe_map.get(tf_name, tf_name)
                    if tf_key not in ohlcv:
                        self.logger.warning(f"Missing {tf_name} timeframe data")
                        missing_timeframes.append(tf_name)
            
            # If only one timeframe is missing, we may be able to continue with slightly reduced accuracy
            if len(missing_timeframes) == 1:
                self.logger.warning(f"Missing 1 timeframe: {missing_timeframes[0]}. Will continue with reduced accuracy.")
                
                # Store original weights for later restoration
                if not hasattr(self, '_original_weights'):
                    self._original_weights = self.timeframe_weights.copy()
                
                # Adjust weights to account for missing timeframe
                missing_tf = missing_timeframes[0]
                missing_weight = self.timeframe_weights.get(missing_tf, 0)
                
                if missing_weight > 0:
                    # Redistribute the missing weight proportionally
                    available_tfs = [tf for tf in self.timeframe_weights if tf != missing_tf]
                    total_available_weight = sum(self.timeframe_weights[tf] for tf in available_tfs)
                    
                    if total_available_weight > 0:
                        for tf in available_tfs:
                            self.timeframe_weights[tf] += (missing_weight * self.timeframe_weights[tf] / total_available_weight)
                    
                    # Set missing timeframe weight to 0
                    self.timeframe_weights[missing_tf] = 0
                    
                    self.logger.debug(f"Adjusted weights: {self.timeframe_weights}")
                
                # Continue analysis with available timeframes
                return True
            elif len(missing_timeframes) > 1:
                if len(missing_timeframes) == len(self.required_timeframes):
                    self.logger.error("All required timeframes are missing")
                    return False
                else:
                    self.logger.warning(f"Missing multiple timeframes: {missing_timeframes}. Analysis may be less accurate.")
            
            # Validate available timeframes
            valid_timeframes = 0
            for tf_name in self.required_timeframes:
                if tf_name in ohlcv:
                    if self._validate_timeframe_data(ohlcv[tf_name], tf_name):
                        valid_timeframes += 1
                    else:
                        self.logger.warning(f"Invalid data for {tf_name} timeframe")
                else:
                    # Try with mapped timeframe key
                    tf_key = self.timeframe_map.get(tf_name, tf_name)
                    if tf_key in ohlcv and self._validate_timeframe_data(ohlcv[tf_key], tf_name):
                        valid_timeframes += 1
                        self.logger.debug(f"Using mapped timeframe {tf_key} for {tf_name}")
            
            # If we have at least one valid timeframe, we can proceed
            if valid_timeframes > 0:
                self.logger.info(f"Found {valid_timeframes} valid timeframes out of {len(self.required_timeframes)}")
                return True
            else:
                self.logger.error("No valid timeframes found")
                return False
            
        except Exception as e:
            self.logger.error(f"Error validating input: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False

    def _validate_timeframe_data(self, df_data: Union[pd.DataFrame, Dict[str, Any]], timeframe_name: str) -> bool:
        """Validate timeframe data structure and content.
        
        Args:
            df_data: DataFrame or dictionary containing timeframe data
            timeframe_name: Name of the timeframe for logging purposes
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            # Handle case where df is wrapped in a dict with 'data' key
            if isinstance(df_data, dict):
                if 'data' in df_data:
                    df = df_data['data']
                    self.logger.debug(f"Extracted DataFrame from 'data' key for {timeframe_name}")
                elif 'dataframe' in df_data:
                    df = df_data['dataframe']
                    self.logger.debug(f"Extracted DataFrame from 'dataframe' key for {timeframe_name}")
                else:
                    # Try to find DataFrame in the dictionary
                    for key, value in df_data.items():
                        if isinstance(value, pd.DataFrame):
                            df = value
                            self.logger.debug(f"Found DataFrame in key '{key}' for {timeframe_name}")
                            break
                    else:
                        self.logger.debug(f"Timeframe {timeframe_name} dict does not contain a DataFrame: {list(df_data.keys())}")
                        return False
            else:
                df = df_data
                
            if not isinstance(df, pd.DataFrame):
                self.logger.debug(f"Timeframe {timeframe_name} data is not a DataFrame, got {type(df)}")
                return False
                
            if df.empty:
                self.logger.debug(f"Timeframe {timeframe_name} DataFrame is empty")
                return False
                
            # Check required columns - be flexible with column names
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            
            # Map common alternative column names
            column_mapping = {
                'open': ['open', 'Open', 'OPEN', 'o', 'O'],
                'high': ['high', 'High', 'HIGH', 'h', 'H'],
                'low': ['low', 'Low', 'LOW', 'l', 'L'],
                'close': ['close', 'Close', 'CLOSE', 'c', 'C'],
                'volume': ['volume', 'Volume', 'VOLUME', 'v', 'V']
            }
            
            # Check if all required columns are present (considering alternatives)
            missing_cols = []
            for col in required_cols:
                if not any(alt_col in df.columns for alt_col in column_mapping[col]):
                    missing_cols.append(col)
            
            if missing_cols:
                self.logger.debug(f"Timeframe {timeframe_name} missing columns: {missing_cols}")
                self.logger.debug(f"Available columns: {list(df.columns)}")
                return False
                
            # Check minimum data points
            try:
                # Try to get the min_candles from validation_requirements
                min_required = self.validation_requirements.get('timeframes', {}).get('min_candles', {}).get(timeframe_name, 50)
            except (KeyError, AttributeError, TypeError) as e:
                # Fallback to default value if any error occurs
                self.logger.debug(f"Error accessing validation_requirements for {timeframe_name}: {str(e)}")
                min_required = 50
                
            if len(df) < min_required:
                self.logger.debug(f"Timeframe {timeframe_name} has insufficient data points: {len(df)} < {min_required}")
                return False
                
            self.logger.debug(f"Timeframe {timeframe_name} validation passed: {len(df)} data points")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating timeframe {timeframe_name}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False

    def _validate_dataframe(self, df: pd.DataFrame, debug: DebugMetrics) -> bool:
        """Validate DataFrame structure and contents."""
        try:
            if df is None or df.empty:
                debug.warnings.append("Empty DataFrame")
                return False
            
            required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                if 'timestamp' in missing_cols and isinstance(df.index, pd.DatetimeIndex):
                    df['timestamp'] = df.index.astype(np.int64) // 10**6
                    missing_cols.remove('timestamp')
                elif 'timestamp' in missing_cols and 'datetime' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['datetime']).astype(np.int64) // 10**6
                    missing_cols.remove('timestamp')
                
                if missing_cols:
                    debug.warnings.append(f"Missing columns: {missing_cols}")
                    return False
            
            return True
            
        except Exception as e:
            debug.warnings.append(f"Validation error: {str(e)}")
            self.logger.error(f"Error in DataFrame validation: {str(e)}")
            return False

    def _analyze_sr_levels(self, ohlcv_data: Dict[str, pd.DataFrame]) -> float:
        """Analyze support/resistance levels."""
        try:
            scores = []
            available_timeframes = set(ohlcv_data.keys()) & set(self.required_timeframes)
            missing_timeframes = set(self.required_timeframes) - available_timeframes
            
            if missing_timeframes:
                self.logger.warning(f"Missing timeframes for SR analysis: {', '.join(missing_timeframes)}")
            
            if not available_timeframes:
                self.logger.error("No valid timeframes available for SR analysis")
                return 50.0
                
            # Normalize weights based on available timeframes
            total_weight = sum(self.timeframe_weights[tf] for tf in available_timeframes)
            if total_weight == 0:
                self.logger.error("Total weight for available timeframes is zero")
                return 50.0
                
            normalized_weights = {tf: self.timeframe_weights[tf] / total_weight for tf in available_timeframes}
            
            for tf in available_timeframes:
                data = ohlcv_data[tf]
                if not isinstance(data, pd.DataFrame) or data.empty:
                    self.logger.warning(f"Invalid DataFrame for timeframe {tf}")
                    continue
                    
                if len(data) < 30:  # Need sufficient data for reliable SR levels
                    self.logger.warning(f"Insufficient data points for timeframe {tf}: {len(data)} rows")
                    continue
                    
                # Get current price
                current_price = data['close'].iloc[-1]
                
                # Find SR levels
                levels = self._find_sr_levels(data)
                
                # Score based on proximity to levels
                level_scores = self._calculate_level_proximity(current_price, levels)
                
                # Weight by normalized timeframe weight
                tf_score = np.mean(level_scores) * normalized_weights[tf]
                scores.append(tf_score)
                
            if not scores:
                self.logger.warning("No timeframes had valid data for SR analysis")
                return 50.0
                
            return float(np.sum(scores))
            
        except Exception as e:
            self.logger.error(f"Error in SR analysis: {str(e)}")
            self.logger.error(traceback.format_exc())
            return 50.0

    def _find_sr_levels(self, data):
        """
        Find support and resistance levels in the given data.
        
        Args:
            data (pd.DataFrame): OHLCV data
            
        Returns:
            list: List of support and resistance levels
        """
        try:
            if data is None or data.empty or len(data) < 30:
                self.logger.warning("Insufficient data for SR level detection")
                return []
                
            # Use zigzag to identify swing highs and lows
            highs = data['high'].values
            lows = data['low'].values
            closes = data['close'].values
            
            # Parameters for swing point detection
            window = min(14, len(data) // 4)  # Adaptive window size
            threshold = 0.003  # 0.3% price movement threshold
            
            # Find swing highs
            swing_highs = []
            for i in range(window, len(data) - window):
                if highs[i] == max(highs[i-window:i+window+1]):
                    # Check if it's a significant swing
                    if any(highs[i] > highs[j] * (1 + threshold) for j in range(i-window, i)) and \
                       any(highs[i] > highs[j] * (1 + threshold) for j in range(i+1, i+window+1)):
                        swing_highs.append((i, highs[i]))
            
            # Find swing lows
            swing_lows = []
            for i in range(window, len(data) - window):
                if lows[i] == min(lows[i-window:i+window+1]):
                    # Check if it's a significant swing
                    if any(lows[i] < lows[j] * (1 - threshold) for j in range(i-window, i)) and \
                       any(lows[i] < lows[j] * (1 - threshold) for j in range(i+1, i+window+1)):
                        swing_lows.append((i, lows[i]))
            
            # Combine and sort levels
            all_levels = [level for _, level in swing_highs] + [level for _, level in swing_lows]
            
            # Filter out levels that are too close to each other
            if not all_levels:
                return []
                
            # Current price
            current_price = closes[-1]
            
            # Group levels that are within 0.5% of each other
            grouped_levels = []
            all_levels.sort()
            
            current_group = [all_levels[0]]
            for level in all_levels[1:]:
                if level < current_group[-1] * 1.005 and level > current_group[-1] * 0.995:
                    current_group.append(level)
                else:
                    # Add average of current group
                    grouped_levels.append(sum(current_group) / len(current_group))
                    current_group = [level]
            
            # Add the last group
            if current_group:
                grouped_levels.append(sum(current_group) / len(current_group))
            
            # Filter out levels that are too far from current price (>20%)
            relevant_levels = [level for level in grouped_levels 
                              if level < current_price * 1.2 and level > current_price * 0.8]
            
            return relevant_levels
            
        except Exception as e:
            self.logger.error(f"Error finding SR levels: {str(e)}")
            return []

    def _analyze_trend_position(self, ohlcv_data: Dict[str, pd.DataFrame]) -> float:
        """Analyze position relative to trend with enhanced detection."""
        try:
            scores = []
            available_timeframes = set(ohlcv_data.keys()) & set(self.required_timeframes)
            missing_timeframes = set(self.required_timeframes) - available_timeframes
            
            if missing_timeframes:
                self.logger.warning(f"Missing timeframes for trend analysis: {', '.join(missing_timeframes)}")
            
            if not available_timeframes:
                self.logger.error("No valid timeframes available for trend analysis")
                return 50.0
                
            # Normalize weights based on available timeframes
            total_weight = sum(self.timeframe_weights[tf] for tf in available_timeframes)
            if total_weight == 0:
                self.logger.error("Total weight for available timeframes is zero")
                return 50.0
                
            normalized_weights = {tf: self.timeframe_weights[tf] / total_weight for tf in available_timeframes}
            
            for tf in available_timeframes:
                data = ohlcv_data[tf]
                if not isinstance(data, pd.DataFrame) or data.empty:
                    self.logger.warning(f"Invalid DataFrame for timeframe {tf}")
                    continue
                    
                if len(data) < 200:  # Ideally need 200 periods for longest EMA
                    self.logger.debug(f"Limited data for timeframe {tf}: {len(data)} rows (adaptive EMA calculation will be used)")
                
                current_price = data['close'].iloc[-1]
                
                # Use more timeframes for robustness, adjusted based on available data
                max_period = min(200, len(data) - 10)  # Ensure we have at least 10 values after EMA calculation
                if max_period <= 10:
                    self.logger.warning(f"Insufficient data for trend calculation in {tf} timeframe: {len(data)} rows")
                    continue
                    
                # Determine which EMAs we can calculate based on available data
                ema_periods = [min(period, max_period) for period in [10, 20, 50, 100, 200] if period <= max_period]
                ma_data = {}
                
                # Calculate multiple EMAs for better trend detection
                for period in ema_periods:
                    if len(data) >= period:
                        ma_data[f'ema{period}'] = talib.EMA(data['close'], timeperiod=period)
                
                if not ma_data:
                    self.logger.warning(f"Insufficient data for trend calculation in {tf} timeframe")
                    continue
                
                # Price position relative to EMAs
                price_positions = []
                ema_alignments = []
                for name, series in ma_data.items():
                    if not series.empty and len(series) > 0:
                        latest_ma = series.iloc[-1]
                        position = (current_price / latest_ma - 1) * 100
                        price_positions.append(position)
                        
                        # Record if price is above or below this MA
                        ema_alignments.append(1 if position > 0 else -1)
                
                # Calculate average position
                avg_position = np.mean(price_positions) if price_positions else 0
                
                # Calculate alignment score (are EMAs aligned in same direction?)
                alignment_score = abs(sum(ema_alignments)) / len(ema_alignments) if ema_alignments else 0
                
                # Calculate trend momentum (are shorter EMAs crossing longer ones?)
                momentum_score = 0
                if len(ma_data) >= 2:
                    # Check alignment of shorter vs longer EMAs
                    shorter_emas = [ma_data[f'ema{p}'] for p in [10, 20] if f'ema{p}' in ma_data]
                    longer_emas = [ma_data[f'ema{p}'] for p in [50, 100, 200] if f'ema{p}' in ma_data]
                    
                    if shorter_emas and longer_emas:
                        # Calculate average of shorter vs longer EMAs
                        avg_short = np.mean([ema.iloc[-1] for ema in shorter_emas])
                        avg_long = np.mean([ema.iloc[-1] for ema in longer_emas])
                        
                        # Positive if shorter above longer (bullish)
                        momentum = (avg_short / avg_long - 1) * 100
                        momentum_score = np.tanh(momentum * 0.05) * 25  # Scale to -25 to +25
                
                # Convert to trend score (0-100)
                # Combine position and alignment for final score
                position_component = avg_position * 5  # Amplify the signal
                alignment_component = alignment_score * 10
                
                # Combine components with weights
                trend_score = 50 + position_component + momentum_score + alignment_component
                
                # Weight by timeframe and add to scores
                scores.append(float(np.clip(trend_score, 0, 100)) * normalized_weights[tf])
                
            return float(np.sum(scores)) if scores else 50.0
            
        except Exception as e:
            self.logger.error(f"Error in trend analysis: {str(e)}")
            return 50.0

    def _calculate_volume_profile_score(self, df: pd.DataFrame) -> float:
        """Calculate volume profile score using adaptive bins and GMM clustering."""
        try:
            if df.empty or 'volume' not in df.columns:
                return 50.0
                
            # Calculate adaptive bin size based on price volatility
            price_std = df['close'].std()
            price_range = df['close'].max() - df['close'].min()
            adaptive_bins = max(20, min(200, int(price_range / (price_std * 0.1))))
            
            # Calculate volume profile
            price_levels = pd.qcut(df['close'], q=adaptive_bins, duplicates='drop')
            volume_profile = df.groupby(price_levels, observed=False)['volume'].sum()
            
            # Get POC and value area
            poc_level = volume_profile.idxmax()
            current_price = df['close'].iloc[-1]
            
            # Calculate value area (70% of volume)
            total_volume = volume_profile.sum()
            sorted_profile = volume_profile.sort_values(ascending=False)
            value_area = sorted_profile[sorted_profile.cumsum() <= (total_volume * self.value_area_volume)]
            
            va_high = value_area.index.max().right
            va_low = value_area.index.min().left
            
            # Score based on position relative to value area
            if current_price >= va_low and current_price <= va_high:
                va_position = (current_price - va_low) / (va_high - va_low)
                score = 100 * (1 - abs(va_position - 0.5) * 2)
            else:
                distance = min(abs(current_price - va_high), abs(current_price - va_low))
                score = 50 - (distance / current_price * 100)
                
            return float(np.clip(score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating volume profile: {str(e)}")
            return 50.0

    def _calculate_vwap_score(self, timeframe_data: Dict[str, Any]) -> float:
        """Calculate VWAP score using multiple timeframes."""
        try:
            self.logger.debug("VWAP Analysis:")
            scores = []
            weights = {'htf': 0.4, 'mtf': 0.35, 'ltf': 0.25}
            
            for tf, weight in weights.items():
                if tf in timeframe_data:
                    df = timeframe_data[tf].get('data', pd.DataFrame())
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        tf_score = self._calculate_single_vwap_score(df)
                        scores.append(tf_score * weight)
                        self.logger.debug(f"- {tf.upper()} Score: {tf_score:.2f} (weight: {weight:.2f})")
            
            final_score = sum(scores) if scores else 50.0
            self.logger.debug(f"- Final VWAP Score: {final_score:.2f}")
            
            return final_score
            
        except Exception as e:
            self.logger.error(f"Error calculating VWAP score: {str(e)}")
            return 50.0

    @handle_indicator_error
    def _calculate_composite_value_score(self, data: Dict[str, Any]) -> float:
        """Calculate composite value score."""
        try:
            # Add detailed logging
            self.logger.debug("Composite Value Analysis:")
            
            value_areas = self._calculate_value_areas(data)
            score = self._calculate_score_from_value_areas(value_areas)
            
            # Log value areas for each timeframe
            for tf, area in value_areas.items():
                self.logger.debug(f"\n{tf.upper()} Value Area:")
                self.logger.debug(f"- POC: {area.get('poc', 0):.2f}")
                self.logger.debug(f"- VAH: {area.get('vah', 0):.2f}")
                self.logger.debug(f"- VAL: {area.get('val', 0):.2f}")
            
            self.logger.debug(f"\nFinal Composite Score: {score:.2f}")
            return score
            
        except Exception as e:
            self.logger.error(f"Error calculating composite value score: {str(e)}")
            return 50.0

    def _calculate_value_areas(self, data: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Calculate value areas from price data."""
        try:
            value_areas = {}
            for tf, tf_data in data.items():
                # Extract DataFrame from the nested structure
                df = tf_data.get('data', pd.DataFrame())
                if isinstance(df, pd.DataFrame) and not df.empty:
                    # Calculate value area high/low
                    volume_profile = self._calculate_volume_profile(df)
                    if all(v != 0 for v in volume_profile.values()):
                        value_areas[tf] = volume_profile
            return value_areas
        except Exception as e:
            self.logger.error(f"Error calculating value areas: {str(e)}")
            return {}

    def calculate_trend_score(self, market_data: Union[Dict[str, Any], pd.DataFrame]) -> float:
        """Calculate trend score."""
        try:
            # Handle DataFrame input
            if isinstance(market_data, pd.DataFrame):
                df = market_data
            else:
                # Handle Dict input with nested OHLCV structure
                if 'ohlcv' not in market_data:
                    logger.warning("Missing OHLCV data")
                    return 50.0

                ohlcv_data = market_data['ohlcv']
                if not isinstance(ohlcv_data, dict):
                    logger.warning("Invalid OHLCV data format")
                    return 50.0

                # Get first available timeframe data
                df = None
                for tf_data in ohlcv_data.values():
                    if isinstance(tf_data, dict):
                        if 'dataframe' in tf_data:
                            df = tf_data['dataframe']
                            break
                        elif 'data' in tf_data:
                            df = pd.DataFrame(tf_data['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                            break

            if df is None or df.empty:
                logger.warning("No valid OHLCV data found")
                return 50.0

            # Calculate trend indicators
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['sma_200'] = df['close'].rolling(window=200).mean()

            # Get latest values
            current_price = df['close'].iloc[-1]
            sma_20 = df['sma_20'].iloc[-1]
            sma_50 = df['sma_50'].iloc[-1]
            sma_200 = df['sma_200'].iloc[-1]

            # Calculate base trend score
            base_score = 50.0

            # Short-term trend (SMA 20)
            if current_price > sma_20:
                base_score += 10
            elif current_price < sma_20:
                base_score -= 10

            # Medium-term trend (SMA 50)
            if current_price > sma_50:
                base_score += 10
            elif current_price < sma_50:
                base_score -= 10

            # Long-term trend (SMA 200)
            if current_price > sma_200:
                base_score += 10
            elif current_price < sma_200:
                base_score -= 10

            # Calculate momentum adjustment
            returns = df['close'].pct_change()
            momentum = returns.tail(10).mean() * 100
            momentum_adj = np.clip(momentum * 10, -10, 10)

            # Calculate alignment adjustment
            alignment_adj = 0
            if sma_20 > sma_50 and sma_50 > sma_200:
                alignment_adj = 10  # Strong uptrend alignment
            elif sma_20 < sma_50 and sma_50 < sma_200:
                alignment_adj = -10  # Strong downtrend alignment

            # Calculate final score
            score = base_score + momentum_adj + alignment_adj

            logger.debug(f"Trend Score: base={base_score:.2f}, momentum={momentum_adj:.2f}, alignment={alignment_adj:+.2f}, final={score:.2f}")
            return float(np.clip(score, 0, 100))
            
        except Exception as e:
            logger.error(f"Error calculating trend score: {str(e)}")
            return 50.0

    def calculate_support_score(self, timeframe_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate support score using multiple timeframes."""
        try:
            scores = []
            weights = {'htf': 0.4, 'mtf': 0.35, 'ltf': 0.25}
            
            for tf, weight in weights.items():
                if tf in timeframe_data:
                    df = timeframe_data[tf]
                    tf_score = self._calculate_single_support_score(df)
                    scores.append(tf_score * weight)
                    
            return float(np.clip(sum(scores) if scores else 50.0, 0, 100))
            
        except Exception as e:
            logger.error(f"Error calculating support score: {str(e)}")
            return 50.0

    def _calculate_dynamic_thresholds(self, df: pd.DataFrame, settings: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate dynamic thresholds for imbalance detection based on historical data.
        
        Args:
            df: DataFrame containing price and volume data
            settings: Dictionary containing threshold settings
            
        Returns:
            Dictionary containing calculated threshold values
        """
        try:
            # Get base threshold values from settings
            base_volume_threshold = settings.get('volume_threshold', 1.5)
            base_price_threshold = settings.get('price_threshold', 0.01)
            
            # Calculate volume statistics
            mean_volume = df['volume'].mean()
            std_volume = df['volume'].std()
            
            # Calculate price statistics
            price_changes = df['close'].pct_change().abs()
            mean_price_change = price_changes.mean()
            std_price_change = price_changes.std()
            
            # Calculate dynamic thresholds
            volume_threshold = mean_volume + (std_volume * base_volume_threshold)
            price_threshold = mean_price_change + (std_price_change * base_price_threshold)
            
            # Calculate additional thresholds for different levels
            return {
                'volume_threshold': volume_threshold,
                'price_threshold': price_threshold,
                'strong_volume_threshold': volume_threshold * 2,
                'strong_price_threshold': price_threshold * 2,
                'extreme_volume_threshold': volume_threshold * 3,
                'extreme_price_threshold': price_threshold * 3
            }
            
        except Exception as e:
            logger.error(f"Error calculating dynamic thresholds: {str(e)}")
            # Return default thresholds if calculation fails
            return {
                'volume_threshold': 1.5,
                'price_threshold': 0.01,
                'strong_volume_threshold': 3.0,
                'strong_price_threshold': 0.02,
                'extreme_volume_threshold': 4.5,
                'extreme_price_threshold': 0.03
            }

    async def _detect_imbalance_levels(self, df: pd.DataFrame, thresholds: Dict[str, float], settings: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect imbalance levels in price data using dynamic thresholds.
        """
        try:
            bullish_levels = []
            bearish_levels = []
            
            # Get threshold values with defaults
            volume_threshold = thresholds.get('volume_threshold', 1.5)
            price_threshold = thresholds.get('price_threshold', 0.01)
            
            # Group data into price rows for analysis
            df['price_row'] = (df['close'] / settings.get('ticks_per_row', 50)).round() * settings.get('ticks_per_row', 50)
            grouped = df.groupby('price_row').agg({
                'volume': 'sum',
                'close': ['first', 'last']
            })
            
            # Analyze each price level for imbalances
            for idx, row in grouped.iterrows():
                price_change = row['close']['last'] - row['close']['first']
                price_level = idx
                volume = row['volume']
                
                if price_change > 0:
                    imbalance_ratio = 1 + (price_change / row['close']['first'])
                    if imbalance_ratio > volume_threshold:
                        bullish_levels.append({
                            'price_level': price_level,
                            'strength': min(imbalance_ratio / volume_threshold, 1.0),
                            'volume': volume,
                            'ratio': imbalance_ratio
                        })
                elif price_change < 0:
                    imbalance_ratio = 1 / (1 - (price_change / row['close']['first']))
                    if imbalance_ratio > volume_threshold:
                        bearish_levels.append({
                            'price_level': price_level,
                            'strength': min(imbalance_ratio / volume_threshold, 1.0),
                            'volume': volume,
                            'ratio': imbalance_ratio
                        })
            
            # Sort levels by strength
            bullish_levels.sort(key=lambda x: x['strength'], reverse=True)
            bearish_levels.sort(key=lambda x: x['strength'], reverse=True)
            
            # Limit to most significant levels
            max_levels = settings.get('max_levels', 5)
            bullish_levels = bullish_levels[:max_levels]
            bearish_levels = bearish_levels[:max_levels]
            
            return {
                'bullish': bullish_levels,
                'bearish': bearish_levels
            }
            
        except Exception as e:
            logger.error(f"Error detecting imbalance levels: {str(e)}")
            return {'bullish': [], 'bearish': []}

    def _calculate_imbalance_strength(self, ratio: float, thresholds: Dict[str, float]) -> float:
        """
        Calculate the strength of an imbalance based on its ratio and thresholds.
        
        Args:
            ratio (float): Imbalance ratio
            thresholds (Dict[str, float]): Threshold levels
            
        Returns:
            float: Strength score between 0 and 1
        """
        try:
            if ratio >= thresholds['extreme_volume_threshold']:
                return 1.0
            elif ratio >= thresholds['strong_volume_threshold']:
                return 0.75
            elif ratio >= thresholds['volume_threshold']:
                return 0.5
            else:
                return 0.0
        except Exception as e:
            logger.error(f"Error calculating imbalance strength: {str(e)}")
            return 0.0

    def _calculate_volume_score(self, price_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate volume score."""
        try:
            if price_data.empty or 'volume' not in price_data.columns:
                logger.warning("Invalid DataFrame for volume score calculation")
                return 50.0

            # Calculate volume score
            volume_profile = price_data['volume'].sum()
            if volume_profile == 0:
                return 50.0

            # Calculate volume score based on volume profile
            volume_score = 100 * (volume_profile / price_data['volume'].sum())
            return float(np.clip(volume_score, 0, 100))

        except Exception as e:
            logger.error(f"Error calculating volume score: {str(e)}")
            return 50.0

    def _calculate_momentum_score(self, price_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate momentum score."""
        try:
            if price_data.empty or 'close' not in price_data.columns:
                logger.warning("Invalid DataFrame for momentum score calculation")
                return 50.0

            # Calculate momentum score based on price changes
            price_changes = price_data['close'].diff().abs()
            momentum_score = 100 * (price_changes.sum() / price_data['close'].iloc[-1])
            return float(np.clip(momentum_score, 0, 100))

        except Exception as e:
            logger.error(f"Error calculating momentum score: {str(e)}")
            return 50.0

    def _calculate_volatility_score(self, price_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate volatility score."""
        try:
            if price_data.empty or 'close' not in price_data.columns:
                logger.warning("Invalid DataFrame for volatility score calculation")
                return 50.0

            # Calculate volatility score based on price changes
            price_changes = price_data['close'].pct_change().abs()
            volatility_score = 100 * (price_changes.mean() / price_data['close'].iloc[-1])
            return float(np.clip(volatility_score, 0, 100))

        except Exception as e:
            logger.error(f"Error calculating volatility score: {str(e)}")
            return 50.0

    def _calculate_imbalance_score(self, df: pd.DataFrame) -> float:
        """Calculate imbalance score based on price action and volume."""
        try:
            if df.empty or not all(col in df.columns for col in ['high', 'low', 'close', 'volume']):
                return 50.0

            # Get window size from config, default to 20 if not set
            window = self.config.get('analysis', {}).get('position_analysis', {}).get('imbalance', {}).get('window', 20)

            # Get recent data
            recent_data = df.tail(window)

            # Calculate price changes
            price_changes = recent_data['close'].pct_change()
            volume_changes = recent_data['volume'].pct_change()

            # Calculate imbalance ratio
            positive_moves = price_changes > 0
            negative_moves = price_changes < 0

            if len(positive_moves) == 0 or len(negative_moves) == 0:
                return 50.0

            # Calculate average volume on up/down moves
            up_volume = volume_changes[positive_moves].mean() if any(positive_moves) else 0
            down_volume = volume_changes[negative_moves].mean() if any(negative_moves) else 0

            # Avoid division by zero
            if down_volume == 0:
                return 75.0 if up_volume > 0 else 50.0

            # Calculate imbalance ratio
            ratio = up_volume / down_volume if down_volume != 0 else 1.0

            # Convert ratio to score
            if ratio > 1.5:
                score = 75.0
            elif ratio < 0.5:
                score = 25.0
            else:
                score = 50.0 + (ratio - 1.0) * 25.0

            return float(np.clip(score, 0, 100))

        except Exception as e:
            logger.error(f"Error calculating imbalance score: {str(e)}")
            return 50.0

    def _calculate_value_area_score(self, df: pd.DataFrame) -> float:
        """Calculate value area score with alignment consideration."""
        try:
            if df.empty or 'close' not in df.columns:
                return 50.0

            # Calculate existing value areas
            price_min = float(df['low'].min())
            price_max = float(df['high'].max())
            current_price = float(df['close'].iloc[-1])
            
            # Calculate value area levels
            value_profile = self._calculate_value_profile(df)
            poc_price = value_profile['poc']
            va_high = value_profile['va_high']
            va_low = value_profile['va_low']
            
            # Calculate distance to each level
            distances = {
                'poc': abs(current_price - poc_price) / poc_price,
                'va_high': abs(current_price - va_high) / va_high,
                'va_low': abs(current_price - va_low) / va_low
            }
            
            # Score based on alignment of levels
            alignment_count = sum(1 for d in distances.values() if d < 0.001)  # 0.1% threshold
            
            if alignment_count >= 2:
                # High alignment - potential reversal zone
                return 75.0 if current_price < poc_price else 25.0
            elif alignment_count == 1:
                # Single level - potential continuation
                return 25.0 if current_price < poc_price else 75.0
            else:
                # No significant levels - neutral
                return 50.0

        except Exception as e:
            self.logger.error(f"Error calculating value area score: {str(e)}")
            return 50.0

    def _identify_swing_points(self, df: pd.DataFrame) -> Dict[str, float]:
        """Identify swing points with divergence as confirmation bonus."""
        try:
            # Calculate base swing points
            base_levels = self._calculate_base_swing_levels(df)  # ISSUE: This method is missing
            
            # Calculate divergence confirmation bonus
            divergence_bonus = self._calculate_swing_divergence_bonus(df)
            
            # Apply divergence bonus with reduced impact
            final_score = base_levels['score'] + divergence_bonus * 0.1
            
            return {
                'base_score': base_levels['score'],
                'divergence_bonus': divergence_bonus,
                'final_score': final_score,
                'levels': base_levels['levels']
            }
            
        except Exception as e:
            logger.error(f"Error identifying swing points: {str(e)}")
            return {'support': None, 'resistance': None}

    def _calculate_timeframe_score(self, df, timeframe):
        """
        Calculate the price structure score for a specific timeframe.
        
        Args:
            df (pd.DataFrame): OHLCV data for the timeframe
            timeframe (str): The timeframe identifier
            
        Returns:
            float: Score between 0-100
        """
        try:
            self.logger.debug(f"\n=== Calculating {timeframe} Timeframe Score ===")
            
            # 1. Calculate order blocks
            self.logger.debug(f"1. Calculating Order Blocks...")
            order_block = self._calculate_order_blocks(df)
            
            # Log the order block information, not trying to format it as a float
            self.logger.debug(f"   Order Block: {order_block}")
            
            # Calculate order block score based on proximity to current price
            current_price = df['close'].iloc[-1]
            
            # Calculate scores for bullish and bearish order blocks
            bullish_scores = []
            for block in order_block['bullish']:
                distance = abs(current_price - block['price']) / current_price
                score = max(0, 100 - distance * 1000)  # Closer blocks have higher scores
                bullish_scores.append(score * block['strength'] / 100)
                
            bearish_scores = []
            for block in order_block['bearish']:
                distance = abs(current_price - block['price']) / current_price
                score = max(0, 100 - distance * 1000)  # Closer blocks have higher scores
                bearish_scores.append(score * block['strength'] / 100)
                
            # Calculate final order block score
            if bullish_scores and bearish_scores:
                max_bullish = max(bullish_scores) if bullish_scores else 0
                max_bearish = max(bearish_scores) if bearish_scores else 0
                
                # If price is below strongest bullish block, bullish signal
                # If price is above strongest bearish block, bearish signal
                if current_price < order_block['bullish'][0]['price']:
                    order_block_score = 50 + max_bullish / 2
                elif current_price > order_block['bearish'][0]['price']:
                    order_block_score = 50 - max_bearish / 2
                else:
                    order_block_score = 50
            else:
                order_block_score = 50
                
            self.logger.debug(f"   Order Block Score: {order_block_score:.2f}")
            
            # 2. Calculate support/resistance levels
            # ... rest of the method remains unchanged ...
            
            # Return a default score for now
            return 50.0
            
        except Exception as e:
            self.logger.error(f"Error calculating timeframe score: {str(e)}")
            self.logger.debug(f"Full error:\n{traceback.format_exc()}")
            return 50.0

    def _calculate_structural_score(self, df: pd.DataFrame) -> float:
        """Calculate structural score based on price action breaks."""
        try:
            if df.empty or 'close' not in df.columns:
                return 50.0

            # Get recent price action
            window = 20
            recent_data = df.tail(window)
            
            # Calculate local structure
            highs = recent_data['high'].rolling(5).max()
            lows = recent_data['low'].rolling(5).min()
            
            # Detect breaks in structure
            break_up = recent_data['close'] > highs.shift(1)
            break_down = recent_data['close'] < lows.shift(1)
            
            # Calculate break strength
            up_strength = break_up.sum() / window
            down_strength = break_down.sum() / window
            
            # Calculate distance from key levels
            current_price = recent_data['close'].iloc[-1]
            nearest_high = highs[highs > current_price].min()
            nearest_low = lows[lows < current_price].max()
            
            # Score based on break patterns and level proximity
            if up_strength > down_strength:
                score = 75 - (up_strength * 25)  # Higher chance of reversal
            else:
                score = 25 + (down_strength * 25)  # Higher chance of reversal
            
            return float(np.clip(score, 0, 100))
            
        except Exception as e:
            logger.error(f"Error calculating structural score: {str(e)}")
            return 50.0

    def _calculate_sr_alignment_score(self, df: pd.DataFrame) -> float:
        """Calculate support/resistance alignment score."""
        try:
            # Calculate swing points on multiple timeframes
            tf_multipliers = [1, 2, 4]  # Different timeframe views
            swing_points = []
            
            for multiplier in tf_multipliers:
                # Resample data
                resampled = df.copy()
                if multiplier > 1:
                    resampled = df.iloc[::multiplier]
                
                # Get swing points for this timeframe
                points = self._identify_swing_points(resampled)
                if points['support'] is not None:
                    swing_points.append(points['support'])
                if points['resistance'] is not None:
                    swing_points.append(points['resistance'])
            
            if not swing_points:
                return 50.0
            
            # Calculate clusters
            clusters = self._identify_price_clusters(swing_points, threshold=0.002)
            
            # Score based on alignment and current price position
            current_price = df['close'].iloc[-1]
            score = self._calculate_alignment_score(current_price, clusters)
            
            return float(np.clip(score, 0, 100))
            
        except Exception as e:
            logger.error(f"Error calculating SR alignment: {str(e)}")
            return 50.0

    def _calculate_volume_node_score(self, df: pd.DataFrame) -> float:
        """Calculate score based on both high and low volume nodes analysis."""
        try:
            if df.empty or not all(col in df.columns for col in ['close', 'volume']):
                return 50.0
            
            # Calculate volume nodes with more granular bins for better resolution
            price_levels = pd.qcut(df['close'], q=50, duplicates='drop')  # Increased bins
            volume_profile = df.groupby(price_levels, observed=False)['volume'].sum()
            
            # Calculate volume thresholds
            mean_volume = volume_profile.mean()
            std_volume = volume_profile.std()
            
            # Identify significant nodes with more precise thresholds
            high_volume_nodes = volume_profile[volume_profile > mean_volume + std_volume]
            # More stringent criteria for LVNs to better identify "air pockets"
            low_volume_nodes = volume_profile[volume_profile < mean_volume - (std_volume * 1.2)]
            
            if high_volume_nodes.empty and low_volume_nodes.empty:
                return 50.0

            # Calculate node strength and proximity
            current_price = df['close'].iloc[-1]
            node_scores = []
            
            # Process high volume nodes (value areas)
            for level, volume in high_volume_nodes.items():
                distance = abs(level.mid - current_price) / current_price
                strength = (volume - mean_volume) / std_volume
                
                if distance < 0.01:  # Within 1% of node
                    # Higher score when price is above HVN (support)
                    node_score = 75 if current_price > level.mid else 25
                else:
                    # Neutral score weighted by node strength
                    node_score = 50 + (strength * 5)
                
                node_scores.append(('hvn', node_score))
            
            # Process low volume nodes (air pockets)
            for level, volume in low_volume_nodes.items():
                distance = abs(level.mid - current_price) / current_price
                weakness = (mean_volume - volume) / std_volume
                
                # Check if we're approaching LVN
                if distance < 0.02:  # Within 2% of LVN
                    # Calculate trend direction
                    trend = self._calculate_short_term_trend(df)
                    
                    if trend > 0:  # Uptrend
                        # Higher score if LVN is above (potential acceleration zone)
                        node_score = 80 if current_price < level.mid else 40
                    else:  # Downtrend
                        # Lower score if LVN is below (potential acceleration zone)
                        node_score = 40 if current_price > level.mid else 80
                else:
                    # Neutral score with slight bias based on LVN position
                    node_score = 50 + (weakness * 2 * (-1 if current_price > level.mid else 1))
                
                node_scores.append(('lvn', node_score))
            
            # Weight nodes based on market conditions
            trend_strength = abs(self._calculate_short_term_trend(df))
            
            if trend_strength > 0.02:  # Strong trend
                # Give more weight to LVNs in trending markets
                hvn_weight = 0.4
                lvn_weight = 0.6
            else:  # Ranging market
                # Give more weight to HVNs in ranging markets
                hvn_weight = 0.7
                lvn_weight = 0.3
            
            # Calculate separate scores for HVNs and LVNs
            hvn_scores = [score for node_type, score in node_scores if node_type == 'hvn']
            lvn_scores = [score for node_type, score in node_scores if node_type == 'lvn']
            
            final_score = 0.0
            if hvn_scores:
                final_score += np.mean(hvn_scores) * hvn_weight
            if lvn_scores:
                final_score += np.mean(lvn_scores) * lvn_weight
            
            if not hvn_scores and not lvn_scores:
                return 50.0
            
            return float(np.clip(final_score, 0, 100))
            
        except Exception as e:
            logger.error(f"Error calculating volume node score: {str(e)}")
            return 50.0

    def _calculate_short_term_trend(self, df: pd.DataFrame, period: int = 10) -> float:
        """Calculate short-term trend direction and strength."""
        try:
            if len(df) < period:
                return 0.0
            
            # Get recent closes
            recent_closes = df['close'].tail(period)
            
            # Calculate linear regression slope
            x = np.arange(len(recent_closes))
            slope, _ = np.polyfit(x, recent_closes, 1)
            
            # Normalize slope to percentage
            return slope / recent_closes.mean()

        except Exception as e:
            logger.error(f"Error calculating trend: {str(e)}")
            return 0.0

    def _calculate_weighted_score(self, timeframe_scores: Dict[str, float]) -> float:
        """Calculate weighted score across timeframes."""
        try:
            total_score = 0.0
            total_weight = 0.0
            
            for tf, weight in self.timeframe_weights.items():
                if tf in timeframe_scores:
                    total_score += timeframe_scores[tf] * weight
                    total_weight += weight
                    
            return total_score / total_weight if total_weight > 0 else 50.0
            
        except Exception as e:
            self.logger.error(f"Error calculating weighted score: {str(e)}")
            return 50.0

    def _calculate_volume_profile(self, data: Union[pd.DataFrame, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate volume profile metrics including Point of Control and Value Area.
        
        This method analyzes price and volume data to identify key volume-based price levels:
        - Point of Control (POC): The price level with the highest trading volume
        - Value Area High (VAH): Upper boundary containing specified % of volume
        - Value Area Low (VAL): Lower boundary containing specified % of volume
        
        Args:
            data: OHLCV data as DataFrame or dictionary with nested structure
            
        Returns:
            Dict containing:
                - poc: Point of Control price
                - va_high: Value Area High price
                - va_low: Value Area Low price
                - score: Volume profile score (0-100) based on price position
        """
        try:
            self.logger.debug("Calculating volume profile metrics")
            
            # Convert dictionary to DataFrame if needed
            if isinstance(data, dict):
                if 'data' in data:
                    df = pd.DataFrame(data['data'])
                    self.logger.debug(f"Extracted DataFrame from 'data' key, shape: {df.shape}")
                else:
                    df = pd.DataFrame(data)
                    self.logger.debug(f"Converted dict to DataFrame, shape: {df.shape}")
            elif isinstance(data, pd.DataFrame):
                df = data.copy()
                self.logger.debug(f"Using provided DataFrame, shape: {df.shape}")
            else:
                self.logger.error(f"Invalid data type for volume profile: {type(data)}")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            if df.empty or len(df) == 0:
                self.logger.warning("Empty DataFrame provided for volume profile calculation")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            # Ensure required columns exist
            required_cols = ['close', 'volume']
            if not all(col in df.columns for col in required_cols):
                missing = [col for col in required_cols if col not in df.columns]
                self.logger.error(f"Missing required columns for volume profile: {missing}")
                self.logger.debug(f"Available columns: {list(df.columns)}")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            # Calculate price levels with adaptive bin size based on data volatility
            price_min = df['close'].min()
            price_max = df['close'].max()
            price_range = price_max - price_min
            price_std = df['close'].std()
            
            # Determine optimal number of bins (more bins for higher volatility)
            adaptive_bins = max(20, min(self.volume_profile_bins, 
                                       int(price_range / (price_std * 0.1))))
            self.logger.debug(f"Using {adaptive_bins} bins for volume profile")
            
            bins = np.linspace(price_min, price_max, num=adaptive_bins)
            
            # Create volume profile
            df['price_level'] = pd.cut(df['close'], bins=bins, labels=bins[:-1])
            volume_profile = df.groupby('price_level')['volume'].sum()
            
            # Find Point of Control (POC)
            if volume_profile.empty:
                self.logger.warning("Empty volume profile, returning default values")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            poc = float(volume_profile.idxmax())
            
            # Calculate Value Area (70% of total volume)
            total_volume = volume_profile.sum()
            target_volume = total_volume * self.value_area_volume
            sorted_profile = volume_profile.sort_values(ascending=False)
            cumsum = sorted_profile.cumsum()
            value_area = sorted_profile[cumsum <= target_volume]
            
            if value_area.empty:
                self.logger.warning("Empty value area, using fallback calculation")
                # Fallback to simple percentage around POC
                value_area_range = price_range * 0.2
                va_high = poc + value_area_range/2
                va_low = poc - value_area_range/2
            else:
                va_high = float(max(value_area.index))
                va_low = float(min(value_area.index))
            
            # Calculate score based on price position relative to value area
            current_price = float(df['close'].iloc[-1])
            
            self.logger.debug(f"Volume Profile Results:")
            self.logger.debug(f"- Current Price: {current_price:.2f}")
            self.logger.debug(f"- POC: {poc:.2f}")
            self.logger.debug(f"- Value Area: {va_low:.2f} - {va_high:.2f}")
            
            # Score calculation based on price position
            if current_price < va_low:
                # Below value area - bearish bias
                distance_ratio = (current_price - va_low) / (va_low - price_min) if va_low != price_min else -1
                score = 30 * (1 + distance_ratio)
                position = "below_va"
            elif current_price > va_high:
                # Above value area - bullish bias
                distance_ratio = (current_price - va_high) / (price_max - va_high) if price_max != va_high else 1
                score = 70 + 30 * (1 - distance_ratio)
                position = "above_va"
            else:
                # Inside value area - score based on position relative to POC
                position_ratio = (current_price - va_low) / (va_high - va_low) if va_high != va_low else 0.5
                # Use tanh for smooth transition around POC
                score = 50 * (1 + np.tanh((position_ratio - 0.5) * 2))
                position = "inside_va"
                
            final_score = float(np.clip(score, 0, 100))
            
            self.logger.debug(f"- Position: {position}")
            self.logger.debug(f"- Score: {final_score:.2f}")
                
            return {
                'poc': poc,
                'va_high': va_high,
                'va_low': va_low,
                'score': final_score,
                'position': position
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating volume profile: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return {
                'poc': 0,
                'va_high': 0,
                'va_low': 0,
                'score': 50.0
            }

    def _calculate_composite_value(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate composite value score based on price relative to key value indicators.
        
        This method analyzes the relationship between current price and key value indicators:
        - VWAP (Volume-Weighted Average Price)
        - Moving averages (SMA20, SMA50)
        - Recent price action
        
        The composite value score indicates whether the current price is overvalued or 
        undervalued relative to these indicators.
        
        Args:
            df: DataFrame containing OHLCV data
            
        Returns:
            Dict containing:
                - score: Composite value score (0-100)
                - components: Individual component scores
                - metrics: Raw metric values used in calculation
        """
        try:
            self.logger.debug("Calculating composite value score")
            
            if df is None or df.empty or len(df) < 20:
                self.logger.warning("Insufficient data for composite value calculation")
                return {
                    'score': 50.0,
                    'components': {},
                    'metrics': {}
                }
                
            # Validate required columns
            required_cols = ['close', 'volume']
            if not all(col in df.columns for col in required_cols):
                missing = [col for col in required_cols if col not in df.columns]
                self.logger.error(f"Missing required columns for composite value: {missing}")
                return {
                    'score': 50.0,
                    'components': {},
                    'metrics': {}
                }
            
            # Create a copy to avoid modifying original
            df_copy = df.copy()
            
            # Calculate VWAP
            try:
                df_copy['vwap'] = (df_copy['close'] * df_copy['volume']).cumsum() / df_copy['volume'].cumsum()
            except Exception as e:
                self.logger.warning(f"Error calculating VWAP: {str(e)}")
                df_copy['vwap'] = df_copy['close']  # Fallback to close price
            
            # Calculate moving averages with dynamic periods based on available data
            periods = [min(period, len(df_copy) - 5) for period in [20, 50] if period < len(df_copy) - 5]
            
            for period in periods:
                try:
                    df_copy[f'sma{period}'] = df_copy['close'].rolling(window=period).mean()
                except Exception as e:
                    self.logger.warning(f"Error calculating SMA{period}: {str(e)}")
                    df_copy[f'sma{period}'] = df_copy['close']  # Fallback to close price
            
            # Get latest values
            current_price = df_copy['close'].iloc[-1]
            metrics = {
                'current_price': current_price,
                'vwap': df_copy['vwap'].iloc[-1] if 'vwap' in df_copy else current_price
            }
            
            # Add available SMAs to metrics
            for period in periods:
                sma_key = f'sma{period}'
                if sma_key in df_copy:
                    metrics[sma_key] = df_copy[sma_key].iloc[-1]
            
            # Calculate distances as percentage
            components = {}
            
            # VWAP component (40% weight)
            if 'vwap' in metrics:
                vwap_dist = (current_price - metrics['vwap']) / metrics['vwap']
                vwap_score = 50 + (vwap_dist * 100)  # Scale to 0-100 range
                components['vwap'] = float(np.clip(vwap_score, 0, 100))
            
            # SMA components (30% each for SMA20, SMA50)
            for period in periods:
                sma_key = f'sma{period}'
                if sma_key in metrics:
                    sma_dist = (current_price - metrics[sma_key]) / metrics[sma_key]
                    sma_score = 50 + (sma_dist * 100)  # Scale to 0-100 range
                    components[sma_key] = float(np.clip(sma_score, 0, 100))
            
            # Calculate weighted composite score
            weights = {
                'vwap': 0.4,
                'sma20': 0.3,
                'sma50': 0.3
            }
            
            # Adjust weights if some components are missing
            total_weight = sum(weights[k] for k in components.keys() if k in weights)
            if total_weight == 0:
                self.logger.warning("No valid components for composite value calculation")
                return {
                    'score': 50.0,
                    'components': {},
                    'metrics': metrics
                }
                
            # Normalize weights
            norm_weights = {k: weights[k] / total_weight for k in components.keys() if k in weights}
            
            # Calculate final score
            final_score = sum(components[k] * norm_weights[k] for k in components.keys() if k in norm_weights)
            
            self.logger.debug(f"Composite Value Results:")
            self.logger.debug(f"- Current Price: {current_price:.2f}")
            for k, v in metrics.items():
                if k != 'current_price':
                    self.logger.debug(f"- {k}: {v:.2f}")
            self.logger.debug(f"- Component Scores: {components}")
            self.logger.debug(f"- Final Score: {final_score:.2f}")
            
            return {
                'score': float(np.clip(final_score, 0, 100)),
                'components': components,
                'metrics': metrics
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating composite value score: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return {
                'score': 50.0,
                'components': {},
                'metrics': {}
            }

    def _calculate_sr_levels(self, df: pd.DataFrame) -> float:
        """Calculate support/resistance levels using DBSCAN clustering and Market Profile."""
        debug = DebugMetrics(start_time=time.time())
        
        try:
            if len(df) < 20:
                return 50.0
            
            logger.debug("Starting S/R level analysis with clustering and Market Profile")
            
            # Prepare price and volume data
            prices = df['close'].values.reshape(-1, 1)
            volumes = df['volume'].values
            current_price = df['close'].iloc[-1]
            
            # 1. DBSCAN Clustering for price levels
            # Scale epsilon based on price volatility
            price_std = df['close'].std()
            eps = price_std * 0.001  # Adaptive epsilon
            
            clustering = DBSCAN(
                eps=eps,
                min_samples=3,  # Minimum points to form a cluster
                n_jobs=-1
            ).fit(prices, sample_weight=volumes)
            
            # Get cluster centers and strengths
            cluster_data = defaultdict(lambda: {'prices': [], 'volumes': []})
            for idx, label in enumerate(clustering.labels_):
                if label != -1:  # Ignore noise points
                    cluster_data[label]['prices'].append(prices[idx][0])
                    cluster_data[label]['volumes'].append(volumes[idx])
            
            sr_levels = []
            for label, data in cluster_data.items():
                # Volume-weighted average price for cluster
                vwap = np.average(data['prices'], weights=data['volumes'])
                total_volume = sum(data['volumes'])
                price_range = max(data['prices']) - min(data['prices'])
                
                sr_levels.append({
                    'price': vwap,
                    'strength': total_volume / df['volume'].sum(),
                    'range': price_range
                })
            
            # 2. Market Profile Integration
            time_blocks = 30  # Number of time blocks for TPO
            price_blocks = 100  # Number of price blocks
            
            # Create time-price matrix
            matrix = np.zeros((price_blocks, time_blocks))
            
            # Calculate price levels
            price_min = df['low'].min()
            price_max = df['high'].max()
            price_step = (price_max - price_min) / price_blocks
            
            # Fill TPO matrix
            for t in range(time_blocks):
                block_data = df.iloc[t::time_blocks]  # Get data for this time block
                if len(block_data) == 0:
                    continue
                
                for _, row in block_data.iterrows():
                    price_idx = int((row['close'] - price_min) / price_step)
                    if 0 <= price_idx < price_blocks:
                        matrix[price_idx, t] = 1
            
            # Calculate TPO profile
            tpo_profile = matrix.sum(axis=1)
            price_levels = np.linspace(price_min, price_max, price_blocks)
            
            # Find TPO peaks
            tpo_peaks, _ = find_peaks(tpo_profile, distance=5)
            
            # Add TPO-based levels
            for peak in tpo_peaks:
                price_level = price_levels[peak]
                tpo_strength = tpo_profile[peak] / time_blocks
                
                sr_levels.append({
                    'price': price_level,
                    'strength': tpo_strength,
                    'range': price_step * 2
                })
            
            # Combine and score levels
            if not sr_levels:
                logger.warning("No S/R levels detected")
                return 50.0
            
            # Sort levels by strength
            sr_levels.sort(key=lambda x: x['strength'], reverse=True)
            
            # Calculate score components
            
            # 1. Distance to nearest strong level (40%)
            distances = []
            for level in sr_levels:
                dist = abs(current_price - level['price']) / current_price
                strength_weighted_dist = dist / (level['strength'] + 0.001)  # Avoid division by zero
                distances.append((strength_weighted_dist, level['strength']))
            
            nearest_dist, nearest_strength = min(distances, key=lambda x: x[0])
            distance_score = 100 * (1 - min(nearest_dist * 10, 1.0))
            
            # 2. Level strength and clustering (30%)
            strength_score = 100 * nearest_strength
            
            # 3. Level alignment across methods (30%)
            level_alignment = self._calculate_level_alignment(sr_levels, current_price)
            
            # Combine scores
            final_score = (
                distance_score * 0.4 +
                strength_score * 0.3 +
                level_alignment * 0.3
            )
            
            # Add debug metrics
            debug.metrics.update({
                'detected_levels': len(sr_levels),
                'nearest_level_distance': nearest_dist,
                'nearest_level_strength': nearest_strength,
                'distance_score': distance_score,
                'strength_score': strength_score,
                'alignment_score': level_alignment
            })
            
            # Detailed logging
            logger.debug(f"S/R Analysis Results:")
            logger.debug(f"- Detected Levels: {len(sr_levels)}")
            logger.debug(f"- Nearest Level Distance: {nearest_dist:.4f}")
            logger.debug(f"- Nearest Level Strength: {nearest_strength:.4f}")
            logger.debug(f"- Distance Score: {distance_score:.2f}")
            logger.debug(f"- Strength Score: {strength_score:.2f}")
            logger.debug(f"- Alignment Score: {level_alignment:.2f}")
            logger.debug(f"- Final Score: {final_score:.2f}")
            
            return float(np.clip(final_score, 0, 100))
            
        except Exception as e:
            debug.error_count += 1
            raise

    def _calculate_level_alignment(self, sr_levels: List[Dict[str, float]], 
                                     current_price: float) -> float:
        """Calculate alignment score for S/R levels."""
        try:
            if not sr_levels:
                return 0.0
            
            # Group nearby levels
            grouped_levels = []
            current_group = []
            
            # Sort levels by price
            sorted_levels = sorted(sr_levels, key=lambda x: x['price'])
            
            for level in sorted_levels:
                if not current_group:
                    current_group.append(level)
                else:
                    # Check if level is within range of group
                    group_avg = np.mean([l['price'] for l in current_group])
                    if abs(level['price'] - group_avg) / group_avg < 0.001:  # 0.1% threshold
                        current_group.append(level)
                    else:
                        if len(current_group) > 1:
                            grouped_levels.append(current_group)
                        current_group = [level]
            
            if len(current_group) > 1:
                grouped_levels.append(current_group)
            
            # Calculate alignment score
            if not grouped_levels:
                return 0.0
            
            # Score based on number and strength of aligned levels
            max_alignment = 0.0
            for group in grouped_levels:
                group_strength = sum(level['strength'] for level in group)
                group_size = len(group)
                alignment = group_strength * (1 + np.log(group_size))  # Logarithmic scaling
                max_alignment = max(max_alignment, alignment)
            
            return 100 * min(max_alignment, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating level alignment: {str(e)}")
            return 0.0

    def _calculate_price_position(self, current_price: float, 
                                swing_points: Dict[str, Any], 
                                value_area: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate price position relative to key levels."""
        try:
            # Get support/resistance levels
            support = swing_points.get('support', {}).get('price')
            resistance = swing_points.get('resistance', {}).get('price')
            
            # Get value area levels
            va_high = value_area.get('va_high')
            va_low = value_area.get('va_low')
            poc = value_area.get('poc')
            
            # Check if price is in reversal zone
            in_reversal_zone = False
            near_resistance = False
            near_support = False
            
            if support and resistance:
                # Calculate distances
                support_dist = abs(current_price - support) / current_price
                resistance_dist = abs(current_price - resistance) / current_price
                
                # Check if near levels (within 0.2%)
                near_support = support_dist < 0.002
                near_resistance = resistance_dist < 0.002
                
                # Price is in reversal zone if near support/resistance
                in_reversal_zone = near_support or near_resistance
                
            # Check value area alignment
            if va_high and va_low and poc:
                va_position = (current_price - va_low) / (va_high - va_low)
                near_poc = abs(current_price - poc) / current_price < 0.002
                
                # Also consider reversal zone if at value area extremes with POC alignment
                if near_poc and (va_position > 0.8 or va_position < 0.2):
                    in_reversal_zone = True
                
            return {
                'in_reversal_zone': in_reversal_zone,
                'near_resistance': near_resistance,
                'near_support': near_support,
                'value_area_position': va_position if 'va_position' in locals() else 0.5
            }
            
        except Exception as e:
            logger.error(f"Error calculating price position: {str(e)}")
            return {'in_reversal_zone': False}

    def _identify_price_clusters(self, points: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
        """Identify clusters of price levels."""
        try:
            if not points:
                return []
            
            # Extract prices and sort
            prices = [p['price'] for p in points if 'price' in p]
            prices.sort()
            
            clusters = []
            current_cluster = []
            
            for price in prices:
                if not current_cluster:
                    current_cluster.append(price)
                else:
                    # Check if price is within threshold of cluster
                    cluster_avg = sum(current_cluster) / len(current_cluster)
                    if abs(price - cluster_avg) / cluster_avg <= threshold:
                        current_cluster.append(price)
                    else:
                        # Start new cluster
                        if len(current_cluster) > 1:
                            clusters.append({
                                'price': sum(current_cluster) / len(current_cluster),
                                'strength': len(current_cluster)
                            })
                        current_cluster = [price]
                        
            # Add final cluster
            if len(current_cluster) > 1:
                clusters.append({
                    'price': sum(current_cluster) / len(current_cluster),
                    'strength': len(current_cluster)
                })
            
            return clusters
            
        except Exception as e:
            logger.error(f"Error identifying price clusters: {str(e)}")
            return []

    def _calculate_alignment_score(self, current_price: float, clusters: List[Dict[str, Any]]) -> float:
        """Calculate alignment score based on price clusters."""
        try:
            if not clusters:
                return 50.0
            
            # Find nearest cluster
            distances = []
            for cluster in clusters:
                price = cluster['price']
                strength = cluster['strength']
                distance = abs(current_price - price) / current_price
                distances.append((distance, strength))
            
            # Sort by distance
            distances.sort(key=lambda x: x[0])
            nearest_distance, nearest_strength = distances[0]
            
            # Calculate score based on distance and cluster strength
            distance_score = max(0, 1 - (nearest_distance * 100))
            strength_score = min(nearest_strength / len(clusters), 1.0)
            
            score = 50 + (distance_score * 25) + (strength_score * 25)
            return float(np.clip(score, 0, 100))
            
        except Exception as e:
            logger.error(f"Error calculating alignment score: {str(e)}")
            return 50.0

    def _calculate_value_area(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate value area levels."""
        try:
            if df.empty:
                return {'poc': 0, 'va_high': 0, 'va_low': 0}
            
            # Calculate volume profile with observed=True to handle the warning
            price_levels = pd.qcut(df['close'], q=20, duplicates='drop')
            volume_profile = df.groupby(price_levels, observed=True)['volume'].sum()
            
            # Get POC
            poc_level = volume_profile.idxmax()
            poc = poc_level.mid
            
            # Calculate value area (70% of volume)
            total_volume = volume_profile.sum()
            sorted_profile = volume_profile.sort_values(ascending=False)
            value_area = sorted_profile.cumsum() <= (total_volume * 0.7)
            value_area_levels = sorted_profile[value_area].index
            
            return {
                'poc': float(poc),
                'va_high': float(value_area_levels.max().right),
                'va_low': float(value_area_levels.min().left)
            }
            
        except Exception as e:
            logger.error(f"Error calculating value area: {str(e)}")
            return {'poc': 0, 'va_high': 0, 'va_low': 0}

    def _interpret_timeframe_score(self, score: float) -> str:
        """Interpret the score for a single timeframe."""
        try:
            if score >= 70:
                return "Strongly Bullish"
            elif score >= 60:
                return "Moderately Bullish"
            elif score >= 45:
                return "Slightly Bullish"
            elif score > 55:
                return "Neutral"
            elif score >= 40:
                return "Slightly Bearish"
            elif score >= 30:
                return "Moderately Bearish"
            else:
                return "Strongly Bearish"
            
        except Exception as e:
            logger.error(f"Error interpreting timeframe score: {str(e)}")
            return "Unknown"

    def _get_position_interpretation(self, component_scores: Dict[str, float], 
                                       weighted_score: float) -> Dict[str, Any]:
        """Get interpretation of position analysis results."""
        try:
            # Determine overall bias
            if weighted_score >= 70:
                bias = "Strongly Bullish"
            elif weighted_score >= 60:
                bias = "Moderately Bullish"
            elif weighted_score <= 30:
                bias = "Strongly Bearish"
            elif weighted_score <= 40:
                bias = "Moderately Bearish"
            else:
                bias = "Neutral"
            
            # Analyze component alignment
            alignment = "Mixed"
            if all(score > 60 for score in component_scores.values()):
                alignment = "Bullish Aligned"
            elif all(score < 40 for score in component_scores.values()):
                alignment = "Bearish Aligned"
            
            # Calculate confidence score
            confidence = self._calculate_confidence(component_scores)
            
            return {
                'bias': bias,
                'alignment': alignment,
                'components': {
                    name: self._interpret_component_score(name, score)
                    for name, score in component_scores.items()
                },
                'confidence': confidence,
                'strength': 'Strong' if abs(weighted_score - 50) > 20 else 'Moderate'
            }
            
        except Exception as e:
            logger.error(f"Error getting position interpretation: {str(e)}")
            return {
                'bias': 'Neutral',
                'alignment': 'Unknown',
                'components': {},
                'confidence': 0.0,
                'strength': 'Unknown'
            }

    def _calculate_confidence(self, component_scores: Dict[str, float]) -> float:
        """Calculate confidence score based on component scores."""
        try:
            if not component_scores:
                return 0.0
            
            # Calculate mean and standard deviation
            scores = list(component_scores.values())
            mean_score = np.mean(scores)
            std_score = np.std(scores)
            
            # Calculate alignment - lower std means better alignment
            alignment = 1 - min(std_score / 50, 1.0)  # Normalize std to 0-1
            
            # Calculate trend strength
            trend_strength = abs(mean_score - 50) / 50
            
            # Combine alignment and strength
            confidence = (alignment * 0.6) + (trend_strength * 0.4)
            
            return float(np.clip(confidence * 100, 0, 100))
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            return 0.0

    async def calculate(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate price structure indicator scores with detailed analysis.
        
        Args:
            market_data: Dictionary containing OHLCV and other market data
            
        Returns:
            Dict containing indicator scores, components, signals and metadata
        """
        try:
            self.logger.debug("\n=== Calculating Price Structure Score ===")
            
            # Validate input
            if not self.validate_input(market_data):
                self.logger.error("Invalid input data for price structure analysis")
                return self._get_default_scores('Invalid input data')
                
            # Get OHLCV data
            ohlcv_data = market_data.get('ohlcv', {})
            if not ohlcv_data:
                self.logger.warning("Missing OHLCV data")
                return self._get_default_scores('Missing OHLCV data')
                
            # Calculate scores for each timeframe
            timeframe_scores = await self._calculate_timeframe_scores(ohlcv_data)
            
            # Calculate divergences between timeframes
            divergences = self._analyze_timeframe_divergence(timeframe_scores)
            
            # Log multi-timeframe analysis and divergences
            symbol = market_data.get('symbol', '')
            self.log_multi_timeframe_analysis(timeframe_scores, divergences, symbol)
            
            # Calculate component scores
            component_scores = {}
            
            # Support/Resistance levels
            sr_score = self._analyze_sr_levels(ohlcv_data)
            component_scores['support_resistance'] = sr_score
            self.logger.info(f"Support/Resistance: Score={sr_score:.2f}")
            
            # Order blocks and supply/demand zones
            ob_score = self._analyze_orderblock_zones(ohlcv_data)
            component_scores['order_blocks'] = ob_score
            self.logger.info(f"Order Blocks: Score={ob_score:.2f}")
            
            # Trend position relative to key moving averages
            trend_score = self._analyze_trend_position(ohlcv_data)
            component_scores['trend_position'] = trend_score
            self.logger.info(f"Trend Position: Score={trend_score:.2f}")
            
            # Volume analysis including profile and VWAP
            volume_score = self._analyze_volume(ohlcv_data)
            component_scores['volume_profile'] = volume_score
            self.logger.info(f"Volume Profile: Score={volume_score:.2f}")
            
            # Market structure including swing points
            structure_score = self._analyze_market_structure(ohlcv_data)
            component_scores['market_structure'] = structure_score
            self.logger.info(f"Market Structure: Score={structure_score:.2f}")
            
            # Calculate composite value score (separate from market structure)
            # Use base timeframe for composite value calculation
            base_df = None
            for tf in ['base', 'ltf', 'mtf', 'htf']:
                if tf in ohlcv_data and isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                    base_df = ohlcv_data[tf]
                    break
            
            if base_df is not None:
                composite_result = self._calculate_composite_value(base_df)
                composite_value_score = composite_result['score']
                # Ensure score is on 0-100 scale where 100 is bullish
                component_scores['composite_value'] = float(np.clip(composite_value_score, 0, 100))
                self.logger.info(f"Composite Value: Score={composite_value_score:.2f}")
            else:
                # Default to neutral if no data available
                component_scores['composite_value'] = 50.0
                self.logger.warning("No valid data for composite value calculation, using default score")
            
            # Apply divergence bonuses if available
            for key, div_info in divergences.items():
                component = div_info.get('component')
                if component in component_scores:
                    # Calculate bonus based on divergence strength and type
                    strength = div_info.get('strength', 0)
                    div_type = div_info.get('type', 'neutral')
                    
                    # Bullish divergence increases score, bearish decreases
                    bonus = strength * 0.1 * (1 if div_type == 'bullish' else -1)
                    
                    # Apply bonus with limits
                    component_scores[component] = np.clip(component_scores[component] + bonus, 0, 100)
                    
                    # Store bonus in divergence info for logging
                    div_info['bonus'] = bonus
            
            # Calculate final score using our custom weighted score method
            final_score = self._compute_weighted_score(component_scores)
            
            # Extract symbol from market data
            symbol = market_data.get('symbol', '')
            
            # Log final score and component breakdown using our custom method
            self.log_indicator_results(final_score, component_scores, symbol)
            
            # Get signals
            signals = await self.get_signals(market_data)
            
            # Return standardized format with mapped component names for consistency
            mapped_components = {}
            for component, score in component_scores.items():
                config_component = self.component_mapping.get(component, component)
                mapped_components[config_component] = score
                
            return {
                'score': float(np.clip(final_score, 0, 100)),
                'components': mapped_components,
                'signals': signals,
                'timeframe_scores': timeframe_scores,
                'divergences': divergences,
                'metadata': {
                    'timestamp': int(time.time() * 1000),
                    'component_weights': self.component_weights,
                    'timeframe_weights': self.timeframe_weights
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating price structure score: {str(e)}")
            self.logger.error(traceback.format_exc())
            return self._get_default_scores(str(e))

    async def get_signals(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get position-specific signals based on component scores.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Dict containing signal information for each component
        """
        try:
            ohlcv_data = market_data.get('ohlcv', {})
            
            # Calculate all component signals
            sr_score = self._analyze_sr_levels(ohlcv_data)
            trend_score = self._analyze_trend_position(ohlcv_data)
            structure_score = self._analyze_market_structure(ohlcv_data)
            orderblock_score = self._analyze_orderblock_zones(ohlcv_data)
            volume_score = self._analyze_volume(ohlcv_data)
            
            # Generate signals with more detailed information
            signals = {
                'support_resistance': {
                    'value': sr_score,
                    'signal': 'strong_level' if sr_score > 70 else 'weak_level',
                    'bias': 'bullish' if sr_score > 60 else ('bearish' if sr_score < 40 else 'neutral'),
                    'strength': 'strong' if abs(sr_score - 50) > 25 else 'moderate'
                },
                'trend': {
                    'value': trend_score,
                    'signal': 'uptrend' if trend_score > 60 else ('downtrend' if trend_score < 40 else 'sideways'),
                    'bias': 'bullish' if trend_score > 60 else ('bearish' if trend_score < 40 else 'neutral'),
                    'strength': 'strong' if abs(trend_score - 50) > 25 else 'moderate'
                },
                'structure': {
                    'value': structure_score,
                    'signal': 'bullish' if structure_score > 60 else ('bearish' if structure_score < 40 else 'neutral'),
                    'strength': 'strong' if abs(structure_score - 50) > 25 else 'moderate'
                },
                'orderblock': {
                    'value': orderblock_score,
                    'signal': 'strong' if orderblock_score > 70 else ('weak' if orderblock_score < 40 else 'neutral'),
                    'bias': 'bullish' if orderblock_score > 60 else ('bearish' if orderblock_score < 40 else 'neutral'),
                    'strength': 'strong' if abs(orderblock_score - 50) > 25 else 'moderate'
                },
                'volume': {
                    'value': volume_score,
                    'signal': 'high' if volume_score > 70 else ('low' if volume_score < 40 else 'neutral'),
                    'strength': 'strong' if abs(volume_score - 50) > 25 else 'moderate'
                }
            }
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error getting signals: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return {}

    def _calculate_price_volume_correlation(self, df: pd.DataFrame) -> float:
        """Calculate score based on correlation between price moves and volume.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            float: Score from 0-100
        """
        try:
            if df.empty or not all(col in df.columns for col in ['close', 'volume']) or len(df) < 10:
                return 50.0
                
            # Calculate price changes
            df_copy = df.copy()
            df_copy['price_change'] = df_copy['close'].pct_change()
            df_copy['abs_price_change'] = df_copy['price_change'].abs()
            
            # Remove NaN values
            df_copy = df_copy.dropna()
            
            if len(df_copy) < 5:
                return 50.0
                
            # Calculate correlation between absolute price change and volume
            correlation = df_copy['abs_price_change'].corr(df_copy['volume'])
            
            # Calculate directional bias
            # Check if volume is higher on up days vs down days
            up_days = df_copy[df_copy['price_change'] > 0]
            down_days = df_copy[df_copy['price_change'] < 0]
            
            if len(up_days) > 0 and len(down_days) > 0:
                avg_up_volume = up_days['volume'].mean()
                avg_down_volume = down_days['volume'].mean()
                
                if avg_up_volume > avg_down_volume:
                    # Higher volume on up days is bullish
                    direction = 1.0
                else:
                    # Higher volume on down days is bearish
                    direction = -1.0
            else:
                direction = 0.0
                
            # Convert correlation to score (0-100)
            # High correlation is good, direction determines bullish/bearish
            base_score = 50 + (correlation * 25 * direction)
            
            return float(np.clip(base_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating price-volume correlation: {str(e)}")
            return 50.0

    def _analyze_market_structure(self, ohlcv_data: Dict[str, pd.DataFrame]) -> float:
        """Analyze market structure by identifying swing highs/lows and trend patterns.
        
        This method analyzes the market structure across timeframes to determine:
        - Higher highs/higher lows (bullish structure)
        - Lower highs/lower lows (bearish structure)
        - Swing point patterns and potential reversals
        - Trend strength and continuity
        
        Args:
            ohlcv_data: Dictionary of OHLCV DataFrames for different timeframes
            
        Returns:
            float: Market structure score from 0-100, where:
                - 0-30: Bearish market structure
                - 30-45: Slightly bearish structure
                - 45-55: Neutral/transitioning structure
                - 55-70: Slightly bullish structure
                - 70-100: Bullish market structure
        """
        try:
            self.logger.debug("Analyzing market structure across timeframes")
            
            # Validate input
            if not isinstance(ohlcv_data, dict) or not ohlcv_data:
                self.logger.error("Invalid OHLCV data for market structure analysis")
                return 50.0
                
            # Track scores for each timeframe
            timeframe_scores = {}
            
            # Process each timeframe
            for tf, tf_weight in self.timeframe_weights.items():
                if tf not in ohlcv_data:
                    self.logger.debug(f"Timeframe {tf} not available for market structure analysis")
                    continue
                    
                df = ohlcv_data[tf]
                if not isinstance(df, pd.DataFrame) or df.empty:
                    self.logger.debug(f"Invalid DataFrame for timeframe {tf}")
                    continue
                    
                if len(df) < 30:  # Need sufficient data for swing analysis
                    self.logger.debug(f"Insufficient data for timeframe {tf}: {len(df)} rows")
                    continue
                
                self.logger.debug(f"Analyzing market structure for timeframe {tf}")
                
                try:
                    # Identify swing highs and lows
                    window = min(5, len(df) // 10)  # Adaptive window size
                    if window < 2:
                        timeframe_scores[tf] = 50.0
                        continue
                        
                    # Find local maxima and minima
                    highs = df['high'].values
                    lows = df['low'].values
                    
                    # Use argrelextrema to find swing points
                    high_idx = argrelextrema(highs, np.greater_equal, order=window)[0]
                    low_idx = argrelextrema(lows, np.less_equal, order=window)[0]
                    
                    # Get swing high/low values
                    swing_highs = [(idx, highs[idx]) for idx in high_idx if idx < len(highs)]
                    swing_lows = [(idx, lows[idx]) for idx in low_idx if idx < len(lows)]
                    
                    # Sort by index (time)
                    swing_highs.sort(key=lambda x: x[0])
                    swing_lows.sort(key=lambda x: x[0])
                    
                    # Need at least 2 swing highs and 2 swing lows for analysis
                    if len(swing_highs) < 2 or len(swing_lows) < 2:
                        timeframe_scores[tf] = 50.0
                        continue
                        
                    # Analyze recent swing highs (last 3 or fewer)
                    recent_highs = swing_highs[-min(3, len(swing_highs)):]
                    recent_lows = swing_lows[-min(3, len(swing_lows)):]
                    
                    # Check for higher highs and higher lows (bullish)
                    higher_highs = all(recent_highs[i][1] > recent_highs[i-1][1] 
                                      for i in range(1, len(recent_highs)))
                    higher_lows = all(recent_lows[i][1] > recent_lows[i-1][1] 
                                     for i in range(1, len(recent_lows)))
                    
                    # Check for lower highs and lower lows (bearish)
                    lower_highs = all(recent_highs[i][1] < recent_highs[i-1][1] 
                                     for i in range(1, len(recent_highs)))
                    lower_lows = all(recent_lows[i][1] < recent_lows[i-1][1] 
                                    for i in range(1, len(recent_lows)))
                    
                    # Determine structure type and score
                    if higher_highs and higher_lows:
                        structure = 'bullish'
                        score = 75.0
                    elif lower_highs and lower_lows:
                        structure = 'bearish'
                        score = 25.0
                    elif higher_highs and not lower_lows:
                        structure = 'bullish_weak'
                        score = 65.0
                    elif lower_lows and not higher_highs:
                        structure = 'bearish_weak'
                        score = 35.0
                    else:
                        structure = 'neutral'
                        score = 50.0
                    
                    # Calculate trend strength using moving averages
                    try:
                        # Calculate EMAs
                        df_copy = df.copy()
                        
                        # Use dynamic periods based on available data
                        lookback = len(df_copy)
                        periods = []
                        
                        if lookback >= 20:
                            periods.append(20)
                        if lookback >= 50:
                            periods.append(50)
                        if lookback >= 200:
                            periods.append(200)
                            
                        if periods:
                            # Calculate EMAs for each period
                            for period in periods:
                                df_copy[f'ema{period}'] = talib.EMA(df_copy['close'], timeperiod=period)
                                
                            # Get latest values
                            latest_close = df_copy['close'].iloc[-1]
                            
                            # Check EMA alignment (bullish when shorter EMAs above longer ones)
                            ema_values = [df_copy[f'ema{period}'].iloc[-1] for period in periods]
                            
                            # Bullish alignment: EMAs in ascending order from longest to shortest
                            bullish_alignment = all(ema_values[i] > ema_values[i+1] 
                                                   for i in range(len(ema_values)-1))
                            
                            # Bearish alignment: EMAs in descending order from longest to shortest
                            bearish_alignment = all(ema_values[i] < ema_values[i+1] 
                                                   for i in range(len(ema_values)-1))
                            
                            # Adjust score based on EMA alignment
                            if bullish_alignment and structure in ['bullish', 'bullish_weak']:
                                score += 10  # Strengthen bullish score
                            elif bearish_alignment and structure in ['bearish', 'bearish_weak']:
                                score -= 10  # Strengthen bearish score
                            elif bullish_alignment and structure == 'neutral':
                                score += 5   # Slight bullish bias
                            elif bearish_alignment and structure == 'neutral':
                                score -= 5   # Slight bearish bias
                    except Exception as e:
                        self.logger.warning(f"Error calculating EMAs: {str(e)}")
                    
                    # Store timeframe score
                    timeframe_scores[tf] = float(np.clip(score, 0, 100))
                    
                except Exception as e:
                    self.logger.error(f"Error analyzing market structure for timeframe {tf}: {str(e)}")
                    self.logger.debug(traceback.format_exc())
                    timeframe_scores[tf] = 50.0
            
            # If no valid timeframes, return neutral score
            if not timeframe_scores:
                self.logger.warning("No valid timeframes for market structure analysis")
                return 50.0
                
            # Calculate weighted average across timeframes
            total_score = 0.0
            total_weight = 0.0
            
            for tf, score in timeframe_scores.items():
                weight = self.timeframe_weights.get(tf, 0.0)
                total_score += score * weight
                total_weight += weight
                
            if total_weight == 0:
                self.logger.warning("No valid weights for market structure analysis")
                return 50.0
                
            final_score = total_score / total_weight
            self.logger.debug(f"Final market structure score: {final_score:.2f}")
            
            return float(np.clip(final_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error in market structure analysis: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 50.0

    async def _calculate_timeframe_scores(self, ohlcv_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, float]]:
        """Calculate scores for each individual timeframe.
        
        Args:
            ohlcv_data: Dictionary of OHLCV DataFrames for different timeframes
            
        Returns:
            Dict mapping timeframe names to dictionaries of component scores
        """
        try:
            timeframe_scores = {}
            
            for tf in self.timeframe_weights.keys():
                if tf not in ohlcv_data:
                    self.logger.debug(f"Timeframe {tf} not available")
                    continue
                    
                df = ohlcv_data[tf]
                if not isinstance(df, pd.DataFrame) or df.empty:
                    self.logger.debug(f"Invalid DataFrame for timeframe {tf}")
                    continue
                
                self.logger.debug(f"Calculating score for timeframe {tf}")
                
                try:
                    # Calculate score for this timeframe
                    tf_score = self._calculate_timeframe_score(df, tf)
                    
                    # Convert single float score to a dictionary of component scores
                    # This ensures compatibility with log_multi_timeframe_analysis
                    if isinstance(tf_score, float):
                        # Use consistent component names based on our mapping
                        timeframe_scores[tf] = {
                            'overall': tf_score,
                            'support_resistance': self._calculate_sr_levels(df),
                            'order_blocks': self._calculate_order_blocks_score(df),
                            'trend_position': self._calculate_trend_position_score(df),
                            'market_structure': self._calculate_structural_score(df)
                        }
                        
                        # Map component names for consistency
                        mapped_scores = {'overall': tf_score}
                        for component, score in timeframe_scores[tf].items():
                            if component != 'overall':
                                config_component = self.component_mapping.get(component, component)
                                mapped_scores[config_component] = score
                        
                        timeframe_scores[tf] = mapped_scores
                    else:
                        # If tf_score is already a dictionary, map the component names
                        mapped_scores = {}
                        for component, score in tf_score.items():
                            config_component = self.component_mapping.get(component, component)
                            mapped_scores[config_component] = score
                        
                        timeframe_scores[tf] = mapped_scores
                except Exception as e:
                    self.logger.error(f"Error calculating timeframe score for {tf}: {str(e)}")
                    self.logger.debug(traceback.format_exc())
                    timeframe_scores[tf] = {'overall': 50.0}
            
            return timeframe_scores
            
        except Exception as e:
            self.logger.error(f"Error calculating timeframe scores: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return {}
            
    def _calculate_order_blocks_score(self, df: pd.DataFrame) -> float:
        """Calculate score based on order blocks.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            float: Score between 0-100
        """
        try:
            order_block = self._calculate_order_blocks(df)
            current_price = df['close'].iloc[-1]
            
            # Calculate scores for bullish and bearish order blocks
            bullish_scores = []
            for block in order_block['bullish']:
                distance = abs(current_price - block['price']) / current_price
                score = max(0, 100 - distance * 1000)  # Closer blocks have higher scores
                bullish_scores.append(score * block['strength'] / 100)
                
            bearish_scores = []
            for block in order_block['bearish']:
                distance = abs(current_price - block['price']) / current_price
                score = max(0, 100 - distance * 1000)  # Closer blocks have higher scores
                bearish_scores.append(score * block['strength'] / 100)
                
            # Calculate final order block score
            if bullish_scores and bearish_scores:
                max_bullish = max(bullish_scores) if bullish_scores else 0
                max_bearish = max(bearish_scores) if bearish_scores else 0
                
                # If price is below strongest bullish block, bullish signal
                # If price is above strongest bearish block, bearish signal
                if current_price < order_block['bullish'][0]['price']:
                    order_block_score = 50 + max_bullish / 2
                elif current_price > order_block['bearish'][0]['price']:
                    order_block_score = 50 - max_bearish / 2
                else:
                    order_block_score = 50
            else:
                order_block_score = 50
                
            return float(order_block_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating order blocks score: {str(e)}")
            return 50.0
            
    def _calculate_trend_position_score(self, df: pd.DataFrame) -> float:
        """Calculate score based on trend position.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            float: Score between 0-100
        """
        try:
            # Calculate moving averages
            df['ma20'] = df['close'].rolling(window=20).mean()
            df['ma50'] = df['close'].rolling(window=50).mean()
            df['ma200'] = df['close'].rolling(window=200).mean()
            
            # Get latest values
            current_price = df['close'].iloc[-1]
            ma20 = df['ma20'].iloc[-1]
            ma50 = df['ma50'].iloc[-1]
            ma200 = df['ma200'].iloc[-1]
            
            # Calculate trend position score
            score = 50.0
            
            # Price above all MAs = bullish
            if current_price > ma20 and current_price > ma50 and current_price > ma200:
                score = 75.0
            # Price below all MAs = bearish
            elif current_price < ma20 and current_price < ma50 and current_price < ma200:
                score = 25.0
            # Price between MAs = neutral with bias
            elif current_price > ma50 and current_price > ma200:
                score = 65.0
            elif current_price < ma50 and current_price < ma200:
                score = 35.0
            
            return float(score)
            
        except Exception as e:
            self.logger.error(f"Error calculating trend position score: {str(e)}")
            return 50.0

    def _analyze_orderblock_zones(self, ohlcv_data):
        """
        Analyze order block zones in the given OHLCV data.
        
        Args:
            ohlcv_data (dict): Dictionary of OHLCV DataFrames for different timeframes
            
        Returns:
            float: Score representing the significance of order block zones
        """
        try:
            if not ohlcv_data or not isinstance(ohlcv_data, dict):
                self.logger.warning("Invalid OHLCV data for order block analysis")
                return 50.0
                
            # Get available timeframes
            available_timeframes = list(ohlcv_data.keys())
            if not available_timeframes:
                self.logger.warning("No timeframes available for order block analysis")
                return 50.0
                
            # Prioritize higher timeframes for order block analysis
            priority_timeframes = ['htf', 'mtf', 'ltf', 'base']
            timeframes_to_analyze = [tf for tf in priority_timeframes if tf in available_timeframes]
            
            if not timeframes_to_analyze:
                timeframes_to_analyze = available_timeframes
                
            # Get current price from the base timeframe
            base_df = ohlcv_data.get('base', None)
            if base_df is None or base_df.empty:
                self.logger.warning("No base timeframe data available for order block analysis")
                return 50.0
                
            current_price = base_df['close'].iloc[-1]
            
            # Analyze order blocks in each timeframe
            order_block_scores = []
            
            for tf in timeframes_to_analyze:
                df = ohlcv_data.get(tf, None)
                if df is None or df.empty or len(df) < 20:
                    continue
                    
                # Find bullish and bearish order blocks
                bullish_blocks = self._find_bullish_order_blocks(df)
                bearish_blocks = self._find_bearish_order_blocks(df)
                
                # Calculate proximity score to the nearest order block
                proximity_score = self._calculate_order_block_proximity(
                    current_price, bullish_blocks, bearish_blocks)
                
                # Weight by timeframe importance
                tf_weight = self.timeframe_weights.get(tf, 0.25)  # Default weight if not specified
                order_block_scores.append(proximity_score * tf_weight)
            
            if not order_block_scores:
                return 50.0  # Neutral score if no order blocks found
                
            # Normalize the final score
            final_score = sum(order_block_scores) / sum(self.timeframe_weights.get(tf, 0.25) 
                                                       for tf in timeframes_to_analyze)
            
            return min(max(final_score, 0.0), 100.0)
            
        except Exception as e:
            self.logger.error(f"Error analyzing order block zones: {str(e)}")
            return 50.0
            
    def _find_bullish_order_blocks(self, df):
        """
        Find bullish order blocks in the given DataFrame.
        
        Args:
            df (pd.DataFrame): OHLCV DataFrame
            
        Returns:
            list: List of bullish order blocks as (start_idx, end_idx, low, high) tuples
        """
        try:
            if df is None or df.empty or len(df) < 10:
                return []
                
            bullish_blocks = []
            
            # Look for strong bullish moves preceded by consolidation
            for i in range(3, len(df) - 1):
                # Check for a strong bullish candle
                if df['close'].iloc[i] > df['open'].iloc[i] * 1.005:  # At least 0.5% bullish candle
                    # Check if preceded by consolidation or bearish movement
                    prev_range = max(df['high'].iloc[i-3:i]) - min(df['low'].iloc[i-3:i])
                    current_range = df['high'].iloc[i] - df['low'].iloc[i]
                    
                    if current_range > prev_range * 1.5:  # Expansion after consolidation
                        # This is a potential bullish order block
                        block_low = min(df['low'].iloc[i-3:i])
                        block_high = max(df['high'].iloc[i-3:i])
                        bullish_blocks.append((i-3, i-1, block_low, block_high))
            
            return bullish_blocks
            
        except Exception as e:
            self.logger.error(f"Error finding bullish order blocks: {str(e)}")
            return []
            
    def _find_bearish_order_blocks(self, df):
        """
        Find bearish order blocks in the given DataFrame.
        
        Args:
            df (pd.DataFrame): OHLCV DataFrame
            
        Returns:
            list: List of bearish order blocks as (start_idx, end_idx, low, high) tuples
        """
        try:
            if df is None or df.empty or len(df) < 10:
                return []
                
            bearish_blocks = []
            
            # Look for strong bearish moves preceded by consolidation
            for i in range(3, len(df) - 1):
                # Check for a strong bearish candle
                if df['close'].iloc[i] < df['open'].iloc[i] * 0.995:  # At least 0.5% bearish candle
                    # Check if preceded by consolidation or bullish movement
                    prev_range = max(df['high'].iloc[i-3:i]) - min(df['low'].iloc[i-3:i])
                    current_range = df['high'].iloc[i] - df['low'].iloc[i]
                    
                    if current_range > prev_range * 1.5:  # Expansion after consolidation
                        # This is a potential bearish order block
                        block_low = min(df['low'].iloc[i-3:i])
                        block_high = max(df['high'].iloc[i-3:i])
                        bearish_blocks.append((i-3, i-1, block_low, block_high))
            
            return bearish_blocks
            
        except Exception as e:
            self.logger.error(f"Error finding bearish order blocks: {str(e)}")
            return []
            
    def _calculate_order_block_proximity(self, current_price, bullish_blocks, bearish_blocks):
        """
        Calculate proximity score to the nearest order block.
        
        Args:
            current_price (float): Current price
            bullish_blocks (list): List of bullish order blocks
            bearish_blocks (list): List of bearish order blocks
            
        Returns:
            float: Proximity score between 0 and 100
        """
        try:
            if not bullish_blocks and not bearish_blocks:
                return 50.0  # Neutral score if no order blocks
                
            # Find closest bullish block
            closest_bullish_distance = float('inf')
            for _, _, low, high in bullish_blocks:
                if current_price >= low and current_price <= high:
                    # Price is inside a bullish block
                    closest_bullish_distance = 0
                    break
                else:
                    # Calculate distance to block
                    distance = min(abs(current_price - low), abs(current_price - high))
                    closest_bullish_distance = min(closest_bullish_distance, distance)
            
            # Find closest bearish block
            closest_bearish_distance = float('inf')
            for _, _, low, high in bearish_blocks:
                if current_price >= low and current_price <= high:
                    # Price is inside a bearish block
                    closest_bearish_distance = 0
                    break
                else:
                    # Calculate distance to block
                    distance = min(abs(current_price - low), abs(current_price - high))
                    closest_bearish_distance = min(closest_bearish_distance, distance)
            
            # Normalize distances relative to current price
            if closest_bullish_distance != float('inf'):
                closest_bullish_distance = closest_bullish_distance / current_price * 100
            else:
                closest_bullish_distance = 100  # Maximum distance
                
            if closest_bearish_distance != float('inf'):
                closest_bearish_distance = closest_bearish_distance / current_price * 100
            else:
                closest_bearish_distance = 100  # Maximum distance
            
            # Calculate scores based on proximity
            bullish_score = 100 - min(closest_bullish_distance * 5, 100)  # Closer = higher score
            bearish_score = 100 - min(closest_bearish_distance * 5, 100)  # Closer = higher score
            
            # If inside a block, prioritize that signal
            if closest_bullish_distance == 0:
                return 75.0  # Bullish bias
            elif closest_bearish_distance == 0:
                return 25.0  # Bearish bias
            
            # Otherwise, calculate weighted average based on proximity
            if bullish_score > bearish_score:
                # Closer to bullish block
                return 50.0 + (bullish_score - bearish_score) / 4
            else:
                # Closer to bearish block
                return 50.0 - (bearish_score - bullish_score) / 4
            
        except Exception as e:
            self.logger.error(f"Error calculating order block proximity: {str(e)}")
            return 50.0

    def _get_default_scores(self, reason='Insufficient data'):
        """
        Return default scores when analysis cannot be performed.
        
        Args:
            reason (str): Reason for returning default scores
            
        Returns:
            dict: Dictionary containing default component scores, interpretation, and metadata
        """
        self.logger.warning(f"Returning default price structure scores: {reason}")
        
        # Default component scores
        component_scores = {
            'support_resistance': 50.0,
            'order_blocks': 50.0,
            'trend_position': 50.0,
            'volume_analysis': 50.0,
            'market_structure': 50.0
        }
        
        # Default interpretation
        interpretation = "NEUTRAL"
        
        # Default signals
        signals = {
            'support_proximity': 'NEUTRAL',
            'resistance_proximity': 'NEUTRAL',
            'trend_alignment': 'NEUTRAL',
            'orderblock_proximity': 'NEUTRAL',
            'volume_profile': 'NEUTRAL'
        }
        
        # Default metadata
        metadata = {
            'reliability': 0.5,
            'reason': reason,
            'timeframes_analyzed': [],
            'price_levels': []
        }
        
        return {
            'score': 50.0,
            'components': component_scores,
            'signals': signals,
            'interpretation': interpretation,
            'metadata': metadata
        }

    def _calculate_level_proximity(self, current_price, levels):
        """
        Calculate the proximity of the current price to support and resistance levels.
        
        Args:
            current_price (float): The current price
            levels (list): List of support and resistance levels
            
        Returns:
            list: List of scores for each level
        """
        try:
            if not levels or len(levels) == 0:
                self.logger.warning("No support/resistance levels found")
                return [50.0]
                
            scores = []
            for level in levels:
                # Calculate distance as percentage
                distance_pct = abs(current_price - level) / current_price * 100
                
                # Closer levels have higher scores (inverse relationship)
                # Max score at 0% distance, min score at 5% or more distance
                if distance_pct >= 5:
                    score = 0
                else:
                    score = 100 * (1 - distance_pct / 5)
                    
                scores.append(score)
                
            return scores
            
        except Exception as e:
            self.logger.error(f"Error calculating level proximity: {str(e)}")
            return [50.0]

    def _analyze_volume(self, ohlcv_data):
        """
        Analyze volume patterns across timeframes.
        
        Args:
            ohlcv_data (dict): Dictionary of OHLCV data by timeframe
            
        Returns:
            float: Volume analysis score (0-100)
        """
        try:
            if not ohlcv_data or not isinstance(ohlcv_data, dict):
                self.logger.warning("Invalid OHLCV data for volume analysis")
                return 50.0
                
            available_timeframes = [tf for tf in ohlcv_data.keys() 
                                   if isinstance(ohlcv_data[tf], pd.DataFrame) 
                                   and not ohlcv_data[tf].empty]
                                   
            if not available_timeframes:
                self.logger.warning("No valid timeframes available for volume analysis")
                return 50.0
                
            # Calculate volume profile score
            vp_scores = []
            for tf in available_timeframes:
                df = ohlcv_data[tf]
                if 'volume' not in df.columns:
                    continue
                    
                vp_score = self._calculate_volume_profile_score(df)
                vp_scores.append(vp_score)
                
            # Calculate VWAP score
            vwap_score = self._calculate_vwap_score(ohlcv_data)
            
            # Calculate volume node score if available
            vn_scores = []
            for tf in available_timeframes:
                df = ohlcv_data[tf]
                if 'volume' not in df.columns:
                    continue
                    
                try:
                    vn_score = self._calculate_volume_node_score(df)
                    vn_scores.append(vn_score)
                except Exception as e:
                    self.logger.debug(f"Error calculating volume node score: {str(e)}")
                    
            # Combine scores
            scores = []
            if vp_scores:
                scores.append(np.mean(vp_scores))
            if vwap_score is not None:
                scores.append(vwap_score)
            if vn_scores:
                scores.append(np.mean(vn_scores))
                
            if not scores:
                self.logger.warning("No volume analysis scores calculated")
                return 50.0
                
            return float(np.mean(scores))
            
        except Exception as e:
            self.logger.error(f"Error in volume analysis: {str(e)}")
            self.logger.error(traceback.format_exc())
            return 50.0

    def _calculate_order_blocks(self, df):
        """
        Calculate order blocks from price action.
        
        Args:
            df (pd.DataFrame): OHLCV data
            
        Returns:
            dict: Dictionary containing order block information
        """
        try:
            if df.empty or len(df) < 10:
                self.logger.warning("Insufficient data for order block calculation")
                return {'bullish': [], 'bearish': []}
                
            # Initialize result
            order_blocks = {
                'bullish': [],  # Support zones
                'bearish': []   # Resistance zones
            }
            
            # Calculate price swings
            df['swing_high'] = df['high'].rolling(5, center=True).max() == df['high']
            df['swing_low'] = df['low'].rolling(5, center=True).min() == df['low']
            
            # Find potential order blocks
            for i in range(5, len(df) - 5):
                # Bullish order blocks (support)
                if df['swing_low'].iloc[i]:
                    # Look for strong volume and price rejection
                    if df['volume'].iloc[i] > df['volume'].iloc[i-5:i].mean() * 1.5:
                        price_level = df['low'].iloc[i]
                        strength = min(100, df['volume'].iloc[i] / df['volume'].iloc[i-5:i].mean() * 50)
                        order_blocks['bullish'].append({
                            'price': price_level,
                            'strength': strength,
                            'timestamp': df.index[i]
                        })
                
                # Bearish order blocks (resistance)
                if df['swing_high'].iloc[i]:
                    # Look for strong volume and price rejection
                    if df['volume'].iloc[i] > df['volume'].iloc[i-5:i].mean() * 1.5:
                        price_level = df['high'].iloc[i]
                        strength = min(100, df['volume'].iloc[i] / df['volume'].iloc[i-5:i].mean() * 50)
                        order_blocks['bearish'].append({
                            'price': price_level,
                            'strength': strength,
                            'timestamp': df.index[i]
                        })
            
            # Sort by strength
            order_blocks['bullish'] = sorted(order_blocks['bullish'], key=lambda x: x['strength'], reverse=True)
            order_blocks['bearish'] = sorted(order_blocks['bearish'], key=lambda x: x['strength'], reverse=True)
            
            # Take top 5 of each
            order_blocks['bullish'] = order_blocks['bullish'][:5]
            order_blocks['bearish'] = order_blocks['bearish'][:5]
            
            return order_blocks
            
        except Exception as e:
            self.logger.error(f"Error calculating order blocks: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {'bullish': [], 'bearish': []}

    def _interpret_component_score(self, component, score):
        """
        Interpret a component score and provide a textual description.
        
        Args:
            component (str): The component name
            score (float): The component score (0-100)
            
        Returns:
            str: Interpretation of the score
        """
        try:
            if score >= 70:
                strength = "strong"
            elif score >= 55:
                strength = "moderate"
            elif score >= 45:
                strength = "neutral"
            elif score >= 30:
                strength = "weak"
            else:
                strength = "very weak"
                
            if component == "support_resistance":
                if score >= 60:
                    return f"{strength.capitalize()} support nearby"
                elif score <= 40:
                    return f"{strength.capitalize()} resistance nearby"
                else:
                    return "No significant S/R levels nearby"
                    
            elif component == "trend":
                if score >= 60:
                    return f"{strength.capitalize()} bullish trend"
                elif score <= 40:
                    return f"{strength.capitalize()} bearish trend"
                else:
                    return "Neutral trend"
                    
            elif component == "volatility":
                if score >= 60:
                    return f"{strength.capitalize()} volatility expansion"
                elif score <= 40:
                    return f"{strength.capitalize()} volatility contraction"
                else:
                    return "Average volatility"
                    
            elif component == "momentum":
                if score >= 60:
                    return f"{strength.capitalize()} bullish momentum"
                elif score <= 40:
                    return f"{strength.capitalize()} bearish momentum"
                else:
                    return "Neutral momentum"
                    
            else:
                return f"{component}: {score:.2f}"
                
        except Exception as e:
            self.logger.error(f"Error interpreting component score: {str(e)}")
            return f"{component}: {score:.2f}"

    def _compute_weighted_score(self, scores: Dict[str, float]) -> float:
        """Calculate weighted score from components using component mapping.
        
        This method overrides the BaseIndicator method to handle component name mapping.
        """
        try:
            if not scores:
                self.logger.warning("No scores provided for weighted calculation")
                return 50.0
                
            self.logger.debug("Computing weighted score with component mapping")
            self.logger.debug(f"Input scores: {scores}")
            self.logger.debug(f"Component weights: {self.component_weights}")
            
            weighted_sum = 0.0
            weight_sum = 0.0
            
            for component, score in scores.items():
                # Map internal component name to config name if needed
                config_component = self.component_mapping.get(component, component)
                
                # Get weight for the component
                weight = self.component_weights.get(config_component, 0.0)
                
                self.logger.debug(f"Component: {component} -> {config_component}, Score: {score:.2f}, Weight: {weight:.2f}")
                
                weighted_sum += score * weight
                weight_sum += weight
            
            if weight_sum == 0:
                self.logger.warning("No valid weights found for components, using default score")
                return 50.0
                
            final_score = weighted_sum / weight_sum
            self.logger.debug(f"Final weighted score: {final_score:.2f} (sum: {weighted_sum:.2f}, weight: {weight_sum:.2f})")
            
            return float(np.clip(final_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error computing weighted score: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 50.0

    def log_indicator_results(self, final_score: float, component_scores: Dict[str, float], symbol: str = '') -> None:
        """Log indicator results with component mapping for consistent naming.
        
        This method overrides the BaseIndicator method to handle component name mapping.
        
        Args:
            final_score: Final calculated score
            component_scores: Dictionary of component scores
            symbol: Trading symbol (optional)
        """
        try:
            # Map component names for consistent logging
            mapped_scores = {}
            for component, score in component_scores.items():
                config_component = self.component_mapping.get(component, component)
                mapped_scores[config_component] = score
            
            # Call parent method with mapped scores
            super().log_indicator_results(final_score, mapped_scores, symbol)
            
        except Exception as e:
            self.logger.error(f"Error logging indicator results: {str(e)}")
            self.logger.debug(traceback.format_exc())
