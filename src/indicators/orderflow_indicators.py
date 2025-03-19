# src/indicators/orderflow_indicators.py

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Tuple, List, Union, Optional
from src.utils.error_handling import handle_indicator_error
import time
import traceback
from src.core.analysis.confluence import DataValidator
from .base_indicator import BaseIndicator
from ..core.logger import Logger
from scipy import stats
import json

# Get module logger
logger = logging.getLogger('OrderflowIndicators')

class DataUnavailableError(Exception):
    pass

class OrderflowIndicators(BaseIndicator):
    """Orderflow-based trading indicators."""

    def __init__(self, config: Dict[str, Any], logger: Optional[Logger] = None):
        """Initialize OrderflowIndicators."""
        # Set required attributes before calling super().__init__
        self.indicator_type = 'orderflow'
        
        # Initialize component weights with defaults - use the same keys as component scores
        self.component_weights = {
            'cvd': 0.25,                  # Cumulative Volume Delta (buy vs sell volume)
            'trade_flow_score': 0.25,     # Buy vs sell trade flow
            'imbalance_score': 0.15,      # Orderbook imbalance
            'open_interest_score': 0.1,   # Open interest analysis
            'pressure_score': 0.05,       # Market pressure
            'liquidity_score': 0.2        # NEW: Liquidity score based on trade frequency and volume
        }
        
        # Cache for computed values to avoid redundant calculations
        self._cache = {}
        
        # Apply any custom weights from config
        if 'weights' in config:
            for component, weight in config['weights'].items():
                if component in self.component_weights:
                    self.component_weights[component] = float(weight)
        
        # Try to load weights from the confluence configuration
        # This takes precedence over the direct 'weights' in config
        confluence_weights = config.get('confluence', {}).get('weights', {}).get('sub_components', {}).get('orderflow', {})
        if confluence_weights:
            # Map config weight names to component weight keys
            weight_mapping = {
                'cvd': 'cvd',
                'trade_flow': 'trade_flow_score',
                'imbalance': 'imbalance_score',
                'open_interest': 'open_interest_score',
                'pressure': 'pressure_score',
                'liquidity': 'liquidity_score'
            }
            
            # Apply weights from confluence config
            for config_key, component_key in weight_mapping.items():
                if config_key in confluence_weights:
                    self.component_weights[component_key] = float(confluence_weights[config_key])
        
        # Validate and normalize weights
        self._validate_weights()
        
        # Configure lookback periods
        self.divergence_lookback = config.get('divergence_lookback', 20)
        self.min_trades = config.get('min_trades', 100)
        self.cvd_normalization = config.get('cvd_normalization', 'total_volume')
        
        # Configure debug levels
        self.debug_level = config.get('debug_level', 1)
        
        # Configure timeframe weights for multi-timeframe analysis
        self.timeframe_weights = {
            'base': 0.4,  # Base timeframe (usually 1 minute)
            'ltf': 0.3,   # Lower timeframe (usually 5 minutes)
            'mtf': 0.2,   # Medium timeframe (usually 30 minutes)
            'htf': 0.1    # Higher timeframe (usually 4 hours)
        }
        
        # Apply any custom timeframe weights from config
        if 'timeframe_weights' in config:
            for tf, weight in config['timeframe_weights'].items():
                if tf in self.timeframe_weights:
                    self.timeframe_weights[tf] = float(weight)
                    
        # Configure interpretation thresholds
        self.thresholds = {
            'strong_buy': 70,
            'buy': 60,
            'neutral_high': 55,
            'neutral': 50,
            'neutral_low': 45,
            'sell': 40,
            'strong_sell': 30
        }
        
        # Apply any custom thresholds from config
        if 'thresholds' in config:
            for label, value in config['thresholds'].items():
                if label in self.thresholds:
                    self.thresholds[label] = float(value)
        
        # Call parent class constructor
        super().__init__(config, logger)
        
        # Log initialization (after super().__init__ so self.logger is available)
        self.logger.debug(f"Initialized OrderflowIndicators with weights: {self.component_weights}")
        self.logger.debug(f"Timeframe weights: {self.timeframe_weights}")
        self.logger.debug(f"Thresholds: {self.thresholds}")
        
        # Initialize parameters
        self.volume_threshold = config.get('volume_threshold', 1.5)
        self.flow_window = config.get('flow_window', 20)
        self.momentum_lookback = config.get('momentum_lookback', 10)
        
        # Initialize divergence parameters
        divergence_config = config.get('divergence', {})
        self.divergence_strength_threshold = divergence_config.get('strength_threshold', 20.0)
        self.divergence_impact = divergence_config.get('impact_multiplier', 0.2)
        self.time_weighting_enabled = divergence_config.get('time_weighting', True)
        self.recency_factor = divergence_config.get('recency_factor', 1.2)
        
        # Initialize tracking variables
        self.last_component_scores = {}
        self.trade_history = []
        
        # Validate weights
        self._validate_weights()

    @property
    def required_data(self) -> List[str]:
        """Required data fields for orderflow analysis."""
        return ['orderbook', 'trades', 'ohlcv']

    def calculate(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate all orderflow indicators based on market data.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            dict: Dictionary of calculated indicators
        """
        start_time = time.time()
        
        try:
            # Reset cache for new calculation
            self._cache = {}
            
            if not market_data:
                self.logger.error("No market data provided")
                return self.create_error_result("No market data provided")
            
            # Validate input data
            if not self.validate_input(market_data):
                return self.create_error_result("Invalid input data")
            
            # Calculate component scores
            cvd_value = self._calculate_cvd(market_data)
            imbalance_score = self._calculate_imbalance_score(market_data)
            trade_flow_score = self._calculate_trade_flow_score(market_data)
            open_interest_score = self._calculate_open_interest_score(market_data)
            liquidity_score = self._calculate_liquidity_score(market_data)
            
            # For pressure_score, use a default value of 50.0 since the method doesn't exist
            # In a real implementation, you would implement the _calculate_pressure_score method
            pressure_score = 50.0
            if 'orderbook' in market_data:
                # Try to use orderbook data to calculate a basic pressure score
                orderbook = market_data.get('orderbook', {})
                bids = orderbook.get('bids', [])
                asks = orderbook.get('asks', [])
                
                if bids and asks:
                    # Simple pressure calculation based on top of book
                    bid_vol = sum(float(bid[1]) for bid in bids[:5])
                    ask_vol = sum(float(ask[1]) for ask in asks[:5])
                    total_vol = bid_vol + ask_vol
                    
                    if total_vol > 0:
                        imbalance = (bid_vol - ask_vol) / total_vol
                        # Convert to 0-100 scale
                        pressure_score = 50 * (1 + imbalance)
                        # Ensure within bounds
                        pressure_score = max(0, min(100, pressure_score))
            
            # Cache component scores
            component_scores = {
                'cvd': cvd_value,
                'imbalance_score': imbalance_score,
                'trade_flow_score': trade_flow_score,
                'open_interest_score': open_interest_score,
                'pressure_score': pressure_score,
                'liquidity_score': liquidity_score
            }
            
            # Calculate weighted score correctly
            weighted_sum = 0.0
            total_weight = 0.0
            
            for component, score in component_scores.items():
                weight = self.component_weights.get(component, 0.0)
                weighted_sum += score * weight
                total_weight += weight
            
            # Calculate final weighted score - this should be used consistently
            final_score = weighted_sum / total_weight if total_weight > 0 else 50.0
            
            # Check if we have OHLCV data for multiple timeframes
            timeframe_scores = {}
            
            if 'ohlcv' in market_data and isinstance(market_data['ohlcv'], dict):
                ohlcv_data = market_data['ohlcv']
                
                # Log timeframe analysis header
                symbol_str = market_data.get('symbol', '')
                self.logger.info(f"\n=== {symbol_str} Orderflow Multi-Timeframe Analysis ===")
                
                # Process each timeframe
                for tf, tf_weight in self.timeframe_weights.items():
                    if tf in ohlcv_data and not ohlcv_data[tf].empty:
                        # Log timeframe header
                        tf_display = self._get_timeframe_display_name(tf)
                        self.logger.info(f"\n{tf_display} Timeframe:")
                        
                        # Use the same component scores for all timeframes for now
                        # In a more advanced implementation, you might calculate different scores per timeframe
                        for component, score in component_scores.items():
                            # Map component to weight key if needed
                            weight_key = component
                            weight = self.component_weights.get(weight_key, 0.0)
                            weighted_contribution = score * weight
                            self.logger.info(f"- {component}: {score:.2f} × {weight:.2f} = {weighted_contribution:.2f}")
                        
                        # Store scores for this timeframe using final_score for consistency
                        timeframe_scores[tf] = {
                            'scores': component_scores.copy(),
                            'weighted_score': final_score,
                            'weight': tf_weight
                        }
                        
                        # Use final_score consistently in the timeframe score log
                        self.logger.info(f"Timeframe Score: {final_score:.2f} (Weight: {tf_weight:.2f})")
            
            # Calculate divergences between timeframes if we have multiple timeframes
            divergences = {}
            if len(timeframe_scores) > 1:
                divergences = self._analyze_timeframe_divergence(timeframe_scores)
            
            # Calculate price-CVD and price-OI divergences
            price_cvd_divergence = self._calculate_price_cvd_divergence(market_data)
            price_oi_divergence = self._calculate_price_oi_divergence(market_data)
            
            # Get interpretation
            interpretation = self._get_orderflow_interpretation(
                final_score, 
                imbalance_score,
                cvd_value, 
                open_interest_score, 
                trade_flow_score,
                liquidity_score
            )
            
            # Log the results with the consistent final_score
            self.log_indicator_results(final_score, component_scores, market_data.get('symbol', ''))
            
            # Create signals with consistent final_score
            signals = {
                'score': final_score,
                'interpretation': interpretation,
                'divergences': {
                    'price_cvd': price_cvd_divergence,
                    'price_oi': price_oi_divergence,
                    'timeframe': divergences
                }
            }
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Format the final result with consistent final_score
            result = self.create_result(
                score=final_score,
                components=component_scores,
                signals=signals,
                metadata={
                    'timestamp': int(time.time() * 1000),
                    'execution_time': execution_time,
                    'status': 'SUCCESS'
                }
            )
            
            self.logger.info(f"Orderflow score: {final_score:.2f} (took {execution_time:.2f}s)")
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating orderflow indicators: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # Add execution time to error report
            execution_time = time.time() - start_time
            
            # Return default result with error info
            return {
                'score': 50.0,
                'components': {comp: 50.0 for comp in self.component_weights},
                'signals': {},
                'metadata': {
                    'timestamp': int(time.time() * 1000),
                    'execution_time': execution_time,
                    'status': 'ERROR',
                    'error': str(e)
                }
            }

    def _get_timeframe_display_name(self, timeframe: str) -> str:
        """Convert timeframe code to display name."""
        if timeframe == 'base':
            return '1 minute'
        elif timeframe == 'ltf':
            return '5 minute'
        elif timeframe == 'mtf':
            return '30 minute'
        elif timeframe == 'htf':
            return '240 minute'
        elif timeframe.isdigit():
            return f"{timeframe} minute"
        else:
            return timeframe

    def _compute_weighted_score(self, scores: Dict[str, float]) -> float:
        """Compute weighted score from component scores.
        
        Args:
            scores: Dictionary of component scores
            
        Returns:
            float: Weighted score
        """
        try:
            self.logger.debug("Computing weighted score with component mapping")
            self.logger.debug(f"Input scores: {scores}")
            self.logger.debug(f"Component weights: {self.component_weights}")
            
            # Define component mappings 
            component_mapping = {
                # Score key -> Weight key
                'cvd': 'cvd',
                'imbalance_score': 'imbalance',
                'trade_flow_score': 'trade_flow',
                'open_interest_score': 'open_interest',
                'pressure_score': 'pressure'
            }
            
            weighted_sum = 0
            total_weight = 0
            
            for score_key, score_value in scores.items():
                # Map the score key to the weight key if necessary
                weight_key = component_mapping.get(score_key, score_key)
                
                # Get the weight for this component if it exists
                if weight_key in self.component_weights:
                    weight = self.component_weights[weight_key]
                    
                    # Log the component contribution
                    self.logger.debug(f"Component: {score_key} -> {weight_key}, Score: {score_value:.2f}, Weight: {weight:.2f}")
                    
                    # Add to the weighted sum
                    weighted_sum += score_value * weight
                    total_weight += weight
            
            # Safety check for zero weight
            if total_weight <= 0:
                self.logger.warning(f"Total weight is 0 or negative: {total_weight}. Defaulting to 50.0")
                return 50.0
                
            # Calculate the final weighted score
            final_score = weighted_sum / total_weight
            self.logger.debug(f"Final weighted score: {final_score:.2f} (sum: {weighted_sum:.2f}, weight: {total_weight:.2f})")
            
            return final_score
            
        except Exception as e:
            self.logger.error(f"Error computing weighted score: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 50.0

    def log_indicator_results(self, final_score: float, component_scores: Dict[str, float], symbol: str = '') -> None:
        """Log indicator results."""
        if self.debug_level >= 1:
            symbol_prefix = f"[{symbol}] " if symbol else ""
            self.logger.info(f"{symbol_prefix}Orderflow score: {final_score:.2f}")
            
        if self.debug_level >= 2:
            self.logger.debug(f"Component scores for {symbol or 'current market'}:")
            self.logger.debug(f"- CVD: {component_scores.get('cvd', 0):.2f}")
            self.logger.debug(f"- Imbalance: {component_scores.get('imbalance_score', 0):.2f}")
            self.logger.debug(f"- Trade flow: {component_scores.get('trade_flow_score', 0):.2f}")
            self.logger.debug(f"- Open interest: {component_scores.get('open_interest_score', 0):.2f}")
            self.logger.debug(f"- Pressure: {component_scores.get('pressure_score', 0):.2f}")
            self.logger.debug(f"- Liquidity: {component_scores.get('liquidity_score', 0):.2f}")
            
        if self.debug_level >= 3:
            self.logger.debug(f"Component weights:")
            for component, weight in self.component_weights.items():
                score = component_scores.get(component, 0)
                weighted = score * weight
                self.logger.debug(f"- {component}: {score:.2f} * {weight:.2f} = {weighted:.2f}")

    async def get_signals(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get orderflow-based trading signals."""
        try:
            orderbook = market_data.get('orderbook', {})
            
            signals = {
                'trade_flow': 'buy' if self._calculate_trade_flow(market_data['trades']) > 60 else 'sell',
                'trade_size': 'buy' if self._calculate_trade_size(market_data['trades']) > 60 else 'sell',
                'trade_frequency': 'buy' if self._calculate_trade_frequency(market_data['trades']) > 60 else 'sell',
                'trade_impact': self._detect_trade_impact(orderbook)
            }
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error getting orderflow signals: {str(e)}")
            return {}

    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input data for orderflow analysis."""
        try:
            # First check base requirements
            if not self._validate_base_requirements(data):
                return False
                
            # Orderflow-specific validation
            orderbook = data.get('orderbook', {})
            trades = data.get('trades', [])
            
            # Validate orderbook
            if not orderbook:
                self.logger.error("Missing orderbook data")
                return False
                
            required_fields = ['bids', 'asks']
            missing_fields = [f for f in required_fields if f not in orderbook]
            if missing_fields:
                self.logger.error(f"Missing orderbook fields: {missing_fields}")
                return False
                
            # Validate trades
            if not trades:
                self.logger.error("Missing trades data")
                return False
                
            if len(trades) < self.min_trades:
                self.logger.error(f"Insufficient trade history. Required: {self.min_trades}, Got: {len(trades)}")
                return False
                
            # Validate trade structure
            required_trade_fields = ['id', 'price', 'size', 'side', 'time']
            field_mappings = {
                'id': ['id', 'trade_id', 'execId', 'i'],
                'price': ['price', 'execPrice', 'p'],
                'size': ['size', 'amount', 'execQty', 'v'],
                'side': ['side', 'S', 'direction'],
                'time': ['time', 'timestamp', 'T']
            }
            
            for trade in trades[:1]:  # Check first trade only
                missing_fields = []
                for req_field in required_trade_fields:
                    alternatives = field_mappings.get(req_field, [req_field])
                    if not any(alt in trade for alt in alternatives):
                        missing_fields.append(req_field)
                
                if missing_fields:
                    self.logger.error(f"Missing trade fields: {missing_fields}")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error in orderflow data validation: {str(e)}")
            return False

    def _validate_input(self, data: Dict[str, Any]) -> bool:
        """Internal method to validate orderflow data input."""
        try:
            # Check required data components
            required_keys = ['trades', 'orderbook', 'ticker']
            missing_keys = [key for key in required_keys if key not in data]
            
            if missing_keys:
                self.logger.error(f"Missing required data keys: {missing_keys}")
                return False
                
            trades = data.get('trades', [])
            if not isinstance(trades, (list, pd.DataFrame)):
                self.logger.error("Trades must be a list or DataFrame")
                return False
                
            if len(trades) < self.min_trades:
                self.logger.error(f"Insufficient trade data: {len(trades)} < {self.min_trades}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating orderflow data: {str(e)}")
            return False

    def _calculate_confidence(self, market_data: Dict[str, Any]) -> float:
        """Calculate confidence in orderflow analysis."""
        try:
            trades = market_data.get('trades', [])
            
            # Check data quality
            if len(trades) < self.min_trades:
                return 0.5
                
            # Check for consistent trade data
            if not all(isinstance(t, dict) and 'price' in t and 'amount' in t for t in trades):
                return 0.7
                
            return 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5

    async def _calculate_component_scores(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate orderflow-based component scores."""
        try:
            # Use the cache if components are already calculated
            if 'component_scores' in self._cache:
                return self._cache['component_scores']
                
            scores = {}
            
            # Calculate CVD score - use caching internally
            scores['cvd'] = self._calculate_cvd(data)
            
            # Calculate open interest score - use caching internally
            scores['open_interest_score'] = self._calculate_open_interest_score(data)
            
            # Calculate trade flow score - use caching internally
            scores['trade_flow_score'] = self._calculate_trade_flow_score(data)
            
            # Calculate imbalance score - use caching internally
            scores['imbalance_score'] = self._calculate_imbalance_score(data)
            
            # Calculate liquidity score - use caching internally
            scores['liquidity_score'] = self._calculate_liquidity_score(data)
            
            # Store in cache before returning
            self._cache['component_scores'] = scores
            return scores
            
        except Exception as e:
            self.logger.error(f"Error calculating orderflow scores: {str(e)}")
            return {comp: 50.0 for comp in self.component_weights}

    def _validate_weights(self):
        """Validate component weights."""
        # Ensure all weights are present and sum to 1.0
        required_components = ['cvd', 'trade_flow_score', 'imbalance_score', 'open_interest_score', 'pressure_score', 'liquidity_score']
        
        # Check if all required components have weights
        for component in required_components:
            if component not in self.component_weights:
                self.component_weights[component] = 0.20  # Default equal weight
        
        # Normalize weights to sum to 1.0
        total_weight = sum(self.component_weights.values())
        if total_weight != 1.0:
            for component in self.component_weights:
                self.component_weights[component] /= total_weight
                
    def _cached_compute(self, key: str, compute_func, *args, **kwargs):
        """Compute a value with caching to avoid redundant calculations.
        
        Args:
            key: Cache key for this computation
            compute_func: Function to compute the value
            *args, **kwargs: Arguments to pass to compute_func
            
        Returns:
            The computed value, either from cache or freshly calculated
        """
        if key not in self._cache:
            self._cache[key] = compute_func(*args, **kwargs)
        return self._cache[key]
    
    def _calculate_cvd(self, market_data: Dict[str, Any]) -> float:
        """Calculate Cumulative Volume Delta (CVD) from trade data.
        
        Args:
            market_data: Market data dictionary containing trades
            
        Returns:
            float: CVD value
        """
        # Use caching to avoid redundant calculations
        cache_key = 'cvd'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING CVD CALCULATION")
        self.logger.debug("=" * 50)
        
        try:
            # Handle different input types
            trades_df = None
            
            # Log input data type
            self.logger.debug(f"Input market_data type: {type(market_data)}")
            if isinstance(market_data, dict):
                self.logger.debug(f"Market data keys: {list(market_data.keys())}")
            
            # Case 1: market_data is already a DataFrame
            if isinstance(market_data, pd.DataFrame):
                trades_df = market_data.copy()
                self.logger.debug(f"Market data is already a DataFrame, shape: {trades_df.shape}, columns: {list(trades_df.columns)}")
            
            # Case 2: market_data is a list of trade dictionaries
            elif isinstance(market_data, list):
                try:
                    if market_data:
                        self.logger.debug(f"Market data is a list with {len(market_data)} items")
                        if len(market_data) > 0:
                            self.logger.debug(f"First trade sample: {market_data[0]}")
                        trades_df = pd.DataFrame(market_data)
                        self.logger.debug(f"Converted trade list to DataFrame, shape: {trades_df.shape}, columns: {list(trades_df.columns)}")
                    else:
                        self.logger.warning("Empty trade list provided for CVD calculation")
                        return 0.0
                except Exception as e:
                    self.logger.error(f"Error converting trade list to DataFrame: {str(e)}")
                    self.logger.debug(traceback.format_exc())
                    return 0.0
            
            # Case 3: market_data is a dictionary with trade data
            elif isinstance(market_data, dict):
                # Try different possible sources of trade data
                if 'processed_trades' in market_data and isinstance(market_data['processed_trades'], list) and len(market_data['processed_trades']) > 0:
                    try:
                        self.logger.debug(f"Using processed_trades list with {len(market_data['processed_trades'])} items")
                        if len(market_data['processed_trades']) > 0:
                            self.logger.debug(f"First processed trade sample: {market_data['processed_trades'][0]}")
                        trades_df = pd.DataFrame(market_data['processed_trades'])
                        self.logger.debug(f"Converted processed_trades to DataFrame, shape: {trades_df.shape}, columns: {list(trades_df.columns)}")
                    except Exception as e:
                        self.logger.error(f"Error converting processed_trades to DataFrame: {str(e)}")
                        self.logger.debug(traceback.format_exc())
                        return 0.0
                elif 'trades' in market_data and isinstance(market_data['trades'], list) and len(market_data['trades']) > 0:
                    try:
                        self.logger.debug(f"Using trades list with {len(market_data['trades'])} items")
                        if len(market_data['trades']) > 0:
                            self.logger.debug(f"First trade sample: {market_data['trades'][0]}")
                        trades_df = pd.DataFrame(market_data['trades'])
                        self.logger.debug(f"Converted trades list to DataFrame, shape: {trades_df.shape}, columns: {list(trades_df.columns)}")
                    except Exception as e:
                        self.logger.error(f"Error converting trades list to DataFrame: {str(e)}")
                        self.logger.debug(traceback.format_exc())
                        return 0.0
                elif 'trades_df' in market_data and isinstance(market_data['trades_df'], pd.DataFrame) and not market_data['trades_df'].empty:
                    trades_df = market_data['trades_df'].copy()
                    self.logger.debug(f"Using trades_df DataFrame directly, shape: {trades_df.shape}, columns: {list(trades_df.columns)}")
                else:
                    self.logger.warning("No trade data available for CVD calculation")
                    return 0.0
            else:
                self.logger.error(f"Unsupported market_data type for CVD calculation: {type(market_data)}")
                return 0.0
                
            # Ensure we have a valid DataFrame at this point
            if trades_df is None or trades_df.empty:
                self.logger.warning("No valid trade data available for CVD calculation")
                return 0.0
                
            # Log DataFrame info
            self.logger.debug(f"Trade DataFrame info: {len(trades_df)} rows, columns: {list(trades_df.columns)}")
            
            # Map column names to standard names
            column_mappings = {
                'side': ['side', 'S', 'type', 'trade_type'],
                'amount': ['amount', 'size', 'v', 'volume', 'qty', 'quantity']
            }
            
            # Try to find and map the required columns
            for std_col, possible_cols in column_mappings.items():
                if std_col not in trades_df.columns:
                    for col in possible_cols:
                        if col in trades_df.columns:
                            trades_df[std_col] = trades_df[col]
                            self.logger.debug(f"Mapped '{col}' to '{std_col}'")
                            break
            
            # Check if we have the required columns after mapping
            if 'side' not in trades_df.columns or 'amount' not in trades_df.columns:
                missing = []
                if 'side' not in trades_df.columns:
                    missing.append('side')
                if 'amount' not in trades_df.columns:
                    missing.append('amount')
                self.logger.warning(f"Missing required columns after mapping: {missing}. Available columns: {list(trades_df.columns)}")
                return 0.0
            
            # Calculate CVD
            # Convert side to numeric: buy = 1, sell = -1
            try:
                # First ensure side column contains strings
                trades_df['side'] = trades_df['side'].astype(str)
                self.logger.debug(f"Side value counts before normalization: {trades_df['side'].value_counts().to_dict()}")
                
                # Ensure amount column is numeric
                trades_df['amount'] = pd.to_numeric(trades_df['amount'], errors='coerce')
                trades_df = trades_df.dropna(subset=['amount'])  # Drop rows with non-numeric amounts
                self.logger.debug(f"Amount statistics after conversion: min={trades_df['amount'].min()}, max={trades_df['amount'].max()}, mean={trades_df['amount'].mean()}, sum={trades_df['amount'].sum()}")
                
                # Now convert to numeric values using explicit equality checks
                def side_to_numeric(side_val):
                    side_str = str(side_val).lower()
                    if side_str in ['buy', 'b', 'bid', '1', 'true', 'long']:
                        return 1
                    else:
                        return -1
                
                trades_df['side_num'] = trades_df['side'].apply(side_to_numeric)
                self.logger.debug(f"Side numeric value counts: {trades_df['side_num'].value_counts().to_dict()}")
                
                # Calculate signed volume
                trades_df['signed_volume'] = trades_df['amount'] * trades_df['side_num']
                
                # Log some statistics about the signed volume
                signed_volume_stats = {
                    'min': trades_df['signed_volume'].min(),
                    'max': trades_df['signed_volume'].max(),
                    'mean': trades_df['signed_volume'].mean(),
                    'sum': trades_df['signed_volume'].sum(),
                    'buy_volume': trades_df[trades_df['side_num'] > 0]['amount'].sum(),
                    'sell_volume': trades_df[trades_df['side_num'] < 0]['amount'].sum()
                }
                self.logger.debug(f"Signed volume statistics: {signed_volume_stats}")
                
                # Sum to get CVD
                cvd = trades_df['signed_volume'].sum()
                
                self.logger.debug(f"Raw CVD value: {cvd}")
                
                # Get total trading volume
                total_volume = signed_volume_stats['buy_volume'] + signed_volume_stats['sell_volume']
                
                # Convert CVD to a score in the 0-100 range using percentage-based normalization
                # This normalizes CVD relative to total volume, making it scale across different symbols
                if total_volume > 0:
                    # Calculate CVD as percentage of total volume
                    cvd_percentage = cvd / total_volume
                    # Scale to reasonable range for tanh (-3 to 3)
                    normalized_cvd = np.tanh(cvd_percentage * 3)  # Adjust multiplier as needed
                    self.logger.debug(f"CVD percentage of volume: {cvd_percentage:.4f}, Scaled for tanh: {cvd_percentage * 3:.4f}")
                else:
                    normalized_cvd = 0.0
                    self.logger.debug("No volume detected, using default normalized CVD of 0")
                
                # Convert to 0-100 score
                cvd_score = 50 + (normalized_cvd * 50)
                
                self.logger.debug(f"Normalized CVD: {normalized_cvd:.4f}, CVD Score: {cvd_score:.2f}")
                
                # Log execution time
                execution_time = time.time() - start_time
                self.logger.debug(f"CVD calculation completed in {execution_time:.4f} seconds")
                self.logger.debug("=" * 50)
                
                # Store result in cache
                self._cache['cvd'] = cvd_score
                return cvd_score
            except Exception as e:
                self.logger.error(f"Error calculating CVD values: {str(e)}")
                self.logger.debug(traceback.format_exc())
                return 0.0
        except Exception as e:
            self.logger.error(f"Error calculating CVD: {str(e)}")
            self.logger.debug(traceback.format_exc())
            execution_time = time.time() - start_time
            self.logger.debug(f"CVD calculation failed after {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            return 0.0
            
    def _calculate_base_cvd_score(self, cvd_value):
        """
        Calculate a score based on the Cumulative Volume Delta (CVD) value.
        
        Args:
            cvd_value (float): The calculated CVD value
            
        Returns:
            float: Score between 0-100
        """
        try:
            # Simple normalization based on the magnitude of the CVD
            # Positive CVD indicates buying pressure (bullish)
            # Negative CVD indicates selling pressure (bearish)
            
            # Normalize to -1 to 1 range based on typical CVD values
            # May need adjustment for different markets/timeframes
            normalized_cvd = np.tanh(cvd_value / 1000)  # Adjust divisor based on typical values
            
            # Convert to 0-100 score
            score = 50 + (normalized_cvd * 50)
            
            self.logger.debug(f"Base CVD: {cvd_value:.4f}, Normalized: {normalized_cvd:.4f}, Score: {score:.2f}")
            
            return float(np.clip(score, 0, 100))
        except Exception as e:
            self.logger.error(f"Error calculating base CVD score: {str(e)}")
            return 50.0
            
    def _calculate_trade_flow_score(self, market_data):
        """Calculate trade flow score based on buy vs sell volume.
        
        Args:
            market_data: Market data dictionary or trade DataFrame
            
        Returns:
            float: Trade flow score (0-100)
        """
        # Use caching to avoid redundant calculations
        cache_key = 'trade_flow_score'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Try different possible locations for trade data
            trades = None
            
            # First check for processed_trades
            if 'processed_trades' in market_data and isinstance(market_data['processed_trades'], list):
                trades = market_data['processed_trades']
                self.logger.debug("Using processed_trades for trade flow calculation")
            
            # Fall back to regular trades if no processed trades
            elif 'trades' in market_data:
                if isinstance(market_data['trades'], list):
                    trades = market_data['trades']
                    self.logger.debug("Using trades list for trade flow calculation")
                elif isinstance(market_data['trades'], pd.DataFrame):
                    trades = market_data['trades']
                    self.logger.debug("Using trades DataFrame for trade flow calculation")
            
            # Check for trades_df as another option
            elif 'trades_df' in market_data and isinstance(market_data['trades_df'], pd.DataFrame):
                trades = market_data['trades_df']
                self.logger.debug("Using trades_df for trade flow calculation")
            
            # If no valid trades data found
            if not trades or (isinstance(trades, list) and len(trades) < 10):
                self.logger.warning("Insufficient trade data for trade flow calculation")
                return 50.0  # Neutral score
                
            # Calculate trade flow
            try:
                # Handle different types properly
                if isinstance(trades, pd.DataFrame):
                    flow = self._calculate_trade_flow(trades)
                elif isinstance(trades, list):
                    if not trades:
                        return 50.0
                    try:
                        trade_df = pd.DataFrame(trades)
                        flow = self._calculate_trade_flow(trade_df)
                    except Exception as e:
                        self.logger.error(f"Failed to convert trades list to DataFrame: {str(e)}")
                        return 50.0
                else:
                    self.logger.error(f"Unsupported trade data type: {type(trades)}")
                    return 50.0
                
                # Map flow to score (-1 to 1 -> 0 to 100)
                score = 50 + (flow * 50)
                
                # Ensure score is within bounds
                return max(0, min(100, score))
            except Exception as e:
                self.logger.error(f"Error in trade flow calculation: {str(e)}")
                return 50.0
        except Exception as e:
            self.logger.error(f"Error calculating trade flow score: {str(e)}")
            return 50.0  # Neutral score
            
        # Store in cache before returning
        self._cache['trade_flow_score'] = score
        return score

    def _calculate_imbalance_score(self, market_data):
        """Calculate orderbook imbalance score.
        
        Args:
            market_data: Market data dictionary containing orderbook
            
        Returns:
            float: Imbalance score (0-100)
        """
        # Use caching to avoid redundant calculations
        cache_key = 'imbalance_score'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Check if orderbook data exists
            if 'orderbook' not in market_data or not market_data['orderbook']:
                self.logger.warning("No orderbook data available for imbalance calculation")
                return 50.0
                
            orderbook = market_data['orderbook']
            
            # Check for bids and asks
            if 'bids' not in orderbook or 'asks' not in orderbook:
                self.logger.warning("Orderbook missing bids or asks")
                return 50.0
                
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                self.logger.warning("Empty bids or asks in orderbook")
                return 50.0
                
            # Calculate volume at top levels (e.g., top 5 levels)
            depth_levels = 5
            
            # Sum bid and ask volumes
            bid_volume = 0
            for i, bid in enumerate(bids):
                if i >= depth_levels:
                    break
                if len(bid) >= 2:
                    bid_volume += float(bid[1])
                    
            ask_volume = 0
            for i, ask in enumerate(asks):
                if i >= depth_levels:
                    break
                if len(ask) >= 2:
                    ask_volume += float(ask[1])
                    
            total_volume = bid_volume + ask_volume
            if total_volume == 0:
                self.logger.warning("Zero total volume in imbalance calculation")
                return 50.0
                
            # Calculate imbalance ratio (-1 to 1)
            imbalance = (bid_volume - ask_volume) / total_volume
            
            # Map to score (0-100)
            # -1 (all selling) = 0 score
            # 0 (balanced) = 50 score
            # 1 (all buying) = 100 score
            score = 50 + (imbalance * 50)
            
            self.logger.debug(f"Imbalance: Bids={bid_volume:.4f}, Asks={ask_volume:.4f}, Ratio={imbalance:.4f}, Score={score:.2f}")
            return float(np.clip(score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating imbalance score: {str(e)}")
            return 50.0
        
        # Store in cache before returning
        self._cache['imbalance_score'] = score
        return score

    def _get_open_interest_values(self, market_data):
        """
        Get the current and previous open interest values.
        
        Args:
            market_data (dict): Dictionary containing market data with open interest data
            
        Returns:
            dict: Dictionary containing 'current' and 'previous' open interest values,
                  or None if data not available
        """
        try:
            # Check if we have open interest data at the top level
            if 'open_interest' in market_data:
                oi_data = market_data['open_interest']
                
                # Handle different formats of open interest data
                if isinstance(oi_data, dict):
                    # If we have a dictionary with current and previous values
                    if 'current' in oi_data and 'previous' in oi_data:
                        return oi_data  # Return the entire dictionary as is
                    # If we have a dictionary with just current value
                    elif 'current' in oi_data:
                        return {'current': float(oi_data['current']), 'previous': float(oi_data['current']) * 0.98}
                # If we have a simple numeric value
                elif isinstance(oi_data, (int, float)):
                    return {'current': float(oi_data), 'previous': float(oi_data) * 0.98}
            
            # Fallback: check if we have it under sentiment for backward compatibility
            if 'sentiment' in market_data and 'open_interest' in market_data['sentiment']:
                oi_data = market_data['sentiment']['open_interest']
                
                # Handle different formats of open interest data
                if isinstance(oi_data, dict):
                    # If we have a dictionary with current and previous values
                    if 'current' in oi_data and 'previous' in oi_data:
                        return oi_data  # Return the entire dictionary as is
                    # If we have a dictionary with just current value
                    elif 'current' in oi_data:
                        return {'current': float(oi_data['current']), 'previous': float(oi_data['current']) * 0.98}
                # If we have a simple numeric value
                elif isinstance(oi_data, (int, float)):
                    return {'current': float(oi_data), 'previous': float(oi_data) * 0.98}
            
            # Last resort: try to get it from ticker data directly
            if 'ticker' in market_data and isinstance(market_data['ticker'], dict):
                ticker = market_data['ticker']
                current_oi = float(ticker.get('openInterest', 0))
                # We don't have previous value in this case
                return {'current': current_oi, 'previous': current_oi * 0.98}
                
            # If all else fails, return None
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting open interest values: {e}")
            return None

    def _calculate_open_interest_score(self, market_data):
        """Calculate open interest score based on changes.
        
        Args:
            market_data: Dictionary containing open interest data
            
        Returns:
            float: Open interest score (0-100)
        """
        # Use caching to avoid redundant calculations
        cache_key = 'open_interest_score'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        try:
            # Get open interest values
            oi_data = self._get_open_interest_values(market_data)
            
            # Check if we have valid open interest data
            if not oi_data or 'current' not in oi_data or 'previous' not in oi_data:
                self.logger.warning("Missing or invalid open interest data")
                return 50.0  # Return neutral score when data is missing
                
            current_oi = oi_data['current']
            previous_oi = oi_data['previous']
            
            # Calculate percentage change with safety check for division by zero
            if previous_oi == 0 or previous_oi is None:
                oi_change_pct = 0
            else:
                oi_change_pct = ((current_oi - previous_oi) / previous_oi) * 100
                
            self.logger.debug(f"Open interest change: {oi_change_pct:.2f}% (current: {current_oi:.2f}, previous: {previous_oi:.2f})")
            
            # Normalize and convert to score
            if oi_change_pct > 0:
                # Positive OI change: normalized to 0.0-1.0, score 50-100 (bullish)
                normalized_change = min(oi_change_pct / 5.0, 1.0)  # Cap at 5% change
                score = 50 + (normalized_change * 50)
                self.logger.debug(f"Positive OI change: normalized to {normalized_change:.4f}, score: {score:.2f} (bullish)")
            else:
                # Negative OI change: normalized to 0.0-1.0, score 0-50 (bearish)
                normalized_change = min(abs(oi_change_pct) / 5.0, 1.0)  # Cap at 5% change
                score = 50 - (normalized_change * 50)
                self.logger.debug(f"Negative OI change: normalized to {normalized_change:.4f}, score: {score:.2f} (bearish)")
            
            # Interpret the open interest change
            if abs(oi_change_pct) < 0.5:
                interpretation = "Neutral (minimal change)"
            elif oi_change_pct > 0 and score > 70:
                interpretation = "Strongly bullish (increasing open interest)"
            elif oi_change_pct > 0:
                interpretation = "Moderately bullish (slight increase in open interest)"
            elif oi_change_pct < 0 and score < 30:
                interpretation = "Strongly bearish (decreasing open interest)"
            else:
                interpretation = "Moderately bearish (slight decrease in open interest)"
                
            self.logger.debug(f"Open interest interpretation: {interpretation}")
            
            # Store in cache before returning
            self._cache[cache_key] = score
            return score
            
        except Exception as e:
            self.logger.error(f"Error calculating open interest score: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 50.0

    def _get_open_interest_change(self, market_data):
        """
        Calculate the open interest change percentage from market data.
        
        Args:
            market_data (dict): Dictionary containing market data with sentiment data
            
        Returns:
            float: Open interest change percentage or 0.0 if data not available
        """
        try:
            # Get current and previous values using the helper method
            current, previous = self._get_open_interest_values(market_data)
            
            # Calculate percentage change
            if previous == 0:
                return 0.0
            
            change_pct = ((current - previous) / previous) * 100
            self.logger.debug(f"Open interest change: {change_pct:.2f}% (Current: {current}, Previous: {previous})")
            return change_pct
            
        except Exception as e:
            self.logger.error(f"Error calculating open interest change: {e}")
            return 0.0

    def _get_trade_pressure(self, market_data: Dict[str, Any]) -> Tuple[float, float]:
        """
        Get the buy and sell pressure values.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Tuple[float, float]: Buy pressure and sell pressure
        """
        try:
            # Get trades data
            trades = market_data.get('trades', [])
            if not trades or len(trades) < 10:
                return 1.0, 1.0  # Neutral values
                
            # Convert to DataFrame if not already
            trades_df = trades if isinstance(trades, pd.DataFrame) else pd.DataFrame(trades)
            
            # Check if required columns exist
            required_cols = ['side', 'amount', 'price']
            if not all(col in trades_df.columns for col in required_cols):
                # Try alternative column names
                alt_cols = {'side': 'S', 'amount': 'v', 'price': 'p'}
                for req_col, alt_col in alt_cols.items():
                    if req_col not in trades_df.columns and alt_col in trades_df.columns:
                        trades_df[req_col] = trades_df[alt_col]
                
                # Check again after attempting to use alternative columns
                if not all(col in trades_df.columns for col in required_cols):
                    return 1.0, 1.0  # Neutral values
            
            # Calculate buy pressure (sum of buy volume * price)
            buy_df = trades_df[trades_df['side'] == 'buy']
            buy_pressure = (buy_df['amount'] * buy_df['price']).sum() if not buy_df.empty else 0
            
            # Calculate sell pressure (sum of sell volume * price)
            sell_df = trades_df[trades_df['side'] == 'sell']
            sell_pressure = (sell_df['amount'] * sell_df['price']).sum() if not sell_df.empty else 0
            
            # Normalize to reasonable values
            buy_pressure = buy_pressure / 1000000 if buy_pressure > 0 else 0.001
            sell_pressure = sell_pressure / 1000000 if sell_pressure > 0 else 0.001
            
            return buy_pressure, sell_pressure
        except Exception as e:
            self.logger.error(f"Error calculating trade pressure: {str(e)}")
            return 1.0, 1.0  # Neutral values

    def _calculate_liquidity_score(self, market_data: Dict[str, Any]) -> float:
        """Calculate liquidity score based on trade frequency and volume.
        
        This method calculates a trade-based liquidity score that is distinct from the
        orderbook-based liquidity measure. While orderbook liquidity looks at available
        orders and depth, this score focuses on actual trade execution frequency and volume
        to measure realized market liquidity.
        
        The score is calculated using two components:
        1. Trade Frequency: How many trades occur per second
        2. Trade Volume: Total volume traded in the measurement window
        
        Both components are normalized and weighted according to configuration parameters.
        
        Args:
            market_data: Dictionary containing market data with trades, or a direct trades list/DataFrame
            
        Returns:
            float: Liquidity score between 0-100, where:
                  0-25: Low liquidity
                  25-75: Normal liquidity
                  75-100: High liquidity
        """
        
        # Use caching to avoid redundant calculations
        cache_key = 'liquidity_score'
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # Get configuration parameters from config
            liquidity_config = self.config.get('analysis', {}).get('indicators', {}).get('orderflow', {}).get('parameters', {}).get('liquidity', {})
            
            # Extract parameters with defaults if not found in config
            window_minutes = liquidity_config.get('window_minutes', 5)
            max_trades_per_sec = liquidity_config.get('max_trades_per_sec', 5)
            max_volume = liquidity_config.get('max_volume', 1000)
            frequency_weight = liquidity_config.get('frequency_weight', 0.5)
            volume_weight = liquidity_config.get('volume_weight', 0.5)

            # Validate parameters
            if window_minutes <= 0:
                self.logger.warning(f"Invalid window_minutes: {window_minutes}, using default of 5")
                window_minutes = 5
            if max_trades_per_sec <= 0:
                self.logger.warning(f"Invalid max_trades_per_sec: {max_trades_per_sec}, using default of 5")
                max_trades_per_sec = 5
            if max_volume <= 0:
                self.logger.warning(f"Invalid max_volume: {max_volume}, using default of 1000")
                max_volume = 1000
                
            # Validate and normalize weights
            total_weight = frequency_weight + volume_weight
            if total_weight != 1.0:
                self.logger.warning(f"Liquidity weights don't sum to 1.0 ({total_weight}), normalizing")
                frequency_weight /= total_weight
                volume_weight /= total_weight

            # Extract trade data - handle different possible input types
            trades = None
            
            # If market_data is a dictionary
            if isinstance(market_data, dict):
                # First check for processed_trades (highest priority)
                if 'processed_trades' in market_data and isinstance(market_data['processed_trades'], list):
                    trades = market_data['processed_trades']
                    self.logger.debug("Using processed_trades for liquidity calculation")
                
                # Fall back to trades_df
                elif 'trades_df' in market_data and isinstance(market_data['trades_df'], pd.DataFrame):
                    trades_df = market_data['trades_df']
                    self.logger.debug(f"Using trades_df directly, shape: {trades_df.shape}, columns: {list(trades_df.columns)}")
                
                # Fall back to regular trades
                elif 'trades' in market_data:
                    trades = market_data['trades']
                    self.logger.debug(f"Using trades from market_data: {len(trades)} items")
            
            # If market_data is directly a list of trades
            elif isinstance(market_data, list):
                trades = market_data
                self.logger.debug(f"Using direct trades list: {len(trades)} items")
            
            # If market_data is directly a DataFrame
            elif isinstance(market_data, pd.DataFrame):
                trades_df = market_data
                self.logger.debug(f"Using direct DataFrame: {trades_df.shape}, columns: {list(trades_df.columns)}")
            
            # Check if we have valid trade data
            if trades is None and not 'trades_df' in locals():
                self.logger.warning("No valid trade data found for liquidity calculation")
                return 50.0  # Neutral score when data is missing
                
            # If we have trades list, convert to DataFrame
            if trades is not None:
                if not trades or len(trades) < 10:
                    self.logger.warning("Insufficient trade data for liquidity score calculation (< 10 trades)")
                    return 50.0  # Neutral score when data is missing
                
                # Convert trades to DataFrame
                trades_df = pd.DataFrame(trades)
                
                # Ensure required columns exist
                if 'time' not in trades_df.columns:
                    # Try different column names for time
                    time_column_variants = ['timestamp', 'time', 'datetime']
                    for col in time_column_variants:
                        if col in trades_df.columns:
                            trades_df['time'] = trades_df[col]
                            self.logger.debug(f"Mapped '{col}' to 'time' column")
                            break
                
                if 'size' not in trades_df.columns:
                    # Try different column names for size
                    size_column_variants = ['amount', 'volume', 'quantity', 'size']
                    for col in size_column_variants:
                        if col in trades_df.columns:
                            trades_df['size'] = trades_df[col]
                            self.logger.debug(f"Mapped '{col}' to 'size' column")
                            break
            
            # Final check for required columns
            if 'time' not in trades_df.columns or 'size' not in trades_df.columns:
                self.logger.warning("Missing required trade data columns for liquidity calculation")
                return 50.0

            # Ensure numeric conversion of size column (it may come as strings)
            try:
                trades_df['size'] = pd.to_numeric(trades_df['size'])
            except Exception as e:
                self.logger.warning(f"Error converting 'size' to numeric: {str(e)}")
                # Try fallback method using apply
                try:
                    trades_df['size'] = trades_df['size'].apply(lambda x: float(x) if isinstance(x, str) else x)
                except Exception as e:
                    self.logger.error(f"Failed to convert trade sizes to numeric values: {str(e)}")
                    return 50.0  # Return neutral score if conversion fails

            # Convert time column to datetime with appropriate error handling
            try:
                # If time is already numeric, use unit='ms'
                if pd.api.types.is_numeric_dtype(trades_df['time']):
                    trades_df['time'] = pd.to_datetime(trades_df['time'], unit='ms')
                # If time is string, first convert to numeric then to datetime
                else:
                    trades_df['time'] = pd.to_numeric(trades_df['time'])
                    trades_df['time'] = pd.to_datetime(trades_df['time'], unit='ms')
            except Exception as e:
                self.logger.error(f"Error converting time to datetime: {str(e)}")
                return 50.0  # Return neutral score if conversion fails
            
            # Log sample data for debugging
            if len(trades_df) > 0:
                self.logger.debug(f"Sample trade data: {trades_df.iloc[0].to_dict()}")

            # Set rolling window for liquidity measurement based on config
            latest_time = trades_df['time'].max()
            window_start = latest_time - pd.Timedelta(minutes=window_minutes)

            # Filter trades within the time window
            recent_trades = trades_df[trades_df['time'] >= window_start]
            
            if len(recent_trades) < 5:
                self.logger.warning(f"Only {len(recent_trades)} trades in the last {window_minutes} minutes, insufficient for reliable liquidity calculation")
                return 50.0  # Neutral score for insufficient recent data

            # Calculate trade frequency (trades per second)
            trade_frequency = len(recent_trades) / (window_minutes * 60)
            
            # Calculate trade volume
            total_volume = recent_trades['size'].sum()
            
            # Log detailed statistics - safely format numeric values
            self.logger.debug(f"Liquidity calculation statistics:")
            self.logger.debug(f"- Time window: {window_minutes} minutes")
            self.logger.debug(f"- Total trades: {len(recent_trades)}")
            self.logger.debug(f"- Trade frequency: {trade_frequency:.2f} trades/sec (max: {max_trades_per_sec})")
            self.logger.debug(f"- Total volume: {float(total_volume):.2f} (max: {max_volume})")

            # Normalize trade frequency (using configured max value)
            normalized_frequency = min(1, trade_frequency / max_trades_per_sec) * 100
            
            # Normalize trade volume (using configured max value)
            normalized_volume = min(1, float(total_volume) / max_volume) * 100
            
            # Log normalized values
            self.logger.debug(f"Normalized values:")
            self.logger.debug(f"- Frequency score: {normalized_frequency:.2f} (weight: {frequency_weight:.2f})")
            self.logger.debug(f"- Volume score: {normalized_volume:.2f} (weight: {volume_weight:.2f})")

            # Compute final liquidity score with configured weights
            liquidity_score = (normalized_frequency * frequency_weight) + (normalized_volume * volume_weight)
            
            self.logger.debug(f"Final liquidity score: {liquidity_score:.2f}")
            if liquidity_score > 75:
                self.logger.debug("High liquidity detected")
            elif liquidity_score < 25:
                self.logger.debug("Low liquidity detected")
            else:
                self.logger.debug("Normal liquidity levels")

            # Store in cache before returning
            self._cache[cache_key] = liquidity_score

            return round(liquidity_score, 2)

        except Exception as e:
            self.logger.error(f"Error calculating liquidity score: {str(e)}")
            if self.debug_level >= 3:
                import traceback
                self.logger.error(traceback.format_exc())
            return 50.0  # Return neutral score if error occurs

    def _get_orderflow_interpretation(self, weighted_score: float, imbalance_score: float,
                                    cvd_score: float, oi_score: float, trade_score: float, 
                                    liquidity_score: float = 50.0) -> Dict[str, str]:
        """Get interpretation of orderflow analysis."""
        message = ""
        signal = ""
        
        # Base signal based on weighted score
        if weighted_score >= 70:
            message = "Strong bullish orderflow"
            signal = "strong_buy"
        elif weighted_score >= 60:
            message = "Moderately bullish orderflow"
            signal = "buy"
        elif weighted_score <= 30:
            message = "Strong bearish orderflow"
            signal = "strong_sell"
        elif weighted_score <= 40:
            message = "Moderately bearish orderflow"
            signal = "sell"
        else:
            message = "Neutral orderflow"
            signal = "neutral"
        
        # Add liquidity context to the message if available
        if liquidity_score > 75:
            message += " with high liquidity"
        elif liquidity_score < 25:
            message += " with low liquidity"
            
        return {'message': message, 'signal': signal}

    def _calculate_price_cvd_divergence(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate divergence between price and CVD.
        
        This method detects when price is moving in one direction but CVD is moving in the opposite direction,
        which can indicate potential reversals.
        
        Args:
            market_data: Dictionary containing market data with OHLCV and trades
            
        Returns:
            Dict: Divergence information including type and strength
        """
        # Use caching to avoid redundant calculations
        cache_key = 'price_cvd_divergence'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        calculation_start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING PRICE-CVD DIVERGENCE CALCULATION")
        self.logger.debug("=" * 50)
        
        try:
            # Check if we have the required data
            if 'ohlcv' not in market_data:
                self.logger.warning("Missing OHLCV data for price-CVD divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            ohlcv_data = market_data['ohlcv']
            
            # Check if ohlcv_data is a dictionary
            if not isinstance(ohlcv_data, dict):
                self.logger.warning(f"OHLCV data is not a dictionary: {type(ohlcv_data)}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log available timeframes
            self.logger.debug(f"Available OHLCV timeframes: {list(ohlcv_data.keys())}")
                
            # Try to find a valid timeframe
            valid_timeframe = None
            ohlcv_df = None
            
            # First check for direct DataFrame access (for backward compatibility)
            for tf in ['base', 'ltf', '1', '5']:
                if tf in ohlcv_data:
                    # Check if it's a direct DataFrame
                    if isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
                    # Check if it's a nested structure with 'data' key
                    elif isinstance(ohlcv_data[tf], dict) and 'data' in ohlcv_data[tf] and isinstance(ohlcv_data[tf]['data'], pd.DataFrame) and not ohlcv_data[tf]['data'].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]['data']
                        self.logger.debug(f"Found nested DataFrame at timeframe {tf}['data']")
                        break
            
            # Also check for timeframes with '_direct' suffix (added for testing)
            if not valid_timeframe:
                for tf in ['base_direct', 'ltf_direct', '1_direct', '5_direct']:
                    if tf in ohlcv_data and isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
            
            if not valid_timeframe or ohlcv_df is None:
                self.logger.warning("No valid OHLCV timeframe found for price-CVD divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Verify that the DataFrame has the required columns
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in ohlcv_df.columns]
            if missing_columns:
                self.logger.warning(f"OHLCV data missing required columns: {missing_columns}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log OHLCV DataFrame info
            self.logger.debug(f"OHLCV DataFrame for {valid_timeframe}: shape={ohlcv_df.shape}, columns={list(ohlcv_df.columns)}")
            self.logger.debug(f"OHLCV DataFrame index type: {type(ohlcv_df.index)}")
            if len(ohlcv_df) > 0:
                self.logger.debug(f"OHLCV first row: {ohlcv_df.iloc[0].to_dict()}")
                self.logger.debug(f"OHLCV last row: {ohlcv_df.iloc[-1].to_dict()}")
                
            # Use configurable lookback period
            lookback = min(len(ohlcv_df), self.divergence_lookback)
            if lookback < 2:
                self.logger.warning(f"Insufficient OHLCV data for divergence calculation: {len(ohlcv_df)} rows")
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.debug(f"Using lookback period of {lookback} candles for divergence calculation")
            
            # Get trades data
            trades = market_data.get('trades', [])
            if not trades or len(trades) < self.min_trades:
                self.logger.warning(f"Insufficient trade data for price-CVD divergence calculation: {len(trades)} trades, minimum required: {self.min_trades}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Convert trades to DataFrame if needed
            trades_df = trades if isinstance(trades, pd.DataFrame) else pd.DataFrame(trades)
            
            # Log trades DataFrame info
            self.logger.debug(f"Trades DataFrame: shape={trades_df.shape}, columns={list(trades_df.columns)}")
            
            # Ensure we have timestamp in trades
            if 'time' not in trades_df.columns and 'timestamp' in trades_df.columns:
                trades_df['time'] = trades_df['timestamp']
                self.logger.debug("Mapped 'timestamp' to 'time' in trades DataFrame")
            elif 'time' not in trades_df.columns and 'T' in trades_df.columns:
                trades_df['time'] = trades_df['T']
                self.logger.debug("Mapped 'T' to 'time' in trades DataFrame")
                
            if 'time' not in trades_df.columns:
                self.logger.warning("Missing time/timestamp in trades data for price-CVD divergence")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Ensure time column is numeric
            try:
                trades_df['time'] = pd.to_numeric(trades_df['time'])
                self.logger.debug(f"Converted time column to numeric. Sample values: {trades_df['time'].head(3).tolist()}")
            except Exception as e:
                self.logger.warning(f"Failed to convert time column to numeric: {str(e)}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Ensure we have side in trades
            if 'side' not in trades_df.columns and 'S' in trades_df.columns:
                trades_df['side'] = trades_df['S']
                self.logger.debug("Mapped 'S' to 'side' in trades DataFrame")
                
            if 'side' not in trades_df.columns:
                self.logger.warning("Missing side in trades data for price-CVD divergence")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Ensure we have amount/size in trades
            if 'amount' not in trades_df.columns:
                for col in ['size', 'v', 'volume', 'qty', 'quantity']:
                    if col in trades_df.columns:
                        trades_df['amount'] = trades_df[col]
                        self.logger.debug(f"Mapped '{col}' to 'amount' in trades DataFrame")
                        break
                        
            if 'amount' not in trades_df.columns:
                self.logger.warning("Missing amount/size in trades data for price-CVD divergence")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Get price trend
            price_changes = ohlcv_df['close'].diff().tail(lookback)
            price_trend = price_changes.sum()
            
            self.logger.debug(f"Price trend over {lookback} candles: {price_trend:.4f}")
            self.logger.debug(f"Price changes: min={price_changes.min():.4f}, max={price_changes.max():.4f}, mean={price_changes.mean():.4f}")
            
            # Calculate CVD for each candle period
            candle_cvds = []
            candle_timestamps = []
            
            # Ensure proper time tracking for candle processing
            candle_start_time = time.time()
            
            for i in range(1, lookback + 1):
                if i >= len(ohlcv_df):
                    break
                    
                # Get timestamp range for this candle
                # Check if we have a timestamp column or need to use the index
                if 'timestamp' in ohlcv_df.columns:
                    candle_end_time = ohlcv_df.iloc[-i]['timestamp']
                    candle_start_time_ts = ohlcv_df.iloc[-(i+1)]['timestamp'] if i+1 < len(ohlcv_df) else ohlcv_df.iloc[-i]['timestamp'] - 60000  # Fallback: 1 minute earlier
                    self.logger.debug(f"Candle {i} timestamp from column: start={candle_start_time_ts}, end={candle_end_time}")
                    # Save the timestamp for potential interpolation later
                    candle_timestamps.append(candle_end_time)
                else:
                    # Try to use index as timestamp
                    try:
                        candle_end_time = ohlcv_df.index[-i]
                        candle_start_time_ts = ohlcv_df.index[-(i+1)] if i+1 < len(ohlcv_df) else candle_end_time - pd.Timedelta(minutes=1)
                        self.logger.debug(f"Candle {i} timestamp from index: start={candle_start_time_ts}, end={candle_end_time}")
                        # Save the timestamp for potential interpolation later
                        candle_timestamps.append(candle_end_time)
                    except Exception as e:
                        self.logger.debug(f"Failed to get timestamp from index: {str(e)}")
                        continue
                
                # Ensure start_time and end_time are numeric
                try:
                    # Convert pandas Timestamp to milliseconds since epoch
                    if isinstance(candle_start_time_ts, pd.Timestamp):
                        start_time_orig = candle_start_time_ts
                        candle_start_time_ts = int(candle_start_time_ts.timestamp() * 1000)
                        self.logger.debug(f"Converted start_time from pd.Timestamp {start_time_orig} to {candle_start_time_ts}")
                    elif isinstance(candle_start_time_ts, str):
                        start_time_orig = candle_start_time_ts
                        candle_start_time_ts = pd.to_numeric(candle_start_time_ts)
                        self.logger.debug(f"Converted start_time from string {start_time_orig} to {candle_start_time_ts}")
                    
                    if isinstance(candle_end_time, pd.Timestamp):
                        end_time_orig = candle_end_time
                        candle_end_time = int(candle_end_time.timestamp() * 1000)
                        self.logger.debug(f"Converted end_time from pd.Timestamp {end_time_orig} to {candle_end_time}")
                    elif isinstance(candle_end_time, str):
                        end_time_orig = candle_end_time
                        candle_end_time = pd.to_numeric(candle_end_time)
                        self.logger.debug(f"Converted end_time from string {end_time_orig} to {candle_end_time}")
                except Exception as e:
                    self.logger.debug(f"Failed to convert timestamp to numeric: {str(e)}")
                    continue
                
                # Filter trades for this candle
                candle_trades_filtered = trades_df[(trades_df['time'] >= candle_start_time_ts) & (trades_df['time'] < candle_end_time)]
                
                if candle_trades_filtered.empty:
                    self.logger.debug(f"No trades found for candle {i} (time range: {candle_start_time_ts} to {candle_end_time})")
                    candle_cvds.append(0)
                    continue
                
                # Create a copy to avoid SettingWithCopyWarning
                candle_trades = candle_trades_filtered.copy()
                
                self.logger.debug(f"Found {len(candle_trades)} trades for candle {i}")
                    
                # Calculate CVD for this candle
                try:
                    # Log the unique side values to aid in debugging
                    unique_sides = candle_trades['side'].astype(str).unique()
                    self.logger.debug(f"Unique side values in candle {i} trades: {unique_sides}")
                    
                    # Ensure amount column is numeric
                    try:
                        candle_trades.loc[:, 'amount'] = pd.to_numeric(candle_trades['amount'], errors='coerce')
                    except Exception as e:
                        self.logger.warning(f"Error converting amount to numeric: {str(e)}, trying fallback")
                        candle_trades.loc[:, 'amount'] = candle_trades['amount'].apply(lambda x: float(x) if isinstance(x, str) else x)
                    
                    # More robust way to determine buy/sell sides
                    def is_buy_side(side_val):
                        if pd.isna(side_val):
                            return False
                        s = str(side_val).lower().strip()
                        return s in ['buy', 'b', '1', 'true', 'bid', 'long']
                    
                    def is_sell_side(side_val):
                        if pd.isna(side_val):
                            return False
                        s = str(side_val).lower().strip()
                        return s in ['sell', 's', '-1', 'false', 'ask', 'short']
                    
                    # Apply the side detection functions
                    candle_trades.loc[:, 'is_buy'] = candle_trades['side'].apply(is_buy_side)
                    candle_trades.loc[:, 'is_sell'] = candle_trades['side'].apply(is_sell_side)
                    
                    # Log side detection results
                    buy_count = candle_trades['is_buy'].sum()
                    sell_count = candle_trades['is_sell'].sum()
                    unclassified = len(candle_trades) - buy_count - sell_count
                    self.logger.debug(f"Side classification: buy={buy_count}, sell={sell_count}, unclassified={unclassified}")
                    
                    if unclassified > 0 and len(unique_sides) > 0:
                        # If we have unclassified trades, try a more flexible approach
                        if all(side.lower() in ['buy', 'sell'] for side in unique_sides if isinstance(side, str)):
                            self.logger.debug(f"Using simpler case-insensitive matching for side values")
                            candle_trades.loc[:, 'is_buy'] = candle_trades['side'].astype(str).str.lower() == 'buy'
                            candle_trades.loc[:, 'is_sell'] = candle_trades['side'].astype(str).str.lower() == 'sell'
                            buy_count = candle_trades['is_buy'].sum()
                            sell_count = candle_trades['is_sell'].sum()
                            unclassified = len(candle_trades) - buy_count - sell_count
                            self.logger.debug(f"Updated side classification: buy={buy_count}, sell={sell_count}, unclassified={unclassified}")
                    
                    # Check for any remaining unclassified trades
                    if unclassified > 0 and buy_count == 0 and sell_count == 0:
                        # Last resort attempt - case-insensitive partial matching
                        self.logger.debug(f"Attempting case-insensitive partial matching for sides")
                        candle_trades.loc[:, 'is_buy'] = candle_trades['side'].astype(str).str.lower().str.contains('buy', na=False) | candle_trades['side'].astype(str).str.lower().str.contains('bid', na=False)
                        candle_trades.loc[:, 'is_sell'] = candle_trades['side'].astype(str).str.lower().str.contains('sell', na=False) | candle_trades['side'].astype(str).str.lower().str.contains('ask', na=False)
                        buy_count = candle_trades['is_buy'].sum()
                        sell_count = candle_trades['is_sell'].sum()
                        self.logger.debug(f"Final side classification: buy={buy_count}, sell={sell_count}, unclassified={len(candle_trades) - buy_count - sell_count}")
                    
                    # Calculate buy and sell volumes
                    buy_volume = candle_trades[candle_trades['is_buy']]['amount'].sum()
                    sell_volume = candle_trades[candle_trades['is_sell']]['amount'].sum()
                    
                    # Replace NaN with 0
                    buy_volume = 0.0 if pd.isna(buy_volume) else float(buy_volume)
                    sell_volume = 0.0 if pd.isna(sell_volume) else float(sell_volume)
                    
                    # Additional diagnostic for debugging
                    if buy_volume == 0 and sell_volume == 0:
                        # This shouldn't happen if we have trades and properly classified sides
                        # Log a sample of the trades to diagnose the issue
                        if not candle_trades.empty:
                            sample_trades = candle_trades.head(3)
                            self.logger.warning(f"Both buy and sell volumes are 0 despite having {len(candle_trades)} trades. Sample trades:")
                            for idx, trade in sample_trades.iterrows():
                                self.logger.warning(f"Trade {idx}: side={trade['side']}, amount={trade['amount']}, is_buy={trade.get('is_buy', False)}, is_sell={trade.get('is_sell', False)}")
                            
                            # Check for data quality issues
                            amounts = candle_trades['amount'].tolist()
                            amount_stats = {
                                'min': candle_trades['amount'].min() if not candle_trades['amount'].empty else 'N/A',
                                'max': candle_trades['amount'].max() if not candle_trades['amount'].empty else 'N/A',
                                'mean': candle_trades['amount'].mean() if not candle_trades['amount'].empty else 'N/A',
                                'nan_count': candle_trades['amount'].isna().sum(),
                                'zero_count': (candle_trades['amount'] == 0).sum()
                            }
                            self.logger.warning(f"Amount stats: {amount_stats}")
                    
                    self.logger.debug(f"Candle {i} CVD calculation: buy_volume={buy_volume:.4f}, sell_volume={sell_volume:.4f}, types: {type(buy_volume)}, {type(sell_volume)}")
                    
                    candle_cvd = buy_volume - sell_volume
                    candle_cvds.append(candle_cvd)
                    self.logger.debug(f"Candle {i} CVD: {candle_cvd:.4f}")
                except Exception as e:
                    self.logger.warning(f"Error calculating candle {i} CVD: {str(e)}, using 0 instead")
                    # Log more details about the error for debugging
                    import traceback
                    self.logger.debug(f"Error details: {traceback.format_exc()}")
                    
                    # Try to get information about the candle_trades DataFrame
                    try:
                        if 'candle_trades' in locals() and not candle_trades.empty:
                            self.logger.debug(f"Candle trades info: shape={candle_trades.shape}, columns={list(candle_trades.columns)}")
                            self.logger.debug(f"Sample trades: {candle_trades.head(2).to_dict('records')}")
                            self.logger.debug(f"Side values: {candle_trades['side'].value_counts().to_dict()}")
                    except Exception as inner_e:
                        self.logger.debug(f"Failed to log candle trades information: {str(inner_e)}")
                    
                    candle_cvds.append(0)
            
            # Check if we have enough candle CVD values
            if len(candle_cvds) < 2:
                self.logger.warning(f"Insufficient candle CVD data: {len(candle_cvds)} values")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Interpolate for candles without trades if enabled
            if getattr(self, 'interpolate_missing_cvd', True) and 0 in candle_cvds:
                self.logger.debug("Interpolating CVD values for candles without trades")
                # Create a series with timestamps and CVD values
                cvd_series = pd.Series(candle_cvds, index=candle_timestamps[:len(candle_cvds)])
                
                # Find indices of non-zero values
                non_zero_indices = [i for i, cvd in enumerate(candle_cvds) if cvd != 0]
                if not non_zero_indices:
                    self.logger.debug("No non-zero CVD values found for interpolation")
                else:
                    self.logger.debug(f"Found {len(non_zero_indices)} non-zero values at indices: {non_zero_indices}")
                    
                    # Handle zeros before first non-zero (backfill)
                    first_non_zero_idx = non_zero_indices[0]
                    first_non_zero_val = candle_cvds[first_non_zero_idx]
                    if first_non_zero_idx > 0:
                        self.logger.debug(f"Backfilling {first_non_zero_idx} initial zeros before first value {first_non_zero_val}")
                        for j in range(0, first_non_zero_idx):
                            # Use a linear ramp up to the first value
                            candle_cvds[j] = first_non_zero_val * (j + 1) / (first_non_zero_idx + 1)
                    
                    # Handle zeros between non-zero values (interpolation)
                    for idx_pos in range(len(non_zero_indices) - 1):
                        start_idx = non_zero_indices[idx_pos]
                        end_idx = non_zero_indices[idx_pos + 1]
                        start_val = candle_cvds[start_idx]
                        end_val = candle_cvds[end_idx]
                        
                        if end_idx - start_idx > 1:  # If there are zeros between
                            self.logger.debug(f"Interpolating between index {start_idx} ({start_val}) and {end_idx} ({end_val})")
                            for j in range(start_idx + 1, end_idx):
                                # Linear interpolation
                                ratio = (j - start_idx) / (end_idx - start_idx)
                                candle_cvds[j] = start_val + (end_val - start_val) * ratio
                    
                    # Handle zeros after last non-zero (extrapolation)
                    last_non_zero_idx = non_zero_indices[-1]
                    last_non_zero_val = candle_cvds[last_non_zero_idx]
                    
                    if last_non_zero_idx < len(candle_cvds) - 1:
                        # Calculate trend from available non-zero values
                        if len(non_zero_indices) >= 2:
                            # Use the last two non-zero values to determine trend
                            prev_idx = non_zero_indices[-2]
                            prev_val = candle_cvds[prev_idx]
                            last_idx = non_zero_indices[-1]
                            last_val = candle_cvds[last_idx]
                            
                            # Calculate slope (per candle)
                            trend_slope = (last_val - prev_val) / (last_idx - prev_idx)
                            self.logger.debug(f"Extrapolating with slope {trend_slope:.4f} based on last values {prev_val:.4f} and {last_val:.4f}")
                            
                            # Apply diminishing trend after last value (decay factor reduces impact over time)
                            decay_factor = 0.8  # Reduce impact by 20% each candle
                            for j in range(last_non_zero_idx + 1, len(candle_cvds)):
                                steps = j - last_non_zero_idx
                                # Calculate diminishing effect with distance
                                decay = decay_factor ** steps
                                extrapolated_val = last_non_zero_val + (trend_slope * steps * decay)
                                candle_cvds[j] = extrapolated_val
                        else:
                            # Only one non-zero value, use decay from that value
                            self.logger.debug(f"Only one non-zero value ({last_non_zero_val:.4f}), using decay extrapolation")
                            decay_factor = 0.7  # Stronger decay when we have less information
                            for j in range(last_non_zero_idx + 1, len(candle_cvds)):
                                steps = j - last_non_zero_idx
                                # Apply decay from last known value
                                candle_cvds[j] = last_non_zero_val * (decay_factor ** steps)
                        
                        self.logger.debug(f"Extrapolated {len(candle_cvds) - last_non_zero_idx - 1} values after last non-zero value")
                
                zero_count = candle_cvds.count(0)
                self.logger.debug(f"After interpolation, zero values remaining: {zero_count}")
                if zero_count > 0:
                    zero_indices = [i for i, val in enumerate(candle_cvds) if val == 0]
                    self.logger.debug(f"Remaining zeros at indices: {zero_indices}")
                    # Last attempt to fill any remaining zeros with small random values
                    for idx in zero_indices:
                        # Use a small percentage of the max absolute CVD as a fallback
                        max_abs_cvd = max(abs(cvd) for cvd in candle_cvds if cvd != 0) if any(cvd != 0 for cvd in candle_cvds) else 1.0
                        candle_cvds[idx] = max_abs_cvd * 0.01  # 1% of max as fallback
            
            self.logger.debug(f"Calculated CVD for {len(candle_cvds)} candles")
            self.logger.debug(f"Candle CVDs: min={min(candle_cvds):.4f}, max={max(candle_cvds):.4f}, mean={sum(candle_cvds)/len(candle_cvds):.4f}")
            
            # Apply time weighting if enabled
            weighted_candle_cvds = []
            if self.time_weighting_enabled:
                self.logger.debug(f"Applying time weighting with recency factor {self.recency_factor}")
                for i, cvd in enumerate(candle_cvds):
                    # Apply exponential weighting - more recent candles get higher weight
                    # i=0 is the most recent candle
                    weight = self.recency_factor ** (len(candle_cvds) - 1 - i)
                    weighted_candle_cvds.append(cvd * weight)
                    self.logger.debug(f"Candle {i} CVD: {cvd:.2f}, Weight: {weight:.2f}, Weighted: {cvd * weight:.2f}")
            else:
                self.logger.debug("Time weighting disabled, using raw CVD values")
                weighted_candle_cvds = candle_cvds
            
            # Calculate CVD trend with time weighting
            cvd_trend = sum(weighted_candle_cvds)
            
            # For normalization, we need the sum of absolute weighted values
            abs_sum = sum(abs(c) for c in weighted_candle_cvds)
            
            self.logger.debug(f"CVD trend: {cvd_trend:.4f}, Absolute sum: {abs_sum:.4f}")
            
            # Calculate divergence
            divergence_strength = 0.0
            divergence_type = 'neutral'
            
            if (price_trend > 0 and cvd_trend < 0):
                # Bearish divergence: Price up, CVD down
                divergence_type = 'bearish'
                divergence_strength = min(abs(cvd_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bearish divergence: Price trend={price_trend:.4f} (up), CVD trend={cvd_trend:.4f} (down)")
            elif (price_trend < 0 and cvd_trend > 0):
                # Bullish divergence: Price down, CVD up
                divergence_type = 'bullish'
                divergence_strength = min(abs(cvd_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bullish divergence: Price trend={price_trend:.4f} (down), CVD trend={cvd_trend:.4f} (up)")
            else:
                self.logger.debug(f"No divergence detected: Price trend={price_trend:.4f}, CVD trend={cvd_trend:.4f}")
            
            # Only return significant divergences
            if divergence_strength < self.divergence_strength_threshold:
                self.logger.debug(f"Divergence strength {divergence_strength:.2f} below threshold {self.divergence_strength_threshold}, returning neutral")
                
                # Log execution time
                calculation_end_time = time.time()
                execution_time = calculation_end_time - calculation_start_time
                self.logger.debug(f"Price-CVD divergence calculation completed in {execution_time:.4f} seconds")
                self.logger.debug("=" * 50)
                
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.info(f"Price-CVD divergence: {divergence_type}, strength: {divergence_strength:.2f}")
            
            # Fix time tracking for candle processing
            candle_processing_end_time = time.time()
            candle_processing_time = candle_processing_end_time - candle_start_time
            self.logger.debug(f"Processed {lookback} candles in {candle_processing_time:.4f} seconds")
            
            # Calculate the final execution time
            calculation_end_time = time.time()
            execution_time = calculation_end_time - calculation_start_time
            self.logger.debug(f"Price-CVD divergence calculation completed in {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            result = {
                'type': divergence_type,
                'strength': float(divergence_strength)
            }
            
            # Store in cache before returning
            self._cache[cache_key] = result
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating price-CVD divergence: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # Calculate the final execution time
            calculation_end_time = time.time()
            execution_time = calculation_end_time - calculation_start_time
            self.logger.debug(f"Price-CVD divergence calculation failed after {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            return {'type': 'neutral', 'strength': 0.0}

    def _calculate_price_oi_divergence(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate divergence between price and open interest.
        
        This method detects when price is moving in one direction but open interest is moving in the opposite direction,
        which can indicate potential reversals.
        
        Args:
            market_data: Dictionary containing market data with OHLCV and open interest data
            
        Returns:
            Dict: Divergence information including type and strength
        """
        # Use caching to avoid redundant calculations
        cache_key = 'price_oi_divergence'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        # Enhanced debugging: Log market_data top-level keys
        self.logger.debug(f"OI-PRICE DIVERGENCE: Market data keys: {list(market_data.keys())}")
        
        # Check if open interest data is available before proceeding
        if ('open_interest' not in market_data and 
            ('sentiment' not in market_data or 'open_interest' not in market_data.get('sentiment', {}))):
            self.logger.warning("Missing open interest data for price-OI divergence calculation")
            
            # Enhanced debugging: More details about the structure if data is missing
            if 'sentiment' in market_data:
                self.logger.debug(f"OI-PRICE DIVERGENCE: Sentiment keys available: {list(market_data['sentiment'].keys())}")
            if 'open_interest' in market_data:
                self.logger.debug(f"OI-PRICE DIVERGENCE: Open interest appears empty or malformed: {market_data['open_interest']}")
                
            return {'type': 'neutral', 'strength': 0.0}
            
        start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING PRICE-OI DIVERGENCE CALCULATION")
        self.logger.debug("=" * 50)
        
        # Enhanced debugging: Dump full structure of open interest data if available
        if 'open_interest' in market_data:
            oi_dump = market_data['open_interest']
            if isinstance(oi_dump, dict):
                self.logger.debug(f"OI-PRICE DIVERGENCE: Full OI structure: {json.dumps(oi_dump, default=str)}")
            else:
                self.logger.debug(f"OI-PRICE DIVERGENCE: OI not a dictionary: {type(oi_dump)}")
        
        try:
            # Check if we have the required data
            if 'ohlcv' not in market_data:
                self.logger.warning("Missing OHLCV data for price-OI divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            ohlcv_data = market_data['ohlcv']
            
            # Check if ohlcv_data is a dictionary
            if not isinstance(ohlcv_data, dict):
                self.logger.warning(f"OHLCV data is not a dictionary: {type(ohlcv_data)}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log available timeframes
            self.logger.debug(f"Available OHLCV timeframes: {list(ohlcv_data.keys())}")
                
            # Try to find a valid timeframe
            valid_timeframe = None
            ohlcv_df = None
            
            # First check for direct DataFrame access (for backward compatibility)
            for tf in ['base', 'ltf', '1', '5']:
                if tf in ohlcv_data:
                    # Check if it's a direct DataFrame
                    if isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
                    # Check if it's a nested structure with 'data' key
                    elif isinstance(ohlcv_data[tf], dict) and 'data' in ohlcv_data[tf] and isinstance(ohlcv_data[tf]['data'], pd.DataFrame) and not ohlcv_data[tf]['data'].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]['data']
                        self.logger.debug(f"Found nested DataFrame at timeframe {tf}['data']")
                        break
            
            # Also check for timeframes with '_direct' suffix (added for testing)
            if not valid_timeframe:
                for tf in ['base_direct', 'ltf_direct', '1_direct', '5_direct']:
                    if tf in ohlcv_data and isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
            
            if not valid_timeframe or ohlcv_df is None:
                self.logger.warning("No valid OHLCV timeframe found for price-OI divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Verify that the DataFrame has the required columns
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in ohlcv_df.columns]
            if missing_columns:
                self.logger.warning(f"OHLCV data missing required columns: {missing_columns}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log OHLCV DataFrame info
            self.logger.debug(f"OHLCV DataFrame for {valid_timeframe}: shape={ohlcv_df.shape}, columns={list(ohlcv_df.columns)}")
            self.logger.debug(f"OHLCV DataFrame index type: {type(ohlcv_df.index)}")
            if len(ohlcv_df) > 0:
                self.logger.debug(f"OHLCV first row: {ohlcv_df.iloc[0].to_dict()}")
                self.logger.debug(f"OHLCV last row: {ohlcv_df.iloc[-1].to_dict()}")
                
            # Use configurable lookback period
            lookback = min(len(ohlcv_df), self.divergence_lookback)
            if lookback < 2:
                self.logger.warning(f"Insufficient OHLCV data for divergence calculation: {len(ohlcv_df)} rows")
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.debug(f"Using lookback period of {lookback} candles for divergence calculation")
            
            # Check if we have open interest data at the top level
            oi_data = None
            oi_history = []
            
            # First check for open interest at the top level (new structure)
            if 'open_interest' in market_data:
                oi_data = market_data['open_interest']
                self.logger.debug("Found open interest data at top level")
                if isinstance(oi_data, dict):
                    self.logger.debug(f"Open interest data keys: {list(oi_data.keys())}")
            # Fallback to sentiment.open_interest for backward compatibility
            elif 'sentiment' in market_data and 'open_interest' in market_data['sentiment']:
                oi_data = market_data['sentiment']['open_interest']
                self.logger.debug("Found open interest data in sentiment section")
                if isinstance(oi_data, dict):
                    self.logger.debug(f"Open interest data keys: {list(oi_data.keys())}")
            else:
                self.logger.warning("Missing open interest data for price-OI divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Get open interest history
            if isinstance(oi_data, dict) and 'history' in oi_data and isinstance(oi_data['history'], list):
                oi_history = oi_data['history']
                self.logger.debug(f"Using open interest history from 'history' key with {len(oi_history)} entries")
                # Enhanced debugging: Sample of history data
                if len(oi_history) > 0:
                    self.logger.debug(f"OI-PRICE DIVERGENCE: First history entry: {json.dumps(oi_history[0], default=str)}")
                    if len(oi_history) > 1:
                        self.logger.debug(f"OI-PRICE DIVERGENCE: Second history entry: {json.dumps(oi_history[1], default=str)}")
            elif isinstance(oi_data, list):
                # If OI data is already a list
                oi_history = oi_data
                self.logger.debug(f"Using open interest data directly as list with {len(oi_history)} entries")
            else:
                # Enhanced debugging: Log what was found in the structure
                self.logger.warning(f"OI-PRICE DIVERGENCE: No proper history found. OI data type: {type(oi_data)}")
                if isinstance(oi_data, dict):
                    self.logger.warning(f"OI-PRICE DIVERGENCE: OI data keys: {list(oi_data.keys())}")
                # If we don't have history, we can't calculate divergence
                self.logger.warning("No open interest history available for divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            if len(oi_history) < 2:
                self.logger.warning(f"Insufficient open interest history for divergence calculation: {len(oi_history)} entries")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Log sample of OI history
            if len(oi_history) > 0:
                sample_entry = oi_history[0]
                self.logger.debug(f"OI history sample entry: {sample_entry}")
                if isinstance(sample_entry, dict):
                    self.logger.debug(f"OI history entry keys: {list(sample_entry.keys())}")
            
            # Get timestamps for alignment
            # Check if we have a timestamp column or need to use the index
            if 'timestamp' in ohlcv_df.columns:
                start_timestamp = ohlcv_df.iloc[-lookback]['timestamp']
                self.logger.debug(f"Using timestamp column for alignment, start_timestamp: {start_timestamp}")
            else:
                # Try to use index as timestamp
                try:
                    start_timestamp = ohlcv_df.index[-lookback]
                    self.logger.debug(f"Using index for alignment, start_timestamp: {start_timestamp}")
                except Exception as e:
                    self.logger.warning(f"Failed to get start timestamp from OHLCV data: {str(e)}")
                    return {'type': 'neutral', 'strength': 0.0}
            
            # Ensure start_timestamp is numeric
            try:
                # Convert pandas Timestamp to milliseconds since epoch
                if isinstance(start_timestamp, pd.Timestamp):
                    start_timestamp_orig = start_timestamp
                    start_timestamp = int(start_timestamp.timestamp() * 1000)
                    self.logger.debug(f"Converted start_timestamp from pd.Timestamp {start_timestamp_orig} to {start_timestamp}")
                elif isinstance(start_timestamp, str):
                    start_timestamp_orig = start_timestamp
                    start_timestamp = pd.to_numeric(start_timestamp)
                    self.logger.debug(f"Converted start_timestamp from string {start_timestamp_orig} to {start_timestamp}")
            except Exception as e:
                self.logger.warning(f"Failed to convert start_timestamp to numeric: {str(e)}")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Filter OI history to match the same time period as price data
            aligned_oi_values = []
            aligned_timestamps = []
            
            self.logger.debug(f"Aligning OI history with price data, start_timestamp: {start_timestamp}")
            
            for entry in oi_history:
                entry_timestamp = entry['timestamp'] if isinstance(entry, dict) and 'timestamp' in entry else None
                
                # Ensure entry_timestamp is numeric for comparison
                try:
                    if entry_timestamp is not None:
                        entry_timestamp = pd.to_numeric(entry_timestamp) if isinstance(entry_timestamp, (str, pd.Timestamp)) else entry_timestamp
                        
                        if entry_timestamp >= start_timestamp:
                            entry_value = float(entry['value']) if isinstance(entry, dict) and 'value' in entry else float(entry)
                            aligned_oi_values.append(entry_value)
                            aligned_timestamps.append(entry_timestamp)
                except Exception as e:
                    self.logger.debug(f"Failed to process OI entry timestamp: {str(e)}")
                    continue
            
            # Continue with aligned OI values
            if len(aligned_oi_values) < 2:
                self.logger.warning(f"Insufficient aligned OI data for divergence calculation: {len(aligned_oi_values)} entries")
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.debug(f"Successfully aligned {len(aligned_oi_values)} OI entries with price data")
            self.logger.debug(f"Aligned OI values: min={min(aligned_oi_values):.2f}, max={max(aligned_oi_values):.2f}, mean={sum(aligned_oi_values)/len(aligned_oi_values):.2f}")
            
            # Calculate price trend
            price_changes = ohlcv_df['close'].diff().tail(lookback)
            price_trend = price_changes.sum()
            
            self.logger.debug(f"Price trend over {lookback} candles: {price_trend:.4f}")
            self.logger.debug(f"Price changes: min={price_changes.min():.4f}, max={price_changes.max():.4f}, mean={price_changes.mean():.4f}")
            
            # Calculate OI changes
            oi_changes = [aligned_oi_values[i] - aligned_oi_values[i-1] for i in range(1, len(aligned_oi_values))]
            
            self.logger.debug(f"OI changes: {len(oi_changes)} entries")
            self.logger.debug(f"OI changes: min={min(oi_changes):.2f}, max={max(oi_changes):.2f}, mean={sum(oi_changes)/len(oi_changes):.2f}")
            
            # Enhanced debugging: Detailed OI change data
            self.logger.debug("OI-PRICE DIVERGENCE: Detailed OI changes:")
            for i, change in enumerate(oi_changes):
                self.logger.debug(f"  Entry {i}: Value: {aligned_oi_values[i]:.2f}, Previous: {aligned_oi_values[i-1]:.2f}, Change: {change:.2f}")
            
            # Apply time weighting if enabled
            weighted_oi_changes = []
            if self.time_weighting_enabled:
                self.logger.debug(f"Applying time weighting with recency factor {self.recency_factor}")
                for i, change in enumerate(oi_changes):
                    # Apply exponential weighting - more recent changes get higher weight
                    weight = self.recency_factor ** (len(oi_changes) - 1 - i)
                    weighted_oi_changes.append(change * weight)
                    self.logger.debug(f"OI Change {i}: {change:.2f}, Weight: {weight:.2f}, Weighted: {change * weight:.2f}")
            else:
                self.logger.debug("Time weighting disabled, using raw OI changes")
                weighted_oi_changes = oi_changes
            
            # Calculate OI trend with time weighting
            oi_trend = sum(weighted_oi_changes)
            
            # For normalization, we need the sum of absolute weighted values
            abs_sum = sum(abs(c) for c in weighted_oi_changes)
            
            self.logger.debug(f"OI trend: {oi_trend:.4f}, Absolute sum: {abs_sum:.4f}")
            
            # Calculate divergence
            divergence_strength = 0.0
            divergence_type = 'neutral'
            
            # Enhanced debugging: Detailed comparison
            self.logger.debug(f"OI-PRICE DIVERGENCE: Final comparison - Price trend: {price_trend:.4f}, OI trend: {oi_trend:.4f}")
            
            if (price_trend > 0 and oi_trend < 0):
                # Bearish divergence: Price up, OI down
                divergence_type = 'bearish'
                divergence_strength = min(abs(oi_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bearish divergence: Price trend={price_trend:.4f} (up), OI trend={oi_trend:.4f} (down)")
                # Enhanced debugging: Strength calculation
                self.logger.debug(f"OI-PRICE DIVERGENCE: Bearish strength calculation: |{oi_trend:.4f}| / max(1, {abs_sum:.4f}) * 100 = {divergence_strength:.2f}")
            elif (price_trend < 0 and oi_trend > 0):
                # Bullish divergence: Price down, OI up
                divergence_type = 'bullish'
                divergence_strength = min(abs(oi_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bullish divergence: Price trend={price_trend:.4f} (down), OI trend={oi_trend:.4f} (up)")
                # Enhanced debugging: Strength calculation
                self.logger.debug(f"OI-PRICE DIVERGENCE: Bullish strength calculation: |{oi_trend:.4f}| / max(1, {abs_sum:.4f}) * 100 = {divergence_strength:.2f}")
            else:
                self.logger.debug(f"No divergence detected: Price trend={price_trend:.4f}, OI trend={oi_trend:.4f}")
                # Enhanced debugging: Why no divergence was detected
                if price_trend > 0 and oi_trend >= 0:
                    self.logger.debug("OI-PRICE DIVERGENCE: Both price and OI trending up (no divergence)")
                elif price_trend < 0 and oi_trend <= 0:
                    self.logger.debug("OI-PRICE DIVERGENCE: Both price and OI trending down (no divergence)")
                elif price_trend == 0:
                    self.logger.debug("OI-PRICE DIVERGENCE: No price trend detected")
                elif oi_trend == 0:
                    self.logger.debug("OI-PRICE DIVERGENCE: No OI trend detected")
            
            # Only return significant divergences
            if divergence_strength < self.divergence_strength_threshold:
                self.logger.debug(f"Divergence strength {divergence_strength:.2f} below threshold {self.divergence_strength_threshold}, returning neutral")
                
                # Log execution time
                execution_time = time.time() - start_time
                self.logger.debug(f"Price-OI divergence calculation completed in {execution_time:.4f} seconds")
                self.logger.debug("=" * 50)
                
                return {'type': 'neutral', 'strength': 0.0}
                
            self.logger.info(f"Price-OI divergence: {divergence_type}, strength: {divergence_strength:.2f}")
            
            # Log execution time
            execution_time = time.time() - start_time
            self.logger.debug(f"Price-OI divergence calculation completed in {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            result = {
                'type': divergence_type,
                'strength': float(divergence_strength)
            }
            
            # Store in cache before returning
            self._cache[cache_key] = result
            return result
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error calculating price-OI divergence: {str(e)}")
            self.logger.error(f"OI-PRICE DIVERGENCE Error traceback: {traceback.format_exc()}")
            
            # Log market data structure for debugging
            try:
                if 'open_interest' in market_data:
                    self.logger.error(f"OI-PRICE DIVERGENCE: Error with OI structure: {json.dumps(market_data['open_interest'], default=str)}")
                self.logger.error(f"OI-PRICE DIVERGENCE: Market data keys: {list(market_data.keys())}")
            except Exception as json_err:
                self.logger.error(f"OI-PRICE DIVERGENCE: Could not log market data structure due to error: {str(json_err)}")
                
            # Log execution time even in error case
            execution_time = time.time() - start_time if 'start_time' in locals() else -1
            self.logger.debug(f"Price-OI divergence calculation failed in {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            return {'type': 'neutral', 'strength': 0.0}

    def _calculate_trade_flow(self, trades_df: Union[pd.DataFrame, Dict, List]) -> float:
        """Calculate trade flow indicator (buy vs sell pressure).
        
        Args:
            trades_df: DataFrame, dictionary or list containing trade data
            
        Returns:
            float: Trade flow value between -1 and 1
        """
        start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING TRADE FLOW CALCULATION")
        self.logger.debug("=" * 50)
        
        try:
            # Initialize variables
            df = None
            
            # Log input data type
            self.logger.debug(f"Input trades_df type: {type(trades_df)}")
            
            # Handle different input types
            if isinstance(trades_df, pd.DataFrame):
                # Input is already a DataFrame
                df = trades_df.copy()
                self.logger.debug(f"Using trades DataFrame directly, shape: {df.shape}, columns: {list(df.columns)}")
            
            elif isinstance(trades_df, list) and trades_df:
                # Input is a list of trade dictionaries
                try:
                    self.logger.debug(f"Input is a list with {len(trades_df)} trade records")
                    if len(trades_df) > 0:
                        self.logger.debug(f"First trade sample: {trades_df[0]}")
                    df = pd.DataFrame(trades_df)
                    self.logger.debug(f"Converted trades list to DataFrame with {len(trades_df)} records, columns: {list(df.columns)}")
                except Exception as e:
                    self.logger.error(f"Failed to convert trades list to DataFrame: {e}")
                    self.logger.debug(traceback.format_exc())
                    return 0.0
            
            elif isinstance(trades_df, dict):
                # Input is a dictionary, try to find trades data
                self.logger.debug(f"Input is a dictionary with keys: {list(trades_df.keys())}")
                
                if 'trades_df' in trades_df and isinstance(trades_df['trades_df'], pd.DataFrame):
                    df = trades_df['trades_df'].copy()
                    self.logger.debug(f"Using trades_df from dictionary, shape: {df.shape}, columns: {list(df.columns)}")
                
                elif 'trades' in trades_df and isinstance(trades_df['trades'], list) and trades_df['trades']:
                    try:
                        self.logger.debug(f"Using trades list from dictionary with {len(trades_df['trades'])} records")
                        if len(trades_df['trades']) > 0:
                            self.logger.debug(f"First trade sample: {trades_df['trades'][0]}")
                        df = pd.DataFrame(trades_df['trades'])
                        self.logger.debug(f"Converted trades list from dictionary to DataFrame, shape: {df.shape}, columns: {list(df.columns)}")
                    except Exception as e:
                        self.logger.error(f"Failed to convert trades list from dictionary to DataFrame: {e}")
                        self.logger.debug(traceback.format_exc())
                        return 0.0
                
                elif 'processed_trades' in trades_df and isinstance(trades_df['processed_trades'], list) and trades_df['processed_trades']:
                    try:
                        self.logger.debug(f"Using processed_trades from dictionary with {len(trades_df['processed_trades'])} records")
                        if len(trades_df['processed_trades']) > 0:
                            self.logger.debug(f"First processed trade sample: {trades_df['processed_trades'][0]}")
                        df = pd.DataFrame(trades_df['processed_trades'])
                        self.logger.debug(f"Converted processed_trades to DataFrame, shape: {df.shape}, columns: {list(df.columns)}")
                    except Exception as e:
                        self.logger.error(f"Failed to convert processed_trades to DataFrame: {e}")
                        self.logger.debug(traceback.format_exc())
                        return 0.0
                
                else:
                    self.logger.warning("No valid trade data found in dictionary")
                    return 0.0
            
            else:
                self.logger.error(f"Unsupported trades_df type: {type(trades_df)}")
                return 0.0
            
            # Check if we have a valid DataFrame
            if df is None or df.empty:
                self.logger.warning("No trade data available for trade flow calculation")
                return 0.0
            
            # Log DataFrame info
            self.logger.debug(f"Trade DataFrame info: {len(df)} rows, columns: {list(df.columns)}")
            
            # Map column names to standard names
            column_mappings = {
                'side': ['side', 'S', 'type', 'trade_type'],
                'amount': ['amount', 'size', 'v', 'volume', 'qty', 'quantity']
            }
            
            # Try to find and map the required columns
            for std_col, possible_cols in column_mappings.items():
                if std_col not in df.columns:
                    for col in possible_cols:
                        if col in df.columns:
                            df[std_col] = df[col]
                            self.logger.debug(f"Mapped '{col}' to '{std_col}'")
                            break
            
            # Check if we have the required columns after mapping
            if 'side' not in df.columns or 'amount' not in df.columns:
                missing = []
                if 'side' not in df.columns:
                    missing.append('side')
                if 'amount' not in df.columns:
                    missing.append('amount')
                self.logger.warning(f"Missing required columns after mapping: {missing}. Available columns: {list(df.columns)}")
                return 0.0
            
            # Normalize side values
            try:
                # Convert to string first to handle numeric side values
                df['side'] = df['side'].astype(str)
                self.logger.debug(f"Side value counts before normalization: {df['side'].value_counts().to_dict()}")
                
                # Ensure amount column is numeric
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                
                # Log amount statistics before dropping NaN values
                amount_stats_before = {
                    'count': len(df),
                    'nan_count': df['amount'].isna().sum(),
                    'min': df['amount'].min() if not df['amount'].isna().all() else 'N/A',
                    'max': df['amount'].max() if not df['amount'].isna().all() else 'N/A',
                    'mean': df['amount'].mean() if not df['amount'].isna().all() else 'N/A',
                    'sum': df['amount'].sum() if not df['amount'].isna().all() else 'N/A'
                }
                self.logger.debug(f"Amount statistics before dropping NaN: {amount_stats_before}")
                
                # Drop rows with non-numeric amounts
                df = df.dropna(subset=['amount'])
                
                # Log amount statistics after dropping NaN values
                amount_stats_after = {
                    'count': len(df),
                    'min': df['amount'].min() if not df.empty else 'N/A',
                    'max': df['amount'].max() if not df.empty else 'N/A',
                    'mean': df['amount'].mean() if not df.empty else 'N/A',
                    'sum': df['amount'].sum() if not df.empty else 'N/A'
                }
                self.logger.debug(f"Amount statistics after dropping NaN: {amount_stats_after}")
                
                # Normalize to lowercase
                df['side'] = df['side'].str.lower()
                
                # Map different side values to buy/sell
                buy_values = ['buy', 'b', 'bid', '1', 'true', 'long']
                sell_values = ['sell', 's', 'ask', 'offer', '-1', 'false', 'short']
                
                # Create a normalized side column
                df['norm_side'] = 'unknown'
                df.loc[df['side'].isin(buy_values), 'norm_side'] = 'buy'
                df.loc[df['side'].isin(sell_values), 'norm_side'] = 'sell'
                
                # Log normalized side value counts
                norm_side_counts = df['norm_side'].value_counts().to_dict()
                self.logger.debug(f"Normalized side value counts: {norm_side_counts}")
                
                # Log unknown sides
                unknown_count = (df['norm_side'] == 'unknown').sum()
                if unknown_count > 0:
                    unknown_pct = (unknown_count / len(df)) * 100
                    self.logger.warning(f"Found {unknown_count} trades ({unknown_pct:.2f}%) with unknown side values")
                    
                    # Log some examples of unknown side values
                    unknown_sides = df[df['norm_side'] == 'unknown']['side'].unique()
                    self.logger.debug(f"Examples of unknown side values: {unknown_sides[:10]}")
                    
                    # Randomly assign sides to unknown values to avoid bias
                    unknown_mask = df['norm_side'] == 'unknown'
                    random_sides = np.random.choice(['buy', 'sell'], size=unknown_count)
                    df.loc[unknown_mask, 'norm_side'] = random_sides
                    self.logger.debug(f"Randomly assigned sides to {unknown_count} trades")
                    
                    # Log updated normalized side value counts
                    updated_norm_side_counts = df['norm_side'].value_counts().to_dict()
                    self.logger.debug(f"Updated normalized side value counts after random assignment: {updated_norm_side_counts}")
                
                # Calculate buy and sell volumes
                buy_volume = pd.to_numeric(df[df['norm_side'] == 'buy']['amount'].sum(), errors='coerce')
                sell_volume = pd.to_numeric(df[df['norm_side'] == 'sell']['amount'].sum(), errors='coerce')
                
                # Replace NaN with 0
                buy_volume = 0.0 if pd.isna(buy_volume) else float(buy_volume)
                sell_volume = 0.0 if pd.isna(sell_volume) else float(sell_volume)
                
                self.logger.debug(f"Trade flow volumes: buy_volume={buy_volume}, sell_volume={sell_volume}, types: {type(buy_volume)}, {type(sell_volume)}")
                
                total_volume = buy_volume + sell_volume
                
                if total_volume > 0:
                    # Calculate trade flow: range from -1 (all sells) to 1 (all buys)
                    trade_flow = (buy_volume - sell_volume) / total_volume
                    buy_pct = (buy_volume / total_volume) * 100
                    sell_pct = (sell_volume / total_volume) * 100
                    self.logger.debug(f"Trade flow calculated: {trade_flow:.4f} (buy: {buy_volume:.4f} [{buy_pct:.2f}%], sell: {sell_volume:.4f} [{sell_pct:.2f}%])")
                    
                    # Log execution time
                    execution_time = time.time() - start_time
                    self.logger.debug(f"Trade flow calculation completed in {execution_time:.4f} seconds")
                    self.logger.debug("=" * 50)
                    
                    return float(trade_flow)
                else:
                    self.logger.warning("Zero total volume, cannot calculate trade flow")
                    execution_time = time.time() - start_time
                    self.logger.debug(f"Trade flow calculation completed in {execution_time:.4f} seconds with zero volume")
                    self.logger.debug("=" * 50)
                    return 0.0
                    
            except Exception as e:
                self.logger.error(f"Error calculating trade flow volumes: {str(e)}")
                self.logger.debug(traceback.format_exc())
                execution_time = time.time() - start_time
                self.logger.debug(f"Trade flow calculation failed after {execution_time:.4f} seconds")
                self.logger.debug("=" * 50)
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error in trade flow calculation: {str(e)}")
            self.logger.debug(traceback.format_exc())
            execution_time = time.time() - start_time
            self.logger.debug(f"Trade flow calculation failed after {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            return 0.0