import pandas as pd
import numpy as np
from typing import Dict, Any, Union, List, Optional
import logging
import traceback
import time
from scipy import stats

from src.utils.indicators import IndicatorUtils
from src.core.error.utils import handle_calculation_error, handle_indicator_error, validate_input
from src.config.manager import ConfigManager
from .base_indicator import BaseIndicator, IndicatorMetrics, DebugLevel, debug_method
from .debug_template import DebugLoggingMixin
from ..core.logger import Logger
from src.core.analysis.indicator_utils import log_score_contributions, log_component_analysis, log_final_score, log_calculation_details, log_multi_timeframe_analysis
# Add InterpretationGenerator import to use centralized interpretation system
from src.core.analysis.interpretation_generator import InterpretationGenerator
from src.core.analysis.indicator_utils import log_indicator_results as centralized_log_indicator_results


# Get module logger
logger = logging.getLogger('VolumeIndicators')

class VolumeIndicators(BaseIndicator, DebugLoggingMixin):
    """
    Volume-based trading indicators using industry-standard parameters.
    
    Features:
    - EMA-based relative volume calculations for responsiveness
    - Industry-standard 30-period RVOL lookback
    - Professional RVOL thresholds (2.0+ for entries, 3.0+ for high-probability)
    - Multi-component volume analysis (ADL, CMF, OBV, Volume Profile, VWAP)
    
    Enhanced with comprehensive debug logging following OrderbookIndicators model.
    
    RVOL Signal Levels:
    - RVOL >= 4.0: Extreme volume (potential overextension)
    - RVOL >= 3.0: Strong volume (high-probability setups)
    - RVOL >= 2.0: Significant volume (professional entry level)
    - RVOL >= 1.0: Normal volume (average activity)
    - RVOL < 1.0: Low volume (weak participation)
    """

    def __init__(self, config: Dict[str, Any], logger: Optional[Logger] = None):
        # Set required attributes before calling super().__init__
        self.indicator_type = 'volume'
        
        # Default component weights (updated to include moved components)
        default_weights = {
            'volume_delta': 0.20,    # Volume Delta (20%)
            'adl': 0.15,            # ADL (15%)
            'cmf': 0.15,            # CMF (15%)
            'relative_volume': 0.15, # Relative Volume (15%)
            'obv': 0.15,            # OBV (15%)
            'volume_profile': 0.10,  # Volume Profile (10%) - moved from price_structure
            'vwap': 0.10,           # VWAP (10%) - moved from price_structure
        }
        
        # Initialize config with default structure if not provided
        if not config:
            config = {}
        
        # Ensure required config structures exist
        if 'analysis' not in config:
            config['analysis'] = {}
        if 'indicators' not in config['analysis']:
            config['analysis']['indicators'] = {}
        if 'volume' not in config['analysis']['indicators']:
            config['analysis']['indicators']['volume'] = {}
        
        # Get volume specific config
        volume_config = config['analysis']['indicators']['volume']
        
        # Initialize components config if not present
        if 'components' not in volume_config:
            volume_config['components'] = {}
        
        # **** IMPORTANT: Must set component_weights BEFORE calling super().__init__ ****
        # Initialize component weights dictionary with defaults
        self.component_weights = default_weights.copy()
        
        # Now call super().__init__
        super().__init__(config, logger)
        
        # Read component weights from config if available
        components_config = volume_config['components']
        
        # Try to get weights from confluence section first (most accurate)
        confluence_weights = config.get('confluence', {}).get('weights', {}).get('sub_components', {}).get('volume', {})
        
        # Override defaults with weights from config
        for component, default_weight in default_weights.items():
            # First try to get from confluence configuration (most reliable source)
            if confluence_weights and component in confluence_weights:
                self.component_weights[component] = confluence_weights[component]
            # Then try from component config 
            elif isinstance(components_config.get(component), dict):
                self.component_weights[component] = components_config.get(component, {}).get('weight', default_weight)
        
        # Normalize weights to ensure they sum to 1.0
        weight_sum = sum(self.component_weights.values())
        if weight_sum != 0:
            for component in self.component_weights:
                self.component_weights[component] /= weight_sum
        
        # Set default parameters if not provided in config
        # These parameters are used throughout the indicator calculations
        self.params = {
            # Volume delta parameters
            'volume_delta_lookback': 20,      # Lookback period for volume delta
            'volume_delta_threshold': 1.5,    # Threshold for significant volume delta
            'volume_delta_smoothing': 5,      # Smoothing period for volume delta
            
            # CMF parameters
            'cmf_period': 20,                 # Lookback period for CMF
            'cmf_smoothing': 0.5,             # Smoothing factor for CMF
            
            # ADL parameters
            'adl_lookback': 20,               # Lookback period for ADL trend
            
            # OBV parameters
            'obv_lookback': 20,               # Lookback period for OBV
            'obv_smoothing': 5,               # Smoothing period for OBV
            
            # Relative volume parameters (industry standards)
            'rel_vol_period': 30,             # Industry standard: 30-period lookback
            'rel_vol_threshold': 2.0,         # Industry standard: RVOL > 2.0 for entries
            
            # Professional RVOL thresholds
            'rel_vol_significant': 2.0,       # Professional entry level
            'rel_vol_strong': 3.0,            # High-probability signals
            'rel_vol_extreme': 4.0,           # Overextension warning level
            'rel_vol_weak': 1.0,              # Below average volume threshold
            
            # Minimum required data points
            'min_base_candles': 100,          # Minimum candles for base timeframe
            'min_ltf_candles': 50,            # Minimum candles for LTF
            'min_mtf_candles': 50,            # Minimum candles for MTF
            'min_htf_candles': 20,            # Minimum candles for HTF
            
            # Minimum trade history
            'min_trades': 1000,               # Minimum trades for reliable volume analysis
            
            # Orderbook parameters
            'orderbook_levels': 100,          # Minimum orderbook levels for good analysis
            
            # Other parameters
            'divergence_impact': 0.2,         # Impact of divergence on scores
            'timeframe_divergence_threshold': 15.0,  # Threshold for timeframe divergence
            
            # Volume divergence parameters
            'max_divergence': 0.5,            # Maximum divergence value for normalization
            'min_strength': 0.3,              # Minimum strength threshold for divergence
            'correlation_window': 14          # Window for correlation calculations
        }
        
        # Make sure volume_config has a parameters section
        if 'parameters' not in volume_config:
            volume_config['parameters'] = {}
            
        # Update params with values from config
        parameters = volume_config['parameters']
        for param, default_value in self.params.items():
            config_value = parameters.get(param, default_value)
            self.params[param] = config_value
            
            # Also update the config with these values to ensure consistency
            parameters[param] = config_value
            
        self.logger.debug(f"Initialized volume indicators with parameters: {self.params}")
        
        # Add timeframe weights from config
        self.timeframe_weights = {
            tf_name: self.config['timeframes'][tf_name]['weight'] 
            for tf_name in ['base', 'ltf', 'mtf', 'htf']
            if 'timeframes' in self.config 
            and tf_name in self.config['timeframes']
            and 'weight' in self.config['timeframes'][tf_name]
        }
        
        # Set default timeframe weights if not available
        if not self.timeframe_weights:
            self.timeframe_weights = {
                'base': 0.5,
                'ltf': 0.15,
                'mtf': 0.20,
                'htf': 0.15
            }
            self.logger.debug("Using default timeframe weights as none were provided in config")
            
        # Volume profile configuration (moved from price_structure_indicators)
        volume_profile_params = volume_config.get('parameters', {}).get('volume_profile', {})
        
        # Value area volume percentage (default 70% of total volume)
        self.value_area_volume = volume_profile_params.get('value_area_percentage', 0.7)
        
        # Volume profile bins configuration
        self.volume_profile_bins = volume_profile_params.get('bins', 100)
        
        # VWAP configuration (moved from price_structure_indicators)
        vwap_params = volume_config.get('parameters', {}).get('vwap', {})
        
        # VWAP debug logging configuration
        self.vwap_debug_logging = vwap_params.get('debug_logging', False)
        
        # VWAP standard deviation bands configuration
        self.vwap_use_std_bands = vwap_params.get('use_std_bands', True)
        
        # VWAP session weights
        session_weights = vwap_params.get('session_weights', {})
        self.vwap_daily_weight = session_weights.get('daily', 0.6)
        self.vwap_weekly_weight = session_weights.get('weekly', 0.4)
        
        # VWAP scoring thresholds
        scoring_config = vwap_params.get('scoring', {})
        self.vwap_scoring = {
            'extreme_overbought': scoring_config.get('extreme_overbought', 95),
            'strong_overbought': scoring_config.get('strong_overbought', 80),
            'moderate_overbought': scoring_config.get('moderate_overbought', 65),
            'neutral': scoring_config.get('neutral', 50),
            'moderate_oversold': scoring_config.get('moderate_oversold', 35),
            'strong_oversold': scoring_config.get('strong_oversold', 20),
            'extreme_oversold': scoring_config.get('extreme_oversold', 5)
        }
        
        self.logger.info(f"Volume profile configuration: value_area_percentage={self.value_area_volume:.1%}, bins={self.volume_profile_bins}")
        self.logger.info(f"VWAP configuration: std_bands={'enabled' if self.vwap_use_std_bands else 'disabled'}, "
                        f"debug={'enabled' if self.vwap_debug_logging else 'disabled'}, "
                        f"weights=daily:{self.vwap_daily_weight:.1f}/weekly:{self.vwap_weekly_weight:.1f}")

    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input data for volume analysis."""
        try:
            self.logger.debug("\n=== Starting Volume Validation ===")
            
            # First check base requirements
            self.logger.debug("Checking base requirements...")
            base_valid = self._validate_base_requirements(data)
            self.logger.debug(f"Base requirements valid: {base_valid}")
            if not base_valid:
                return False
                
            # Volume-specific validation
            ohlcv_data = data.get('ohlcv', {})
            self.logger.debug(f"OHLCV keys: {list(ohlcv_data.keys())}")
            
            # Updated required timeframes list
            required_timeframes = ['base', 'ltf', 'mtf', 'htf']
            missing_tfs = [tf for tf in required_timeframes if tf not in ohlcv_data]
            if missing_tfs:
                friendly_names = [self.TIMEFRAME_CONFIG[tf]['friendly_name'] for tf in missing_tfs]
                self.logger.error(f"Missing timeframes: {', '.join(friendly_names)}")
                return False
                    
            # Check each timeframe
            for tf in required_timeframes:
                self.logger.debug(f"\nChecking timeframe: {tf}")
                
                # Get DataFrame
                df = ohlcv_data.get(tf)
                
                self.logger.debug(f"Timeframe ({tf}) type: {type(df)}")
                
                # Validate DataFrame type
                if not isinstance(df, pd.DataFrame):
                    self.logger.error(f"Invalid type for {tf}: {type(df)}")
                    return False
                    
                # Check if empty using pandas empty property
                if df.empty:
                    self.logger.error(f"Empty DataFrame for {tf}")
                    return False
                    
                # Log DataFrame details
                self.logger.debug(f"DataFrame shape: {df.shape}")
                self.logger.debug(f"DataFrame columns: {list(df.columns)}")
                
                # Check required columns
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    self.logger.error(f"Missing columns in {tf}: {missing_columns}")
                    return False
                
                # Check minimum candle requirements
                min_param_name = f'min_{tf}_candles'
                min_candles = self.params.get(min_param_name)
                if min_candles and len(df) < min_candles:
                    self.logger.warning(f"Insufficient {tf} candles: {len(df)} < {min_candles}")
                    # Don't return False here, just warn
            
            # Check trade history if available
            trades = data.get('trades', [])
            min_trades = self.params.get('min_trades', 1000)
            if isinstance(trades, list) and len(trades) < min_trades:
                self.logger.warning(f"Insufficient trade history: {len(trades)} < {min_trades}")
                # Don't return False, just warn
            
            # Check orderbook depth if available
            orderbook = data.get('orderbook', {})
            min_levels = self.params.get('orderbook_levels', 100)
            
            if isinstance(orderbook, dict):
                asks = orderbook.get('asks', [])
                bids = orderbook.get('bids', [])
                
                if len(asks) < min_levels or len(bids) < min_levels:
                    self.logger.warning(f"Shallow orderbook: asks={len(asks)}, bids={len(bids)}, min={min_levels}")
                    # Don't return False, just warn
                    
            self.logger.debug("\nVolume validation successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in volume data validation: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    async def calculate_score(self, market_data: Dict[str, Any]) -> float:
        """Calculate volume score with detailed component logging."""
        try:
            self.logger.info("\n=== VOLUME INDICATORS Detailed Calculation ===")
            
            # Get symbol from market data
            symbol = market_data.get('symbol', '')
            
            # Calculate volume delta
            delta_score = self._calculate_volume_delta(market_data)
            raw_delta = self._get_raw_volume_delta(market_data)
            self.logger.info(f"Volume Delta: Raw={raw_delta:.2f}, Score={delta_score:.2f}")
            
            # Calculate ADL (Accumulation/Distribution Line)
            adl_score = self._calculate_adl_score(market_data)
            adl_trend = self._get_adl_trend(market_data)
            self.logger.info(f"ADL: Trend Direction={adl_trend:.4f}, Score={adl_score:.2f}")
            
            # Calculate CMF (Chaikin Money Flow)
            cmf_score = self._calculate_cmf_score(market_data)
            cmf_value = self._get_cmf_value(market_data)
            self.logger.info(f"CMF: Value={cmf_value:.4f}, Score={cmf_score:.2f}")
            
            # Calculate relative volume
            rel_vol_score = self._calculate_relative_volume(market_data)
            rel_vol_ratio = self._get_relative_volume_ratio(market_data)
            self.logger.info(f"Relative Volume: Ratio={rel_vol_ratio:.2f}, Score={rel_vol_score:.2f}")
            
            # Calculate OBV (On-Balance Volume)
            obv_score = self._calculate_obv_score(market_data)
            obv_trend = self._get_obv_trend(market_data)
            self.logger.info(f"OBV: Trend={obv_trend:.4f}, Score={obv_score:.2f}")
            
            # Combine component scores
            scores = {
                'volume_delta': delta_score,
                'adl': adl_score,
                'cmf': cmf_score,
                'relative_volume': rel_vol_score,
                'obv': obv_score
            }
            
            # Use the standard log_score_contributions function with symbol
            from src.core.analysis.indicator_utils import log_score_contributions, log_final_score
            
            # Log component contribution breakdown
            log_score_contributions(
                self.logger,
                f"{symbol} Volume Score Contribution Breakdown",
                scores,
                self.component_weights,
                symbol=symbol
            )
            
            # Calculate weighted score
            final_score = self._compute_weighted_score(scores)
            
            # Log final score
            log_final_score(
                self.logger,
                "Volume",
                final_score,
                symbol=symbol
            )
            
            return final_score
            
        except Exception as e:
            self.logger.error(f"Error calculating volume score: {str(e)}")
            return 50.0

            self.logger.debug(f"Overall: {interpretation} (Score: {final_score:.2f})")

            # Use enhanced component analysis formatting for component breakdown
            log_component_analysis(self.logger, "Volume Analysis Interpretation", components)

        except Exception as e:
            self.logger.error(f"Error logging volume interpretation: {str(e)}")

    async def get_signals(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get volume-specific signals using industry-standard RVOL thresholds."""
        try:
            primary_tf = list(market_data['ohlcv'].keys())[0]
            df = market_data['ohlcv'][primary_tf]
            
            # Calculate RVOL using industry-standard 30-period lookback
            rvol_ratio = self._get_relative_volume_ratio(market_data)
            
            # Get professional thresholds
            significant_threshold = self.params.get('rel_vol_significant', 2.0)
            strong_threshold = self.params.get('rel_vol_strong', 3.0)
            extreme_threshold = self.params.get('rel_vol_extreme', 4.0)
            weak_threshold = self.params.get('rel_vol_weak', 1.0)
            
            # Generate RVOL-based signals using industry standards
            rvol_signal = self._generate_rvol_signal(rvol_ratio, significant_threshold, 
                                                   strong_threshold, extreme_threshold, weak_threshold)
            
            return {
                'relative_volume': {
                    'value': rvol_ratio,
                    'signal': rvol_signal['signal'],
                    'strength': rvol_signal['strength'],
                    'description': rvol_signal['description']
                },
                'volume_sma': {
                    'value': self._calculate_volume_sma_score(df),
                    'signal': 'high' if self._calculate_volume_sma_score(df) > 70 else 'low'
                },
                'volume_trend': {
                    'value': self._calculate_volume_trend_score(df),
                    'signal': 'increasing' if self._calculate_volume_trend_score(df) > 60 else 'decreasing'
                },
                'volume_profile': {
                    'value': self._calculate_volume_profile_score(df),
                    'signal': 'bullish' if self._calculate_volume_profile_score(df) > 65 else 'bearish'
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting volume signals: {str(e)}")
            return {}

    def _generate_rvol_signal(self, rvol_ratio: float, significant: float, strong: float, 
                             extreme: float, weak: float) -> Dict[str, str]:
        """
        Generate RVOL signal based on industry-standard thresholds.
        
        Args:
            rvol_ratio: Current RVOL value
            significant: Threshold for significant volume (default 2.0)
            strong: Threshold for strong volume (default 3.0)
            extreme: Threshold for extreme volume (default 4.0)
            weak: Threshold for weak volume (default 1.0)
            
        Returns:
            Dict with signal, strength, and description
        """
        try:
            if rvol_ratio >= extreme:
                return {
                    'signal': 'extreme_volume',
                    'strength': 'extreme',
                    'description': f'Extreme volume spike (RVOL: {rvol_ratio:.2f}x) - potential overextension'
                }
            elif rvol_ratio >= strong:
                return {
                    'signal': 'strong_volume',
                    'strength': 'strong',
                    'description': f'Strong volume (RVOL: {rvol_ratio:.2f}x) - high-probability setup'
                }
            elif rvol_ratio >= significant:
                return {
                    'signal': 'significant_volume',
                    'strength': 'significant',
                    'description': f'Significant volume (RVOL: {rvol_ratio:.2f}x) - professional entry level'
                }
            elif rvol_ratio >= weak:
                return {
                    'signal': 'normal_volume',
                    'strength': 'normal',
                    'description': f'Normal volume (RVOL: {rvol_ratio:.2f}x) - average activity'
                }
            else:
                return {
                    'signal': 'low_volume',
                    'strength': 'weak',
                    'description': f'Low volume (RVOL: {rvol_ratio:.2f}x) - weak participation'
                }
                
        except Exception as e:
            self.logger.error(f"Error generating RVOL signal: {str(e)}")
            return {
                'signal': 'unknown',
                'strength': 'unknown',
                'description': 'Error calculating RVOL signal'
            }

    def _calculate_confidence(self, market_data: Dict[str, Any]) -> float:
        """Calculate confidence in volume analysis."""
        try:
            primary_tf = list(market_data['ohlcv'].keys())[0]
            df = market_data['ohlcv'][primary_tf]
            
            # Calculate confidence based on data quality
            min_required_points = 20
            if len(df) < min_required_points:
                return 0.5
                
            # Check for consistent volume data
            volume_zeros = (df['volume'] == 0).sum()
            if volume_zeros / len(df) > 0.1:  # More than 10% zeros
                return 0.7
                
            return 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5

    def _calculate_volume_sma_score(self, df: pd.DataFrame) -> float:
        """Calculate volume SMA comparison score."""
        try:
            # Calculate volume SMAs
            vol_sma_short = df['volume'].rolling(window=20).mean()
            vol_sma_long = df['volume'].rolling(window=50).mean()
            
            # Calculate score based on SMA relationship
            current_ratio = vol_sma_short.iloc[-1] / vol_sma_long.iloc[-1]
            
            # Normalize to 0-100 range
            score = min(max((current_ratio - 0.5) * 100, 0), 100)
            
            return float(score)
            
        except Exception as e:
            self.logger.error(f"Error calculating volume SMA score: {str(e)}")
            return 50.0

    def _calculate_volume_trend_score(self, df: pd.DataFrame) -> float:
        """Calculate volume trend score."""
        try:
            # Calculate volume trend
            vol_change = df['volume'].pct_change()
            trend_score = vol_change.rolling(window=10).mean() * 100
            
            # Normalize to 0-100 range
            score = min(max(trend_score.iloc[-1] + 50, 0), 100)
            
            return float(score)
            
        except Exception as e:
            self.logger.error(f"Error calculating volume trend score: {str(e)}")
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
            
            # Calculate volume profile using numeric indices instead of interval objects
            bins = np.linspace(df['close'].min(), df['close'].max(), adaptive_bins + 1)
            df['price_level'] = pd.cut(df['close'], bins=bins, labels=False)
            bin_centers = (bins[:-1] + bins[1:]) / 2
            volume_profile = df.groupby('price_level')['volume'].sum()
            volume_profile.index = bin_centers[volume_profile.index.astype(int)]
            
            # Get POC and value area
            poc_level = float(volume_profile.idxmax())
            current_price = df['close'].iloc[-1]
            
            # Calculate value area (70% of volume)
            total_volume = volume_profile.sum()
            sorted_profile = volume_profile.sort_values(ascending=False)
            value_area_volume = total_volume * getattr(self, 'value_area_volume', 0.7)
            
            # Find value area price levels
            cumulative_volume = 0
            value_area_indices = []
            
            for idx, vol in sorted_profile.items():
                cumulative_volume += vol
                value_area_indices.append(idx)
                if cumulative_volume >= value_area_volume:
                    break
            
            va_high = max(value_area_indices)
            va_low = min(value_area_indices)
            
            # Score based on position relative to value area
            if current_price >= va_low and current_price <= va_high:
                va_position = (current_price - va_low) / (va_high - va_low) if va_high != va_low else 0.5
                score = 100 * (1 - abs(va_position - 0.5) * 2)
            else:
                distance = min(abs(current_price - va_high), abs(current_price - va_low))
                score = 50 - (distance / current_price * 100)
                
            return float(np.clip(score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating volume profile: {str(e)}")
            return 50.0

    @handle_calculation_error(default_value={'volume_delta': 50.0, 'divergence': 0.0})
    def calculate_volume_delta(self, trades_df: pd.DataFrame, price_df: pd.DataFrame = None, window: int = None) -> Dict[str, float]:
        """Calculate Volume Delta with divergence as bonus signal."""
        try:
            self.logger.debug("\n=== Starting Volume Delta Calculation ===")
            self.logger.debug(f"Input trades shape: {trades_df.shape if trades_df is not None else 'None'}")
            self.logger.debug(f"Input price shape: {price_df.shape if price_df is not None else 'None'}")
            
            # Debug: Check trades_df structure
            if trades_df is not None:
                self.logger.debug(f"Trades DataFrame columns: {trades_df.columns.tolist()}")
                self.logger.debug(f"Trades DataFrame dtypes: {trades_df.dtypes.to_dict()}")
                if not trades_df.empty:
                    self.logger.debug(f"First few rows of trades_df:\n{trades_df.head()}")
            
            # Use parameter from config or default
            if window is None:
                window = self.params.get('volume_delta_lookback', 20)
                self.logger.debug(f"Using volume delta lookback window: {window}")
            
            # Calculate base volume delta score
            try:
                base_score = self._calculate_base_volume_score(trades_df)
                self.logger.debug(f"Base volume score: {base_score:.2f}")
            except Exception as e:
                self.logger.error(f"Error in _calculate_base_volume_score: {str(e)}")
                base_score = 50.0
            
            # Calculate divergence bonus
            divergence_bonus = 0.0
            divergence_value = 0.0
            if price_df is not None:
                try:
                    self.logger.debug("Calculating divergence bonus...")
                    divergence_bonus = self._calculate_volume_divergence_bonus(price_df)
                    if isinstance(divergence_bonus, dict):
                        self.logger.debug(f"Divergence bonus: {divergence_bonus}")
                        # Extract the strength value for calculations
                        divergence_value = divergence_bonus.get('strength', 0.0)
                    else:
                        self.logger.debug(f"Divergence bonus: {divergence_bonus:.2f}")
                        divergence_value = divergence_bonus
                except Exception as e:
                    self.logger.error(f"Error in _calculate_volume_divergence_bonus: {str(e)}")
                    divergence_bonus = 0.0
                    divergence_value = 0.0
            
            # Apply divergence bonus with configurable multiplier using safer parameter access
            divergence_impact = self.params.get('divergence_impact', 0.2)
            
            # Ensure the divergence_impact parameter is set in params to avoid future warnings
            if 'divergence_impact' not in self.params:
                self.params['divergence_impact'] = divergence_impact
                self.logger.debug(f"Set default divergence_impact parameter: {divergence_impact}")
            
            final_score = np.clip(base_score + divergence_value * divergence_impact, 0, 100)
            self.logger.debug(f"Final score: {final_score:.2f} (divergence impact: {divergence_impact})")
            
            return {
                'base_score': float(base_score),
                'divergence_bonus': divergence_bonus if isinstance(divergence_bonus, dict) else float(divergence_bonus),
                'final_score': float(final_score)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating volume delta: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return {'volume_delta': 50.0, 'divergence': 0.0}
    
    @handle_calculation_error(default_value=pd.Series(dtype=float))
    def calculate_adl(self, df: pd.DataFrame) -> pd.Series:
        """Calculate the Accumulation/Distribution Line (ADL), which tracks the cumulative flow 
        of money into and out of a security.
        
        Handles both standard and CCXT OHLCV formats:
        Standard: volume, high, low, close
        CCXT: volume, high, low, close
        """
        try:
            # Validate input data
            if df.empty:
                self.logger.warning("Empty DataFrame provided for ADL calculation")
                return pd.Series([50.0])
            
            self.logger.debug(f"ADL input DataFrame columns: {df.columns.tolist()}")
            self.logger.debug(f"ADL input DataFrame shape: {df.shape}")
            
            # Handle CCXT OHLCV format if numeric columns
            if df.columns.dtype == 'int64':
                df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                self.logger.info("Detected CCXT OHLCV format, renamed columns")

            # Check for required columns
            required_cols = {'high', 'low', 'close'}
            if not required_cols.issubset(df.columns):
                missing = required_cols - set(df.columns)
                self.logger.warning(f"Missing required columns for ADL calculation: {missing}")
                return pd.Series([50.0])
                
            # Handle different volume column names
            volume_col = None
            for col in ['volume', 'amount', 'vol', 'quantity']:
                if col in df.columns:
                    volume_col = col
                    break
                    
            if not volume_col:
                self.logger.warning("No volume/amount column found for ADL calculation, assuming last column is volume")
                # Fallback: assume the last column is volume
                df['volume'] = df.iloc[:, -1]
                volume_col = 'volume'

            # Create a copy to avoid modifying original data
            df = df.copy()

            # Convert numeric columns with 0 instead of NaN
            for col in ['high', 'low', 'close', volume_col]:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                self.logger.debug(f"Column {col} stats - min: {df[col].min():.2f}, max: {df[col].max():.2f}")

            # Skip rows where all values are 0
            valid_rows = (df['high'] != 0) & (df['low'] != 0) & (df['close'] != 0) & (df[volume_col] != 0)
            df = df[valid_rows].copy()

            if len(df) == 0:
                self.logger.warning("No valid data points after cleaning")
                return pd.Series([50.0])

            # Calculate Money Flow Multiplier with safety checks
            hlrange = df['high'] - df['low']
            # Replace zero ranges with 0.1% of the high price
            hlrange = np.where(hlrange == 0, df['high'] * 0.001, hlrange)
            
            # Calculate CLV (Close Location Value)
            clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / hlrange
            clv = clv.clip(-1, 1)  # Ensure CLV is between -1 and 1
            
            # Calculate Money Flow Volume
            mfv = clv * df[volume_col]
            
            # Calculate ADL with running sum
            adl = mfv.cumsum()
            
            # Log ADL stats before normalization
            self.logger.debug(f"ADL stats before normalization - min: {adl.min():.2f}, max: {adl.max():.2f}, current: {adl.iloc[-1]:.2f}")
            
            # Normalize to 0-100 scale with robust bounds
            adl_range = adl.max() - adl.min()
            if adl_range == 0:
                normalized_adl = pd.Series([50.0] * len(adl), index=adl.index)
            else:
                normalized_adl = ((adl - adl.min()) / adl_range * 100).clip(0, 100)
            
            # Ensure the series has values
            if normalized_adl.empty:
                self.logger.warning("Empty normalized ADL series")
                return pd.Series([50.0])
            
            # Log final normalized value
            self.logger.info(f"Final normalized ADL value: {normalized_adl.iloc[-1]:.2f}")
            
            return normalized_adl
            
        except Exception as e:
            self.logger.error(f"Error calculating ADL: {str(e)}")
            self.logger.debug("Traceback:", exc_info=True)
            return pd.Series([50.0])

    @handle_calculation_error(default_value=pd.Series(dtype=float))
    def calculate_cmf(self, df: pd.DataFrame, period: int = 20, smoothing: float = 0.5) -> pd.Series:
        """Calculate Chaikin Money Flow (CMF), which measures the amount of Money Flow Volume 
        over a specific period.
        
        Args:
            df (pd.DataFrame): OHLCV data
            period (int): Lookback period for CMF calculation
            smoothing (float): Exponential smoothing factor (0-1)
        
        Returns:
            pd.Series: Normalized CMF values (0-100)
        """
        try:
            # Validate input data
            if df.empty:
                self.logger.warning("Empty DataFrame provided for CMF calculation")
                return pd.Series([50.0])
            
            self.logger.debug(f"CMF input DataFrame columns: {df.columns.tolist()}")
            self.logger.debug(f"CMF input DataFrame shape: {df.shape}")
            self.logger.debug(f"CMF input DataFrame head:\n{df.head(5)}")
            
            # Handle CCXT OHLCV format if numeric columns
            if df.columns.dtype == 'int64':
                df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                self.logger.info("Detected CCXT OHLCV format, renamed columns")
                
            # Check for required columns
            required_cols = {'high', 'low', 'close'}
            if not required_cols.issubset(df.columns):
                missing = required_cols - set(df.columns)
                self.logger.warning(f"Missing required columns for CMF calculation: {missing}")
                return pd.Series([50.0])
                
            # Handle different volume column names
            volume_col = None
            for col in ['volume', 'amount', 'vol', 'quantity']:
                if col in df.columns:
                    volume_col = col
                    break
                    
            if not volume_col:
                self.logger.warning("No volume/amount column found for CMF calculation, assuming last column is volume")
                # Fallback: assume the last column is volume
                df['volume'] = df.iloc[:, -1]
                volume_col = 'volume'

            self.logger.debug(f"Using columns: high='high', low='low', close='close', volume='{volume_col}'")

            # Create a copy to avoid modifying original data
            df = df.copy()

            # Convert numeric columns
            for col in ['high', 'low', 'close', volume_col]:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                self.logger.debug(f"Column {col} stats - min: {df[col].min():.2f}, max: {df[col].max():.2f}, nan count: {df[col].isna().sum()}")

            # Drop any rows with NaN values
            original_len = len(df)
            df = df.dropna(subset=['high', 'low', 'close', volume_col])
            if len(df) < original_len:
                self.logger.warning(f"Dropped {original_len - len(df)} rows with NaN values")
            
            if len(df) < period:
                self.logger.warning(f"Insufficient data points for CMF calculation. Need {period}, got {len(df)}")
                return pd.Series([50.0])

            # Calculate Money Flow Multiplier
            hlrange = df['high'] - df['low']
            zero_ranges = (hlrange == 0).sum()
            if zero_ranges > 0:
                self.logger.warning(f"Found {zero_ranges} periods with zero price range")
            
            # Avoid division by zero
            hlrange = hlrange.replace(0, np.nan)
            
            # Calculate close location value
            clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / hlrange
            clv = clv.fillna(0)  # Fill NaN with neutral value
            self.logger.debug(f"CLV stats - min: {clv.min():.4f}, max: {clv.max():.4f}, mean: {clv.mean():.4f}")
            
            # Calculate Money Flow Volume
            mfv = clv * df[volume_col]
            
            # Calculate rolling sums with adaptive period
            mfv_sum = mfv.rolling(window=period, min_periods=1).sum()
            vol_sum = df[volume_col].rolling(window=period, min_periods=1).sum()
            
            # Calculate CMF
            cmf = np.where(vol_sum != 0, mfv_sum / vol_sum, 0)
            cmf = pd.Series(cmf, index=df.index)
            self.logger.debug(f"CMF (raw) stats - min: {cmf.min():.4f}, max: {cmf.max():.4f}, mean: {cmf.mean():.4f}")
            
            # Apply exponential smoothing
            if smoothing > 0:
                cmf = cmf.ewm(alpha=smoothing, adjust=False).mean()
            
            # Log CMF stats before normalization
            self.logger.debug(f"CMF stats before normalization - min: {cmf.min():.2f}, max: {cmf.max():.2f}, current: {cmf.iloc[-1]:.2f}")
            
            # Normalize to 0-100 scale with bounds checking
            normalized_cmf = np.clip((cmf + 1) * 50, 0, 100)
            self.logger.debug(f"Normalized CMF stats - min: {normalized_cmf.min():.2f}, max: {normalized_cmf.max():.2f}, mean: {normalized_cmf.mean():.2f}, current: {normalized_cmf.iloc[-1]:.2f}")
            
            # Log final normalized value
            self.logger.info(f"Final normalized CMF value: {normalized_cmf.iloc[-1]:.2f}")
            
            # Check for divergence
            price_trend = df['close'].diff().rolling(window=period).mean()
            cmf_trend = normalized_cmf.diff().rolling(window=period).mean()
            
            # Detect bullish and bearish divergence
            bullish_div = (price_trend < 0) & (cmf_trend > 0)
            bearish_div = (price_trend > 0) & (cmf_trend < 0)
            
            if bullish_div.iloc[-1]:
                self.logger.info("Detected bullish CMF divergence")
            elif bearish_div.iloc[-1]:
                self.logger.info("Detected bearish CMF divergence")
            
            # Ensure we return a valid score
            if pd.isna(normalized_cmf.iloc[-1]):
                self.logger.warning("Final CMF value is NaN, returning neutral value")
                return pd.Series([50.0])
                
            return pd.Series(normalized_cmf)
            
        except Exception as e:
            self.logger.error(f"Error calculating CMF: {str(e)}")
            self.logger.debug("Traceback:", exc_info=True)
            return pd.Series([50.0])
    
    @handle_calculation_error(default_value=pd.Series(dtype=float))
    def calculate_relative_volume(self, df: pd.DataFrame, period: int = 30) -> pd.Series:
        """
        Calculate relative volume using EMA for more responsive analysis.
        
        Relative Volume (RVOL) compares current volume to recent average volume.
        Uses EMA instead of SMA for faster response to volume changes.
        Industry standard: 30-period lookback for professional trading.
        
        Args:
            df: DataFrame with OHLCV data
            period: EMA period for volume baseline (default: 30, industry standard)
            
        Returns:
            pd.Series: Relative volume ratios where 1.0 = normal volume
            
        Professional Interpretation:
            - RVOL >= 2.0: Entry consideration level
            - RVOL >= 3.0: High-probability setup
            - RVOL >= 4.0: Potential overextension
        """
        try:
            self.logger.debug("\n=== Calculating Relative Volume (EMA-based, Industry Standard) ===")
            self.logger.debug(f"Input shape: {df.shape}")
            self.logger.debug(f"Using EMA period: {period} (industry standard: 30)")
            
            # Find volume column with expanded column list
            volume_col = None
            for col in ['volume', 'amount', 'vol', 'quantity']:
                if col in df.columns:
                    volume_col = col
                    break
                    
            if not volume_col:
                self.logger.warning("No volume column found, assuming last column is volume")
                # Fallback: assume the last column is volume
                df['volume'] = df.iloc[:, -1]
                volume_col = 'volume'
            
            # Calculate metrics using EMA for more responsive analysis
            volume = df[volume_col].astype(float)
            # EMA gives more weight to recent volume, better for detecting anomalies
            volume_ema = volume.ewm(span=period, adjust=False).mean()
            
            self.logger.debug("\nVolume Statistics:")
            self.logger.debug(f"Current volume: {volume.iloc[-1]:.2f}")
            self.logger.debug(f"EMA volume baseline: {volume_ema.iloc[-1]:.2f}")
            
            # Calculate relative volume with safety check
            rel_vol = np.where(volume_ema > 0, volume / volume_ema, 1.0)
            rel_vol = pd.Series(rel_vol, index=df.index)
            
            self.logger.debug(f"Relative volume (RVOL): {rel_vol.iloc[-1]:.2f}")
            
            return rel_vol
            
        except Exception as e:
            self.logger.error(f"Error calculating relative volume: {str(e)}", exc_info=True)
            return pd.Series([50.0] * len(df))

    def _calculate_relative_volume(self, market_data: Dict[str, Any]) -> float:
        """
        Calculate relative volume score from market data.
        
        Supports both traditional RVOL and price-aware RVOL based on configuration.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: Relative volume score (0-100) where 0 is very bearish and 100 is very bullish
        """
        try:
            # Check if price-aware mode is enabled
            price_aware_mode = self.config.get('price_aware_mode', False)
            
            if price_aware_mode:
                self.logger.debug("Using price-aware RVOL calculation")
                return self._calculate_price_aware_relative_volume(market_data)
            
            # Traditional RVOL calculation
            self.logger.debug("Using traditional RVOL calculation")
            
            # Extract OHLCV data
            if 'ohlcv' not in market_data or not market_data['ohlcv'] or 'base' not in market_data['ohlcv']:
                self.logger.warning("No OHLCV data found for relative volume calculation")
                return 50.0
                
            df = market_data['ohlcv']['base']
            
            # Get period from config or use default
            period = self.config.get('relative_volume_period', 20)
            
            # Calculate relative volume using the existing method
            rel_vol_series = self.calculate_relative_volume(df, period=period)
            
            # Return the latest value or default to 50.0
            if rel_vol_series.empty:
                return 50.0
            
            # Get the raw RVOL value
            rel_vol = float(rel_vol_series.iloc[-1])
            
            # Normalize RVOL to 0-100 score where 0 is very bearish and 100 is very bullish
            # RVOL < 1: Below average volume (bearish)
            # RVOL > 1: Above average volume (bullish)
            
            # Define the boundaries for normalization
            # RVOL ranges typically from 0.1 to 3.0 in normal market conditions
            min_rvol = self.config.get('min_rvol', 0.1)
            max_rvol = self.config.get('max_rvol', 3.0)
            
            # For bearish signal (RVOL < 1), map 0.1 to 0 and 1.0 to 50
            if rel_vol < 1.0:
                # Normalize to 0-50 range
                score = 50 * (rel_vol - min_rvol) / (1.0 - min_rvol)
            # For bullish signal (RVOL >= 1), map 1.0 to 50 and 3.0 to 100
            else:
                # Normalize to 50-100 range
                score = 50 + 50 * (rel_vol - 1.0) / (max_rvol - 1.0)
            
            # Ensure the score is within 0-100 range
            score = np.clip(score, 0, 100)
            
            self.logger.debug(f"Traditional RVOL: {rel_vol:.2f}, Normalized score: {score:.2f}")
            
            return float(score)
            
        except Exception as e:
            self.logger.error(f"Error calculating relative volume score: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 50.0

    def _calculate_base_volume_score(self, df: pd.DataFrame) -> float:
        """Calculate base volume score."""
        try:
            self.logger.debug(f"_calculate_base_volume_score called with df shape: {df.shape if df is not None else 'None'}")
            if df is None or df.empty:
                self.logger.debug("DataFrame is None or empty, returning 50.0")
                return 50.0
            
            # Handle different volume column names with expanded list
            volume_col = None
            for col in ['volume', 'amount', 'size', 'vol', 'quantity']:
                if col in df.columns:
                    volume_col = col
                    break
                
            if not volume_col:
                # Try to check if any column contains volume or size in its name
                volume_cols = [col for col in df.columns if any(term in col.lower() for term in ['volume', 'size', 'amount', 'quantity', 'vol'])]
                if volume_cols:
                    volume_col = volume_cols[0]
                else:
                    self.logger.warning("No volume/amount column found, using neutral score")
                    return 50.0

            # Calculate volume metrics
            volume = pd.to_numeric(df[volume_col], errors='coerce').fillna(0)
            volume_ma = volume.rolling(window=20, min_periods=1).mean()
            volume_std = volume.rolling(window=20, min_periods=1).std()
            
            # Calculate relative volume with safety checks
            current_volume = volume.iloc[-1]
            avg_volume = volume_ma.iloc[-1]
            
            if avg_volume == 0 or pd.isna(avg_volume):
                return 50.0
                
            relative_volume = current_volume / avg_volume
            
            # Convert to score
            score = 50 + (np.tanh(relative_volume - 1) * 50)
            
            return float(np.clip(score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating base volume score: {str(e)}")
            return 50.0

    def _calculate_volume_trend(self, trades_data: pd.DataFrame) -> float:
        """Calculate volume trend score."""
        try:
            if isinstance(trades_data, list):
                trades_df = pd.DataFrame(trades_data)
            else:
                trades_df = trades_data.copy()

            if trades_df.empty:
                return 50.0

            # Convert volume to numeric if needed
            if 'amount' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['amount'], errors='coerce')
            elif 'volume' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['volume'], errors='coerce')
            else:
                return 50.0

            # Calculate volume trend using simple moving averages
            short_ma = trades_df['volume'].rolling(window=5).mean()
            long_ma = trades_df['volume'].rolling(window=20).mean()

            if short_ma.empty or long_ma.empty:
                return 50.0

            # Calculate trend strength
            trend = (short_ma.iloc[-1] / long_ma.iloc[-1] - 1) * 100
            
            # Normalize to 0-100 scale
            score = self._normalize_value(trend, -50, 50)
            return score

        except Exception as e:
            self.logger.error(f"Error calculating volume trend: {str(e)}")
            return 50.0

    def _calculate_volume_volatility(self, trades_data: pd.DataFrame) -> float:
        """Calculate volume volatility score."""
        try:
            if isinstance(trades_data, list):
                trades_df = pd.DataFrame(trades_data)
            else:
                trades_df = trades_data.copy()

            if trades_df.empty:
                return 50.0

            # Convert volume to numeric if needed
            if 'amount' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['amount'], errors='coerce')
            elif 'volume' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['volume'], errors='coerce')
            else:
                return 50.0

            # Calculate volume volatility using standard deviation
            volatility = trades_df['volume'].std() / trades_df['volume'].mean()
            
            # Normalize to 0-100 scale
            score = self._normalize_value(volatility, 0, 2)
            return score

        except Exception as e:
            self.logger.error(f"Error calculating volume volatility: {str(e)}")
            return 50.0

    def normalize_volume(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize volume values with safety checks."""
        try:
            if pd.isna(value) or pd.isna(min_val) or pd.isna(max_val):
                self.logger.warning("NaN values in normalization, returning neutral value")
                return 50.0
                
            if min_val == max_val:
                # Instead of returning 0, calculate relative to historical average
                historical_avg = self.calculate_historical_average(value)
                normalized = 50.0 * (value / historical_avg) if historical_avg > 0 else 50.0
                return float(np.clip(normalized, 0, 100))
                
            normalized = ((value - min_val) / (max_val - min_val)) * 100
            return float(np.clip(normalized, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error in normalize_volume: {e}")
            return 50.0

    def calculate_historical_average(self, current_value: float) -> float:
        """Calculate historical average for normalization when min equals max."""
        try:
            # Use exponential moving average of recent values
            if not hasattr(self, '_historical_values'):
                self._historical_values = []
            
            self._historical_values.append(current_value)
            if len(self._historical_values) > 100:  # Keep last 100 values
                self._historical_values.pop(0)
                
            if not self._historical_values:
                return current_value
                
            return np.mean(self._historical_values)
            
        except Exception as e:
            self.logger.error(f"Error calculating historical average: {e}")
            return current_value if current_value > 0 else 1.0

    def _normalize_value(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize a value to the range [0, 100]"""
        try:
            normalized = ((value - min_val) / (max_val - min_val)) * 100
            return float(np.clip(normalized, 0, 100))
        except:
            return 50.0

    def _compute_weighted_score(self, indicators: Dict[str, float]) -> float:
        """
        Compute weighted average of indicators.
        """
        try:
            weighted_sum = sum(value * self.component_weights.get(name, 0) 
                             for name, value in indicators.items())
            weight_sum = sum(self.component_weights.get(name, 0) 
                            for name in indicators.keys())
            
            if weight_sum == 0:
                return 50.0
                
            return weighted_sum / weight_sum
            
        except Exception as e:
            self.logger.error(f"Error in _compute_weighted_score: {e}")
            return 50.0

    def _calculate_volume_indicators(self, trades_data: pd.DataFrame, price_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate all volume indicators and return their normalized values."""
        indicators = {}
        
        try:
            # Validate trades_data
            required_trades_columns = {'size', 'price', 'side'}
            if not all(col in trades_data.columns for col in required_trades_columns):
                self.logger.error(f"Missing required columns in trades_data. Required: {required_trades_columns}")
                return {name: 50.0 for name in self.component_weights.keys()}

            # Validate price_data
            required_price_columns = {'high', 'low', 'close', 'volume'}
            if not all(col in price_data.columns for col in required_price_columns):
                self.logger.error(f"Missing required columns in price_data. Required: {required_price_columns}")
                return {name: 50.0 for name in self.component_weights.keys()}

            # Ensure data is not empty
            if trades_data.empty or price_data.empty:
                self.logger.error("Empty dataframe received")
                return {name: 50.0 for name in self.component_weights.keys()}

            # Calculate volume delta
            volume_delta = self.calculate_volume_delta(trades_data, price_data, self.divergence_window)
            indicators['volume_delta'] = volume_delta['volume_delta']

            # Calculate ADL
            adl = self.calculate_adl(price_data)
            indicators['adl'] = self._normalize_value(adl.iloc[-1], adl.min(), adl.max())

            # Calculate CMF
            cmf = self.calculate_cmf(price_data)
            indicators['cmf'] = self._normalize_value(cmf.iloc[-1], -1, 1)

            # Calculate Relative Volume
            rvol = self.calculate_relative_volume(price_data)
            indicators['relative_volume'] = self._normalize_value(rvol.iloc[-1], 0, 3)

            return indicators
            
        except Exception as e:
            self.logger.error(f"Error in _calculate_volume_indicators: {str(e)}")
            return {name: 50.0 for name in self.component_weights.keys()}

    @handle_calculation_error(default_value=pd.Series(dtype=float))
    def calculate_obv(self, df: pd.DataFrame) -> pd.Series:
        """Calculate On-Balance Volume (OBV).
        
        OBV adds volume on up days and subtracts it on down days to measure buying/selling pressure.
        
        Args:
            df (pd.DataFrame): OHLCV data with 'close' and 'volume' columns
            
        Returns:
            pd.Series: Normalized OBV values (0-100)
        """
        try:
            # Validate input data
            if df.empty:
                self.logger.warning("Empty DataFrame provided for OBV calculation")
                return pd.Series([50.0])
            
            # Handle CCXT OHLCV format if numeric columns
            if df.columns.dtype == 'int64':
                df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                
            # Check for required columns
            if 'close' not in df.columns:
                self.logger.warning("Missing close price for OBV calculation")
                return pd.Series([50.0])
                
            # Handle different volume column names with expanded list
            volume_col = None
            for col in ['volume', 'amount', 'vol', 'quantity']:
                if col in df.columns:
                    volume_col = col
                    break
                    
            if not volume_col:
                self.logger.warning("No volume/amount column found for OBV calculation, assuming last column is volume")
                # Fallback: assume the last column is volume
                df['volume'] = df.iloc[:, -1]
                volume_col = 'volume'

            # Create a copy to avoid modifying original data
            df = df.copy()

            # Convert numeric columns
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df[volume_col] = pd.to_numeric(df[volume_col], errors='coerce')

            # Calculate price changes
            price_change = df['close'].diff()

            # Calculate OBV
            obv = pd.Series(0.0, index=df.index)
            
            # Initial value
            obv.iloc[0] = df[volume_col].iloc[0]
            
            # Calculate OBV based on price changes
            for i in range(1, len(df)):
                if price_change.iloc[i] > 0:
                    obv.iloc[i] = obv.iloc[i-1] + df[volume_col].iloc[i]
                elif price_change.iloc[i] < 0:
                    obv.iloc[i] = obv.iloc[i-1] - df[volume_col].iloc[i]
                else:
                    obv.iloc[i] = obv.iloc[i-1]

            # Log OBV stats before normalization
            self.logger.debug(f"OBV stats before normalization - min: {obv.min():.2f}, max: {obv.max():.2f}, current: {obv.iloc[-1]:.2f}")
            
            # Calculate rolling mean and std for dynamic normalization
            obv_mean = obv.rolling(window=20, min_periods=1).mean()
            obv_std = obv.rolling(window=20, min_periods=1).std()
            
            # Normalize using z-score and sigmoid transformation with safety checks
            z_score = np.where(obv_std > 0, (obv - obv_mean) / obv_std, 0)
            normalized_obv = 100 / (1 + np.exp(-0.5 * z_score))  # Sigmoid transformation
            
            # Ensure we return valid scores
            normalized_obv = pd.Series(normalized_obv, index=df.index).fillna(50.0).clip(0, 100)
            
            # Log final normalized value
            self.logger.info(f"Final normalized OBV value: {normalized_obv.iloc[-1]:.2f}")
            
            return normalized_obv
            
        except Exception as e:
            self.logger.error(f"Error calculating OBV: {str(e)}")
            self.logger.debug("Traceback:", exc_info=True)
            return pd.Series([50.0])

    @handle_calculation_error(default_value=pd.Series(dtype=float))
    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index (ADX) for trend strength."""
        try:
            if df.empty or not all(col in df.columns for col in ['high', 'low', 'close']):
                return pd.Series([0.0])

            # Calculate True Range
            df = df.copy()
            df['prev_close'] = df['close'].shift(1)
            tr1 = df['high'] - df['low']
            tr2 = abs(df['high'] - df['prev_close'])
            tr3 = abs(df['low'] - df['prev_close'])
            tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
            
            # Calculate Directional Movement
            df['prev_high'] = df['high'].shift(1)
            df['prev_low'] = df['low'].shift(1)
            
            plus_dm = df['high'] - df['prev_high']
            minus_dm = df['prev_low'] - df['low']
            
            plus_dm = plus_dm.where((plus_dm > 0) & (plus_dm > minus_dm), 0)
            minus_dm = minus_dm.where((minus_dm > 0) & (minus_dm > plus_dm), 0)
            
            # Calculate Smoothed Averages
            tr_smooth = tr.ewm(span=period, min_periods=period).mean()
            plus_di = 100 * (plus_dm.ewm(span=period, min_periods=period).mean() / tr_smooth)
            minus_di = 100 * (minus_dm.ewm(span=period, min_periods=period).mean() / tr_smooth)
            
            # Calculate ADX
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.ewm(span=period, min_periods=period).mean()
            
            return adx

        except Exception as e:
            self.logger.error(f"Error calculating ADX: {str(e)}")
            return pd.Series([0.0])

    def _calculate_volume_divergence_bonus(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate volume divergence bonus."""
        try:
            # Ensure required columns exist
            required_cols = ['close']
            if not all(col in df.columns for col in required_cols):
                self.logger.error("Missing required columns for volume divergence calculation")
                return {'strength': 0.0, 'direction': 'neutral'}
            
            # Find volume column with expanded list
            volume_col = None
            for col in ['volume', 'amount', 'size', 'vol', 'quantity']:
                if col in df.columns:
                    volume_col = col
                    break
                
            if not volume_col:
                # Try to check if any column contains volume or size in its name
                volume_cols = [col for col in df.columns if any(term in col.lower() for term in ['volume', 'size', 'amount', 'quantity', 'vol'])]
                if volume_cols:
                    volume_col = volume_cols[0]
                else:
                    self.logger.warning("No volume column found for divergence calculation")
                    return {'strength': 0.0, 'direction': 'neutral'}
            
            # Get parameters directly from self.params which we've properly initialized in __init__
            max_divergence = self.params.get('max_divergence', 0.5)
            min_strength = self.params.get('min_strength', 0.3) 
            
            # Calculate price and volume changes with better error handling
            price_changes = pd.to_numeric(df['close'], errors='coerce').pct_change().fillna(0)
            volume_changes = pd.to_numeric(df[volume_col], errors='coerce').pct_change().fillna(0)
            
            # Get correlation window from params
            corr_window = self.params.get('correlation_window', 14)
            
            # Ensure window is reasonable
            if corr_window < 2:
                self.logger.warning(f"Correlation window too small: {corr_window}, using default 14")
                corr_window = 14
            elif corr_window > len(df) // 2:
                self.logger.warning(f"Correlation window too large: {corr_window}, using len(df)/2")
                corr_window = len(df) // 2
            
            # Calculate rolling correlations with validated window and error handling
            try:
                correlation = price_changes.rolling(window=corr_window).corr(volume_changes)
                
                # Debug: Check correlation structure
                self.logger.debug(f"Correlation type: {type(correlation)}")
                self.logger.debug(f"Correlation shape: {correlation.shape if hasattr(correlation, 'shape') else 'No shape'}")
                
                # Handle NaN in correlation - fix potential DataFrame ambiguity
                if hasattr(correlation, 'isna'):
                    if correlation.isna().all():
                        self.logger.warning("All correlation values are NaN, using neutral direction")
                        return {'strength': 0.0, 'direction': 'neutral'}
                else:
                    self.logger.warning("Correlation object has no isna method, using neutral direction")
                    return {'strength': 0.0, 'direction': 'neutral'}
                
                # Fill NaN values with 0 (neutral correlation)
                correlation = correlation.fillna(0)
                
                # Calculate divergence score
                recent_correlation = correlation.iloc[-1]
                historical_correlation = correlation.mean()
                
                divergence = abs(recent_correlation - historical_correlation)
                
                # Normalize divergence score
                normalized_score = min(100 * (divergence / max_divergence), 100)
                
                # Apply strength threshold
                if normalized_score < min_strength:
                    return {'strength': 0.0, 'direction': 'neutral'}
                
                # Determine divergence direction
                if recent_correlation > historical_correlation:
                    direction = 'bullish'
                else:
                    direction = 'bearish'
                
                return {'strength': normalized_score, 'direction': direction}
            except Exception as e:
                self.logger.warning(f"Error in correlation calculation: {str(e)}")
                return {'strength': 0.0, 'direction': 'neutral'}
        
        except Exception as e:
            self.logger.error(f"Error calculating volume divergence bonus: {str(e)}")
            return {'strength': 0.0, 'direction': 'neutral'}

    @property
    def required_data(self) -> List[str]:
        """Required data fields for volume analysis."""
        return ['ohlcv', 'trades']

    @debug_method(DebugLevel.DETAILED)
    async def calculate(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate volume indicator scores with comprehensive debug logging.
        
        Args:
            market_data: Dictionary containing OHLCV and other market data
            
        Returns:
            Dict containing indicator scores, components, signals and metadata
        """
        start_time = time.time()
        
        try:
            symbol = market_data.get('symbol', '')
            self.logger.info(f"\n=== VOLUME INDICATORS Detailed Calculation ===")
            self.logger.info(f"Symbol: {symbol}")
            
            # 1. Log data quality metrics
            self._log_data_quality_metrics(market_data)
            
            # 2. Validate input with detailed logging
            self._log_calculation_step("Input Validation", {
                "market_data_keys": list(market_data.keys()),
                "ohlcv_timeframes": list(market_data.get('ohlcv', {}).keys()) if 'ohlcv' in market_data else [],
                "has_trades": 'trades' in market_data,
                "has_orderbook": 'orderbook' in market_data
            })
            
            if not self.validate_input(market_data):
                self.logger.error("❌ Input validation failed")
                return self.get_default_result()
            
            self.logger.info("✅ Input validation passed successfully")
            
            # 3. Component calculation with timing
            component_times = {}
            component_scores = {}
            
            # Volume Delta calculation
            start_component = time.time()
            self._log_component_calculation_header("Volume Delta", f"Analyzing buy/sell volume imbalance")
            
            volume_delta_score = self._calculate_volume_delta(market_data)
            delta_value = self._get_raw_volume_delta(market_data)
            component_scores['volume_delta'] = volume_delta_score
            
            self._log_calculation_step("Volume Delta Results", {
                "raw_delta": delta_value,
                "normalized_score": volume_delta_score,
                "interpretation": "Bullish" if volume_delta_score > 60 else "Bearish" if volume_delta_score < 40 else "Neutral"
            })
            
            component_times['volume_delta'] = self._log_component_timing("Volume Delta", start_component)
            
            # ADL calculation
            start_component = time.time()
            self._log_component_calculation_header("Accumulation/Distribution Line", f"Analyzing price-volume relationship")
            
            adl_score = self._calculate_adl_score(market_data)
            adl_trend = self._get_adl_trend(market_data)
            component_scores['adl'] = adl_score
            
            self._log_calculation_step("ADL Results", {
                "trend_direction": adl_trend,
                "normalized_score": adl_score,
                "interpretation": "Accumulation" if adl_score > 60 else "Distribution" if adl_score < 40 else "Neutral"
            })
            
            component_times['adl'] = self._log_component_timing("ADL", start_component)
            
            # CMF calculation
            start_component = time.time()
            self._log_component_calculation_header("Chaikin Money Flow", f"Analyzing money flow pressure")
            
            cmf_score = self._calculate_cmf_score(market_data)
            cmf_value = self._get_cmf_value(market_data)
            component_scores['cmf'] = cmf_score
            
            self._log_calculation_step("CMF Results", {
                "raw_cmf_value": cmf_value,
                "normalized_score": cmf_score,
                "interpretation": "Strong buying pressure" if cmf_score > 70 else "Strong selling pressure" if cmf_score < 30 else "Neutral pressure"
            })
            
            component_times['cmf'] = self._log_component_timing("CMF", start_component)
            
            # Relative Volume calculation
            start_component = time.time()
            self._log_component_calculation_header("Relative Volume", f"Analyzing volume vs historical average")
            
            rel_volume_score = self._calculate_relative_volume(market_data)
            rel_volume_ratio = self._get_relative_volume_ratio(market_data)
            component_scores['relative_volume'] = rel_volume_score
            
            # Enhanced RVOL interpretation
            if rel_volume_ratio >= 4.0:
                rvol_interpretation = "Extreme volume - potential overextension"
            elif rel_volume_ratio >= 3.0:
                rvol_interpretation = "Strong volume - high-probability setup"
            elif rel_volume_ratio >= 2.0:
                rvol_interpretation = "Significant volume - professional entry level"
            elif rel_volume_ratio >= 1.0:
                rvol_interpretation = "Normal volume - average activity"
            else:
                rvol_interpretation = "Low volume - weak participation"
            
            self._log_calculation_step("Relative Volume Results", {
                "rvol_ratio": rel_volume_ratio,
                "normalized_score": rel_volume_score,
                "interpretation": rvol_interpretation
            })
            
            component_times['relative_volume'] = self._log_component_timing("Relative Volume", start_component)
            
            # OBV calculation
            start_component = time.time()
            self._log_component_calculation_header("On-Balance Volume", f"Analyzing volume-price trend confirmation")
            
            obv_score = self._calculate_obv_score(market_data)
            obv_trend = self._get_obv_trend(market_data)
            component_scores['obv'] = obv_score
            
            self._log_calculation_step("OBV Results", {
                "trend_strength": obv_trend,
                "normalized_score": obv_score,
                "interpretation": "Confirming uptrend" if obv_score > 60 else "Confirming downtrend" if obv_score < 40 else "Neutral trend"
            })
            
            component_times['obv'] = self._log_component_timing("OBV", start_component)
            
            # Volume Profile calculation
            start_component = time.time()
            self._log_component_calculation_header("Volume Profile", f"Analyzing volume distribution at price levels")
            
            volume_profile_score = self._calculate_volume_profile_score(market_data['ohlcv']['base'])
            component_scores['volume_profile'] = volume_profile_score
            
            self._log_calculation_step("Volume Profile Results", {
                "profile_score": volume_profile_score,
                "interpretation": "Bullish profile" if volume_profile_score > 60 else "Bearish profile" if volume_profile_score < 40 else "Neutral profile"
            })
            
            component_times['volume_profile'] = self._log_component_timing("Volume Profile", start_component)
            
            # VWAP calculation
            start_component = time.time()
            self._log_component_calculation_header("VWAP", f"Analyzing volume-weighted average price")
            
            vwap_score = self._calculate_vwap_score(market_data)
            component_scores['vwap'] = vwap_score
            
            self._log_calculation_step("VWAP Results", {
                "vwap_score": vwap_score,
                "interpretation": "Above VWAP - bullish" if vwap_score > 60 else "Below VWAP - bearish" if vwap_score < 40 else "Near VWAP - neutral"
            })
            
            component_times['vwap'] = self._log_component_timing("VWAP", start_component)
            
            # 4. Calculate divergences
            self._log_calculation_step("Divergence Analysis", {
                "checking_volume_price_divergence": True,
                "has_trade_data": 'trades' in market_data and isinstance(market_data['trades'], pd.DataFrame)
            })
            
            divergences = {}
            if 'trades' in market_data and isinstance(market_data['trades'], pd.DataFrame) and not market_data['trades'].empty:
                divergence_result = self._calculate_volume_divergence_bonus(market_data['ohlcv']['base'])
                if divergence_result:
                    divergences['volume_price'] = divergence_result
                    self.logger.info(f"Volume-Price divergence detected: {divergence_result}")
            
            # 5. Apply divergence bonuses
            adjusted_scores = self._apply_divergence_bonuses(component_scores, divergences)
            
            # 6. Calculate final weighted score
            final_score = self._compute_weighted_score(adjusted_scores)
            
            # 7. Log performance metrics
            total_time = (time.time() - start_time) * 1000
            self._log_performance_metrics(component_times, total_time)
            
            # 8. Enhanced logging with centralized formatting
            centralized_log_indicator_results(
                logger=self.logger,
                indicator_name="Volume",
                final_score=final_score,
                component_scores=adjusted_scores,
                weights=self.component_weights,
                symbol=symbol
            )
            
            # 9. Add enhanced trading context logging
            self._log_trading_context(final_score, adjusted_scores, symbol, "Volume")
            
            # 10. Generate signals
            signals = await self.get_signals(market_data)
            
            # 11. Collect raw values for metadata
            raw_values = {
                'volume_delta': float(delta_value),
                'adl_trend': float(adl_trend),
                'cmf': float(cmf_value),
                'relative_volume': float(rel_volume_ratio),
                'obv_trend': float(obv_trend),
                'volume_profile': float(volume_profile_score),
                'vwap': float(vwap_score)
            }
            
            # 12. Generate interpretation
            try:
                interpreter = InterpretationGenerator()
                interpretation_data = {
                    'score': final_score,
                    'components': adjusted_scores,
                    'signals': signals,
                    'metadata': {'raw_values': raw_values}
                }
                interpretation = interpreter._interpret_volume(interpretation_data)
            except Exception as e:
                self.logger.error(f"Error generating volume interpretation: {str(e)}")
                # Fallback interpretation
                if final_score > 65:
                    interpretation = f"Strong bullish volume (score: {final_score:.1f})"
                elif final_score < 35:
                    interpretation = f"Strong bearish volume (score: {final_score:.1f})"
                else:
                    interpretation = f"Neutral volume conditions (score: {final_score:.1f})"
            
            # 13. Return standardized format
            return {
                'score': float(np.clip(final_score, 0, 100)),
                'components': adjusted_scores,
                'signals': signals,
                'interpretation': interpretation,
                'divergences': divergences,
                'metadata': {
                    'timestamp': int(time.time() * 1000),
                    'calculation_time': total_time,
                    'component_times_ms': component_times,
                    'component_weights': self.component_weights,
                    'timeframe_weights': self.timeframe_weights,
                    'raw_values': raw_values,
                    'status': 'SUCCESS'
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating volume indicators: {str(e)}")
            self.logger.error(traceback.format_exc())
            return self.get_default_result()

    def _calculate_vwap_score(self, timeframe_data: Dict[str, Any]) -> float:
        """Calculate VWAP score using multiple timeframes."""
        try:
            if getattr(self, 'vwap_debug_logging', False):
                self.logger.debug("VWAP Analysis:")
            scores = []
            weights = {'htf': 0.4, 'mtf': 0.35, 'ltf': 0.25}
            
            if not timeframe_data or not isinstance(timeframe_data, dict):
                self.logger.warning("Invalid timeframe data for VWAP analysis - using DEFAULT value 50.0")
                return 50.0
                
            # Handle both data formats:
            # 1. Direct OHLCV data: timeframe_data = {'ohlcv': {'htf': DataFrame, 'mtf': DataFrame, ...}}
            # 2. Nested data format: timeframe_data = {'htf': {'data': DataFrame}, 'mtf': {'data': DataFrame}, ...}
            
            ohlcv_data = timeframe_data.get('ohlcv', {})
            if ohlcv_data:
                # Format 1: Direct OHLCV data from confluence analyzer
                if getattr(self, 'vwap_debug_logging', False):
                    self.logger.debug(f"Using direct OHLCV format with timeframes: {list(ohlcv_data.keys())}")
                available_timeframes = ohlcv_data
            else:
                # Format 2: Nested data format
                if getattr(self, 'vwap_debug_logging', False):
                    self.logger.debug(f"Using nested data format with timeframes: {list(timeframe_data.keys())}")
                available_timeframes = timeframe_data
                
            if getattr(self, 'vwap_debug_logging', False):
                self.logger.debug(f"Available timeframes: {list(available_timeframes.keys())}")
            
            available_tfs = 0
            for tf, weight in weights.items():
                if tf in available_timeframes:
                    # Handle both data formats
                    if isinstance(available_timeframes[tf], pd.DataFrame):
                        # Direct DataFrame format
                        df = available_timeframes[tf]
                        if getattr(self, 'vwap_debug_logging', False):
                            self.logger.debug(f"Using direct DataFrame for {tf}")
                    elif isinstance(available_timeframes[tf], dict) and 'data' in available_timeframes[tf]:
                        # Nested format with 'data' key
                        df = available_timeframes[tf]['data']
                        if getattr(self, 'vwap_debug_logging', False):
                            self.logger.debug(f"Using nested data format for {tf}")
                    else:
                        if getattr(self, 'vwap_debug_logging', False):
                            self.logger.debug(f"- Skipping {tf} - invalid data format: {type(available_timeframes[tf])}")
                        continue
                        
                    if isinstance(df, pd.DataFrame) and not df.empty and 'close' in df.columns and 'volume' in df.columns:
                        tf_score = self._calculate_single_vwap_score(df)
                        scores.append(tf_score * weight)
                        if getattr(self, 'vwap_debug_logging', False):
                            self.logger.debug(f"- {tf.upper()} Score: {tf_score:.2f} (weight: {weight:.2f})")
                        available_tfs += 1
                    else:
                        if getattr(self, 'vwap_debug_logging', False):
                            self.logger.debug(f"- Skipping {tf} - invalid DataFrame or missing columns")
                else:
                    if getattr(self, 'vwap_debug_logging', False):
                        self.logger.debug(f"- Timeframe {tf} not available")
            
            if not scores:
                self.logger.warning("No valid timeframe VWAP scores calculated - using DEFAULT value 50.0")
                return 50.0
                
            final_score = sum(scores)
            if getattr(self, 'vwap_debug_logging', False):
                self.logger.debug(f"- Final VWAP Score: {final_score:.2f} (calculated from {available_tfs} timeframes)")
            
            # Verify if the score is suspiciously close to the default value
            self._verify_score_not_default(final_score, "Multi-timeframe VWAP")
            
            return final_score
            
        except Exception as e:
            self.logger.error(f"Error calculating VWAP score: {str(e)}")
            self.logger.warning("Using DEFAULT value 50.0 due to error")
            return 50.0

    def _calculate_single_vwap_score(self, df: pd.DataFrame) -> float:
        """Calculate VWAP score for a single timeframe.
        
        Args:
            df: DataFrame containing OHLCV data
            
        Returns:
            float: VWAP score from 0-100
        """
        try:
            if df.empty or len(df) < 2:
                return 50.0
                
            # Validate required columns
            if not all(col in df.columns for col in ['high', 'low', 'close', 'volume']):
                self.logger.warning("Missing required columns for VWAP calculation")
                return 50.0
                
            # Calculate typical price (HLC/3)
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            
            # Calculate VWAP
            tp_volume = typical_price * df['volume']
            vwap = tp_volume.cumsum() / df['volume'].cumsum()
            
            # Get current price and VWAP
            current_price = df['close'].iloc[-1]
            current_vwap = vwap.iloc[-1]
            
            if current_vwap == 0:
                return 50.0
                
            # Calculate price vs VWAP ratio
            price_vwap_ratio = current_price / current_vwap
            
            # Convert to score using tanh transformation
            # Score > 50 when price > VWAP (bullish)
            # Score < 50 when price < VWAP (bearish)
            score = 50 * (1 + np.tanh(np.log(price_vwap_ratio)))
            
            return float(np.clip(score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating single VWAP score: {str(e)}")
            return 50.0

    def _verify_score_not_default(self, score: float, component_name: str) -> None:
        """Verify that a score is not suspiciously close to the default value.
        
        Args:
            score: The calculated score
            component_name: Name of the component for logging
        """
        try:
            if abs(score - 50.0) < 0.1:  # Very close to default
                self.logger.warning(f"{component_name} score ({score:.2f}) is suspiciously close to default value 50.0")
        except Exception as e:
            self.logger.debug(f"Error in score verification: {str(e)}")

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
            volume_profile_bins = getattr(self, 'volume_profile_bins', 100)
            adaptive_bins = max(20, min(volume_profile_bins, 
                                       int(price_range / (price_std * 0.1))))
            self.logger.debug(f"Using {adaptive_bins} bins for volume profile")
            
            bins = np.linspace(price_min, price_max, num=adaptive_bins)
            
            # Create volume profile
            df['price_level'] = pd.cut(df['close'], bins=bins, labels=False)
            # Map labels back to price points for easier interpretation
            price_points = (bins[:-1] + bins[1:]) / 2
            volume_profile = df.groupby('price_level')['volume'].sum()
            volume_profile.index = price_points[volume_profile.index]
            
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
            value_area_volume = getattr(self, 'value_area_volume', 0.7)
            target_volume = total_volume * value_area_volume
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

    def _apply_divergence_bonuses(self, component_scores: Dict[str, float], divergences: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """
        Apply divergence bonuses to component scores with detailed logging.
        
        Args:
            component_scores: Dictionary of component scores
            divergences: Dictionary of divergence information
            
        Returns:
            Dictionary of adjusted component scores
        """
        if not divergences:
            return component_scores
            
        # Make a copy to avoid modifying the original
        adjusted_scores = component_scores.copy()
        
        indicator_name = self.__class__.__name__.replace('Indicators', '')
        self.logger.info(f"\n=== Applying {indicator_name} Indicator Divergence Bonuses ===")
        self.logger.info(f"Original component scores:")
        for component, score in component_scores.items():
            self.logger.info(f"  - {component}: {score:.2f}")
            
        # Track total adjustments per component
        adjustments = {component: 0.0 for component in component_scores}
        
        # Apply bonuses from divergences
        for key, div_info in divergences.items():
            component = div_info.get('component')
            
            if component not in adjusted_scores:
                continue
                
            # Get bonus information
            bonus = div_info.get('bonus', 0.0)
            if 'bonus' not in div_info:
                # Calculate bonus based on divergence strength and type
                strength = div_info.get('strength', 0)
                div_type = div_info.get('type', 'neutral')
                
                # Bullish divergence increases score, bearish decreases
                bonus = strength * 0.1 * (1 if div_type == 'bullish' else -1)
                
                # Store bonus in divergence info for logging
                div_info['bonus'] = bonus
                
            if bonus == 0.0:
                continue
                
            # Get timeframe information if available
            tf1, tf2 = div_info.get('timeframes', ['', ''])
            if tf1 and tf2:
                tf1_friendly = self.TIMEFRAME_CONFIG.get(tf1, {}).get('friendly_name', tf1.upper())
                tf2_friendly = self.TIMEFRAME_CONFIG.get(tf2, {}).get('friendly_name', tf2.upper())
                timeframe_info = f"between {tf1_friendly} and {tf2_friendly}"
            else:
                timeframe_info = "in analysis"
            
            div_type = div_info.get('type', 'neutral')
            
            # Log the adjustment
            self.logger.info(f"  Adjusting {component} by {bonus:.2f} points ({div_type} divergence {timeframe_info})")
            
            # Update the score
            old_score = adjusted_scores[component]
            adjusted_scores[component] = np.clip(old_score + bonus, 0, 100)
            
            # Track total adjustment
            adjustments[component] += bonus
        
        # Store the adjustments for later use in the log_indicator_results method
        self._divergence_adjustments = adjustments
        
        # Log summary of adjustments
        self.logger.info("\nFinal adjusted scores:")
        for component, score in adjusted_scores.items():
            original = component_scores[component]
            adjustment = adjustments[component]
            
            if adjustment != 0:
                direction = "+" if adjustment > 0 else ""
                self.logger.info(f"  - {component}: {original:.2f} → {score:.2f} ({direction}{adjustment:.2f})")
            else:
                self.logger.info(f"  - {component}: {score:.2f} (unchanged)")
                
        return adjusted_scores

    def log_indicator_results(self, final_score: float, component_scores: Dict[str, float], symbol: str = "") -> None:
        """
        Log indicator results with divergence adjustment information.
        
        This overrides the base method to include information about divergence adjustments
        in the score contribution breakdown.
        
        Args:
            final_score: Final calculated score
            component_scores: Dictionary of component scores
            symbol: Optional symbol to include in the title
        """
        indicator_name = self.__class__.__name__.replace('Indicators', '')
        
        divergence_adjustments = getattr(self, '_divergence_adjustments', {})

        centralized_log_indicator_results(
            logger=self.logger,
            indicator_name=indicator_name,
            final_score=final_score,
            component_scores=component_scores,
            weights=self.component_weights,
            symbol=symbol,
            divergence_adjustments=divergence_adjustments
        )

    def _calculate_adl_score(self, market_data: Dict[str, Any]) -> float:
        """
        Calculate ADL (Accumulation/Distribution Line) score from market data.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: ADL score (0-100) where 0 is very bearish and 100 is very bullish
        """
        try:
            # Extract OHLCV data
            if 'ohlcv' not in market_data or not market_data['ohlcv'] or 'base' not in market_data['ohlcv']:
                self.logger.warning("No OHLCV data found for ADL calculation")
                return 50.0
                
            df = market_data['ohlcv']['base']
            
            # Calculate ADL using the existing method
            adl_series = self.calculate_adl(df)
            
            # Return neutral score if series is empty
            if adl_series.empty:
                return 50.0
            
            # Get the ADL trend to determine bullish/bearish direction
            # Use the existing _get_adl_trend method which returns a value from -1 to 1
            adl_trend = self._get_adl_trend(market_data)
            
            # Get the current ADL value
            current_adl = float(adl_series.iloc[-1])
            
            # Calculate normalized score based on ADL trend and value
            # If trend is positive (bullish), score should be > 50
            # If trend is negative (bearish), score should be < 50
            
            # First normalize trend to 0-100 scale
            trend_score = 50 + (adl_trend * 50)
            
            # For additional context, look at recent ADL change (last 5 periods)
            if len(adl_series) >= 5:
                recent_change = (adl_series.iloc[-1] - adl_series.iloc[-5]) / max(abs(adl_series.iloc[-5]), 1)
                # Clip to reasonable range
                recent_change = np.clip(recent_change, -1.0, 1.0)
                # Factor into score (weighted 30% recent change, 70% trend)
                score = (0.7 * trend_score) + (0.3 * (50 + recent_change * 50))
            else:
                score = trend_score
            
            # Ensure the score is within 0-100 range
            score = np.clip(score, 0, 100)
            
            self.logger.debug(f"ADL: {current_adl:.2f}, Trend: {adl_trend:.2f}, Normalized score: {score:.2f}")
            
            return float(score)
            
        except Exception as e:
            self.logger.error(f"Error calculating ADL score: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 50.0

    def _get_adl_trend(self, market_data: Dict[str, Any]) -> float:
        """
        Get ADL trend direction from market data.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: ADL trend direction (-1 to 1)
        """
        try:
            # Extract OHLCV data
            if 'ohlcv' not in market_data or not market_data['ohlcv'] or 'base' not in market_data['ohlcv']:
                self.logger.warning("No OHLCV data found for ADL trend calculation")
                return 0.0
                
            df = market_data['ohlcv']['base']
            
            # Calculate ADL using the existing method
            adl_series = self.calculate_adl(df)
            
            # Need at least 20 periods to calculate trend
            if len(adl_series) < 20:
                return 0.0
                
            # Calculate short-term and long-term trends
            short_ma = adl_series.rolling(window=5).mean()
            long_ma = adl_series.rolling(window=20).mean()
            
            # Calculate trend direction (normalized between -1 and 1)
            if pd.isna(short_ma.iloc[-1]) or pd.isna(long_ma.iloc[-1]):
                return 0.0
                
            if long_ma.iloc[-1] == 0:
                return 0.0
                
            trend = (short_ma.iloc[-1] / long_ma.iloc[-1] - 1)
            
            # Clip to reasonable range
            return float(np.clip(trend, -1.0, 1.0))
            
        except Exception as e:
            self.logger.error(f"Error calculating ADL trend: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 0.0

    def _calculate_cmf_score(self, market_data: Dict[str, Any]) -> float:
        """
        Calculate CMF (Chaikin Money Flow) score from market data.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: CMF score (0-100) where 0 is very bearish and 100 is very bullish
        """
        try:
            # Extract raw CMF value (should be between -1 and 1)
            cmf_value = self._get_cmf_value(market_data)

            # Get CMF min/max bounds from config or use defaults
            min_cmf = self.config.get('min_cmf', -1.0)
            max_cmf = self.config.get('max_cmf', 1.0)

            # Linear mapping from CMF to score
            # -1 (min_cmf) -> 0
            # 0 -> 50
            # +1 (max_cmf) -> 100
            normalized_score = 50 * (1 + (cmf_value / max(abs(min_cmf), abs(max_cmf))))

            # Ensure score is within 0-100 range
            score = np.clip(normalized_score, 0, 100)

            self.logger.debug(f"CMF (raw): {cmf_value:.4f}, Normalized score: {score:.2f}")

            return float(score)
            
        except Exception as e:
            self.logger.error(f"Error calculating CMF score: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 50.0

    def _get_cmf_value(self, market_data: Dict[str, Any]) -> float:
        """
        Get raw CMF value from market data.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: Raw CMF value
        """
        try:
            # Extract OHLCV data
            if 'ohlcv' not in market_data or not market_data['ohlcv'] or 'base' not in market_data['ohlcv']:
                self.logger.warning("No OHLCV data found for CMF value calculation")
                return 0.0
                
            df = market_data['ohlcv']['base']
            
            # Get period from config or use default
            period = self.config.get('cmf_period', 20)
            
            # Calculate raw CMF (before normalization)
            # Money Flow Multiplier
            hlrange = df['high'] - df['low']
            hlrange = hlrange.replace(0, np.nan)
            
            # Calculate close location value
            clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / hlrange
            clv = clv.fillna(0)
            
            # Calculate Money Flow Volume
            mfv = clv * df['volume']
            
            # Calculate CMF
            mfv_sum = mfv.rolling(window=period, min_periods=1).sum()
            vol_sum = df['volume'].rolling(window=period, min_periods=1).sum()
            
            cmf_raw = np.where(vol_sum != 0, mfv_sum / vol_sum, 0)
            
            # Get the latest value
            if len(cmf_raw) == 0:
                return 0.0
                
            return float(cmf_raw[-1])
                
        except Exception as e:
            self.logger.error(f"Error calculating raw CMF value: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 0.0

    def _calculate_obv_score(self, market_data: Dict[str, Any]) -> float:
        """
        Calculate OBV (On-Balance Volume) score from market data.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: OBV score (0-100) where 0 is very bearish and 100 is very bullish
        """
        try:
            # Extract OHLCV data
            if 'ohlcv' not in market_data or not market_data['ohlcv'] or 'base' not in market_data['ohlcv']:
                self.logger.warning("No OHLCV data found for OBV calculation")
                return 50.0
                
            df = market_data['ohlcv']['base']
            
            # Calculate OBV using the existing method
            obv_series = self.calculate_obv(df)
            
            # Return neutral score if series is empty
            if obv_series.empty:
                return 50.0
            
            # Get the OBV trend to determine bullish/bearish direction
            # Use the existing _get_obv_trend method which returns a value from -1 to 1
            obv_trend = self._get_obv_trend(market_data)
            
            # Get the current OBV value
            current_obv = float(obv_series.iloc[-1])
            
            # Calculate normalized score based on OBV trend
            # If trend is positive (bullish), score should be > 50
            # If trend is negative (bearish), score should be < 50
            
            # First normalize trend to 0-100 scale
            trend_score = 50 + (obv_trend * 50)
            
            # For additional context, look at OBV rate of change
            if len(obv_series) >= 10:
                # Calculate rate of change over last 10 periods
                obv_roc = (obv_series.iloc[-1] - obv_series.iloc[-10]) 
                
                # Normalize ROC to a reasonable range
                # Use a sigmoid function to map any value to -1 to 1 range
                # The divisor controls sensitivity (higher = less sensitive)
                norm_roc = np.tanh(obv_roc / max(abs(current_obv) / 10, 1))
                
                # Add ROC component to score (weighted 70% trend, 30% ROC)
                roc_score = 50 + (norm_roc * 50)
                score = (0.7 * trend_score) + (0.3 * roc_score)
            else:
                score = trend_score
            
            # Ensure the score is within 0-100 range
            score = np.clip(score, 0, 100)
            
            self.logger.debug(f"OBV: {current_obv:.2f}, Trend: {obv_trend:.2f}, Normalized score: {score:.2f}")
            
            return float(score)
            
        except Exception as e:
            self.logger.error(f"Error calculating OBV score: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 50.0


    def _calculate_volume_delta(self, market_data: Dict[str, Any]) -> float:
        """
        Calculate volume delta score from market data.
        This method adapts calculate_volume_delta to work with market_data format.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: Volume delta score (0-100)
        """
        try:
            self.logger.info("=== _calculate_volume_delta DEBUG ===")
            # Extract trades data - fix DataFrame ambiguity in boolean operations
            if 'processed_trades' in market_data and market_data['processed_trades'] is not None:
                processed_trades = market_data['processed_trades']
                # Check if it's a non-empty DataFrame or non-empty list
                if isinstance(processed_trades, pd.DataFrame) and not processed_trades.empty:
                    trades_df = processed_trades
                    self.logger.info(f"Using processed_trades DataFrame directly: {trades_df.shape}")
                elif isinstance(processed_trades, list) and len(processed_trades) > 0:
                    trades_df = pd.DataFrame(processed_trades)
                    self.logger.info(f"Created trades_df from processed_trades list with {len(processed_trades)} items")
                else:
                    self.logger.warning("processed_trades exists but is empty or invalid")
                    return 50.0
            elif 'trades' in market_data and market_data['trades'] is not None:
                trades = market_data['trades']
                # Check if it's a non-empty DataFrame or non-empty list
                if isinstance(trades, pd.DataFrame) and not trades.empty:
                    trades_df = trades
                    self.logger.info(f"Using trades DataFrame directly: {trades_df.shape}")
                elif isinstance(trades, list) and len(trades) > 0:
                    trades_df = pd.DataFrame(trades)
                    self.logger.info(f"Created trades_df from trades list with {len(trades)} items")
                else:
                    self.logger.warning("trades exists but is empty or invalid")
                    return 50.0
            else:
                self.logger.warning("No trades data found for volume delta calculation")
                return 50.0
                
            # Debug the trades DataFrame structure
            self.logger.info(f"Trades DataFrame columns: {trades_df.columns.tolist()}")
            self.logger.info(f"Trades DataFrame dtypes: {trades_df.dtypes.to_dict()}")
            if not trades_df.empty:
                self.logger.info(f"First row of trades_df: {trades_df.iloc[0].to_dict()}")
                if 'side' in trades_df.columns:
                    self.logger.info(f"Side column unique values: {trades_df['side'].unique()}")
                    self.logger.info(f"Side column type: {type(trades_df['side'].iloc[0]) if len(trades_df) > 0 else 'Empty'}")
                
            # Extract price data (OHLCV)
            price_df = None
            if 'ohlcv' in market_data and market_data['ohlcv'] and 'base' in market_data['ohlcv']:
                price_df = market_data['ohlcv']['base']
                
            # Calculate volume delta using the existing method
            result = self.calculate_volume_delta(trades_df, price_df)
            
            # Return the final score or default to 50.0
            return result.get('final_score', 50.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating volume delta: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 50.0
            
    def _get_raw_volume_delta(self, market_data: Dict[str, Any]) -> float:
        """
        Get raw volume delta value from market data.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: Raw volume delta value
        """
        try:
            # Extract trades data
            if 'processed_trades' in market_data and market_data['processed_trades']:
                # Convert processed trades to DataFrame if it's a list
                if isinstance(market_data['processed_trades'], list):
                    trades_df = pd.DataFrame(market_data['processed_trades'])
                else:
                    trades_df = market_data['processed_trades']
            elif 'trades' in market_data and market_data['trades']:
                # Convert trades to DataFrame if it's a list
                if isinstance(market_data['trades'], list):
                    trades_df = pd.DataFrame(market_data['trades'])
                else:
                    trades_df = market_data['trades']
            else:
                self.logger.warning("No trades data found for raw volume delta calculation")
                return 0.0
                
            # Check if we have the necessary columns
            if 'side' not in trades_df.columns:
                self.logger.warning("Missing 'side' column in trades data")
                return 0.0
                
            # Normalize side values - fix DataFrame ambiguity issue
            # Debug: Check the actual data structure
            self.logger.debug(f"Trades DataFrame shape: {trades_df.shape}")
            self.logger.debug(f"Trades DataFrame columns: {trades_df.columns.tolist()}")
            self.logger.debug(f"Side column type: {type(trades_df['side'])}")
            self.logger.debug(f"Side column sample values: {trades_df['side'].head().tolist()}")
            
            # Use a more robust approach to handle potential DataFrame issues
            try:
                # Convert side column to string first to avoid any DataFrame ambiguity
                side_series = trades_df['side'].astype(str)
                trades_df['side_value'] = side_series.map(lambda x: 1 if x.lower() == 'buy' else -1)
                self.logger.debug(f"Successfully mapped side values: {trades_df['side_value'].value_counts().to_dict()}")
            except Exception as e:
                self.logger.error(f"Error in side mapping: {str(e)}")
                # Fallback approach using numpy where (most robust)
                try:
                    trades_df['side_value'] = np.where(trades_df['side'].astype(str).str.lower() == 'buy', 1, -1)
                    self.logger.debug("Used numpy where fallback for side mapping")
                except Exception as e2:
                    self.logger.error(f"Error in numpy where fallback: {str(e2)}")
                    # Final fallback - assume equal buy/sell
                    trades_df['side_value'] = 0
                    self.logger.warning("Used neutral fallback for side mapping")
                
            # Get volume column
            volume_col = 'amount'
            if 'size' in trades_df.columns:
                volume_col = 'size'
                
            if volume_col not in trades_df.columns:
                self.logger.warning(f"Missing volume column ({volume_col}) in trades data")
                return 0.0
                
            # Calculate buy and sell volumes
            buy_volume = trades_df[trades_df['side_value'] == 1][volume_col].sum()
            sell_volume = trades_df[trades_df['side_value'] == -1][volume_col].sum()
            
            # Calculate raw delta ratio
            total_volume = buy_volume + sell_volume
            if total_volume == 0:
                return 0.0
                
            return (buy_volume - sell_volume) / total_volume
            
        except Exception as e:
            self.logger.error(f"Error calculating raw volume delta: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 0.0

    def _validate_weights(self):
        """Validate that weights sum to 1.0"""
        comp_total = sum(self.component_weights.values())
        if not np.isclose(comp_total, 1.0):
            self.logger.warning(f"Component weights sum to {comp_total}, normalizing")
            self.component_weights = {k: v/comp_total for k, v in self.component_weights.items()}

    def _get_default_scores(self, reason: str = 'UNKNOWN') -> Dict[str, Any]:
        """Return default scores when analysis fails."""
        timestamp = int(time.time() * 1000)
        return {
            'score': 50.0,
            'components': {
                'volume_delta': 50.0,
                'adl': 50.0,
                'cmf': 50.0,
                'relative_volume': 50.0,
                'obv': 50.0
            },
            'metadata': {
                'timestamp': timestamp,
                'error': f'Failed to calculate volume indicators: {reason}',
                'status': 'ERROR'
            }
        }

    def _get_obv_trend(self, market_data: Dict[str, Any]) -> float:
        """
        Get OBV trend direction from market data.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: OBV trend direction (-1 to 1)
        """
        try:
            # Extract OHLCV data
            if 'ohlcv' not in market_data or not market_data['ohlcv'] or 'base' not in market_data['ohlcv']:
                self.logger.warning("No OHLCV data found for OBV trend calculation")
                return 0.0
            
            df = market_data['ohlcv']['base']
            
            # Calculate OBV using the existing method
            obv_series = self.calculate_obv(df)
            
            # Need at least 20 periods to calculate trend
            if len(obv_series) < 20:
                return 0.0
            
            # Calculate short-term and long-term trends
            short_ma = obv_series.rolling(window=5, min_periods=1).mean()
            long_ma = obv_series.rolling(window=20, min_periods=1).mean()
            
            # Calculate trend direction (normalized between -1 and 1) with safety checks
            if pd.isna(short_ma.iloc[-1]) or pd.isna(long_ma.iloc[-1]):
                return 0.0
            
            if abs(long_ma.iloc[-1]) < 1e-10:  # Safer than checking for exactly zero
                return 0.0
            
            trend = (short_ma.iloc[-1] / long_ma.iloc[-1] - 1)
            
            # Clip to reasonable range
            return float(np.clip(trend, -1.0, 1.0))
        
        except Exception as e:
            self.logger.error(f"Error calculating OBV trend: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 0.0

    def _get_relative_volume_ratio(self, market_data: Dict[str, Any]) -> float:
        """
        Get relative volume ratio from market data using EMA for consistency.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: Relative volume ratio (current volume / EMA volume)
        """
        try:
            # Extract OHLCV data
            if 'ohlcv' not in market_data or not market_data['ohlcv'] or 'base' not in market_data['ohlcv']:
                self.logger.warning("No OHLCV data found for relative volume ratio calculation")
                return 1.0
                
            df = market_data['ohlcv']['base']
            
            # Get period from params or use default
            period = self.params.get('rel_vol_period', 20)
            
            # Find volume column with expanded search
            volume_col = None
            for col in ['volume', 'amount', 'vol', 'size', 'quantity']:
                if col in df.columns:
                    volume_col = col
                    break
                
            if not volume_col:
                # Try to check if any column contains volume or size in its name
                volume_cols = [col for col in df.columns if any(term in col.lower() for term in ['volume', 'size', 'amount', 'quantity', 'vol'])]
                if volume_cols:
                    volume_col = volume_cols[0]
                else:
                    self.logger.warning("No volume column found for relative volume ratio calculation")
                    return 1.0
            
            # Calculate current volume and EMA volume with proper error handling
            volume = pd.to_numeric(df[volume_col], errors='coerce').fillna(0)
            current_volume = volume.iloc[-1]
            
            # Use EMA instead of SMA for consistency with primary calculation method
            volume_ema = volume.ewm(span=period, adjust=False).mean().iloc[-1]
            
            # Calculate ratio with safety check
            if volume_ema == 0 or pd.isna(volume_ema):
                return 1.0
                
            ratio = current_volume / volume_ema
            
            # Return with reasonable limits
            return float(np.clip(ratio, 0.0, 10.0))
            
        except Exception as e:
            self.logger.error(f"Error calculating relative volume ratio: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 1.0

    def _calculate_price_aware_relative_volume(self, market_data: Dict[str, Any]) -> float:
        """
        Calculate price-aware relative volume score that considers both volume intensity 
        and price movement direction for more accurate trading signals.
        
        This addresses the limitation where high volume + declining price gets bullish scores.
        
        Args:
            market_data: Dictionary containing market data with OHLCV
            
        Returns:
            float: Price-aware RVOL score (0-100) where:
                   - High volume + up price = High bullish score (75-100)
                   - High volume + down price = Low bearish score (0-25)
                   - Low volume = Neutral range (40-60)
        """
        try:
            # Extract OHLCV data
            if 'ohlcv' not in market_data or not market_data['ohlcv'] or 'base' not in market_data['ohlcv']:
                self.logger.warning("No OHLCV data found for price-aware RVOL calculation")
                return 50.0
                
            df = market_data['ohlcv']['base']
            
            if df.empty or len(df) < 2:
                return 50.0
            
            # Get configuration parameters
            period = self.config.get('relative_volume_period', 30)
            price_weight = self.config.get('price_weight', 0.6)  # How much price direction affects score
            
            # Calculate base RVOL
            rel_vol_series = self.calculate_relative_volume(df, period=period)
            if rel_vol_series.empty:
                return 50.0
            
            rel_vol = float(rel_vol_series.iloc[-1])
            
            # Calculate price factors
            current_candle = df.iloc[-1]
            previous_candle = df.iloc[-2]
            
            # 1. Price Direction Factor (-1 to +1)
            price_change = (current_candle['close'] - previous_candle['close']) / previous_candle['close']
            price_direction = np.tanh(price_change * 20)  # Sigmoid scaling
            
            # 2. Candle Body Strength Factor (0 to 1)
            candle_range = current_candle['high'] - current_candle['low']
            candle_body = abs(current_candle['close'] - current_candle['open'])
            body_strength = candle_body / candle_range if candle_range > 0 else 0
            
            # 3. Intraday Position Factor (-1 to +1)
            # Where did price close within the day's range?
            if candle_range > 0:
                close_position = ((current_candle['close'] - current_candle['low']) / candle_range) * 2 - 1
            else:
                close_position = 0
            
            # 4. Multi-period Price Momentum (3-period)
            if len(df) >= 4:
                price_momentum = (current_candle['close'] - df.iloc[-4]['close']) / df.iloc[-4]['close']
                momentum_factor = np.tanh(price_momentum * 10)
            else:
                momentum_factor = price_direction
            
            # Combine price factors with weights
            price_factor = (
                price_direction * 0.4 +          # Current candle direction
                close_position * 0.3 +           # Intraday strength
                momentum_factor * 0.2 +          # Multi-period momentum
                (body_strength - 0.5) * 0.1      # Candle conviction
            )
            
            # Normalize base RVOL score (same as original method)
            min_rvol = self.config.get('min_rvol', 0.1)
            max_rvol = self.config.get('max_rvol', 3.0)
            
            if rel_vol < 1.0:
                base_score = 50 * (rel_vol - min_rvol) / (1.0 - min_rvol)
            else:
                base_score = 50 + 50 * (rel_vol - 1.0) / (max_rvol - 1.0)
            
            base_score = np.clip(base_score, 0, 100)
            
            # Apply price-aware adjustment
            # High volume scenarios get more price influence
            volume_intensity = min(rel_vol / 2.0, 1.0)  # 0 to 1 scale
            price_influence = price_weight * volume_intensity
            
            # Calculate final score
            if price_factor > 0:
                # Bullish price action: enhance positive scores
                final_score = base_score + (100 - base_score) * price_factor * price_influence
            else:
                # Bearish price action: reduce scores toward bearish territory
                final_score = base_score + (base_score - 0) * price_factor * price_influence
            
            final_score = np.clip(final_score, 0, 100)
            
            # Logging for analysis
            self.logger.debug(f"Price-Aware RVOL Analysis:")
            self.logger.debug(f"  Base RVOL: {rel_vol:.2f}x → Base Score: {base_score:.1f}")
            self.logger.debug(f"  Price Change: {price_change*100:.2f}%")
            self.logger.debug(f"  Price Direction: {price_direction:.2f}")
            self.logger.debug(f"  Close Position: {close_position:.2f}")
            self.logger.debug(f"  Body Strength: {body_strength:.2f}")
            self.logger.debug(f"  Combined Price Factor: {price_factor:.2f}")
            self.logger.debug(f"  Final Score: {final_score:.1f}")
            
            return float(final_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating price-aware relative volume: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 50.0

    def _calculate_directional_volume_score(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate separate up-volume and down-volume scores for more granular analysis.
        
        Returns:
            Dict with 'up_volume_score', 'down_volume_score', and 'net_volume_score'
        """
        try:
            if 'ohlcv' not in market_data or not market_data['ohlcv'] or 'base' not in market_data['ohlcv']:
                return {'up_volume_score': 50.0, 'down_volume_score': 50.0, 'net_volume_score': 50.0}
                
            df = market_data['ohlcv']['base']
            
            if df.empty or len(df) < 2:
                return {'up_volume_score': 50.0, 'down_volume_score': 50.0, 'net_volume_score': 50.0}
            
            # Find volume column
            volume_col = None
            for col in ['volume', 'amount', 'vol', 'quantity']:
                if col in df.columns:
                    volume_col = col
                    break
            
            if not volume_col:
                return {'up_volume_score': 50.0, 'down_volume_score': 50.0, 'net_volume_score': 50.0}
            
            # Calculate price changes
            df = df.copy()
            df['price_change'] = df['close'].pct_change()
            
            # Separate up and down volume
            df['up_volume'] = np.where(df['price_change'] > 0, df[volume_col], 0)
            df['down_volume'] = np.where(df['price_change'] < 0, df[volume_col], 0)
            
            # Calculate EMAs for up and down volume
            period = self.config.get('relative_volume_period', 30)
            up_volume_ema = df['up_volume'].ewm(span=period, adjust=False).mean()
            down_volume_ema = df['down_volume'].ewm(span=period, adjust=False).mean()
            
            # Current values
            current_up_vol = df['up_volume'].iloc[-1]
            current_down_vol = df['down_volume'].iloc[-1]
            avg_up_vol = up_volume_ema.iloc[-1]
            avg_down_vol = down_volume_ema.iloc[-1]
            
            # Calculate relative volumes
            up_rvol = current_up_vol / avg_up_vol if avg_up_vol > 0 else 1.0
            down_rvol = current_down_vol / avg_down_vol if avg_down_vol > 0 else 1.0
            
            # Convert to scores (0-100)
            up_score = min(up_rvol * 25, 100)  # Up volume is bullish
            down_score = max(100 - down_rvol * 25, 0)  # Down volume is bearish
            
            # Net score considers the balance
            total_current = current_up_vol + current_down_vol
            if total_current > 0:
                up_ratio = current_up_vol / total_current
                net_score = up_ratio * 100
            else:
                net_score = 50.0
            
            return {
                'up_volume_score': float(up_score),
                'down_volume_score': float(down_score),
                'net_volume_score': float(net_score)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating directional volume scores: {str(e)}")
            return {'up_volume_score': 50.0, 'down_volume_score': 50.0, 'net_volume_score': 50.0}
    
    def _log_component_specific_alerts(self, component_scores: Dict[str, float], 
                                     alerts: List[str], indicator_name: str) -> None:
        """Log Volume Indicators specific alerts."""
        # Volume Delta alerts
        volume_delta_score = component_scores.get('volume_delta', 50)
        if volume_delta_score >= 75:
            alerts.append("Volume Delta Extremely Bullish - Strong buying pressure")
        elif volume_delta_score <= 25:
            alerts.append("Volume Delta Extremely Bearish - Strong selling pressure")
        
        # Relative Volume alerts
        rel_volume_score = component_scores.get('relative_volume', 50)
        if rel_volume_score >= 80:
            alerts.append("Relative Volume Extreme - RVOL > 4.0x - Potential overextension")
        elif rel_volume_score >= 70:
            alerts.append("Relative Volume Strong - RVOL > 3.0x - High-probability setup")
        elif rel_volume_score >= 60:
            alerts.append("✅ Relative Volume Significant - RVOL > 2.0x - Professional entry level")
        elif rel_volume_score <= 30:
            alerts.append("Relative Volume Low - RVOL < 1.0x - Weak participation")
        
        # CMF alerts
        cmf_score = component_scores.get('cmf', 50)
        if cmf_score >= 75:
            alerts.append("Chaikin Money Flow Extremely Bullish - Strong buying pressure")
        elif cmf_score <= 25:
            alerts.append("Chaikin Money Flow Extremely Bearish - Strong selling pressure")
        
        # ADL alerts
        adl_score = component_scores.get('adl', 50)
        if adl_score >= 75:
            alerts.append("ADL Extremely Bullish - Strong accumulation")
        elif adl_score <= 25:
            alerts.append("ADL Extremely Bearish - Strong distribution")
        
        # OBV alerts
        obv_score = component_scores.get('obv', 50)
        if obv_score >= 75:
            alerts.append("OBV Extremely Bullish - Strong trend confirmation")
        elif obv_score <= 25:
            alerts.append("OBV Extremely Bearish - Strong trend confirmation")
        
        # Volume Profile alerts
        volume_profile_score = component_scores.get('volume_profile', 50)
        if volume_profile_score >= 75:
            alerts.append("Volume Profile Bullish - Price at high-volume support")
        elif volume_profile_score <= 25:
            alerts.append("Volume Profile Bearish - Price at high-volume resistance")
        
        # VWAP alerts
        vwap_score = component_scores.get('vwap', 50)
        if vwap_score >= 75:
            alerts.append("VWAP Extremely Bullish - Strong above VWAP")
        elif vwap_score <= 25:
            alerts.append("VWAP Extremely Bearish - Strong below VWAP")
