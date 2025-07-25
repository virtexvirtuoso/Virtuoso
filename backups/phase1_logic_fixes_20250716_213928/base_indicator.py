from typing import Dict, Any, Optional, List, Union
try:
    from typing import TypedDict
except ImportError:
    # Python < 3.8 compatibility
    from typing_extensions import TypedDict
import time
import logging
import traceback
import pandas as pd
import numpy as np
import functools
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
from src.core.logger import Logger
import inspect
import copy
from src.validation import ValidationService, ValidationContext

# BaseIndicator API Standardization:
# - All indicators now use calculate() as the standard entry point
# - calculate() returns a standardized dictionary with keys:
#   - score: Overall indicator score (0-100)
#   - components: Individual component scores
#   - signals: Trading signals and interpretations
#   - metadata: Additional data including timestamp and raw values
# - Helper methods (calculate_score, get_signals, validate_input) are optional
#   and provide default implementations

# Create a single logger for module-level logging
indicator_logger = Logger(__name__)
indicator_logger.debug(f"Initializing BaseIndicator module at {__file__}")
indicator_logger.debug(f"Module attributes pre-class: {dir()}")

# Define DebugLevel first
indicator_logger.debug("1. Defining DebugLevel enum")
class DebugLevel(Enum):
    MINIMAL = 0
    BASIC = 1 
    DETAILED = 2
    FULL = 3
    
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

# Then define decorator
indicator_logger.debug("2. Defining debug decorator")
def debug_method(level: DebugLevel = DebugLevel.BASIC):
    """Decorator to add debug logging to indicator methods."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            debug = DebugMetrics(start_time=time.time())
            
            try:
                # Run method
                result = await func(self, *args, **kwargs)
                
                # Update debug metrics
                debug.computation_time = time.time() - debug.start_time
                
                # Log debug info
                self._log_debug_info(func.__name__, debug, level, result)
                
                return result
                
            except Exception as e:
                # Log error debug info
                self._log_error_debug(func.__name__, debug, e)
                raise
                
        return wrapper
    return decorator

# First define all type definitions
indicator_logger.debug("3. Defining type structures")
class IndicatorResult(TypedDict):
    """Type definition for indicator results."""
    score: float
    components: Dict[str, float]
    signals: Dict[str, Any]
    metadata: Dict[str, Any]

# First define helper classes
indicator_logger.debug("4. Defining helper classes")
@dataclass
class DebugMetrics:
    """Store debug metrics for indicator analysis"""
    start_time: float
    computation_time: Optional[float] = None
    input_rows: int = 0
    input_validation: bool = False
    error_count: int = 0
    warnings: List[str] = None
    metrics: Dict[str, float] = None
    
    def __post_init__(self):
        self.warnings = []
        self.metrics = {}

class IndicatorMetrics:
    """Data class for indicator metrics."""
    def __init__(self, score: float = 50.0, signals: Dict[str, Any] = None, 
                 confidence: float = 0.0, timestamp: int = None, 
                 metadata: Dict[str, Any] = None):
        self.score = score
        self.signals = signals or {}
        self.metadata = metadata or {}
        self.warnings = []
        self.errors = []
        self.computation_time = 0.0
        self.timestamp = timestamp or int(time.time() * 1000)
        self.confidence = confidence
        
    # ... rest of IndicatorMetrics methods ...

indicator_logger.debug("5. Starting BaseIndicator definition")
class BaseIndicator(ABC):
    """Base class for all trading indicators."""
    
    _REQUIRED_DATA = {
        'technical': ['ohlcv', 'timeframes'],
        'volume': ['ohlcv', 'trades'],
        'orderbook': ['orderbook'],
        'orderflow': ['trades', 'orderbook'],
        'sentiment': ['sentiment'],
        'price_structure': ['ohlcv', 'timeframes']
    }
    
    # Move this to class level (lines 162-165)
    VALID_INDICATOR_TYPES = {
        'technical', 'volume', 'orderbook', 'orderflow',
        'sentiment', 'price_structure'
    }
    
    def __init__(self, config: Dict[str, Any], logger: Optional[Logger] = None):
        """Base class constructor"""
        self.config = config or {}
        self.logger = logger or Logger(__name__)
        
        # Timeframe config from root level
        self.TIMEFRAME_CONFIG = {}
        for tf_name, tf_config in config['timeframes'].items():
            self.TIMEFRAME_CONFIG[tf_name] = {
                'friendly_name': f"{tf_config['interval']} minute",
                'interval': str(tf_config['interval']),
                'min_candles': tf_config['validation']['min_candles']
            }

        # Data validation configuration
        self.DATA_REQUIREMENTS = {
            'ohlcv': {
                'required_columns': ['open', 'high', 'low', 'close', 'volume'],
                'timeframes': self.TIMEFRAME_CONFIG
            },
            'trades': {
                'required_fields': ['price', 'size', 'side', 'time'],
                'min_trades': config.get('validation_requirements', {}).get('trades', {}).get('min_trades', 50),
                'max_age': config.get('validation_requirements', {}).get('trades', {}).get('max_age', 3600)
            },
            'orderbook': {
                'required_fields': ['bids', 'asks', 'timestamp'],
                'min_levels': config.get('validation_requirements', {}).get('orderbook', {}).get('min_levels', 10)
            }
        }

        # Required columns for OHLCV data
        self.REQUIRED_COLUMNS = ['open', 'high', 'low', 'close', 'volume']
        
        # Required timeframes for validation
        self.required_timeframes = list(self.TIMEFRAME_CONFIG.keys())

        # Reverse mapping for validation
        self.interval_to_name = {
            tf_config['interval']: tf_name 
            for tf_name, tf_config in self.TIMEFRAME_CONFIG.items()
        }

        # Standard timeframe weights
        self.timeframe_weights = {
            tf_name: self.config['timeframes'][tf_name]['weight']
            for tf_name in ['base', 'ltf', 'mtf', 'htf'] 
            if tf_name in self.config['timeframes']
        }

        self.validation_requirements = {
            'ohlcv': {
                'required': True,
                'timeframes': {
                    tf_name: {'min_candles': tf_config['min_candles']} 
                    for tf_name, tf_config in self.TIMEFRAME_CONFIG.items()
                },
                'columns': ['open', 'high', 'low', 'close', 'volume']
            },
            'trades': {
                'required': True,
                'fields': ['price', 'size', 'side', 'time'],
                'min_trades': config.get('validation_requirements', {}).get('trades', {}).get('min_trades', 50),
                'max_age': config.get('validation_requirements', {}).get('trades', {}).get('max_age', 3600)
            }
        }

        try:
            # Log initialization details
            self.logger.debug(f"\n=== Initializing {self.__class__.__name__} ===")
            self.logger.debug(f"1. Indicator type: {getattr(self, 'indicator_type', 'Not set')}")
            self.logger.debug(f"2. Required data: {self._REQUIRED_DATA.get(getattr(self, 'indicator_type', ''), [])}")
            
            # Validate indicator type
            if not hasattr(self, 'indicator_type'):
                self.logger.error("indicator_type not set")
                raise ValueError("Child class must set indicator_type before calling super().__init__")
            
            if self.indicator_type not in self.VALID_INDICATOR_TYPES:
                self.logger.error(f"Invalid indicator type: {self.indicator_type}")
                self.logger.error(f"Valid types: {self.VALID_INDICATOR_TYPES}")
                raise ValueError(f"Invalid indicator type: {self.indicator_type}")
            
            # Add debug logging
            self.logger.debug("\n=== BaseIndicator Initialization ===")
            self.logger.debug(f"Class attributes: {dir(self.__class__)}")
            self.logger.debug(f"Config keys: {list(config.keys())}")
            self.logger.debug(f"Config analysis section: {config.get('analysis', {})}")
            
            # Check if indicator types are in config
            indicator_types = config.get('analysis', {}).get('indicator_types', [])
            self.logger.debug(f"Configured indicator types: {indicator_types}")
            
            # Log inheritance chain
            mro = self.__class__.__mro__
            self.logger.debug(f"Class inheritance chain: {[cls.__name__ for cls in mro]}")
            
            # Validate component weights are set by child class
            if not hasattr(self, 'component_weights'):
                raise ValueError("Child class must set component_weights before calling super().__init__")
            
            # Initialize from config
            self._initialize_from_config(config)
            
            # Validate weights
            self._validate_weights()

            # Initialize debug metrics
            self.debug_metrics = DebugMetrics(start_time=time.time())

            self.required_data_keys = ['ticker', 'timeframe', 'ohlcv']
            self.required_sentiment_components = ['funding_rate', 'long_short_ratio', 'liquidations']

            # Add initialization logging
            self.logger.debug("\n=== Indicator Initialization ===")
            self.logger.debug(f"Indicator class: {self.__class__.__name__}")
            self.logger.debug(f"Config: {config}")
            
            # Log validation requirements
            self.logger.debug("\nValidation Requirements:")
            if hasattr(self, 'validation_requirements'):
                self.logger.debug(f"- Requirements: {self.validation_requirements}")
            else:
                self.logger.warning("No validation_requirements defined")
            
            if hasattr(self, 'required_data_keys'):
                self.logger.debug(f"- Required keys: {self.required_data_keys}")
            else:
                self.logger.warning("No required_data_keys defined")

            # Add validation requirements
            self.validation_requirements = {
                'ohlcv': ['open', 'high', 'low', 'close', 'volume'],
                'orderbook': ['bids', 'asks'],
                'trades': ['id', 'price', 'size', 'side', 'time'],
                'ticker': ['last', 'volume']
            }

        except Exception as e:
            self.logger.error(f"Error initializing: {str(e)}")
            raise

    def _initialize_from_config(self, config: Dict[str, Any]) -> None:
        """Initialize indicator settings from config."""
        try:
            # Get indicator-specific config
            indicator_config = config.get('analysis', {}).get('indicators', {}).get(self.indicator_type, {})
            
            # Update weights if provided in config
            if 'weights' in indicator_config:
                self.component_weights.update(indicator_config['weights'])
                
            # Validate weights
            self._validate_weights()
            
        except Exception as e:
            self.logger.error(f"Error initializing from config: {str(e)}")
            raise

    @abstractmethod
    async def calculate(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Standard entry point for all indicator calculations.
        
        This method should:
        1. Validate input data
        2. Calculate component scores
        3. Calculate the overall indicator score
        4. Generate signals
        5. Return a standardized dictionary with score, components, signals, and metadata
        
        Returns:
            Dict with keys: 'score', 'components', 'signals', 'metadata'
        """
        pass
        
    async def calculate_score(self, market_data: Dict[str, Any]) -> float:
        """Calculate main indicator score.
        
        This is a helper method that can be used by the calculate() method.
        Child classes may override this method to implement specific scoring logic.
        """
        return 50.0  # Default neutral score
        
    async def get_signals(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get indicator-specific signals.
        
        This is a helper method that can be used by the calculate() method.
        Child classes may override this method to implement specific signal generation logic.
        """
        return {}  # Default empty signals
        
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input data.
        
        This is a helper method that can be used by the calculate() method.
        Child classes may override this method to implement specific validation logic.
        """
        return True  # Default validation passes

    def _calculate_confidence(self, market_data: Dict[str, Any]) -> float:
        """Calculate confidence score between 0-1."""
        return 1.0  # Default implementation - can be overridden
        
    def _get_metadata(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get additional indicator metadata."""
        return {}  # Default implementation - can be overridden
        
    def _validate_weights(self) -> None:
        """Validate and normalize component weights to sum to 1.0"""
        try:
            if not self.component_weights:
                return
                
            comp_total = sum(self.component_weights.values())
            if not np.isclose(comp_total, 1.0, rtol=1e-5):
                self.logger.warning(f"Component weights sum to {comp_total}, normalizing")
                self.component_weights = {k: v/comp_total for k, v in self.component_weights.items()}
                
            self.logger.debug("Weights validated and normalized")
            
        except Exception as e:
            self.logger.error(f"Error validating weights: {str(e)}")
            raise

    def _get_default_metrics(self) -> IndicatorMetrics:
        """Return default metrics for error cases."""
        self.logger.debug(f"Component weights before normalization: {self.component_weights}")
        self.logger.debug(f"IndicatorMetrics expected parameters: {inspect.signature(IndicatorMetrics.__init__)}")
        
        default_params = {
            'score': 50.0,
            'signals': {},
            'confidence': 0.0,
            'timestamp': int(time.time() * 1000),
            'metadata': {'error': True}
        }
        self.logger.debug(f"Attempting to create metrics with params: {default_params}")
        
        return IndicatorMetrics(
            score=50.0,
            signals={},
            confidence=0.0,
            timestamp=int(time.time() * 1000),
            metadata={'error': True}
        )
            
    def _log_debug_info(self, method_name: str, debug: DebugMetrics, 
                       level: DebugLevel, result: Any) -> None:
        """Log debug information based on debug level"""
        
        # Basic logging for all levels
        self.logger.debug(f"\n=== {method_name} Debug Info ===")
        self.logger.debug(f"Execution time: {debug.computation_time:.4f}s")
        self.logger.debug(f"Input rows: {debug.input_rows}")
        
        if debug.warnings:
            self.logger.warning("Warnings:")
            for warning in debug.warnings:
                self.logger.warning(f"- {warning}")
        
        # Additional logging based on level
        if level >= DebugLevel.BASIC:
            self.logger.debug("\nValidation Results:")
            self.logger.debug(f"- Input validation: {'✓' if debug.input_validation else '✗'}")
            self.logger.debug(f"- Error count: {debug.error_count}")
        
        if level >= DebugLevel.DETAILED:
            self.logger.debug("\nMetrics:")
            for metric, value in debug.metrics.items():
                self.logger.debug(f"- {metric}: {value}")
        
        if level >= DebugLevel.FULL:
            self.logger.debug("\nFull Result:")
            self.logger.debug(f"{result}")

    def _log_error_debug(self, method_name: str, debug: DebugMetrics, error: Exception) -> None:
        """Log error debug information"""
        self.logger.error(f"\n=== {method_name} Error Debug ===")
        self.logger.error(f"Error type: {type(error).__name__}")
        self.logger.error(f"Error message: {str(error)}")
        self.logger.error(f"Execution time until error: {time.time() - debug.start_time:.4f}s")
        self.logger.error(f"Input rows processed: {debug.input_rows}")
        if debug.warnings:
            self.logger.error("Warnings before error:")
            for warning in debug.warnings:
                self.logger.error(f"- {warning}") 

    def _validate_timeframes(self, data: Dict[str, Any]) -> bool:
        """Validate timeframe data structure."""
        try:
            if not isinstance(data, dict):
                self.logger.error(f"Invalid data type: {type(data)}")
                return False
            
            # Check OHLCV data exists
            if 'ohlcv' not in data:
                self.logger.error("Missing OHLCV data")
                return False
            
            ohlcv_data = data['ohlcv']
            self.logger.debug(f"OHLCV keys: {list(ohlcv_data.keys())}")
            
            # Convert interval-based keys to timeframe names
            normalized_ohlcv = {}
            for key in ohlcv_data.keys():
                # Handle both '1m' and '1' style keys
                clean_key = key.rstrip('m').rstrip('min')
                
                # Try to map to timeframe name
                if clean_key in self.interval_to_name:
                    tf_name = self.interval_to_name[clean_key]
                    normalized_ohlcv[tf_name] = ohlcv_data[key]
                elif key in self.TIMEFRAME_CONFIG:
                    # Key is already a timeframe name
                    normalized_ohlcv[key] = ohlcv_data[key]
                else:
                    self.logger.error(f"Unrecognized timeframe key: {key}")
                    self.logger.error(f"Expected one of: {list(self.interval_to_name.keys())} or {list(self.TIMEFRAME_CONFIG.keys())}")
                    return False

            # Validate each required timeframe
            for tf_name, tf_config in self.TIMEFRAME_CONFIG.items():
                # Check timeframe exists
                if tf_name not in normalized_ohlcv:
                    self.logger.error(f"Missing {tf_name} timeframe ({tf_config['friendly_name']})")
                    return False
                
                df = normalized_ohlcv[tf_name]
                
                # Validate DataFrame
                if not isinstance(df, pd.DataFrame):
                    self.logger.error(f"Invalid {tf_name} data type: {type(df)}")
                    return False
                
                if df.empty:
                    self.logger.error(f"Empty DataFrame for {tf_name}")
                    return False
                
                # Validate columns
                missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
                if missing_cols:
                    self.logger.error(f"Missing columns in {tf_name}: {missing_cols}")
                    return False
                
                # Check minimum candles
                if len(df) < tf_config['min_candles']:
                    self.logger.error(f"Insufficient candles in {tf_name}: {len(df)} < {tf_config['min_candles']}")
                    return False
                
                self.logger.debug(f"Validated {tf_name} ({tf_config['friendly_name']}): {df.shape[0]} candles")
            
            self.logger.debug("All timeframes validated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in timeframe validation: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return False

    def _validate_components(self, scores: Dict[str, float]) -> bool:
        """Validate component scores against weights."""
        try:
            # Check all required components are present
            missing = set(self.component_weights.keys()) - set(scores.keys())
            if missing:
                self.logger.error(f"Missing components: {missing}")
                return False
                
            # Validate score ranges
            invalid = [k for k, v in scores.items() if not 0 <= v <= 100]
            if invalid:
                self.logger.error(f"Invalid scores for components: {invalid}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating components: {str(e)}")
            return False 

    def _get_timeframe_data(self, data: Dict[str, Any], timeframe: str) -> Optional[pd.DataFrame]:
        """Get data for specific timeframe with validation."""
        try:
            if 'ohlcv' not in data:
                self.logger.error("Missing OHLCV data")
                return None

            # Get data using timeframe name directly
            df = data['ohlcv'].get(timeframe)
            if not isinstance(df, pd.DataFrame) or df.empty:
                self.logger.error(f"Invalid DataFrame for {timeframe}")
                return None

            required_columns = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_columns):
                self.logger.error(f"Missing required columns in {timeframe}")
                return None

            return df

        except Exception as e:
            self.logger.error(f"Error getting timeframe data: {str(e)}")
            return None

    def _analyze_timeframe_divergence(self, timeframe_scores: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Analyze divergences between timeframes."""
        try:
            divergences = {}
            base_scores = timeframe_scores.get('base', {})
            
            for tf in ['ltf', 'mtf', 'htf']:
                tf_scores = timeframe_scores.get(tf, {})
                if not tf_scores:
                    continue
                    
                # Compare each component across timeframes
                for component in self.component_weights:
                    base_score = base_scores.get(component, 50.0)
                    tf_score = tf_scores.get(component, 50.0)
                    
                    # Calculate divergence
                    divergence = tf_score - base_score
                    if abs(divergence) > 20:  # Significant divergence
                        divergences[f"{tf}_{component}"] = {
                            'type': 'bullish' if divergence > 0 else 'bearish',
                            'strength': abs(divergence),
                            'timeframe': tf,
                            'component': component
                        }
                        
            return divergences
            
        except Exception as e:
            self.logger.error(f"Error analyzing timeframe divergence: {str(e)}")
            return {} 

    def _validate_field_data(self, field: str, data: Any) -> bool:
        """Validate specific data field."""
        try:
            requirements = self.validation_requirements.get(self.indicator_type, {})
            field_reqs = requirements.get(field)
            
            if not field_reqs:
                return True
                
            if isinstance(field_reqs, list):  # Required columns
                if isinstance(data, pd.DataFrame):
                    return all(col in data.columns for col in field_reqs)
                elif isinstance(data, dict):
                    return all(col in data for col in field_reqs)
                return False
                
            if isinstance(field_reqs, int):  # Minimum points
                if isinstance(data, pd.DataFrame):
                    return data.shape[0] >= field_reqs
                return len(data) >= field_reqs
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating {field}: {str(e)}")
            return False 

    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Single entry point for all data validation."""
        try:
            self.logger.debug("\n=== Validating Input Data ===")
            
            # Basic type check
            if not isinstance(data, dict):
                self.logger.error(f"Invalid input type: {type(data)}")
                return False

            # Validate OHLCV data
            if 'ohlcv' in self.required_data:
                if not self._validate_ohlcv_data(data.get('ohlcv', {})):
                    return False

            # Validate trade data
            if 'trades' in self.required_data:
                if not self._validate_trade_data(data.get('trades', [])):
                    return False

            # Validate orderbook data
            if 'orderbook' in self.required_data:
                if not self._validate_orderbook_data(data.get('orderbook', {})):
                    return False

            self.logger.debug("All validations passed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error in input validation: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return False

    def _validate_ohlcv_data(self, data: Dict[str, pd.DataFrame]) -> bool:
        """Validate OHLCV data structure."""
        try:
            self.logger.debug("\n=== Validating OHLCV Data ===")
            self.logger.debug(f"Available timeframes: {list(data.keys())}")

            # Validate each required timeframe
            for tf_name, tf_config in self.TIMEFRAME_CONFIG.items():
                if tf_name not in data:
                    self.logger.error(f"Missing timeframe: {tf_name} ({tf_config['friendly_name']})")
                    return False

                df = data[tf_name]
                if not isinstance(df, pd.DataFrame) or df.empty:
                    self.logger.error(f"Invalid or empty DataFrame for {tf_name}")
                    return False

                # Validate columns
                missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
                if missing_cols:
                    self.logger.error(f"Missing columns in {tf_name}: {missing_cols}")
                    return False

                # Validate minimum candles
                if len(df) < tf_config['min_candles']:
                    self.logger.error(f"Insufficient candles in {tf_name}: {len(df)} < {tf_config['min_candles']}")
                    return False

                self.logger.debug(f"Validated {tf_name} ({tf_config['friendly_name']}): {df.shape[0]} candles")

            self.logger.debug("All timeframes validated successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error validating OHLCV data: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return False

    def calculate_depth(self, orderbook):
        if not isinstance(orderbook, dict):
            raise ValueError("Orderbook must be a dictionary")
            
        try:
            # Convert string values to float before creating numpy arrays
            bids = np.array([[float(price), float(size)] for price, size in orderbook.get('bids', [])])
            asks = np.array([[float(price), float(size)] for price, size in orderbook.get('asks', [])])
            
            # Calculate depth using numpy arrays directly
            bid_depth = np.sum(bids[:, 1]) if len(bids) > 0 else 0
            ask_depth = np.sum(asks[:, 1]) if len(asks) > 0 else 0
            
            return bid_depth, ask_depth
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error calculating depth: {str(e)}")
            return 0, 0

    def get_sentiment_metrics(self, data):
        required_components = ['long_short_ratio', 'liquidations']
        available_components = data.get('sentiment', {})
        
        # Check for missing components
        missing = [comp for comp in required_components if comp not in available_components]
        if missing:
            self.logger.warning(f"Missing sentiment components: {missing}")
            # Return default values instead of failing
            return {
                'long_short_ratio': 1.0,  # Neutral default
                'liquidations': []  # Empty list default
            }
        
        return available_components 

    def validate_input_data(self, data: Dict[str, Any]) -> bool:
        try:
            self.logger.debug("Starting input data validation...")
            
            # Log top-level keys provided by the data payload.
            overall_keys = list(data.keys())
            self.logger.debug(f"Top-level keys in data: {overall_keys}")
            
            # Log the expected timeframes for reference.
            self.logger.debug(f"Expected timeframes: {self.required_timeframes}")
            
            if 'ohlcv' not in data:
                self.logger.error("Missing OHLCV data")
                return False
            available_timeframes = list(data['ohlcv'].keys())
            self.logger.debug(f"Available OHLCV keys: {available_timeframes}")
            
            # Validate each required timeframe's data
            for tf in self.required_timeframes:
                if tf not in data['ohlcv']:
                    self.logger.error(f"Missing expected timeframe: {tf}")
                    self.logger.error(f"Full available timeframes: {available_timeframes}")
                    return False
                df = data['ohlcv'][tf]
                self.logger.debug(
                    f"Timeframe '{tf}': DataFrame type: {type(df)}, empty: {df.empty if hasattr(df, 'empty') else 'N/A'}"
                )
                if not isinstance(df, pd.DataFrame):
                    self.logger.error(f"Data for '{tf}' is not a DataFrame. Got type: {type(df)}")
                    return False

                # Log columns details to detect duplicate columns or multi-index issues.
                self.logger.debug(f"Timeframe '{tf}': DataFrame columns: {list(df.columns)}")
                
                # Validate volume column explicitly 
                try:
                    volume_data = df['volume']
                    self.logger.debug(f"Timeframe '{tf}': Volume column type: {type(volume_data)}")
                    if isinstance(volume_data, pd.DataFrame):
                        self.logger.debug(f"Timeframe '{tf}': Volume data columns: {list(volume_data.columns)}; shape: {volume_data.shape}")
                    preview = volume_data.head().to_dict() if hasattr(volume_data, 'head') else str(volume_data)
                    self.logger.debug(f"Timeframe '{tf}': Volume data preview: {preview}")
                    if getattr(volume_data, 'empty', True):
                        self.logger.error(f"Volume data is empty for timeframe: {tf}")
                        return False
                except Exception as ex:
                    self.logger.error(f"Exception while accessing volume data for timeframe '{tf}': {str(ex)}")
                    return False
            
            # Validate Ticker data
            if 'ticker' not in data:
                self.logger.error(f"Ticker missing. Top-level keys: {overall_keys}")
                return False
            else:
                ticker_data = data['ticker']
                self.logger.debug(f"Ticker data: {ticker_data}, type: {type(ticker_data)}")
                if not isinstance(ticker_data, dict):
                    self.logger.error("Ticker data is not a dict as expected")
                    return False
            
            # Validate Orderbook structure
            if 'orderbook' not in data:
                self.logger.error("Orderbook missing in data")
                return False
            else:
                orderbook = data['orderbook']
                self.logger.debug(f"Orderbook data type: {type(orderbook)}; contents: {orderbook}")
                if not isinstance(orderbook, dict):
                    self.logger.error("Orderbook data is not a dict as expected")
                    return False
            
            # Validate Sentiment data
            if 'sentiment' not in data:
                self.logger.error("Sentiment data is missing")
                return False
            else:
                sentiment = data['sentiment']
                self.logger.debug(f"Sentiment data: {sentiment}, type: {type(sentiment)}")
                if not isinstance(sentiment, dict):
                    self.logger.error("Sentiment data is not a dict as expected")
                    return False
                required_sentiments = self.required_sentiment_components if hasattr(self, 'required_sentiment_components') else ['funding_rate', 'long_short_ratio', 'liquidations']
                missing_sentiments = [comp for comp in required_sentiments if comp not in sentiment]
                if missing_sentiments:
                    self.logger.error(f"Missing required sentiment components: {missing_sentiments}")
                    return False
            
            self.logger.debug("Input data validation passed successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Exception during input data validation: {str(e)}")
            return False

    def _validate_base_requirements(self, data: Dict[str, Any]) -> bool:
        """Standard validation all indicators should use."""
        try:
            self.logger.debug(f"\n=== Validating {self.indicator_type} Data ===")
            
            # Check data type
            if not isinstance(data, dict):
                self.logger.error("Input data must be a dictionary")
                return False
            
            # Check required fields
            missing_fields = [f for f in self.required_data if f not in data]
            if missing_fields:
                self.logger.error(f"Missing required fields: {missing_fields}")
                return False
            
            # Validate each required field
            for field in self.required_data:
                if not self._validate_field_data(field, data[field]):
                    return False
                
            return True
            
        except Exception as e:
            self.handle_error(e, "base validation")
            return False

    @property
    def required_data(self):
        """Get required data for this indicator type."""
        return self._REQUIRED_DATA.get(self.indicator_type, [])

    def _normalize_value(self, value: float, min_val: float, max_val: float, scale: float = 100.0) -> float:
        """Normalize a value to a given scale (default 0-100)."""
        try:
            if max_val == min_val:
                return scale/2  # Return middle value
            normalized = (value - min_val) / (max_val - min_val)
            return float(np.clip(normalized * scale, 0, scale))
        except Exception as e:
            self.logger.error(f"Error normalizing value: {str(e)}")
            return scale/2

    def _compute_weighted_score(self, scores: Dict[str, float]) -> float:
        """Calculate weighted score from components."""
        try:
            if not scores:
                return 50.0
                
            weighted_sum = sum(
                scores[component] * self.component_weights.get(component, 0)
                for component in scores
                if component in self.component_weights
            )
            weight_sum = sum(
                self.component_weights.get(component, 0)
                for component in scores
                if component in self.component_weights
            )
            
            if weight_sum == 0:
                return 50.0
                
            return float(np.clip(weighted_sum / weight_sum, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error computing weighted score: {str(e)}")
            return 50.0

    def get_default_result(self) -> IndicatorResult:
        """Standard default result format."""
        return {
            'score': 50.0,
            'components': {k: 50.0 for k in self.component_weights.keys()},
            'signals': {},
            'metadata': {
                'timestamp': int(time.time() * 1000),
                'status': 'ERROR',
                'error': 'Default result returned'
            }
        }
        
    def create_result(self, score: float, components: Dict[str, float], 
                     signals: Dict[str, Any] = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a standardized result dictionary.
        
        Args:
            score: Overall indicator score (0-100)
            components: Dictionary of component scores
            signals: Dictionary of trading signals (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            Standardized result dictionary
        """
        result = {
            'score': float(np.clip(score, 0, 100)),
            'components': components,
            'signals': signals or {},
            'metadata': metadata or {}
        }
        
        # Ensure timestamp is included in metadata
        if 'timestamp' not in result['metadata']:
            result['metadata']['timestamp'] = int(time.time() * 1000)
            
        return result

    def handle_error(self, e: Exception, context: str) -> None:
        """Standardized error handling."""
        error_msg = f"Error in {self.indicator_type} {context}: {str(e)}"
        self.logger.error(error_msg)
        self.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Update debug metrics
        if hasattr(self, 'debug_metrics'):
            self.debug_metrics.error_count += 1
            if hasattr(self.debug_metrics, 'warnings'):
                self.debug_metrics.warnings.append(error_msg)

    def get_signal_template(self) -> Dict[str, Any]:
        """Standard signal format all indicators should use."""
        return {
            'trend': {
                'signal': 'neutral',
                'strength': 0,
                'timeframe': 'current'
            },
            'levels': {
                'support': [],
                'resistance': []
            },
            'alerts': [],
            'metadata': {
                'timestamp': int(time.time() * 1000),
                'confidence': 0.0
            }
        }

    def _validate_trade_data(self, trades: List[Dict[str, Any]]) -> bool:
        """Validate trade data structure"""
        try:
            return self.validation_service.validate(trades, ValidationContext(data_type="trades"))
            
        except Exception as e:
            self.logger.error(f"Error validating trade data: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return False

    def _validate_orderbook_data(self, orderbook: Dict[str, Any]) -> bool:
        """Validate orderbook data structure."""
        try:
            return self.validation_service.validate(orderbook, ValidationContext(data_type="orderbook"))
            
        except Exception as e:
            self.logger.error(f"Error validating orderbook: {str(e)}")
            return False

    def log_indicator_results(self, final_score: float, component_scores: Dict[str, float], symbol: str = "") -> None:
        """
        Log indicator results with consistent formatting.
        
        This method ensures all indicators use the same formatting for their
        final scores and component breakdowns.
        
        Args:
            final_score: Final calculated score
            component_scores: Dictionary of component scores
            symbol: Optional symbol to include in the title
        """
        from src.core.analysis.indicator_utils import log_indicator_results
        
        # Use the helper function from indicator_utils
        log_indicator_results(
            self.logger, 
            self.__class__.__name__.replace('Indicators', ''), 
            final_score, 
            component_scores, 
            self.component_weights, 
            symbol
        )
        
    def log_multi_timeframe_analysis(self, 
                                    timeframe_scores: Dict[str, Dict[str, float]], 
                                    divergences: Dict[str, Any] = None,
                                    symbol: str = "") -> None:
        """
        Log multi-timeframe analysis and divergence information.
        
        This method provides detailed logging of scores across different timeframes
        and any divergence bonuses that were applied.
        
        Args:
            timeframe_scores: Dictionary mapping timeframes to component scores
            divergences: Optional dictionary of divergence information
            symbol: Optional symbol to include in the title
        """
        if not timeframe_scores:
            self.logger.debug("No multi-timeframe data available for logging")
            return
            
        indicator_name = self.__class__.__name__.replace('Indicators', '')
        
        # Log header
        self.logger.info(f"\n=== {symbol} {indicator_name} Multi-Timeframe Analysis ===")
        
        # Log timeframe scores
        for tf, scores in timeframe_scores.items():
            if not scores:
                continue
                
            # Get friendly timeframe name
            tf_friendly = self.TIMEFRAME_CONFIG.get(tf, {}).get('friendly_name', tf.upper())
            
            # Log timeframe header
            self.logger.info(f"\n{tf_friendly} Timeframe:")
            
            # Log component scores for this timeframe
            for component, score in scores.items():
                weight = self.component_weights.get(component, 0)
                contribution = score * weight
                self.logger.info(f"- {component}: {score:.2f} × {weight:.2f} = {contribution:.2f}")
                
            # Calculate and log weighted score for this timeframe
            tf_weight = self.timeframe_weights.get(tf, 0)
            tf_score = self._compute_weighted_score(scores)
            self.logger.info(f"Timeframe Score: {tf_score:.2f} (Weight: {tf_weight:.2f})")
        
        # Log divergence information if available
        if divergences:
            self.logger.info("\n=== Divergence Analysis ===")
            
            for key, div_info in divergences.items():
                div_type = div_info.get('type', 'unknown')
                strength = div_info.get('strength', 0)
                tf = div_info.get('timeframe', '')
                component = div_info.get('component', '')
                
                # Get friendly timeframe name
                tf_friendly = self.TIMEFRAME_CONFIG.get(tf, {}).get('friendly_name', tf.upper())
                
                # Format divergence type with color
                if div_type == 'bullish':
                    type_str = "BULLISH"
                elif div_type == 'bearish':
                    type_str = "BEARISH"
                else:
                    type_str = div_type.upper()
                
                self.logger.info(f"- {tf_friendly} {component}: {type_str} divergence (Strength: {strength:.2f})")
                
                # Log any bonus applied
                if 'bonus' in div_info:
                    bonus = div_info['bonus']
                    self.logger.info(f"  Applied bonus: {bonus:.2f}")

class ValidationError(Exception):
    pass

class AnalysisError(Exception):
    pass 

# Move logging AFTER the single class definition
indicator_logger.debug("\n=== BaseIndicator Module Configuration ===")
indicator_logger.debug(f"1. Required Data Configuration:")
indicator_logger.debug(f"   _REQUIRED_DATA keys: {BaseIndicator._REQUIRED_DATA.keys()}")
indicator_logger.debug(f"   VALID_INDICATOR_TYPES: {BaseIndicator.VALID_INDICATOR_TYPES}")
indicator_logger.debug(f"2. Checking for mismatches:")
indicator_logger.debug(f"   Types in VALID_INDICATOR_TYPES but not in _REQUIRED_DATA: {BaseIndicator.VALID_INDICATOR_TYPES - set(BaseIndicator._REQUIRED_DATA.keys())}")
indicator_logger.debug(f"   Types in _REQUIRED_DATA but not in VALID_INDICATOR_TYPES: {set(BaseIndicator._REQUIRED_DATA.keys()) - BaseIndicator.VALID_INDICATOR_TYPES}") 

indicator_logger.debug("5. Module initialization complete")
indicator_logger.debug(f"Final available names: {dir()}") 