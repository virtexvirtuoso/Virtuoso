import pandas as pd
import numpy as np
from typing import Dict, Any, Union, List, Optional
import logging
import traceback
import time
from scipy import stats

from src.utils.indicators import IndicatorUtils
from src.utils.error_handling import handle_calculation_error, handle_indicator_error, validate_input
from src.config.manager import ConfigManager
from .base_indicator import BaseIndicator, IndicatorMetrics
from ..core.logger import Logger
from src.core.analysis.indicator_utils import log_score_contributions, log_component_analysis, log_final_score, log_calculation_details, log_multi_timeframe_analysis


# Get module logger
logger = logging.getLogger('VolumeIndicators')

class VolumeIndicators(BaseIndicator):
    """Volume-based trading indicators."""

    def __init__(self, config: Dict[str, Any], logger: Optional[Logger] = None):
        # Set required attributes before calling super().__init__
        self.indicator_type = 'volume'
        
        # Default component weights
        default_weights = {
            'volume_delta': 0.20,    # Volume Delta (20%)
            'adl': 0.15,            # ADL (15%)
            'cmf': 0.15,            # CMF (15%)
            'relative_volume': 0.20, # Relative Volume (20%)
            'obv': 0.15,            # OBV (15%)
            'divergence': 0.15      # Divergence (15%)
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
        
        # Read component weights from config if available
        components_config = volume_config['components']
        self.component_weights = {}
        
        # Use weights from config or fall back to defaults
        for component, default_weight in default_weights.items():
            component_config = components_config.get(component, {})
            if isinstance(component_config, dict):
                config_weight = component_config.get('weight', default_weight)
            else:
                config_weight = default_weight
            self.component_weights[component] = config_weight
        
        # Now call super().__init__
        super().__init__(config, logger)
        
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
            
            # Relative volume parameters
            'rel_vol_period': 20,             # Period for relative volume comparison
            'rel_vol_threshold': 1.5,         # Threshold for significant volume increase
            
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
            
            # Log component contribution breakdown
            self.logger.info("\n=== Volume Score Contribution Breakdown ===")
            for component, score in scores.items():
                weight = self.component_weights.get(component, 0)
                contribution = score * weight
                self.logger.info(f"{component}: {score:.2f} × {weight:.2f} = {contribution:.2f}")
            
            # Calculate weighted score
            final_score = self._compute_weighted_score(scores)
            self.logger.info(f"\nFinal Volume Score: {final_score:.2f}")
            
            return final_score
            
        except Exception as e:
            self.logger.error(f"Error calculating volume score: {str(e)}")
            return 50.0

    def _log_volume_interpretation(self, final_score: float, components: Dict[str, float]) -> None:
        """Log interpretation of volume analysis results."""
        try:
            # Interpret overall score
            if final_score >= 70:
                interpretation = "Strong bullish volume"
            elif final_score >= 60:
                interpretation = "Moderate bullish volume"
            elif final_score <= 30:
                interpretation = "Strong bearish volume"
            elif final_score <= 40:
                interpretation = "Moderate bearish volume"
            else:
                interpretation = "Neutral volume conditions"

            self.logger.debug(f"Overall: {interpretation} (Score: {final_score:.2f})")

            # Use enhanced component analysis formatting for component breakdown
            log_component_analysis(self.logger, "Volume Analysis Interpretation", components)

        except Exception as e:
            self.logger.error(f"Error logging volume interpretation: {str(e)}")

    async def get_signals(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get volume-specific signals."""
        try:
            primary_tf = list(market_data['ohlcv'].keys())[0]
            df = market_data['ohlcv'][primary_tf]
            
            return {
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
        """Calculate volume profile score."""
        try:
            # Calculate up/down volume ratio
            up_volume = df.loc[df['close'] > df['open'], 'volume'].sum()
            down_volume = df.loc[df['close'] < df['open'], 'volume'].sum()
            
            if down_volume == 0:
                return 100.0
                
            ratio = up_volume / down_volume
            
            # Normalize to 0-100 range
            score = min(max((ratio - 0.5) * 100, 0), 100)
            
            return float(score)
            
        except Exception as e:
            self.logger.error(f"Error calculating volume profile score: {str(e)}")
            return 50.0

    @handle_calculation_error(default_value={'volume_delta': 50.0, 'divergence': 0.0})
    def calculate_volume_delta(self, trades_df: pd.DataFrame, price_df: pd.DataFrame = None, window: int = None) -> Dict[str, float]:
        """Calculate Volume Delta with divergence as bonus signal."""
        try:
            self.logger.debug("\n=== Starting Volume Delta Calculation ===")
            self.logger.debug(f"Input trades shape: {trades_df.shape if trades_df is not None else 'None'}")
            self.logger.debug(f"Input price shape: {price_df.shape if price_df is not None else 'None'}")
            
            # Use parameter from config or default
            if window is None:
                window = self.params.get('volume_delta_lookback', 20)
                self.logger.debug(f"Using volume delta lookback window: {window}")
            
            # Calculate base volume delta score
            base_score = self._calculate_base_volume_score(trades_df)
            self.logger.debug(f"Base volume score: {base_score:.2f}")
            
            # Calculate divergence bonus
            divergence_bonus = 0.0
            if price_df is not None:
                self.logger.debug("Calculating divergence bonus...")
                divergence_bonus = self._calculate_volume_divergence_bonus(price_df)
                if isinstance(divergence_bonus, dict):
                    self.logger.debug(f"Divergence bonus: {divergence_bonus}")
                    # Extract the strength value for calculations
                    divergence_value = divergence_bonus.get('strength', 0.0)
                else:
                    self.logger.debug(f"Divergence bonus: {divergence_bonus:.2f}")
                    divergence_value = divergence_bonus
            
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
            
            # Calculate Money Flow Volume
            mfv = clv * df[volume_col]
            
            # Calculate rolling sums with adaptive period
            mfv_sum = mfv.rolling(window=period, min_periods=1).sum()
            vol_sum = df[volume_col].rolling(window=period, min_periods=1).sum()
            
            # Calculate CMF
            cmf = np.where(vol_sum != 0, mfv_sum / vol_sum, 0)
            cmf = pd.Series(cmf, index=df.index)
            
            # Apply exponential smoothing
            if smoothing > 0:
                cmf = cmf.ewm(alpha=smoothing, adjust=False).mean()
            
            # Log CMF stats before normalization
            self.logger.debug(f"CMF stats before normalization - min: {cmf.min():.2f}, max: {cmf.max():.2f}, current: {cmf.iloc[-1]:.2f}")
            
            # Normalize to 0-100 scale with bounds checking
            normalized_cmf = np.clip((cmf + 1) * 50, 0, 100)
            
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
    def calculate_relative_volume(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate relative volume with improved debugging."""
        try:
            self.logger.debug("\n=== Calculating Relative Volume ===")
            self.logger.debug(f"Input shape: {df.shape}")
            self.logger.debug(f"Using period: {period}")
            
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
            
            # Calculate metrics
            volume = df[volume_col].astype(float)
            # Changed from SMA to EMA
            volume_ema = volume.ewm(span=period, adjust=False).mean()
            
            self.logger.debug("\nVolume Statistics:")
            self.logger.debug(f"Current volume: {volume.iloc[-1]:.2f}")
            self.logger.debug(f"Average volume (EMA): {volume_ema.iloc[-1]:.2f}")
            
            # Calculate relative volume with safety check
            rel_vol = np.where(volume_ema > 0, volume / volume_ema, 1.0)
            rel_vol = pd.Series(rel_vol, index=df.index)
            
            self.logger.debug(f"Relative volume: {rel_vol.iloc[-1]:.2f}")
            
            return rel_vol
            
        except Exception as e:
            self.logger.error(f"Error calculating relative volume: {str(e)}", exc_info=True)
            return pd.Series([50.0] * len(df))

    def _calculate_relative_volume(self, market_data: Dict[str, Any]) -> float:
        """
        Calculate relative volume score from market data.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: Relative volume score (0-100) where 0 is very bearish and 100 is very bullish
        """
        try:
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
            
            self.logger.debug(f"RVOL: {rel_vol:.2f}, Normalized score: {score:.2f}")
            
            return float(score)
            
        except Exception as e:
            self.logger.error(f"Error calculating relative volume score: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 50.0

    def _calculate_base_volume_score(self, df: pd.DataFrame) -> float:
        """Calculate base volume score."""
        try:
            if df is None or df.empty:
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
                
                # Handle NaN in correlation
                if correlation.isna().all():
                    self.logger.warning("All correlation values are NaN, using neutral direction")
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

    async def calculate(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate volume indicator scores with detailed analysis.
        
        Args:
            market_data: Dictionary containing OHLCV and other market data
            
        Returns:
            Dict containing indicator scores, components, signals and metadata
        """
        try:
            self.logger.info("\n=== VOLUME INDICATORS Detailed Calculation ===")
            
            # Validate input
            if not self.validate_input(market_data):
                self.logger.error("Invalid input data for volume analysis")
                return {
                    'score': 50.0,
                    'components': {},
                    'signals': {},
                    'metadata': {'error': 'Invalid input data'}
                }
            
            # Extract symbol from market data
            symbol = market_data.get('symbol', '')
            
            # Calculate scores for each timeframe
            timeframe_scores = {}
            base_scores = None  # Will hold the base timeframe scores
            
            for tf, tf_weight in self.timeframe_weights.items():
                if tf not in market_data.get('ohlcv', {}):
                    continue
                    
                tf_df = market_data['ohlcv'][tf]
                if not isinstance(tf_df, pd.DataFrame) or tf_df.empty:
                    continue
                
                # Calculate component scores for this timeframe
                tf_scores = {}
                
                # Volume Delta
                tf_scores['volume_delta'] = self._calculate_volume_delta(market_data)
                
                # ADL
                tf_scores['adl'] = self._calculate_adl_score(market_data)
                
                # CMF
                tf_scores['cmf'] = self._calculate_cmf_score(market_data)
                
                # Relative Volume
                tf_scores['relative_volume'] = self._calculate_relative_volume(market_data)
                
                # OBV
                tf_scores['obv'] = self._calculate_obv_score(market_data)
                
                # Store scores for this timeframe
                timeframe_scores[tf] = tf_scores
                
                # Store base timeframe scores to avoid recalculation
                if tf == 'base':
                    base_scores = tf_scores
            
            # Create volume signals dictionary
            signals = {}
            
            # For now, we'll use the base timeframe scores for signal generation
            # In the future, consider weighted multi-timeframe approach
            tf = 'base'
            if tf in timeframe_scores:
                scores = timeframe_scores[tf]
                
                # Calculate volume profile signals
                volume_sma = self._calculate_volume_sma_score(market_data['ohlcv'][tf])
                volume_trend = self._calculate_volume_trend_score(market_data['ohlcv'][tf])
                volume_profile = self._calculate_volume_profile_score(market_data['ohlcv'][tf])
                
                signals['volume_sma'] = {'value': volume_sma, 'signal': 'low' if volume_sma < 33 else 'normal' if volume_sma < 66 else 'high'}
                signals['volume_trend'] = {'value': volume_trend, 'signal': 'decreasing' if volume_trend < 33 else 'stable' if volume_trend < 66 else 'increasing'}
                signals['volume_profile'] = {'value': volume_profile, 'signal': 'bearish' if volume_profile < 33 else 'neutral' if volume_profile < 66 else 'bullish'}
            
            # Calculate divergences for bonus points
            divergences = {}
            
            # For demonstration, let's add a simple divergence check
            if 'trades' in market_data and isinstance(market_data['trades'], pd.DataFrame) and not market_data['trades'].empty:
                # Calculate divergence between volume and price
                divergence_result = self._calculate_volume_divergence_bonus(market_data['ohlcv']['base'])
                if divergence_result:
                    divergences['volume_price'] = divergence_result
            
            # Create a final component scores dictionary combining all timeframes
            component_scores = {}
            
            # Calculate weighted component scores
            # For now, we'll use explicit calculations for each component
            # In the future, consider a more modular approach
            if all(tf in timeframe_scores for tf in self.timeframe_weights):
                # Volume Delta
                delta_score = self._calculate_volume_delta(market_data)
                delta_value = self._get_raw_volume_delta(market_data)
                component_scores['volume_delta'] = delta_score
                self.logger.info(f"Volume Delta: Raw={delta_value:.2f}, Score={delta_score:.2f}")
                
                # ADL
                adl_score = self._calculate_adl_score(market_data)
                adl_trend = self._get_adl_trend(market_data)
                component_scores['adl'] = adl_score
                self.logger.info(f"ADL: Trend Direction={adl_trend:.4f}, Score={adl_score:.2f}")
                
                # CMF
                cmf_score = self._calculate_cmf_score(market_data)
                cmf_value = self._get_cmf_value(market_data)
                component_scores['cmf'] = cmf_score
                self.logger.info(f"CMF: Value={cmf_value:.4f}, Score={cmf_score:.2f}")
                
                # Relative Volume
                rel_volume_score = self._calculate_relative_volume(market_data)
                rel_volume_ratio = self._get_relative_volume_ratio(market_data)
                component_scores['relative_volume'] = rel_volume_score
                self.logger.info(f"Relative Volume: Ratio={rel_volume_ratio:.2f}, Score={rel_volume_score:.2f}")
                
                # OBV
                obv_score = self._calculate_obv_score(market_data)
                obv_trend = self._get_obv_trend(market_data)
                component_scores['obv'] = obv_score
                self.logger.info(f"OBV: Trend={obv_trend:.4f}, Score={obv_score:.2f}")
                
                # Note: VWAP has been removed from volume components
            
            # Apply divergence bonuses using enhanced method
            adjusted_scores = self._apply_divergence_bonuses(component_scores, divergences)
            
            # Calculate final score using component weights
            final_score = self._compute_weighted_score(adjusted_scores)
            
            # Log component contribution breakdown and final score
            self.log_indicator_results(final_score, adjusted_scores, symbol)
            
            # Get signals
            signals = await self.get_signals(market_data)
            
            # Collect raw values for metadata
            raw_values = {
                'volume_delta': float(self._get_raw_volume_delta(market_data)),
                'adl_trend': float(adl_trend),
                'cmf': float(self._get_cmf_value(market_data)),
                'relative_volume': float(self._get_relative_volume_ratio(market_data)),
                'obv_trend': float(self._get_obv_trend(market_data))
            }
            
            # Return standardized format
            return {
                'score': float(np.clip(final_score, 0, 100)),
                'components': adjusted_scores,
                'signals': signals,
                'timeframe_scores': timeframe_scores,
                'divergences': divergences,
                'metadata': {
                    'timestamp': int(time.time() * 1000),
                    'component_weights': self.component_weights,
                    'timeframe_weights': self.timeframe_weights,
                    'raw_values': raw_values
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating volume indicators: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {
                'score': 50.0,
                'components': {},
                'signals': {},
                'metadata': {'error': str(e)}
            }

    def _calculate_vwap_score(self, market_data: Dict[str, Any]) -> float:
        """Calculate VWAP-based score."""
        try:
            df = market_data['ohlcv']['base']
            
            # Calculate VWAP
            df['vwap'] = (df['high'] + df['low'] + df['close']) / 3 * df['volume']
            df['vwap'] = df['vwap'].cumsum() / df['volume'].cumsum()
            
            # Calculate score based on price vs VWAP
            price_vwap_ratio = df['close'].iloc[-1] / df['vwap'].iloc[-1]
            
            # Normalize to 0-100 score
            score = 50 * (1 + np.tanh(np.log(price_vwap_ratio)))
            return float(np.clip(score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating VWAP score: {str(e)}")
            return 50.0

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
        # Get the indicator name (remove "Indicators" suffix)
        indicator_name = self.__class__.__name__.replace('Indicators', '')
        
        # First check if we have divergence adjustment data
        divergence_adjustments = {}
        
        # See if we have the adjustments stored
        if hasattr(self, '_divergence_adjustments'):
            divergence_adjustments = self._divergence_adjustments
        
        # First log the component breakdown with divergence adjustments
        breakdown_title = f"{indicator_name} Score Contribution Breakdown"
        
        # Create list of (component, score, weight, contribution) tuples
        contributions = []
        for component, score in component_scores.items():
            weight = self.component_weights.get(component, 0)
            contribution = score * weight
            contributions.append((component, score, weight, contribution))
        
        # Sort by contribution (highest first)
        contributions.sort(key=lambda x: x[3], reverse=True)
        
        # Use enhanced formatter with divergence adjustments
        from src.core.formatting.formatter import LogFormatter
        formatted_section = LogFormatter.format_score_contribution_section(
            breakdown_title, 
            contributions, 
            symbol,
            divergence_adjustments
        )
        self.logger.info(formatted_section)
        
        # Then log the final score
        from src.core.analysis.indicator_utils import log_final_score
        log_final_score(self.logger, indicator_name, final_score, symbol)

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
            # Extract OHLCV data
            if 'ohlcv' not in market_data or not market_data['ohlcv'] or 'base' not in market_data['ohlcv']:
                self.logger.warning("No OHLCV data found for CMF calculation")
                return 50.0
                
            df = market_data['ohlcv']['base']
            
            # Get period from config or use default
            period = self.config.get('cmf_period', 20)
            
            # Calculate CMF using the existing method
            cmf_series = self.calculate_cmf(df, period=period)
            
            # Return neutral score if series is empty
            if cmf_series.empty:
                return 50.0
            
            # Get raw CMF value (typically ranges from -1 to 1)
            cmf_value = float(cmf_series.iloc[-1])
            
            # Normalize CMF to 0-100 scale
            # CMF range is typically -1 to +1, where:
            # -1 is extremely bearish (strong selling pressure)
            # 0 is neutral
            # +1 is extremely bullish (strong buying pressure)
            
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
            
            self.logger.debug(f"CMF: {cmf_value:.4f}, Normalized score: {score:.2f}")
            
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
                self.logger.warning("No trades data found for volume delta calculation")
                return 50.0
                
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
                
            # Normalize side values
            trades_df['side_value'] = trades_df['side'].map(lambda x: 1 if x.lower() in ['buy'] else -1)
                
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
        Get relative volume ratio from market data.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: Relative volume ratio (current volume / average volume)
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
            
            # Calculate current volume and average volume with proper error handling
            volume = pd.to_numeric(df[volume_col], errors='coerce').fillna(0)
            current_volume = volume.iloc[-1]
            avg_volume = volume.rolling(window=period, min_periods=1).mean().iloc[-1]
            
            # Calculate ratio with safety check
            if avg_volume == 0 or pd.isna(avg_volume):
                return 1.0
                
            ratio = current_volume / avg_volume
            
            # Return with reasonable limits
            return float(np.clip(ratio, 0.0, 10.0))
            
        except Exception as e:
            self.logger.error(f"Error calculating relative volume ratio: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 1.0
