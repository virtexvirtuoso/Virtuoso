# src/indicators/orderbook_indicators.py

from logging import config
from typing_extensions import Protocol
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Union, Optional
import logging
from functools import lru_cache
import asyncio
import traceback
import time
from src.core.error.utils import handle_indicator_error
from collections import deque
from .base_indicator import BaseIndicator
from .debug_template import DebugLoggingMixin
from ..core.logger import Logger
from datetime import datetime, timezone
import math
from src.core.analysis.indicator_utils import log_score_contributions, log_component_analysis, log_final_score, log_calculation_details, log_indicator_results as centralized_log_indicator_results
# Add InterpretationGenerator import to use centralized interpretation system
from src.core.analysis.interpretation_generator import InterpretationGenerator
# Manipulation detection imports integrated directly
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import hashlib

logger = logging.getLogger('OrderbookIndicators')

class MarketDataRepository(Protocol):
    async def get_orderbook(self, symbol: str) -> Dict[str, Any]: ...
    async def get_trades(self, symbol: str) -> List[Dict[str, Any]]: ...

class OrderbookIndicators(BaseIndicator, DebugLoggingMixin):
    """Orderbook-based trading indicators that provide insights into market microstructure.
    
    This class calculates multiple orderbook-based metrics to evaluate market conditions
    and potential price direction. Each component provides unique insights into market
    microstructure and order flow dynamics.
    
    Enhanced with comprehensive debug logging and manipulation detection capabilities.
    
    Components and weights (optimized based on academic research with manipulation filtering):
    1. Depth (20%)
       - Core liquidity distribution and impact resistance analysis
       - Measures available liquidity at various price levels
       - Reduced from 22% to accommodate manipulation detection
       
    2. Imbalance (18%)
       - Broad pressure signal that complements OIR
       - Analyzes buy vs sell side liquidity asymmetry
       - Reduced from 20% for better component balance
       
    3. Order Imbalance Ratio - OIR (16%)
       - #1 academic metric for return prediction
       - Measures directional pressure from order flow imbalances
       - Reduced from 18% to balance with other components
       
    4. Liquidity (14%)
       - Composite depth/spread metric key for execution costs
       - Evaluates overall market liquidity quality
       - Reduced from 15% for weight optimization
       
    5. Market Pressure Index - MPI (11%)
       - Dynamic pressure detection with adaptive thresholds
       - Identifies accumulation and distribution patterns
       - Reduced from 12% for improved balance
       
    6. Manipulation Detection (8%)
       - NEW: Detects spoofing, layering, and wash trading patterns
       - Filters false signals from artificial order placement
       - Critical for maintaining signal integrity in volatile markets
       
    7. Absorption/Exhaustion (8%)
       - Supply/demand fatigue detection (situational)
       - Identifies when large orders are being absorbed
       - Maintained at 8% for specialized scenarios
       
    8. Depth Imbalance - DI (5%)
       - #2 academic metric for asymmetry measurement
       - Measures structural imbalances in order book depth
       - Maintained at 5% for academic completeness
    
    These 8 components are weighted and combined to create an overall orderbook score
    that ranges from 0-100, where values above 50 indicate bullish bias and
    values below 50 indicate bearish bias. The manipulation component ensures
    signal reliability by filtering artificial market conditions.
    """

    indicator_type = 'orderbook'

    def __init__(self, config_data: Dict[str, Any] = None, logger=None):
        # Set required attributes before calling super().__init__
        self.indicator_type = 'orderbook'
        
        # Optimized component weights based on academic research and predictive power analysis
        # Distribution prioritizes thesis-backed metrics (OIR/DI) and top-ranked components
        # Academic metrics now represent 23% total weight (OIR: 18%, DI: 5%) - AC removed due to OIR overlap
        # Now includes manipulation detection to filter false signals
        default_weights = {
            'depth': 0.20,              # Reduced from 0.22 to accommodate manipulation
            'imbalance': 0.18,          # Reduced from 0.20
            'oir': 0.16,                # Reduced from 0.18
            'liquidity': 0.14,          # Reduced from 0.15
            'mpi': 0.11,                # Reduced from 0.12
            'absorption_exhaustion': 0.08,  # Kept at 0.08
            'di': 0.05,                 # Kept at 0.05
            'manipulation': 0.08        # New component for detecting spoofing/layering
        }
        
        # Initialize component weights dictionary with defaults
        self.component_weights = default_weights.copy()
        
        # Set configuration parameters before calling super().__init__
        config = config_data or {}
        
        # Set weights first (needed for validation)
        self.weight_imbalance = config.get('orderbook', {}).get('weights', {}).get('imbalance', 0.3)
        self.weight_pressure = config.get('orderbook', {}).get('weights', {}).get('pressure', 0.3)
        self.weight_liquidity = config.get('orderbook', {}).get('weights', {}).get('liquidity', 0.2)
        self.weight_spread = config.get('orderbook', {}).get('weights', {}).get('spread', 0.2)
        
        # Now it's safe to call super().__init__
        super().__init__(config_data, logger or Logger(__name__).logger)
        
        # Configuration parameters
        self.depth_levels = self.config.get('orderbook', {}).get('depth_levels', 10)
        self.imbalance_threshold = self.config.get('orderbook', {}).get('imbalance_threshold', 1.5)
        self.liquidity_threshold = self.config.get('orderbook', {}).get('liquidity_threshold', 1.5)
        self.spread_factor = self.config.get('orderbook', {}).get('spread_factor', 2.0)
        self.max_spread_bps = self.config.get('orderbook', {}).get('max_spread_bps', 50)
        self.min_price_impact = self.config.get('orderbook', {}).get('min_price_impact', 0.05)
        
        # Get sigmoid transformation parameters from config
        sigmoid_config = self.config.get('orderbook', {}).get('parameters', {}).get('sigmoid_transformation', {})
        self.default_sensitivity = sigmoid_config.get('default_sensitivity', 0.12)
        self.imbalance_sensitivity = sigmoid_config.get('imbalance_sensitivity', 0.15)
        self.pressure_sensitivity = sigmoid_config.get('pressure_sensitivity', 0.18)
        
        # Initialize parameters
        self.spread_ma_period = self.config.get('orderbook', {}).get('spread_ma_period', 20)
        self.obps_depth = self.config.get('orderbook', {}).get('obps_depth', 10)
        self.obps_decay = self.config.get('orderbook', {}).get('obps_decay', 0.85)
        
        # Add alert thresholds
        alert_params = self.config.get('orderbook', {}).get('alerts', {})
        self.large_order_threshold_usd = alert_params.get('large_order_threshold_usd', 100000)
        self.aggressive_price_threshold = alert_params.get('aggressive_price_threshold', 0.002)
        self.alert_cooldown = alert_params.get('cooldown', 60)
        
        # Initialize tracking variables
        self.previous_orderbook = None
        self.last_update_time = None
        self.order_flow_history = deque(maxlen=self.spread_ma_period)
        self.spread_history = deque(maxlen=self.spread_ma_period)
        self.depth_history = deque(maxlen=self.spread_ma_period)
        self.mpi_history = deque(maxlen=self.spread_ma_period)
        self.obps_history = deque(maxlen=self.spread_ma_period)
        self._last_alert_time = 0.0
        
        # Initialize integrated manipulation detection
        self._init_manipulation_detection(config)
        
        # Validate weights
        self._validate_weights()
        
        self.logger.info(f"Initialized {self.__class__.__name__} with integrated manipulation detection")
        self.logger.info(f"Config: {self.config}")

    def _init_manipulation_detection(self, config: Dict[str, Any]):
        """Initialize integrated manipulation detection system"""
        manipulation_config = config.get('manipulation_detection', {})
        
        # Core manipulation detection parameters
        self.manipulation_enabled = manipulation_config.get('enabled', True)
        
        # Historical data storage (circular buffers)
        history_config = manipulation_config.get('history', {})
        max_snapshots = history_config.get('max_snapshots', 50)
        
        self.orderbook_history = deque(maxlen=max_snapshots)
        self.volume_history = deque(maxlen=max_snapshots)
        self.delta_history = deque(maxlen=max_snapshots)
        self.price_history = deque(maxlen=max_snapshots)
        self.trade_history = deque(maxlen=history_config.get('trade_history_size', 100))
        
        # Spoofing detection parameters
        spoofing_config = manipulation_config.get('spoofing', {})
        self.spoof_volatility_threshold = spoofing_config.get('volatility_threshold', 2.0)
        self.spoof_min_size_usd = spoofing_config.get('min_order_size_usd', 10000)
        self.spoof_execution_threshold = spoofing_config.get('execution_ratio_threshold', 0.1)
        
        # Layering detection parameters
        layering_config = manipulation_config.get('layering', {})
        self.layer_price_gap = layering_config.get('price_gap_threshold', 0.001)
        self.layer_size_uniformity = layering_config.get('size_uniformity_threshold', 0.1)
        self.layer_min_count = layering_config.get('min_layers', 3)
        
        # Enhanced detection features
        self.order_lifecycles = defaultdict(dict)  # Order lifecycle tracking
        self.completed_orders = deque(maxlen=500)
        self.trade_clusters = deque(maxlen=50)
        self.trade_velocity = deque(maxlen=100)
        self.phantom_orders = deque(maxlen=200)
        self.wash_pairs = deque(maxlen=100)
        self.iceberg_candidates = defaultdict(list)
        
        # Wash trading detection
        wash_config = manipulation_config.get('wash_trading', {})
        self.wash_time_window = wash_config.get('time_window_ms', 1000)
        self.trade_fingerprints = deque(maxlen=500)
        
        # Fake liquidity detection
        fake_liquidity_config = manipulation_config.get('fake_liquidity', {})
        self.fake_liquidity_threshold = fake_liquidity_config.get('withdrawal_threshold', 0.3)
        
        # Iceberg order detection
        iceberg_config = manipulation_config.get('iceberg', {})
        self.iceberg_refill_threshold = iceberg_config.get('refill_threshold', 0.8)
        
        # Performance metrics
        self.manipulation_detection_count = 0
        self.last_manipulation_detection = None
        self.correlation_accuracy = 0.0
        
        self.logger.info("Integrated manipulation detection initialized")

    def _validate_weights(self):
        """Validate that indicator weights sum to 1.0"""
        total_weight = (self.weight_imbalance + self.weight_pressure + 
                      self.weight_liquidity + self.weight_spread)
        
        if abs(total_weight - 1.0) > 0.001:
            self.logger.warning(f"Orderbook indicator weights sum to {total_weight}, normalizing")
            # Normalize weights
            self.weight_imbalance /= total_weight
            self.weight_pressure /= total_weight
            self.weight_liquidity /= total_weight
            self.weight_spread /= total_weight

    def _apply_sigmoid_transformation(self, value: float, sensitivity: float = 0.12, center: float = 50.0) -> float:
        """
        Apply sigmoid transformation to amplify signals outside the neutral range.
        
        Args:
            value: The value to transform
            sensitivity: Controls how aggressive the transformation is (lower = more aggressive)
            center: The center point considered neutral
            
        Returns:
            Transformed value in the same range as the input
        """
        try:
            # Normalize around center
            normalized = (value - center) / 50.0
            
            # Apply sigmoid with sensitivity parameter
            transformed = 1.0 / (1.0 + np.exp(-normalized / sensitivity))
            
            # Scale back to original range
            result = transformed * 100.0
            
            self.logger.debug(f"Sigmoid transformation: input={value:.2f}, sensitivity={sensitivity}, output={result:.2f}")
            return float(result)
        except Exception as e:
            self.logger.error(f"Error in sigmoid transformation: {str(e)}")
            return value  # Return original value on error

    def _calculate_oir_score(self, bids: np.ndarray, asks: np.ndarray) -> float:
        """Calculate Order Imbalance Ratio (OIR) score.
        
        Formula: (sum_bid_volume - sum_ask_volume) / (sum_bid_volume + sum_ask_volume)
        
        Strongest and most consistent predictor of short-term returns across models;
        absorbs most explanatory power from other asymmetry measures; robust for capital pressure analysis.
        Normalized to 0-100 (50 neutral) for short-term price prediction.
        
        Args:
            bids: Numpy array of bid [price, volume] pairs
            asks: Numpy array of ask [price, volume] pairs
            
        Returns:
            OIR score from 0-100
        """
        try:
            self.logger.debug("\n=== OIR (ORDER IMBALANCE RATIO) CALCULATION DEBUG ===")
            
            levels = min(self.depth_levels, len(bids), len(asks))
            self.logger.debug(f"Using {levels} levels (max configured: {self.depth_levels})")
            
            if levels == 0:
                self.logger.warning("No orderbook levels available for OIR calculation")
                return 50.0
            
            # Log raw orderbook data for first few levels
            self.logger.debug("Raw orderbook data (first 5 levels):")
            for i in range(min(5, levels)):
                self.logger.debug(f"  Level {i+1}: Bid [{bids[i,0]:.4f}, {bids[i,1]:.2f}], Ask [{asks[i,0]:.4f}, {asks[i,1]:.2f}]")
            
            # Sum volumes for top levels
            sum_bid_volume = np.sum(bids[:levels, 1].astype(float))
            sum_ask_volume = np.sum(asks[:levels, 1].astype(float))
            
            self.logger.debug(f"Volume summation:")
            self.logger.debug(f"  Sum bid volume: {sum_bid_volume:.2f}")
            self.logger.debug(f"  Sum ask volume: {sum_ask_volume:.2f}")
            self.logger.debug(f"  Total volume: {sum_bid_volume + sum_ask_volume:.2f}")
            
            if sum_bid_volume + sum_ask_volume == 0:
                self.logger.warning("Zero total volume detected in OIR calculation")
                return 50.0
            
            # Calculate OIR using academic formula
            oir = (sum_bid_volume - sum_ask_volume) / (sum_bid_volume + sum_ask_volume)
            self.logger.debug(f"Academic OIR formula:")
            self.logger.debug(f"  OIR = (sum_bid_volume - sum_ask_volume) / (sum_bid_volume + sum_ask_volume)")
            self.logger.debug(f"  OIR = ({sum_bid_volume:.2f} - {sum_ask_volume:.2f}) / ({sum_bid_volume:.2f} + {sum_ask_volume:.2f})")
            self.logger.debug(f"  OIR = {sum_bid_volume - sum_ask_volume:.2f} / {sum_bid_volume + sum_ask_volume:.2f}")
            self.logger.debug(f"  OIR = {oir:.6f}")
            
            # Interpret OIR value
            if oir > 0.1:
                interpretation = "Strong buying pressure"
            elif oir > 0.05:
                interpretation = "Moderate buying pressure"
            elif oir > -0.05:
                interpretation = "Balanced order flow"
            elif oir > -0.1:
                interpretation = "Moderate selling pressure"
            else:
                interpretation = "Strong selling pressure"
            
            self.logger.debug(f"OIR interpretation: {interpretation}")
            
            # Normalize to 0-100 (sigmoid for amplification, as in thesis short-term effects)
            raw_score = 50.0 * (1 + oir)  # Maps [-1,1] to [0,100]
            self.logger.debug(f"Raw score calculation:")
            self.logger.debug(f"  Raw score = 50.0 * (1 + OIR)")
            self.logger.debug(f"  Raw score = 50.0 * (1 + {oir:.6f})")
            self.logger.debug(f"  Raw score = {raw_score:.2f}")
            
            transformed_score = self._apply_sigmoid_transformation(
                raw_score, 
                sensitivity=self.imbalance_sensitivity, 
                center=50.0
            )
            
            self.logger.debug(f"Sigmoid transformation:")
            self.logger.debug(f"  Sensitivity: {self.imbalance_sensitivity}")
            self.logger.debug(f"  Input: {raw_score:.2f}")
            self.logger.debug(f"  Output: {transformed_score:.2f}")
            
            final_score = float(np.clip(transformed_score, 0, 100))
            
            # Log academic significance
            if abs(oir) > 0.1:
                self.logger.info(f"Significant OIR detected: {oir:.4f} - Academic #1 predictor shows {interpretation}")
            
            self.logger.debug(f"Final OIR score: {final_score:.2f}")
            return final_score
        
        except Exception as e:
            self.logger.error(f"Error calculating OIR score: {str(e)}")
            self.logger.debug(f"OIR calculation error details: {traceback.format_exc()}")
            return 50.0

    def _calculate_di_score(self, bids: np.ndarray, asks: np.ndarray) -> float:
        """Calculate Depth Imbalance (DI) score.
        
        Formula: sum_bid_volume - sum_ask_volume
        
        Strong predictor in short horizons; significant in univariate models and event studies;
        captures absolute imbalance intuitively but less dominant than OIR in multivariate specs due to overlap.
        Normalized to 0-100 (50 neutral) for asymmetry measurement.
        
        Args:
            bids: Numpy array of bid [price, volume] pairs
            asks: Numpy array of ask [price, volume] pairs
            
        Returns:
            DI score from 0-100
        """
        try:
            self.logger.debug("\n=== DI (DEPTH IMBALANCE) CALCULATION DEBUG ===")
            
            levels = min(self.depth_levels, len(bids), len(asks))
            self.logger.debug(f"Using {levels} levels (max configured: {self.depth_levels})")
            
            if levels == 0:
                self.logger.warning("No orderbook levels available for DI calculation")
                return 50.0
            
            # Log volume analysis for first few levels
            self.logger.debug("Volume analysis (first 5 levels):")
            bid_volumes = []
            ask_volumes = []
            for i in range(min(5, levels)):
                bid_vol = float(bids[i, 1])
                ask_vol = float(asks[i, 1])
                bid_volumes.append(bid_vol)
                ask_volumes.append(ask_vol)
                self.logger.debug(f"  Level {i+1}: Bid volume: {bid_vol:.2f}, Ask volume: {ask_vol:.2f}")
            
            # Sum volumes for top levels
            sum_bid_volume = np.sum(bids[:levels, 1].astype(float))
            sum_ask_volume = np.sum(asks[:levels, 1].astype(float))
            
            self.logger.debug(f"Volume summation:")
            self.logger.debug(f"  Sum bid volume: {sum_bid_volume:.2f}")
            self.logger.debug(f"  Sum ask volume: {sum_ask_volume:.2f}")
            self.logger.debug(f"  Total volume: {sum_bid_volume + sum_ask_volume:.2f}")
            
            # Calculate DI using academic formula
            di = sum_bid_volume - sum_ask_volume
            self.logger.debug(f"Academic DI formula:")
            self.logger.debug(f"  DI = sum_bid_volume - sum_ask_volume")
            self.logger.debug(f"  DI = {sum_bid_volume:.2f} - {sum_ask_volume:.2f}")
            self.logger.debug(f"  DI = {di:.2f}")
            
            # Interpret DI value
            total_volume = sum_bid_volume + sum_ask_volume
            if total_volume > 0:
                di_percentage = (di / total_volume) * 100
                self.logger.debug(f"DI as percentage of total volume: {di_percentage:.2f}%")
                
                if di_percentage > 10:
                    interpretation = "Strong bid-side excess"
                elif di_percentage > 5:
                    interpretation = "Moderate bid-side excess"
                elif di_percentage > -5:
                    interpretation = "Balanced depth"
                elif di_percentage > -10:
                    interpretation = "Moderate ask-side excess"
                else:
                    interpretation = "Strong ask-side excess"
            else:
                interpretation = "No volume data"
                
            self.logger.debug(f"DI interpretation: {interpretation}")
            
            # Normalize using tanh for symmetry around 0, scale to 0-100
            # Use total volume for scaling to make it relative
            if total_volume == 0:
                self.logger.warning("Zero total volume detected in DI calculation")
                return 50.0
                
            # Normalize DI by total volume to get relative imbalance
            normalized_di = np.tanh(di / (total_volume + 1e-10))  # Bound -1 to 1
            self.logger.debug(f"Normalization process:")
            self.logger.debug(f"  Normalized DI = tanh(DI / total_volume)")
            self.logger.debug(f"  Normalized DI = tanh({di:.2f} / {total_volume:.2f})")
            self.logger.debug(f"  Normalized DI = tanh({di/total_volume:.6f})")
            self.logger.debug(f"  Normalized DI = {normalized_di:.6f}")
            
            raw_score = 50.0 * (1 + normalized_di)  # Maps [-1,1] to [0,100]
            self.logger.debug(f"Raw score calculation:")
            self.logger.debug(f"  Raw score = 50.0 * (1 + normalized_DI)")
            self.logger.debug(f"  Raw score = 50.0 * (1 + {normalized_di:.6f})")
            self.logger.debug(f"  Raw score = {raw_score:.2f}")
            
            transformed_score = self._apply_sigmoid_transformation(
                raw_score, 
                sensitivity=0.15,  # Moderate sensitivity per thesis robustness
                center=50.0
            )
            
            self.logger.debug(f"Sigmoid transformation:")
            self.logger.debug(f"  Sensitivity: 0.15 (moderate per academic research)")
            self.logger.debug(f"  Input: {raw_score:.2f}")
            self.logger.debug(f"  Output: {transformed_score:.2f}")
            
            final_score = float(np.clip(transformed_score, 0, 100))
            
            # Log academic significance
            if abs(normalized_di) > 0.1:
                self.logger.info(f"Significant DI detected: {di:.2f} ({di_percentage:.1f}%) - Academic #2 predictor shows {interpretation}")
            
            self.logger.debug(f"Final DI score: {final_score:.2f}")
            return final_score
        
        except Exception as e:
            self.logger.error(f"Error calculating DI score: {str(e)}")
            self.logger.debug(f"DI calculation error details: {traceback.format_exc()}")
            return 50.0

    def _update_historical_metrics(self, spread: float, depth: float) -> None:
        """Update historical metrics for spread and depth."""
        # Update spread history
        self.spread_history.append(spread)
        if len(self.spread_history) > self.spread_ma_period:
            self.spread_history.pop(0)
        self.typical_spread = np.median(self.spread_history)
        
        # Update depth history
        self.depth_history.append(depth)
        if len(self.depth_history) > self.spread_ma_period:
            self.depth_history.pop(0)
        self.typical_depth = np.percentile(self.depth_history, 50)

    def _calculate_orderbook_imbalance(self, market_data: Dict[str, Any]) -> float:
        """Calculate enhanced orderbook imbalance using volume and price sensitivity.
        
        Args:
            market_data: Dictionary containing market data including orderbook
            
        Returns:
            float: Normalized imbalance score (0-100) where:
                  0 = extremely bearish (ask-heavy)
                  50 = neutral
                  100 = extremely bullish (bid-heavy)
        """
        try:
            self.logger.debug("\n=== ORDERBOOK IMBALANCE CALCULATION DEBUG ===")
            
            # Extract orderbook data from market_data
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            self.logger.debug(f"Raw orderbook data - Bids: {len(bids)}, Asks: {len(asks)}")
            
            if not bids or not asks:
                self.logger.warning("Empty orderbook detected")
                return 50.0  # Neutral imbalance
            
            # Convert to numpy arrays if they aren't already
            if not isinstance(bids, np.ndarray):
                bids = np.array(bids, dtype=float)
            if not isinstance(asks, np.ndarray):
                asks = np.array(asks, dtype=float)
                
            self.logger.debug(f"Converted arrays - Bids shape: {bids.shape}, Asks shape: {asks.shape}")
                
            # 1. Dynamic depth and mid-price calculation
            levels = min(10, len(bids), len(asks))  # Use up to 10 levels
            self.logger.debug(f"Using {levels} levels for analysis")
            
            # Ensure values are floats before calculation
            try:
                bid_price = float(bids[0, 0])
                ask_price = float(asks[0, 0])
                mid_price = (bid_price + ask_price) / 2
                self.logger.debug(f"Price levels - Best bid: {bid_price:.4f}, Best ask: {ask_price:.4f}, Mid: {mid_price:.4f}")
            except (ValueError, TypeError, IndexError) as e:
                self.logger.error(f"Error converting price to float: {str(e)}")
                return 50.0  # Return neutral score on error
            
            # Calculate spread and total depth with error handling
            try:
                spread = (asks[0, 0] - bids[0, 0]) / mid_price
                total_depth = np.sum(bids[:levels, 1]) + np.sum(asks[:levels, 1])
                self.logger.debug(f"Market metrics - Spread: {spread:.6f} ({spread*10000:.2f} bps), Total depth: {total_depth:.2f}")
            except IndexError:
                self.logger.error("Invalid price/size data in orderbook")
                return 50.0
            
            # Update historical metrics
            self._update_historical_metrics(spread, total_depth)
            
            # Normalize spread using historical data with safety check
            normalized_spread = min(1.0, spread / (self.typical_spread + 1e-10)) if hasattr(self, 'typical_spread') else 0.5
            self.logger.debug(f"Normalized spread: {normalized_spread:.4f} (typical: {getattr(self, 'typical_spread', 'N/A')})")
            
            # 2. Volume-weighted imbalance with normalized weights
            level_weights = np.exp(-np.arange(levels) * 0.3)  # Slower decay
            level_weights /= np.sum(level_weights)  # Ensure weights sum to 1
            
            self.logger.debug("Level weights (exponential decay):")
            for i, weight in enumerate(level_weights):
                self.logger.debug(f"  Level {i+1}: {weight:.4f} ({weight*100:.1f}%)")
            
            try:
                weighted_bid_volume = np.sum(bids[:levels, 1] * level_weights)
                weighted_ask_volume = np.sum(asks[:levels, 1] * level_weights)
                total_weighted_volume = weighted_bid_volume + weighted_ask_volume
                
                self.logger.debug(f"Volume-weighted analysis:")
                self.logger.debug(f"  Weighted bid volume: {weighted_bid_volume:.2f}")
                self.logger.debug(f"  Weighted ask volume: {weighted_ask_volume:.2f}")
                self.logger.debug(f"  Total weighted volume: {total_weighted_volume:.2f}")
                
            except (IndexError, ValueError) as e:
                self.logger.error(f"Error calculating weighted volumes: {str(e)}")
                return 50.0
            
            # Check for meaningful volume with logging
            if total_weighted_volume < 1e-6:
                self.logger.warning("Negligible total weighted volume detected")
                return 50.0  # Neutral if no meaningful volume
                
            weighted_imbalance = (weighted_bid_volume - weighted_ask_volume) / total_weighted_volume
            self.logger.debug(f"Weighted imbalance: {weighted_imbalance:.6f}")
            
            # 3. Price-sensitive imbalance with dynamic sensitivity
            try:
                bid_distances = np.abs(bids[:levels, 0] - mid_price) / mid_price
                ask_distances = np.abs(asks[:levels, 0] - mid_price) / mid_price
                
                self.logger.debug("Price distance analysis:")
                for i in range(min(5, levels)):
                    self.logger.debug(f"  Level {i+1} - Bid distance: {bid_distances[i]:.6f}, Ask distance: {ask_distances[i]:.6f}")
                    
            except IndexError:
                self.logger.error("Error calculating price distances")
                return 50.0
            
            # Dynamic price sensitivity based on normalized spread
            price_sensitivity = 15 * min(1.5, 1 + normalized_spread)
            self.logger.debug(f"Price sensitivity factor: {price_sensitivity:.2f}")
            
            # Calculate and normalize price weights with epsilon
            bid_weights = np.exp(-bid_distances * price_sensitivity)
            ask_weights = np.exp(-ask_distances * price_sensitivity)
            
            self.logger.debug("Price-based weights (before normalization):")
            for i in range(min(5, levels)):
                self.logger.debug(f"  Level {i+1} - Bid weight: {bid_weights[i]:.4f}, Ask weight: {ask_weights[i]:.4f}")
            
            # Ensure weights sum to 1 even under edge cases
            bid_weights = bid_weights / (np.sum(bid_weights) + 1e-10)
            ask_weights = ask_weights / (np.sum(ask_weights) + 1e-10)
            
            self.logger.debug("Price-based weights (normalized):")
            for i in range(min(5, levels)):
                self.logger.debug(f"  Level {i+1} - Bid weight: {bid_weights[i]:.4f}, Ask weight: {ask_weights[i]:.4f}")
            
            # Calculate price-weighted volumes with error handling
            try:
                price_weighted_bid = np.sum(bids[:levels, 1] * bid_weights)
                price_weighted_ask = np.sum(asks[:levels, 1] * ask_weights)
                total_price_weighted = price_weighted_bid + price_weighted_ask
                
                self.logger.debug(f"Price-weighted analysis:")
                self.logger.debug(f"  Price-weighted bid volume: {price_weighted_bid:.2f}")
                self.logger.debug(f"  Price-weighted ask volume: {price_weighted_ask:.2f}")
                self.logger.debug(f"  Total price-weighted volume: {total_price_weighted:.2f}")
                
            except (IndexError, ValueError) as e:
                self.logger.error(f"Error calculating price-weighted volumes: {str(e)}")
                return 50.0
            
            # Check for meaningful price-weighted volume with logging
            if total_price_weighted < 1e-6:
                self.logger.warning("Negligible price-weighted volume detected")
                price_sensitive_imbalance = 0.0
            else:
                price_sensitive_imbalance = (price_weighted_bid - price_weighted_ask) / total_price_weighted
                
            self.logger.debug(f"Price-sensitive imbalance: {price_sensitive_imbalance:.6f}")
            
            # 4. Combine metrics with dynamic weighting based on normalized spread
            price_weight = min(0.8, 0.5 + normalized_spread)  # Cap at 0.8 for stability
            volume_weight = 1 - price_weight
            
            self.logger.debug(f"Combination weights - Volume: {volume_weight:.3f}, Price: {price_weight:.3f}")
            
            # Use numpy's average for cleaner weighted combination
            final_imbalance = np.average(
                [weighted_imbalance, price_sensitive_imbalance],
                weights=[volume_weight, price_weight]
            )
            
            self.logger.debug(f"Combined imbalance: {final_imbalance:.6f}")
            
            # 5. Apply sigmoid normalization for smoother distribution
            normalized_imbalance = 50 * (1 + np.tanh(2 * final_imbalance))
            self.logger.debug(f"Sigmoid normalized imbalance: {normalized_imbalance:.2f}")
            
            # 6. Dynamic depth confidence calculation using historical depth
            depth_confidence = min(1.0, total_depth / (self.typical_depth + 1e-10)) if hasattr(self, 'typical_depth') else 0.5
            self.logger.debug(f"Depth confidence: {depth_confidence:.3f} (typical depth: {getattr(self, 'typical_depth', 'N/A')})")
            
            # 7. Final score calculation with confidence adjustment
            final_score = 50 + (normalized_imbalance - 50) * depth_confidence
            self.logger.debug(f"Final imbalance score: {final_score:.2f}")
            
            # Log significant deviations for monitoring
            if abs(final_score - 50) > 30:  # Log extreme imbalances
                self.logger.info(
                    f"Large imbalance detected: {final_score:.2f}, "
                    f"spread: {spread:.6f}, depth: {total_depth:.2f}"
                )
            
            return float(np.clip(final_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating orderbook imbalance: {str(e)}")
            self.logger.debug(f"Error details: {traceback.format_exc()}")
            return 50.0

    def calculate_absorption_exhaustion(self, bids: np.ndarray, asks: np.ndarray) -> Dict[str, float]:
        """Calculate absorption and exhaustion metrics."""
        try:
            if len(bids) < 3 or len(asks) < 3:
                return {
                    'absorption_score': 50.0,
                    'exhaustion_score': 50.0,
                    'combined_score': 50.0,
                    'raw_metrics': {
                        'bid_concentration': 0.5,
                        'ask_concentration': 0.5,
                        'bid_replenishment': 0.5,
                        'ask_replenishment': 0.5
                    }
                }
                
            # Convert to float arrays
            try:
                bids_float = bids.astype(float)
                asks_float = asks.astype(float)
            except (ValueError, TypeError) as e:
                self.logger.error(f"Error converting orderbook data to float: {str(e)}")
                return {
                    'absorption_score': 50.0,
                    'exhaustion_score': 50.0,
                    'combined_score': 50.0,
                    'raw_metrics': {
                        'bid_concentration': 0.5,
                        'ask_concentration': 0.5,
                        'bid_replenishment': 0.5,
                        'ask_replenishment': 0.5
                    }
                }
                
            # Calculate volume concentration at top of book
            bid_concentration = np.sum(bids_float[:3, 1]) / np.sum(bids_float[:, 1])
            ask_concentration = np.sum(asks_float[:3, 1]) / np.sum(asks_float[:, 1])
            
            # Calculate price gaps for order replenishment
            bid_gaps = np.diff(bids_float[:, 0]) / bids_float[0, 0]  # Normalize by price
            ask_gaps = np.diff(asks_float[:, 0]) / asks_float[0, 0]
            
            # Calculate replenishment metrics (inverse of gaps)
            bid_replenishment = 1 / (1 + np.mean(bid_gaps))
            ask_replenishment = 1 / (1 + np.mean(ask_gaps))
            
            # Calculate absorption score based on concentration and replenishment
            absorption_score = (
                (bid_concentration + ask_concentration) / 2 * 0.7 +  # Weight concentration more heavily
                (bid_replenishment + ask_replenishment) / 2 * 0.3
            )
            
            # Calculate exhaustion score based on volume imbalance
            bid_volume = np.sum(bids_float[:, 1])
            ask_volume = np.sum(asks_float[:, 1])
            total_volume = bid_volume + ask_volume
            
            # Normalize to 0-1 range
            volume_imbalance = (bid_volume - ask_volume) / total_volume if total_volume > 0 else 0
            
            # Calculate exhaustion based on concentration and imbalance
            bid_exhaustion = bid_concentration * (1 + volume_imbalance) if volume_imbalance > 0 else bid_concentration
            ask_exhaustion = ask_concentration * (1 - volume_imbalance) if volume_imbalance < 0 else ask_concentration
            
            # Final exhaustion score (higher = more exhausted)
            exhaustion_score = (bid_exhaustion + ask_exhaustion) / 2
            
            # Normalize scores to 0-100 range
            absorption_score = float(np.clip(absorption_score * 100, 0, 100))
            exhaustion_score = float(np.clip(exhaustion_score * 100, 0, 100))
            
            # Calculate combined score that considers both metrics
            # High absorption + low exhaustion = bullish
            # Low absorption + high exhaustion = bearish
            combined_score = 50 + (absorption_score - 50) * 0.6 - (exhaustion_score - 50) * 0.4
            
            return {
                'absorption_score': absorption_score,
                'exhaustion_score': exhaustion_score,
                'combined_score': float(np.clip(combined_score, 0, 100)),
                'raw_metrics': {
                    'bid_concentration': float(bid_concentration),
                    'ask_concentration': float(ask_concentration),
                    'bid_replenishment': float(bid_replenishment),
                    'ask_replenishment': float(ask_replenishment)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating absorption/exhaustion: {str(e)}")
            return {
                'absorption_score': 50.0,
                'exhaustion_score': 50.0,
                'combined_score': 50.0,
                'raw_metrics': {
                    'bid_concentration': 0.5,
                    'ask_concentration': 0.5,
                    'bid_replenishment': 0.5,
                    'ask_replenishment': 0.5
                }
            }

    def calculate_spread_score(self, bids: np.ndarray, asks: np.ndarray) -> Dict[str, float]:
        """Calculate enhanced spread score with stability metrics."""
        try:
            if len(bids) < 3 or len(asks) < 3:
                return {'score': 50.0, 'relative_spread': 0.0, 'stability': 0.5}
                
            # Basic spread calculations
            mid_price = (asks[0, 0] + bids[0, 0]) / 2
            relative_spread = (asks[0, 0] - bids[0, 0]) / mid_price
            
            # Calculate spread stability
            bid_spreads = np.diff(bids[:3, 0]) / bids[0, 0]
            ask_spreads = np.diff(asks[:3, 0]) / asks[0, 0]
            spread_stability = 1 - np.mean([np.std(bid_spreads), np.std(ask_spreads)])

            # Calculate final spread score
            spread_base_score = 100 * np.exp(-10 * relative_spread)
            final_score = spread_base_score * 0.7 + spread_stability * 100 * 0.3
            
            return {
                'score': float(np.clip(final_score, 0, 100)),
                'relative_spread': float(relative_spread),
                'stability': float(spread_stability)
            }
        except Exception as e:
            self.logger.error(f"Error calculating spread score: {str(e)}")
            return {'score': 50.0, 'relative_spread': 0.0, 'stability': 0.5}

    def calculate_slope_score(self, bids: np.ndarray, asks: np.ndarray) -> float:
        """Calculate enhanced slope score using volume-weighted multi-level analysis.
        
        Returns:
            float: Score between 0-100 where:
                  0 = extremely bearish slope
                  50 = neutral
                  100 = extremely bullish slope
        """
        try:
            if len(bids) < 3 or len(asks) < 3:
                return 50.0

            # Convert to float arrays and get volumes
            bid_prices = bids[:, 0].astype(float)
            ask_prices = asks[:, 0].astype(float)
            bid_volumes = bids[:, 1].astype(float)
            ask_volumes = asks[:, 1].astype(float)

            # Calculate mid price for normalization
            mid_price = (bid_prices[0] + ask_prices[0]) / 2

            # Calculate volume-weighted slopes for multiple segments
            segments = [3, 5, 10]  # Analyze different depth segments
            segment_weights = [0.5, 0.3, 0.2]  # Weight closer levels more heavily
            
            bid_slopes = []
            ask_slopes = []
            
            for seg in segments:
                seg = min(seg, len(bid_prices), len(ask_prices))
                
                # Normalize prices relative to mid price
                norm_bid_prices = (bid_prices[:seg] - mid_price) / mid_price
                norm_ask_prices = (ask_prices[:seg] - mid_price) / mid_price
                
                # Calculate volume-weighted slopes
                bid_x = np.arange(seg)
                ask_x = np.arange(seg)
                
                # Weight by volume
                bid_weights = bid_volumes[:seg] / np.sum(bid_volumes[:seg])
                ask_weights = ask_volumes[:seg] / np.sum(ask_volumes[:seg])
                
                # Calculate weighted slopes
                bid_slope = np.polyfit(bid_x, norm_bid_prices, 1, w=bid_weights)[0]
                ask_slope = np.polyfit(ask_x, norm_ask_prices, 1, w=ask_weights)[0]
                
                bid_slopes.append(bid_slope)
                ask_slopes.append(ask_slope)
            
            # Combine slopes with segment weights
            final_bid_slope = np.sum([s * w for s, w in zip(bid_slopes, segment_weights)])
            final_ask_slope = np.sum([s * w for s, w in zip(ask_slopes, segment_weights)])
            
            # Calculate slope difference and normalize
            slope_diff = final_bid_slope - final_ask_slope
            
            # Use sigmoid for smooth normalization between 0 and 100
            slope_score = 50 * (1 + np.tanh(5 * slope_diff))
            
            # Add confidence factor based on volume consistency
            volume_consistency = 1 - np.mean([
                np.std(bid_volumes[:10]) / np.mean(bid_volumes[:10]),
                np.std(ask_volumes[:10]) / np.mean(ask_volumes[:10])
            ])
            
            # Adjust score based on confidence
            confidence_factor = 0.8 + (0.2 * volume_consistency)
            slope_score = 50 + (slope_score - 50) * confidence_factor
            
            return float(np.clip(slope_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating slope score: {str(e)}")
            return 50.0

    def calculate_obps(self, bids: np.ndarray, asks: np.ndarray) -> Dict[str, float]:
        """Calculate Order Book Pressure Score (OBPS).
        
        Returns:
            Dict containing:
                - score: normalized OBPS (0-100)
                - bid_pressure: bid-side pressure metric
                - ask_pressure: ask-side pressure metric
                - raw_ratio: raw bid/ask ratio before normalization
        """
        try:
            self.logger.debug("\n=== Order Book Pressure Score (OBPS) Analysis ===")
            
            if len(bids) == 0 or len(asks) == 0:
                self.logger.warning("Empty orderbook arrays detected")
                return {
                    'score': 50.0,
                    'bid_pressure': 0.0,
                    'ask_pressure': 0.0,
                    'raw_ratio': 1.0
                }

            # Log input data summary
            self.logger.debug(f"Analysis depth: {self.obps_depth} levels")
            self.logger.debug(f"Decay factor: {self.obps_decay}")
            self.logger.debug(f"Available levels - Bids: {len(bids)}, Asks: {len(asks)}")

            # Calculate and log weight distribution
            depth = min(self.obps_depth, len(bids), len(asks))
            weights = np.power(self.obps_decay, np.arange(depth))
            weights /= weights.sum()  # Normalize weights
            
            self.logger.debug("\n--- Weight Distribution ---")
            for i, w in enumerate(weights):
                self.logger.debug(f"Level {i+1}: {w:.4f} ({w*100:.1f}%)")
            
            # Calculate weighted volumes with detailed logging
            self.logger.debug("\n--- Volume Analysis ---")
            
            # Bid side analysis
            bid_volumes = bids[:depth, 1]
            weighted_bid_volumes = bid_volumes * weights
            bid_pressure = np.sum(weighted_bid_volumes)
            
            self.logger.debug("\nBid Side:")
            for i in range(depth):
                self.logger.debug(
                    f"Level {i+1}: Price={bids[i,0]:.2f}, "
                    f"Vol={bid_volumes[i]:.2f}, "
                    f"Weighted={weighted_bid_volumes[i]:.2f}"
                )
            self.logger.debug(f"Total Bid Pressure: {bid_pressure:.2f}")
            
            # Ask side analysis
            ask_volumes = asks[:depth, 1]
            weighted_ask_volumes = ask_volumes * weights
            ask_pressure = np.sum(weighted_ask_volumes)
            
            self.logger.debug("\nAsk Side:")
            for i in range(depth):
                self.logger.debug(
                    f"Level {i+1}: Price={asks[i,0]:.2f}, "
                    f"Vol={ask_volumes[i]:.2f}, "
                    f"Weighted={weighted_ask_volumes[i]:.2f}"
                )
            self.logger.debug(f"Total Ask Pressure: {ask_pressure:.2f}")
            
            # Pressure calculations with logging
            self.logger.debug("\n--- Pressure Metrics ---")
            total_pressure = bid_pressure + ask_pressure
            self.logger.debug(f"Total Pressure: {total_pressure:.2f}")
            
            if total_pressure > 0:
                raw_ratio = bid_pressure / ask_pressure
                pressure_imbalance = (bid_pressure - ask_pressure) / total_pressure
                self.logger.debug(f"Bid/Ask Ratio: {raw_ratio:.4f}")
                self.logger.debug(f"Pressure Imbalance: {pressure_imbalance:.4f}")
            else:
                self.logger.warning("Zero total pressure detected - using neutral values")
                raw_ratio = 1.0
                pressure_imbalance = 0.0
            
            # Score calculation with logging
            self.logger.debug("\n--- Score Calculation ---")
            base_score = 50 * (1 + np.tanh(2 * pressure_imbalance))
            self.logger.debug(f"Base Score: {base_score:.2f}")
            
            # Trend analysis with detailed logging
            self.obps_history.append(base_score)
            self.logger.debug(f"Historical Scores: {list(self.obps_history)}")
            
            if len(self.obps_history) > 1:
                score_changes = [x - y for x, y in zip(
                    list(self.obps_history)[1:], 
                    list(self.obps_history)[:-1]
                )]
                trend = np.mean(score_changes)
                trend_factor = np.tanh(3 * trend)
                
                self.logger.debug(f"Recent Score Changes: {score_changes}")
                self.logger.debug(f"Average Change: {trend:.4f}")
                self.logger.debug(f"Trend Factor: {trend_factor:.4f}")
                
                final_score = base_score + (trend_factor * 5)
                self.logger.debug(f"Trend Adjustment: {trend_factor * 5:+.2f}")
            else:
                self.logger.debug("Insufficient history for trend calculation")
                final_score = base_score
            
            final_score = float(np.clip(final_score, 0, 100))
            self.logger.debug(f"\nFinal OBPS Score: {final_score:.2f}")
            
            # Market interpretation
            self.logger.debug("\n--- Market Interpretation ---")
            if final_score > 60:
                self.logger.debug("Strong buying pressure in order book")
            elif final_score < 40:
                self.logger.debug("Strong selling pressure in order book")
            else:
                self.logger.debug("Neutral order book pressure")
            
            # Log significant pressure changes
            if abs(pressure_imbalance) > 0.3:
                self.logger.info(
                    f"Significant order book pressure: {pressure_imbalance:.2f} "
                    f"({'bid' if pressure_imbalance > 0 else 'ask'} dominance)"
                )
            
            return {
                'score': final_score,
                'bid_pressure': float(bid_pressure),
                'ask_pressure': float(ask_pressure),
                'raw_ratio': float(raw_ratio)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating OBPS: {str(e)}", exc_info=True)
            return {
                'score': 50.0,
                'bid_pressure': 0.0,
                'ask_pressure': 0.0,
                'raw_ratio': 1.0
            }

    def calculate_dom_momentum(self, current_bids: np.ndarray, current_asks: np.ndarray) -> Dict[str, float]:
        """Calculate Depth of Market momentum."""
        try:
            self.logger.debug("\n--- DOM Momentum Analysis ---")
            current_time = time.time()
            
            if self.previous_orderbook is None or self.last_update_time is None:
                self.logger.debug("Initializing DOM tracking - using neutral values")
                self.previous_orderbook = {
                    'bids': current_bids.copy(),
                    'asks': current_asks.copy()
                }
                self.last_update_time = current_time
                return {
                    'score': 50.0,
                    'flow_velocity': 0.0,
                    'bid_stack_pressure': 0.0,
                    'ask_stack_pressure': 0.0
                }

            # Calculate and log time delta with more context
            time_delta = max(0.001, current_time - self.last_update_time)
            self.logger.debug(f"Time delta: {time_delta:.3f}s")
            self.logger.debug(f"Update frequency: {1/time_delta:.1f} Hz")
            
            prev_bids = self.previous_orderbook['bids']
            prev_asks = self.previous_orderbook['asks']
            
            # Calculate and log volume changes with percentages
            total_prev_volume = np.sum(prev_bids[:, 1]) + np.sum(prev_asks[:, 1])
            total_curr_volume = np.sum(current_bids[:, 1]) + np.sum(current_asks[:, 1])
            
            bid_volume_delta = np.sum(current_bids[:, 1]) - np.sum(prev_bids[:, 1])
            ask_volume_delta = np.sum(current_asks[:, 1]) - np.sum(prev_asks[:, 1])
            
            self.logger.debug("\nVolume Analysis:")
            self.logger.debug(f"Total volume change: {total_curr_volume - total_prev_volume:.2f} ({((total_curr_volume/total_prev_volume)-1)*100:.1f}%)")
            self.logger.debug(f"Bid volume delta: {bid_volume_delta:.2f} ({(bid_volume_delta/np.sum(prev_bids[:, 1]))*100:.1f}%)")
            self.logger.debug(f"Ask volume delta: {ask_volume_delta:.2f} ({(ask_volume_delta/np.sum(prev_asks[:, 1]))*100:.1f}%)")
            
            # Calculate and log enhanced flow metrics
            flow_velocity = (abs(bid_volume_delta) + abs(ask_volume_delta)) / time_delta
            bid_stack_pressure = bid_volume_delta / time_delta
            ask_stack_pressure = ask_volume_delta / time_delta
            
            self.logger.debug("\nFlow Metrics:")
            self.logger.debug(f"Flow velocity: {flow_velocity:.2f} units/s")
            self.logger.debug(f"Bid stack pressure: {bid_stack_pressure:.2f} units/s")
            self.logger.debug(f"Ask stack pressure: {ask_stack_pressure:.2f} units/s")
            self.logger.debug(f"Net stack pressure: {bid_stack_pressure - ask_stack_pressure:.2f} units/s")
            
            # Update history and calculate components with more detailed stats
            self.order_flow_history.append({
                'velocity': flow_velocity,
                'bid_pressure': bid_stack_pressure,
                'ask_pressure': ask_stack_pressure,
                'timestamp': current_time
            })
            
            # Calculate and log enhanced component scores
            self.logger.debug("\nComponent Analysis:")
            
            # 1. Enhanced velocity score with volatility
            velocities = [x['velocity'] for x in self.order_flow_history]
            avg_velocity = np.mean(velocities)
            velocity_std = np.std(velocities) if len(velocities) > 1 else 0
            velocity_score = 50 * (1 + np.tanh(flow_velocity / (avg_velocity + 1e-10) - 1))
            
            self.logger.debug("Velocity Metrics:")
            self.logger.debug(f"Current velocity: {flow_velocity:.2f} units/s")
            self.logger.debug(f"Average velocity: {avg_velocity:.2f} units/s")
            self.logger.debug(f"Velocity volatility: {velocity_std:.2f}")
            self.logger.debug(f"Velocity score: {velocity_score:.2f}")
            
            # 2. Enhanced pressure score with historical context
            net_pressure = bid_stack_pressure - ask_stack_pressure
            pressure_score = 50 * (1 + np.tanh(net_pressure / (avg_velocity + 1e-10)))
            
            self.logger.debug("\nPressure Metrics:")
            self.logger.debug(f"Net pressure: {net_pressure:.2f} units/s")
            self.logger.debug(f"Pressure score: {pressure_score:.2f}")
            
            # 3. Trend persistence score
            if len(self.order_flow_history) > 1:
                pressure_trend = np.mean([
                    1 if x['bid_pressure'] > x['ask_pressure'] else -1 
                    for x in self.order_flow_history
                ])
                trend_score = 50 * (1 + np.tanh(pressure_trend))
                self.logger.debug(f"Pressure trend: {pressure_trend:.2f}")
                self.logger.debug(f"Trend score: {trend_score:.2f}")
            else:
                trend_score = 50.0
                self.logger.debug("Insufficient history for trend calculation")
            
            # Calculate final score
            final_score = (
                velocity_score * 0.3 +
                pressure_score * 0.4 +
                trend_score * 0.3
            )
            
            self.logger.debug(f"\nFinal DOM Score: {final_score:.2f}")
            
            # Log market interpretation
            self.logger.debug("\nDOM Interpretation:")
            if final_score > 60:
                self.logger.debug("Strong buying pressure in order book")
            elif final_score < 40:
                self.logger.debug("Strong selling pressure in order book")
            else:
                self.logger.debug("Neutral order book pressure")
            
            if abs(net_pressure) > avg_velocity * 2:
                self.logger.info(f"Significant DOM pressure detected: {net_pressure:.2f} {'bid' if net_pressure > 0 else 'ask'} side")
            
            # Update state
            self.previous_orderbook = {
                'bids': current_bids.copy(),
                'asks': current_asks.copy()
            }
            self.last_update_time = current_time
            
            return {
                'score': float(np.clip(final_score, 0, 100)),
                'flow_velocity': float(flow_velocity),
                'bid_stack_pressure': float(bid_stack_pressure),
                'ask_stack_pressure': float(ask_stack_pressure)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating DOM momentum: {str(e)}")
            return {
                'score': 50.0,
                'flow_velocity': 0.0,
                'bid_stack_pressure': 0.0,
                'ask_stack_pressure': 0.0
            }

    def detect_large_aggressive_orders(self, bids: np.ndarray, asks: np.ndarray, symbol: str) -> Dict[str, Any]:
        """Detect and alert for large aggressive orders in the orderbook.
        
        Args:
            bids: numpy array of bid orders [price, size]
            asks: numpy array of ask orders [price, size]
            symbol: Trading pair symbol
            
        Returns:
            Dict containing detection results and metrics
        """
        try:
            if len(bids) == 0 or len(asks) == 0:
                return {'detected': False}
            
            current_time = time.time()
            
            # Check alert cooldown
            if current_time - self._last_alert_time < self.alert_cooldown:
                return {'detected': False, 'reason': 'cooldown'}
            
            # Calculate mid price and thresholds
            # Ensure values are converted to float
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid_price = (best_bid + best_ask) / 2
            
            # Calculate USD values using price * size
            # Detect large bids near ask price (aggressive buys)
            aggressive_bids = [
                bid for bid in bids 
                if (float(bid[1]) * float(bid[0])) > self.large_order_threshold_usd and 
                (abs(float(bid[0]) - best_ask) / mid_price) < self.aggressive_price_threshold
            ]
            
            # Detect large asks near bid price (aggressive sells)
            aggressive_asks = [
                ask for ask in asks 
                if (float(ask[1]) * float(ask[0])) > self.large_order_threshold_usd and 
                (abs(float(ask[0]) - best_bid) / mid_price) < self.aggressive_price_threshold
            ]
            
            if aggressive_bids or aggressive_asks:
                # Get the largest order for alert message (in USD)
                largest_bid_usd = max([float(b[0]) * float(b[1]) for b in aggressive_bids], default=0)
                largest_ask_usd = max([float(a[0]) * float(a[1]) for a in aggressive_asks], default=0)
                largest_side = 'bid' if largest_bid_usd > largest_ask_usd else 'ask'
                largest_size_usd = max(largest_bid_usd, largest_ask_usd)
                
                # Find the corresponding order details
                if largest_side == 'bid':
                    largest_order = max(aggressive_bids, key=lambda x: float(x[0]) * float(x[1]))
                else:
                    largest_order = max(aggressive_asks, key=lambda x: float(x[0]) * float(x[1]))
                
                largest_base_size = float(largest_order[1])
                largest_price = float(largest_order[0])
                
                alert_data = {
                    'detected': True,
                    'symbol': symbol,
                    'side': largest_side,
                    'size': largest_base_size,
                    'price': largest_price,
                    'usd_value': largest_size_usd,
                    'aggressive_bids': [{
                        'price': float(b[0]), 
                        'size': float(b[1]),
                        'usd_value': float(b[0]) * float(b[1])
                    } for b in aggressive_bids],
                    'aggressive_asks': [{
                        'price': float(a[0]), 
                        'size': float(a[1]),
                        'usd_value': float(a[0]) * float(a[1])
                    } for a in aggressive_asks],
                    'timestamp': current_time
                }
                
                # Send alert if manager is configured
                if self.alert_manager:
                    alert_msg = (
                        f"Large aggressive {largest_side} detected in {symbol}\n"
                        f"Size: {largest_base_size:.3f} {symbol.split('-')[0]}\n"
                        f"USD Value: ${largest_size_usd:,.2f}\n"
                        f"Price: ${largest_price:,.2f}\n"
                        f"Total orders: {len(aggressive_bids)} bids, {len(aggressive_asks)} asks"
                    )
                    
                    self.alert_manager.send_alert(
                        level="WARNING",
                        message=alert_msg,
                        details={
                            'type': 'large_aggressive_order',
                            **alert_data
                        }
                    )
                    
                    self._last_alert_time = current_time
                
                self.logger.warning(
                    f"Large aggressive orders in {symbol}: "
                    f"{len(aggressive_bids)} bids, {len(aggressive_asks)} asks, "
                    f"largest: ${largest_size_usd:,.2f}"
                )
                
                return alert_data
                
            return {'detected': False}
            
        except Exception as e:
            self.logger.error(f"Error detecting large aggressive orders: {str(e)}")
            return {'detected': False, 'error': str(e)}

    def calculate_pressure(self, orderbook: Dict[str, Any]) -> Dict[str, float]:
        """Calculate orderbook pressure with enhanced sensitivity."""
        try:
            self.logger.debug("\n=== MARKET PRESSURE INDEX (MPI) CALCULATION DEBUG ===")
            
            if not isinstance(orderbook, dict) or 'bids' not in orderbook or 'asks' not in orderbook:
                self.logger.warning("Invalid orderbook structure for pressure calculation")
                return {
                    'score': 50.0,
                    'bid_pressure': 0.0,
                    'ask_pressure': 0.0,
                    'imbalance': 0.0,
                    'ratio': 1.0
                }
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            self.logger.debug(f"Raw orderbook data - Bids: {len(bids)}, Asks: {len(asks)}")
            
            # Use more levels for better precision
            levels_to_use = min(20, len(bids), len(asks))
            if levels_to_use == 0:
                self.logger.warning("No orderbook levels available for pressure calculation")
                return {'score': 50.0, 'bid_pressure': 0.0, 'ask_pressure': 0.0, 'imbalance': 0.0, 'ratio': 1.0}
            
            self.logger.debug(f"Using {levels_to_use} levels for pressure analysis")
            
            # Calculate bid and ask pressure with distance weighting
            bid_pressure = 0
            ask_pressure = 0
            
            # Reference price (mid-point)
            if bids and asks:
                best_bid = float(bids[0][0])
                best_ask = float(asks[0][0])
                mid_price = (best_bid + best_ask) / 2
                spread = best_ask - best_bid
                spread_pct = spread / mid_price
                
                self.logger.debug(f"Reference prices:")
                self.logger.debug(f"  Best bid: {best_bid:.4f}")
                self.logger.debug(f"  Best ask: {best_ask:.4f}")
                self.logger.debug(f"  Mid price: {mid_price:.4f}")
                self.logger.debug(f"  Spread: {spread:.4f} ({spread_pct*10000:.2f} bps)")
            else:
                self.logger.error("No bid/ask data available")
                return {'score': 50.0, 'bid_pressure': 0.0, 'ask_pressure': 0.0, 'imbalance': 0.0, 'ratio': 1.0}
                
            # Calculate weighted pressure with detailed distance-based weighting
            self.logger.debug("\nDistance-weighted pressure calculation:")
            self.logger.debug("Level | Bid Price | Bid Qty | Distance | Weight | Weighted")
            self.logger.debug("-" * 70)
            
            for i in range(levels_to_use):
                if i < len(bids):
                    bid_price, bid_qty = float(bids[i][0]), float(bids[i][1])
                    # More weight to closer levels - quadratic decrease
                    price_factor = 1 - ((mid_price - bid_price) / mid_price)**2
                    # Apply greater weight to levels close to the mid price
                    weighted_bid = bid_qty * price_factor**2
                    bid_pressure += weighted_bid
                    
                    if i < 5:  # Log first 5 levels
                        distance = (mid_price - bid_price) / mid_price
                        self.logger.debug(f"B{i+1:2d}   | {bid_price:9.4f} | {bid_qty:7.2f} | {distance:8.4f} | {price_factor**2:6.4f} | {weighted_bid:8.2f}")
                    
                if i < len(asks):
                    ask_price, ask_qty = float(asks[i][0]), float(asks[i][1])
                    # More weight to closer levels - quadratic decrease
                    price_factor = 1 - ((ask_price - mid_price) / mid_price)**2
                    # Apply greater weight to levels close to the mid price
                    weighted_ask = ask_qty * price_factor**2
                    ask_pressure += weighted_ask
                    
                    if i < 5:  # Log first 5 levels
                        distance = (ask_price - mid_price) / mid_price
                        self.logger.debug(f"A{i+1:2d}   | {ask_price:9.4f} | {ask_qty:7.2f} | {distance:8.4f} | {price_factor**2:6.4f} | {weighted_ask:8.2f}")
            
            self.logger.debug(f"\nPressure totals:")
            self.logger.debug(f"  Total bid pressure: {bid_pressure:.2f}")
            self.logger.debug(f"  Total ask pressure: {ask_pressure:.2f}")
            
            # Calculate pressure metrics
            if ask_pressure == 0:
                ratio = float('inf')
                imbalance = 1.0
                self.logger.debug("  Ask pressure is zero - infinite ratio")
            elif bid_pressure == 0:
                ratio = 0.0
                imbalance = -1.0
                self.logger.debug("  Bid pressure is zero - zero ratio")
            else:
                ratio = bid_pressure / ask_pressure
                imbalance = (bid_pressure - ask_pressure) / (bid_pressure + ask_pressure)
                self.logger.debug(f"  Pressure ratio: {ratio:.4f}")
                self.logger.debug(f"  Pressure imbalance: {imbalance:.4f}")
                
            # Calculate volume concentration at top of book
            top_bid_levels = min(3, len(bids))
            top_ask_levels = min(3, len(asks))
            
            top_bid_vol = sum(float(bids[i][1]) for i in range(top_bid_levels))
            top_ask_vol = sum(float(asks[i][1]) for i in range(top_ask_levels))
            
            total_bid_vol = sum(float(bids[i][1]) for i in range(min(levels_to_use, len(bids))))
            total_ask_vol = sum(float(asks[i][1]) for i in range(min(levels_to_use, len(asks))))
            
            bid_concentration = top_bid_vol / total_bid_vol if total_bid_vol > 0 else 0
            ask_concentration = top_ask_vol / total_ask_vol if total_ask_vol > 0 else 0
            
            self.logger.debug(f"\nVolume concentration analysis:")
            self.logger.debug(f"  Top 3 bid volume: {top_bid_vol:.2f} / {total_bid_vol:.2f} = {bid_concentration:.3f}")
            self.logger.debug(f"  Top 3 ask volume: {top_ask_vol:.2f} / {total_ask_vol:.2f} = {ask_concentration:.3f}")
            
            # Factor in concentration and spread
            # High concentration means more effective pressure
            bid_pressure_adjusted = bid_pressure * (1 + bid_concentration)
            ask_pressure_adjusted = ask_pressure * (1 + ask_concentration)
            
            self.logger.debug(f"\nConcentration-adjusted pressure:")
            self.logger.debug(f"  Adjusted bid pressure: {bid_pressure:.2f} × {1 + bid_concentration:.3f} = {bid_pressure_adjusted:.2f}")
            self.logger.debug(f"  Adjusted ask pressure: {ask_pressure:.2f} × {1 + ask_concentration:.3f} = {ask_pressure_adjusted:.2f}")
            
            # Recalculate imbalance with adjusted pressures
            if bid_pressure_adjusted + ask_pressure_adjusted > 0:
                imbalance_adjusted = (bid_pressure_adjusted - ask_pressure_adjusted) / (bid_pressure_adjusted + ask_pressure_adjusted)
            else:
                imbalance_adjusted = 0
                
            self.logger.debug(f"  Adjusted imbalance: {imbalance_adjusted:.4f}")
                
            # Factor in spread - tighter spread means more conviction
            # Moderate impact: narrower spread increases importance of imbalance
            spread_factor = np.clip(1 - (spread_pct * 50), 0.5, 1.5)  # Limits impact
            
            self.logger.debug(f"\nSpread factor analysis:")
            self.logger.debug(f"  Spread percentage: {spread_pct*100:.4f}%")
            self.logger.debug(f"  Spread factor: {spread_factor:.3f}")
            
            # Calculate score based on imbalance with spread factor
            score = 50 * (1 + imbalance_adjusted * spread_factor)
            
            self.logger.debug(f"\nFinal score calculation:")
            self.logger.debug(f"  Score = 50 * (1 + imbalance_adjusted * spread_factor)")
            self.logger.debug(f"  Score = 50 * (1 + {imbalance_adjusted:.4f} * {spread_factor:.3f})")
            self.logger.debug(f"  Score = 50 * (1 + {imbalance_adjusted * spread_factor:.4f})")
            self.logger.debug(f"  Score = {score:.2f}")
            
            # Log significant imbalance
            if abs(imbalance_adjusted) > 0.3:
                direction = "bid" if imbalance_adjusted > 0 else "ask"
                self.logger.info(f"Significant orderbook imbalance: {imbalance_adjusted:.2f} ({direction} dominance)")
            
            return {
                'score': float(np.clip(score, 0, 100)),
                'bid_pressure': float(bid_pressure),
                'ask_pressure': float(ask_pressure),
                'bid_adj': float(bid_pressure_adjusted),
                'ask_adj': float(ask_pressure_adjusted),
                'imbalance': float(imbalance),
                'imbalance_adj': float(imbalance_adjusted),
                'spread_factor': float(spread_factor),
                'ratio': float(np.clip(ratio, 0.01, 100.0))
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating orderbook pressure: {str(e)}")
            self.logger.debug(f"Pressure calculation error details: {traceback.format_exc()}")
            return {
                'score': 50.0,
                'bid_pressure': 0.0,
                'ask_pressure': 0.0,
                'imbalance': 0.0,
                'ratio': 1.0
            }

    def _calculate_liquidity_score(self, market_data: Dict[str, Any]) -> float:
        """Calculate liquidity score based on orderbook depth and spread."""
        try:
            self.logger.debug("\n=== LIQUIDITY SCORE CALCULATION DEBUG ===")
            
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            self.logger.debug(f"Raw orderbook data - Bids: {len(bids)}, Asks: {len(asks)}")
            
            if not bids or not asks:
                self.logger.warning("Empty orderbook data for liquidity calculation")
                return 50.0
                
            # Calculate spread
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            spread = (best_ask - best_bid) / best_bid
            
            self.logger.debug(f"Spread analysis:")
            self.logger.debug(f"  Best bid: {best_bid:.4f}")
            self.logger.debug(f"  Best ask: {best_ask:.4f}")
            self.logger.debug(f"  Absolute spread: {best_ask - best_bid:.4f}")
            self.logger.debug(f"  Relative spread: {spread:.6f} ({spread*10000:.2f} bps)")
            
            # Calculate depth (volume within 1% of mid price)
            mid_price = (best_bid + best_ask) / 2
            depth_range = mid_price * 0.01
            
            self.logger.debug(f"Depth analysis (1% range):")
            self.logger.debug(f"  Mid price: {mid_price:.4f}")
            self.logger.debug(f"  Depth range: ±{depth_range:.4f}")
            self.logger.debug(f"  Range: {mid_price - depth_range:.4f} - {mid_price + depth_range:.4f}")
            
            bid_depth = sum(float(bid[1]) for bid in bids if float(bid[0]) >= mid_price - depth_range)
            ask_depth = sum(float(ask[1]) for ask in asks if float(ask[0]) <= mid_price + depth_range)
            
            total_depth = bid_depth + ask_depth
            
            self.logger.debug(f"  Bid depth in range: {bid_depth:.2f}")
            self.logger.debug(f"  Ask depth in range: {ask_depth:.2f}")
            self.logger.debug(f"  Total depth: {total_depth:.2f}")
            
            # Normalize spread (lower is better)
            spread_score = 100 * (1 - min(spread * 200, 0.9))  # Cap at 90% reduction
            self.logger.debug(f"Spread score calculation:")
            self.logger.debug(f"  Spread penalty: {min(spread * 200, 0.9):.4f}")
            self.logger.debug(f"  Spread score: {spread_score:.2f}")
            
            # Normalize depth (higher is better)
            # Use log scale to handle large variations in depth
            depth_score = 50 * (1 + min(math.log1p(total_depth) / 10, 1.0))
            self.logger.debug(f"Depth score calculation:")
            self.logger.debug(f"  Log depth factor: {min(math.log1p(total_depth) / 10, 1.0):.4f}")
            self.logger.debug(f"  Depth score: {depth_score:.2f}")
            
            # Combine with 60% weight on depth, 40% on spread
            liquidity_score = 0.6 * depth_score + 0.4 * spread_score
            
            self.logger.debug(f"Final liquidity score calculation:")
            self.logger.debug(f"  Depth component: {depth_score:.2f} × 0.6 = {depth_score * 0.6:.2f}")
            self.logger.debug(f"  Spread component: {spread_score:.2f} × 0.4 = {spread_score * 0.4:.2f}")
            self.logger.debug(f"  Final liquidity score: {liquidity_score:.2f}")
            
            return float(np.clip(liquidity_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating liquidity score: {str(e)}")
            self.logger.debug(f"Liquidity calculation error details: {traceback.format_exc()}")
            return 50.0

    def _get_imbalance_ratio(self, market_data: Dict[str, Any]) -> float:
        """Calculate the bid/ask imbalance ratio from orderbook data."""
        try:
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return 50.0  # Neutral ratio when data is missing
                
            # Calculate total volume on bid and ask sides (up to depth_levels)
            bid_volume = sum(float(bid[1]) for bid in bids[:self.depth_levels])
            ask_volume = sum(float(ask[1]) for ask in asks[:self.depth_levels])
            
            # Calculate imbalance ratio (bid volume / ask volume)
            if ask_volume > 0:
                ratio = bid_volume / ask_volume
            else:
                ratio = 2.0  # Strong bid imbalance if no asks
            
            # Log raw imbalance ratio
            self.logger.debug(f"Raw bid/ask imbalance ratio: {ratio:.4f}")
            
            # Convert ratio to a score from 0-100 where 50 is balanced
            # 1.0 means equal volume, >1.0 means more bids, <1.0 means more asks
            if ratio >= 1.0:
                # More bids than asks (ratio > 1.0)
                raw_score = 50.0 + 50.0 * min((ratio - 1.0) / 2.0, 1.0)
            else:
                # More asks than bids (ratio < 1.0)
                raw_score = 50.0 - 50.0 * min((1.0 - ratio) / 1.0, 1.0)
            
            # Apply sigmoid transformation using config values
            transformed_score = self._apply_sigmoid_transformation(
                raw_score, 
                sensitivity=self.imbalance_sensitivity, 
                center=50.0
            )
            
            self.logger.debug(f"Imbalance ratio={ratio:.2f}, raw_score={raw_score:.2f}, transformed={transformed_score:.2f}")
            
            # Return the transformed score
            return float(transformed_score)
                
        except Exception as e:
            self.logger.error(f"Error calculating imbalance ratio: {str(e)}")
            return 50.0  # Return neutral score on error

    def _get_liquidity_ratio(self, market_data: Dict[str, Any]) -> float:
        """Calculate the liquidity ratio from orderbook data."""
        try:
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return 1.0  # Neutral ratio
                
            # Calculate best bid/ask
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid_price = (best_bid + best_ask) / 2
            
            # Calculate depth within 0.5% of mid price
            depth_range = mid_price * 0.005
            
            close_bid_volume = sum(float(bid[1]) for bid in bids if float(bid[0]) >= mid_price - depth_range)
            close_ask_volume = sum(float(ask[1]) for ask in asks if float(ask[0]) <= mid_price + depth_range)
            
            # Calculate total volume
            total_bid_volume = sum(float(bid[1]) for bid in bids)
            total_ask_volume = sum(float(ask[1]) for ask in asks)
            
            # Calculate concentration ratio (volume close to mid / total volume)
            if total_bid_volume > 0 and total_ask_volume > 0:
                bid_concentration = close_bid_volume / total_bid_volume
                ask_concentration = close_ask_volume / total_ask_volume
                liquidity_ratio = (bid_concentration + ask_concentration) / 2
            else:
                liquidity_ratio = 0.5  # Neutral if no volume
                
            return float(liquidity_ratio)
            
        except Exception as e:
            self.logger.error(f"Error calculating liquidity ratio: {str(e)}")
            return 0.5

    def _calculate_price_impact_score(self, market_data: Dict[str, Any]) -> float:
        """Calculate score based on price impact of a standard order size."""
        try:
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return 50.0
                
            # Get symbol from market data
            symbol = market_data.get('symbol', 'UNKNOWN')
            
            # Determine standard order size based on symbol
            # This is a simplified approach - in production, you'd use more sophisticated logic
            if 'BTC' in symbol:
                standard_size = 1.0  # 1 BTC
            elif 'ETH' in symbol:
                standard_size = 10.0  # 10 ETH
            else:
                standard_size = 100.0  # Default
                
            # Calculate price impact for buy order
            impact_buy = self._calculate_price_impact(asks, standard_size)
            
            # Calculate price impact for sell order
            impact_sell = self._calculate_price_impact(bids, standard_size)
            
            # Average the impacts
            avg_impact = (impact_buy + impact_sell) / 2
            
            # Convert to score (lower impact is better)
            # Impact of 0.1% (0.001) or less is excellent (score 100)
            # Impact of 1% (0.01) or more is poor (score 0)
            impact_score = 100 * (1 - min(avg_impact * 100, 1.0))
            
            return float(np.clip(impact_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating price impact score: {str(e)}")
            return 50.0

    def _get_price_impact(self, market_data: Dict[str, Any]) -> float:
        """Get the raw price impact value for a standard order."""
        try:
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return 0.005  # Default 0.5% impact
                
            # Get symbol from market data
            symbol = market_data.get('symbol', 'UNKNOWN')
            
            # Determine standard order size based on symbol
            if 'BTC' in symbol:
                standard_size = 1.0  # 1 BTC
            elif 'ETH' in symbol:
                standard_size = 10.0  # 10 ETH
            else:
                standard_size = 100.0  # Default
                
            # Calculate price impact for buy order
            impact_buy = self._calculate_price_impact(asks, standard_size)
            
            # Calculate price impact for sell order
            impact_sell = self._calculate_price_impact(bids, standard_size)
            
            # Average the impacts
            avg_impact = (impact_buy + impact_sell) / 2
            
            return float(avg_impact)
            
        except Exception as e:
            self.logger.error(f"Error calculating price impact: {str(e)}")
            return 0.005

    def _calculate_price_impact(self, orders: List[List[float]], size: float) -> float:
        """Calculate price impact of executing an order of given size."""
        try:
            if not orders:
                return 0.01  # Default 1% impact
                
            remaining_size = size
            initial_price = float(orders[0][0])
            executed_value = 0.0
            
            for price, amount in orders:
                price = float(price)
                amount = float(amount)
                
                if remaining_size <= 0:
                    break
                    
                executed = min(amount, remaining_size)
                executed_value += executed * price
                remaining_size -= executed
                
            if size - remaining_size <= 0:
                return 0.01  # Not enough liquidity
                
            # Calculate average execution price
            avg_price = executed_value / (size - remaining_size)
            
            # Calculate price impact as percentage
            if initial_price > 0:
                impact = abs(avg_price - initial_price) / initial_price
            else:
                impact = 0.01
                
            return float(impact)
            
        except Exception as e:
            self.logger.error(f"Error in price impact calculation: {str(e)}")
            return 0.01

    def _calculate_depth_score(self, market_data: Dict[str, Any]) -> float:
        """Calculate score based on orderbook depth."""
        try:
            self.logger.debug("\n=== DEPTH SCORE CALCULATION DEBUG ===")
            
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            self.logger.debug(f"Raw orderbook data - Bids: {len(bids)}, Asks: {len(asks)}")
            
            if not bids or not asks:
                self.logger.warning("Empty orderbook data for depth calculation")
                return 50.0
                
            # Calculate best bid/ask
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid_price = (best_bid + best_ask) / 2
            
            self.logger.debug(f"Price levels - Best bid: {best_bid:.4f}, Best ask: {best_ask:.4f}, Mid: {mid_price:.4f}")
            
            # Calculate depth at different price levels
            levels = [0.001, 0.005, 0.01, 0.02, 0.05]  # 0.1%, 0.5%, 1%, 2%, 5%
            weights = [0.35, 0.25, 0.20, 0.15, 0.05]   # More weight to closer levels
            
            self.logger.debug("Depth analysis at different price levels:")
            self.logger.debug("Level | Range | Weight | Bid Depth | Ask Depth | Balance | Level Score")
            self.logger.debug("-" * 80)
            
            depth_scores = []
            
            for i, (level, weight) in enumerate(zip(levels, weights)):
                range_min = mid_price * (1 - level)
                range_max = mid_price * (1 + level)
                
                bid_depth = sum(float(bid[1]) for bid in bids if float(bid[0]) >= range_min)
                ask_depth = sum(float(ask[1]) for ask in asks if float(ask[0]) <= range_max)
                
                # Calculate balance between bid and ask depth
                total_depth = bid_depth + ask_depth
                if total_depth > 0:
                    balance = 1 - abs(bid_depth - ask_depth) / total_depth
                else:
                    balance = 0
                    
                # Calculate depth score for this level
                # Use log scale to handle large variations in depth
                level_score = 50 * (1 + min(math.log1p(total_depth) / 10, 1.0))
                
                # Adjust for balance (perfect balance = 1.0 multiplier)
                balanced_score = level_score * (0.5 + 0.5 * balance)
                
                depth_scores.append(balanced_score * weight)
                
                self.logger.debug(f"{level*100:5.1f}% | {range_min:.4f}-{range_max:.4f} | {weight:6.2f} | {bid_depth:9.2f} | {ask_depth:9.2f} | {balance:7.3f} | {balanced_score:10.2f}")
                
            # Sum weighted scores
            final_depth_score = sum(depth_scores)
            
            self.logger.debug(f"\nDepth score components:")
            for i, (level, weight, score) in enumerate(zip(levels, weights, depth_scores)):
                self.logger.debug(f"  Level {level*100:.1f}%: {score:.2f} (weight: {weight:.2f})")
            
            self.logger.debug(f"Final depth score: {final_depth_score:.2f}")
            
            return float(np.clip(final_depth_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating depth score: {str(e)}")
            self.logger.debug(f"Depth calculation error details: {traceback.format_exc()}")
            return 50.0

    def _get_depth_ratio(self, market_data: Dict[str, Any]) -> float:
        """Get the bid/ask depth ratio."""
        try:
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return 1.0  # Neutral ratio
                
            # Calculate best bid/ask
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid_price = (best_bid + best_ask) / 2
            
            # Calculate depth within 2% of mid price
            depth_range = mid_price * 0.02
            
            bid_depth = sum(float(bid[1]) for bid in bids if float(bid[0]) >= mid_price - depth_range)
            ask_depth = sum(float(ask[1]) for ask in asks if float(ask[0]) <= mid_price + depth_range)
            
            # Calculate depth ratio (bid depth / ask depth)
            if ask_depth > 0:
                ratio = bid_depth / ask_depth
            else:
                ratio = 2.0  # Strong bid depth if no asks
                
            return float(ratio)
            
        except Exception as e:
            self.logger.error(f"Error calculating depth ratio: {str(e)}")
            return 1.0

    def _calculate_sr_from_orderbook(self, market_data: Dict[str, Any]) -> float:
        """Calculate support/resistance score from orderbook data."""
        try:
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return 50.0
                
            # Group orders by price levels to find clusters
            price_levels = 20  # Number of price levels to analyze
            price_step = 0.002  # 0.2% steps
            
            # Get current price
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid_price = (best_bid + best_ask) / 2
            
            # Create price bins
            min_price = mid_price * (1 - price_levels * price_step / 2)
            max_price = mid_price * (1 + price_levels * price_step / 2)
            price_bins = np.linspace(min_price, max_price, price_levels + 1)
            
            # Initialize volume arrays
            bid_volumes = np.zeros(price_levels)
            ask_volumes = np.zeros(price_levels)
            
            # Distribute bid volumes into bins
            for bid in bids:
                price = float(bid[0])
                volume = float(bid[1])
                
                if price < min_price:
                    continue
                    
                bin_index = min(int((price - min_price) / (max_price - min_price) * price_levels), price_levels - 1)
                if 0 <= bin_index < price_levels:
                    bid_volumes[bin_index] += volume
            
            # Distribute ask volumes into bins
            for ask in asks:
                price = float(ask[0])
                volume = float(ask[1])
                
                if price > max_price:
                    continue
                    
                bin_index = min(int((price - min_price) / (max_price - min_price) * price_levels), price_levels - 1)
                if 0 <= bin_index < price_levels:
                    ask_volumes[bin_index] += volume
            
            # Find support levels (high bid volume)
            support_strength = np.max(bid_volumes) / (np.mean(bid_volumes) + 1e-10)
            
            # Find resistance levels (high ask volume)
            resistance_strength = np.max(ask_volumes) / (np.mean(ask_volumes) + 1e-10)
            
            # Calculate overall S/R strength
            sr_strength = (support_strength + resistance_strength) / 2
            
            # Convert to score (higher strength = higher score)
            # Strength of 1.0 is average (score 50)
            # Strength of 3.0 or more is strong (score 100)
            sr_score = 50 * (1 + min((sr_strength - 1) / 2, 1.0))
            
            return float(np.clip(sr_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating S/R score: {str(e)}")
            return 50.0

    def _get_sr_strength(self, market_data: Dict[str, Any]) -> float:
        """Get the raw support/resistance strength value."""
        try:
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return 1.0  # Neutral strength
                
            # Group orders by price levels to find clusters
            price_levels = 20  # Number of price levels to analyze
            price_step = 0.002  # 0.2% steps
            
            # Get current price
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid_price = (best_bid + best_ask) / 2
            
            # Create price bins
            min_price = mid_price * (1 - price_levels * price_step / 2)
            max_price = mid_price * (1 + price_levels * price_step / 2)
            price_bins = np.linspace(min_price, max_price, price_levels + 1)
            
            # Initialize volume arrays
            bid_volumes = np.zeros(price_levels)
            ask_volumes = np.zeros(price_levels)
            
            # Distribute bid volumes into bins
            for bid in bids:
                price = float(bid[0])
                volume = float(bid[1])
                
                if price < min_price:
                    continue
                    
                bin_index = min(int((price - min_price) / (max_price - min_price) * price_levels), price_levels - 1)
                if 0 <= bin_index < price_levels:
                    bid_volumes[bin_index] += volume
            
            # Distribute ask volumes into bins
            for ask in asks:
                price = float(ask[0])
                volume = float(ask[1])
                
                if price > max_price:
                    continue
                    
                bin_index = min(int((price - min_price) / (max_price - min_price) * price_levels), price_levels - 1)
                if 0 <= bin_index < price_levels:
                    ask_volumes[bin_index] += volume
            
            # Find support levels (high bid volume)
            support_strength = np.max(bid_volumes) / (np.mean(bid_volumes) + 1e-10)
            
            # Find resistance levels (high ask volume)
            resistance_strength = np.max(ask_volumes) / (np.mean(ask_volumes) + 1e-10)
            
            # Calculate overall S/R strength
            sr_strength = (support_strength + resistance_strength) / 2
            
            return float(sr_strength)
            
        except Exception as e:
            self.logger.error(f"Error calculating S/R strength: {str(e)}")
            return 1.0

    @property
    def required_data(self) -> List[str]:
        """Return the required data types for this indicator."""
        return ['orderbook']
        
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input data for orderbook analysis.
        
        Args:
            data: Dictionary containing market data
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            self.logger.debug("\n=== Starting Orderbook Validation ===")
            
            # First check base requirements
            self.logger.debug("Checking base requirements...")
            if not self._validate_base_requirements(data):
                self.logger.error("Base requirements validation failed")
                return False
                
            # Orderbook-specific validation
            if 'orderbook' not in data:
                self.logger.error("Missing orderbook data")
                return False
                
            orderbook = data.get('orderbook', {})
            
            # Check if orderbook has bids and asks
            if 'bids' not in orderbook or 'asks' not in orderbook:
                self.logger.error("Orderbook missing bids or asks")
                return False
                
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            # Check if bids and asks are not empty
            if len(bids) == 0 or len(asks) == 0:
                self.logger.error(f"Empty orderbook data: bids={len(bids)}, asks={len(asks)}")
                return False
                
            # Check if bids and asks are in the correct format
            if not isinstance(bids, (list, np.ndarray)) or not isinstance(asks, (list, np.ndarray)):
                self.logger.error(f"Invalid orderbook data types: bids={type(bids)}, asks={type(asks)}")
                return False
                
            # Convert to numpy arrays if they are lists
            if isinstance(bids, list):
                bids = np.array(bids)
            if isinstance(asks, list):
                asks = np.array(asks)
                
            # Check if arrays have at least 2 dimensions (price and quantity)
            if bids.ndim < 2 or asks.ndim < 2:
                self.logger.error(f"Invalid orderbook dimensions: bids={bids.ndim}, asks={asks.ndim}")
                return False
                
            # Check if arrays have at least one entry
            if bids.shape[0] == 0 or asks.shape[0] == 0:
                self.logger.error(f"Empty orderbook arrays: bids={bids.shape}, asks={asks.shape}")
                return False
                
            # Check if arrays have at least price and quantity columns
            if bids.shape[1] < 2 or asks.shape[1] < 2:
                self.logger.error(f"Insufficient orderbook columns: bids={bids.shape}, asks={asks.shape}")
                return False
                
            self.logger.debug("\nOrderbook validation successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in orderbook data validation: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False
            
    def _validate_base_requirements(self, data: Dict[str, Any]) -> bool:
        """Validate base requirements for market data.
        
        Args:
            data: Dictionary containing market data
            
        Returns:
            bool: True if base requirements are met, False otherwise
        """
        try:
            # Check if data is a dictionary
            if not isinstance(data, dict):
                self.logger.error(f"Invalid data type: {type(data)}")
                return False
                
            # Check for required fields (exchange field is optional)
            required_fields = ['symbol']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                self.logger.error(f"Missing required fields: {missing_fields}")
                return False
                
            # Optional fields with defaults
            if 'timestamp' not in data:
                data['timestamp'] = int(time.time() * 1000)
                self.logger.debug("Added default timestamp to market data")
                
            if 'exchange' not in data:
                data['exchange'] = 'unknown'
                self.logger.debug("Added default exchange to market data")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error in base requirements validation: {str(e)}")
            return False
            
    async def calculate(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate orderbook indicator scores with detailed analysis.
        
        Args:
            market_data: Dictionary containing orderbook and other market data
            
        Returns:
            Dict containing indicator scores, components, signals and metadata
        """
        try:
            method_start_time = time.time()  # Overall method timing (includes I/O)
            self.logger.info("\n=== ORDERBOOK INDICATORS Detailed Calculation ===")
            
            # Validate input
            if not self.validate_input(market_data):
                self.logger.error("Invalid input data for orderbook analysis")
                return {
                    'score': 50.0,
                    'components': {},
                    'signals': {},
                    'metadata': {'error': 'Invalid input data'}
                }
            
            # Log data quality metrics
            self._log_data_quality_metrics(market_data)
            
            # Extract symbol and orderbook data
            symbol = market_data.get('symbol', '')
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            # Convert to numpy arrays if needed
            if not isinstance(bids, np.ndarray):
                bids = np.array(bids, dtype=float)
            if not isinstance(asks, np.ndarray):
                asks = np.array(asks, dtype=float)
            
            # Start calculation timer (excludes I/O and prep work above)
            calc_start_time = time.time()
            
            # Calculate component scores with timing
            component_scores = {}
            component_times = {}
            
            # Imbalance Score
            comp_start = time.time()
            imbalance_score = self._calculate_orderbook_imbalance(market_data)
            component_scores['imbalance'] = imbalance_score
            component_times['imbalance'] = (time.time() - comp_start) * 1000
            imbalance_ratio = self._get_imbalance_ratio(market_data)
            self.logger.info(f"Bid/Ask Imbalance: Ratio={imbalance_ratio:.4f}, Score={imbalance_score:.2f}")
            
            # Depth Score
            comp_start = time.time()
            depth_score = self._calculate_depth_score(market_data)
            component_scores['depth'] = depth_score
            component_times['depth'] = (time.time() - comp_start) * 1000
            depth_ratio = self._get_depth_ratio(market_data)
            self.logger.info(f"Depth Ratio: Value={depth_ratio:.4f}, Score={depth_score:.2f}")
            
            # Liquidity Score
            comp_start = time.time()
            liquidity_score = self._calculate_liquidity_score(market_data)
            component_scores['liquidity'] = liquidity_score
            component_times['liquidity'] = (time.time() - comp_start) * 1000
            liquidity_ratio = self._get_liquidity_ratio(market_data)
            self.logger.info(f"Liquidity: Ratio={liquidity_ratio:.4f}, Score={liquidity_score:.2f}")
            
            # Absorption/Exhaustion Score
            comp_start = time.time()
            absorption_result = self.calculate_absorption_exhaustion(bids, asks)
            absorption_score = absorption_result['combined_score']
            component_scores['absorption_exhaustion'] = absorption_score
            component_times['absorption_exhaustion'] = (time.time() - comp_start) * 1000
            self.logger.info(f"Absorption/Exhaustion: Score={absorption_score:.2f}")
            
            # Market Pressure Index (MPI)
            comp_start = time.time()
            pressure_data = self.calculate_pressure(orderbook)
            mpi_score = pressure_data['score']
            component_scores['mpi'] = mpi_score
            component_times['mpi'] = (time.time() - comp_start) * 1000
            self.logger.info(f"Market Pressure Index: Score={mpi_score:.2f}, Imbalance={pressure_data['imbalance']:.4f}")
            
            # OIR Score (Academic #1 metric)
            comp_start = time.time()
            oir_score = self._calculate_oir_score(bids, asks)
            component_scores['oir'] = oir_score
            component_times['oir'] = (time.time() - comp_start) * 1000
            self.logger.info(f"OIR (Order Imbalance Ratio): Score={oir_score:.2f}")
            
            # DI Score (Academic #2 metric)
            comp_start = time.time()
            di_score = self._calculate_di_score(bids, asks)
            component_scores['di'] = di_score
            component_times['di'] = (time.time() - comp_start) * 1000
            self.logger.info(f"DI (Depth Imbalance): Score={di_score:.2f}")
            
            # Integrated Manipulation Detection
            comp_start = time.time()
            trades = market_data.get('trades', [])
            manipulation_result = self._analyze_manipulation_integrated(
                orderbook=orderbook,
                trades=trades,
                previous_orderbook=self.previous_orderbook
            )
            
            # Convert manipulation likelihood to score (0-100, where 50 is neutral)
            # High manipulation likelihood = LOW score (bearish for signal quality)
            manipulation_score = 50.0 * (1 - manipulation_result['overall_likelihood'])
            if manipulation_result['overall_likelihood'] > 0:
                manipulation_score += 50.0 * (1 - manipulation_result['overall_likelihood'])
            
            component_scores['manipulation'] = manipulation_score
            component_times['manipulation'] = (time.time() - comp_start) * 1000
            
            # Log manipulation detection results
            if manipulation_result['overall_likelihood'] > 0.5:
                self.logger.warning(
                    f"Market manipulation detected: "
                    f"Type={manipulation_result['manipulation_type']}, "
                    f"Likelihood={manipulation_result['overall_likelihood']:.2%}, "
                    f"Severity={manipulation_result['severity']}"
                )
                
                # Send alert for high-confidence manipulation
                if (manipulation_result['overall_likelihood'] > 0.7 and 
                    hasattr(self, 'alert_manager') and self.alert_manager):
                    await self._send_manipulation_alert(symbol, manipulation_result)
            
            # Calculate final score using component weights
            final_score = self._compute_weighted_score(component_scores)
            
            # Adjust confidence based on manipulation detection
            confidence_multiplier = 1.0
            if manipulation_result['overall_likelihood'] > 0.7:
                confidence_multiplier = 0.7
            elif manipulation_result['overall_likelihood'] > 0.5:
                confidence_multiplier = 0.85
            
            # Log performance metrics (use calculation time, not total method time)
            calc_time = (time.time() - calc_start_time) * 1000  # Actual calculation time
            total_method_time = (time.time() - method_start_time) * 1000  # Total including I/O
            io_time = total_method_time - calc_time
            
            # Log timing breakdown if there's significant I/O time
            if io_time > 100:
                self.logger.debug(f"Timing breakdown - I/O: {io_time:.1f}ms, Calculations: {calc_time:.1f}ms")
            
            # Use calculation time for performance warnings, not total time
            self._log_performance_metrics(component_times, calc_time)
            
            # Log component contribution breakdown and final score
            self.log_indicator_results(final_score, component_scores, symbol)
            
            # Get signals
            signals = await self.get_signals(market_data)
            
            # Collect raw values for metadata
            raw_values = {
                'imbalance_ratio': float(imbalance_ratio),
                'depth_ratio': float(depth_ratio),
                'liquidity_ratio': float(liquidity_ratio),
                'absorption': float(absorption_result['absorption_score']),
                'exhaustion': float(absorption_result['exhaustion_score']),
                'mpi_imbalance': float(pressure_data['imbalance']),
                'oir_score': float(oir_score),
                'di_score': float(di_score),
                'manipulation_likelihood': float(manipulation_result['overall_likelihood']),
                'manipulation_type': manipulation_result['manipulation_type']
            }
            
            # Generate interpretation using centralized interpreter
            try:
                interpreter = InterpretationGenerator()
                interpretation_data = {
                    'score': final_score,
                    'components': component_scores,
                    'signals': signals,
                    'metadata': {'raw_values': raw_values}
                }
                interpretation = interpreter._interpret_orderbook(interpretation_data)
            except Exception as e:
                self.logger.error(f"Error generating orderbook interpretation: {str(e)}")
                # Fallback interpretation
                if final_score > 65:
                    interpretation = f"Strong bullish orderbook (score: {final_score:.1f})"
                elif final_score < 35:
                    interpretation = f"Strong bearish orderbook (score: {final_score:.1f})"
                else:
                    interpretation = f"Neutral orderbook conditions (score: {final_score:.1f})"
            
            # Calculate confidence with manipulation adjustment
            base_confidence = self._calculate_confidence_level(component_scores)
            adjusted_confidence = base_confidence * confidence_multiplier
            
            # Return standardized format
            return {
                'score': float(np.clip(final_score, 0, 100)),
                'components': component_scores,
                'signals': signals,
                'interpretation': interpretation,
                'confidence': adjusted_confidence,
                'manipulation_analysis': manipulation_result,
                'metadata': {
                    'timestamp': int(time.time() * 1000),
                    'component_weights': self.component_weights,
                    'raw_values': raw_values,
                    'performance': {
                        'total_time_ms': calc_time,
                        'component_times_ms': component_times
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating orderbook score: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {
                'score': 50.0,
                'components': {},
                'signals': {},
                'metadata': {'error': str(e)}
            }
            
    def _log_data_quality_metrics(self, market_data: Dict[str, Any]) -> None:
        """Log data quality and completeness metrics."""
        try:
            self.logger.info("\n--- Data Quality Assessment ---")
            
            # Orderbook quality
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            bid_levels = len(bids)
            ask_levels = len(asks)
            
            self.logger.info(f"Orderbook Depth: {bid_levels} bids, {ask_levels} asks")
            
            if bid_levels >= 20 and ask_levels >= 20:
                depth_quality = "Excellent"
            elif bid_levels >= 10 and ask_levels >= 10:
                depth_quality = "Good"
            elif bid_levels >= 5 and ask_levels >= 5:
                depth_quality = "Fair"
            else:
                depth_quality = "Poor"
                
            self.logger.info(f"Depth Quality: {depth_quality}")
            
            # Spread quality
            if bids and asks:
                spread = (float(asks[0][0]) - float(bids[0][0])) / float(bids[0][0])
                spread_bps = spread * 10000
                
                if spread_bps <= 1:
                    spread_quality = "Excellent"
                elif spread_bps <= 5:
                    spread_quality = "Good"
                elif spread_bps <= 20:
                    spread_quality = "Fair"
                else:
                    spread_quality = "Poor"
                    
                self.logger.info(f"Spread: {spread_bps:.1f} bps ({spread_quality})")
                
            # Data freshness
            timestamp = market_data.get('timestamp', time.time() * 1000)
            age_seconds = (time.time() * 1000 - timestamp) / 1000
            
            if age_seconds <= 1:
                freshness = "Excellent"
            elif age_seconds <= 5:
                freshness = "Good"
            elif age_seconds <= 30:
                freshness = "Fair"
            else:
                freshness = "Stale"
                
            self.logger.info(f"Data Age: {age_seconds:.1f}s ({freshness})")
            
        except Exception as e:
            self.logger.error(f"Error logging data quality metrics: {str(e)}")
            
    def _log_performance_metrics(self, component_times: Dict[str, float], total_time: float) -> None:
        """Log performance timing metrics."""
        try:
            self.logger.info("\n--- Performance Metrics ---")
            self.logger.info(f"Total Calculation Time: {total_time:.1f}ms")
            
            # Sort components by time taken
            sorted_times = sorted(component_times.items(), key=lambda x: x[1], reverse=True)
            
            self.logger.info("Component Timing (slowest first):")
            for component, time_ms in sorted_times:
                percentage = (time_ms / total_time) * 100
                self.logger.info(f"  {component}: {time_ms:.1f}ms ({percentage:.1f}%)")
                
            # Performance warnings
            if total_time > 150:
                self.logger.warning(f"⚠️  Slow calculation detected: {total_time:.1f}ms")
                
            slowest_component = max(component_times.items(), key=lambda x: x[1])
            if slowest_component[1] > 75:
                self.logger.warning(f"⚠️  Slow component '{slowest_component[0]}': {slowest_component[1]:.1f}ms")
                
        except Exception as e:
            self.logger.error(f"Error logging performance metrics: {str(e)}")

    def _calculate_orderbook_pressure(self, market_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate orderbook pressure metrics.
        
        Returns:
            tuple: (pressure_score, metadata)
        """
        try:
            # Get orderbook data
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                self.logger.warning("Empty orderbook data for pressure calculation")
                return 50.0, {'error': 'Empty orderbook'}
            
            # Calculate bid and ask volumes
            bid_volumes = [float(bid[1]) for bid in bids[:self.depth_levels]]
            ask_volumes = [float(ask[1]) for ask in asks[:self.depth_levels]]
            
            # Calculate total volumes
            total_bid_volume = sum(bid_volumes)
            total_ask_volume = sum(ask_volumes)
            
            # Calculate weighted pressures (higher weight to closer prices)
            weights = [1.0 - (i / self.depth_levels) for i in range(self.depth_levels)]
            
            # Calculate weighted volumes
            weighted_bid_volume = sum(v * w for v, w in zip(bid_volumes, weights))
            weighted_ask_volume = sum(v * w for v, w in zip(ask_volumes, weights))
            
            # Pressure ratio: >1.0 means buying pressure, <1.0 means selling pressure
            if weighted_ask_volume > 0:
                pressure_ratio = weighted_bid_volume / weighted_ask_volume
            else:
                pressure_ratio = 2.0  # Strong buying pressure if no asks
            
            # Convert ratio to a score from 0-100
            if pressure_ratio >= 1.0:
                # Buying pressure (above 50)
                raw_score = 50.0 + min(50.0 * ((pressure_ratio - 1.0) / 2.0), 50.0)
            else:
                # Selling pressure (below 50)
                raw_score = 50.0 - min(50.0 * ((1.0 - pressure_ratio) / 1.0), 50.0)
            
            # Apply sigmoid transformation to amplify significant pressures
            transformed_score = self._apply_sigmoid_transformation(
                raw_score, 
                sensitivity=self.pressure_sensitivity, 
                center=50.0
            )
            
            self.logger.debug(f"Orderbook pressure: ratio={pressure_ratio:.2f}, raw_score={raw_score:.2f}, transformed={transformed_score:.2f}")
            
            # Create metadata
            metadata = {
                'bid_volume': total_bid_volume,
                'ask_volume': total_ask_volume,
                'pressure_ratio': pressure_ratio,
                'raw_score': raw_score,
                'transformed_score': transformed_score
            }
            
            return transformed_score, metadata
            
        except Exception as e:
            self.logger.error(f"Error calculating orderbook pressure: {str(e)}")
            return 50.0, {'error': str(e)}

    def log_indicator_results(self, final_score: float, component_scores: Dict[str, float], symbol: str = "") -> None:
        """Log detailed indicator results with proper formatting."""
        # Log the standard breakdown first
        centralized_log_indicator_results(
            logger=self.logger,
            indicator_name="Orderbook",
            final_score=final_score,
            component_scores=component_scores,
            weights=self.component_weights,
            symbol=symbol
        )
        
        # Add enhanced trading context logging
        self._log_trading_context(final_score, component_scores, symbol)
        
    def _log_trading_context(self, final_score: float, component_scores: Dict[str, float], symbol: str) -> None:
        """Log enhanced trading context and actionable insights."""
        try:
            self.logger.info(f"\n=== {symbol} Orderbook Trading Context ===")
            
            # 1. Score Interpretation Bands
            if final_score >= 70:
                strength = "STRONG BULLISH"
                action_bias = "Consider long positions"
                risk_level = "Moderate"
            elif final_score >= 55:
                strength = "MODERATE BULLISH" 
                action_bias = "Slight long bias"
                risk_level = "Low"
            elif final_score >= 45:
                strength = "NEUTRAL"
                action_bias = "Wait for clearer signals"
                risk_level = "High"
            elif final_score >= 30:
                strength = "MODERATE BEARISH"
                action_bias = "Slight short bias" 
                risk_level = "Low"
            else:
                strength = "STRONG BEARISH"
                action_bias = "Consider short positions"
                risk_level = "Moderate"
                
            self.logger.info(f"Signal Strength: {strength}")
            self.logger.info(f"Trading Bias: {action_bias}")
            self.logger.info(f"Risk Level: {risk_level}")
            
            # 2. Component Influence Analysis
            self._log_component_influence(component_scores)
            
            # 3. Threshold Alerts
            self._log_threshold_alerts(final_score, component_scores, symbol)
            
            # 4. Confidence Assessment
            confidence = self._calculate_confidence_level(component_scores)
            self.logger.info(f"Confidence Level: {confidence:.1f}% ({self._get_confidence_label(confidence)})")
            
        except Exception as e:
            self.logger.error(f"Error logging trading context: {str(e)}")
            
    def _log_component_influence(self, component_scores: Dict[str, float]) -> None:
        """Log which components are driving the overall score."""
        try:
            self.logger.info("\n--- Component Influence Analysis ---")
            
            # Calculate component contributions
            contributions = []
            for component, score in component_scores.items():
                weight = self.component_weights.get(component, 0)
                contribution = score * weight
                deviation = abs(score - 50.0)  # Distance from neutral
                influence = deviation * weight  # Influence on final score
                contributions.append((component, score, contribution, influence))
            
            # Sort by influence (highest impact first)
            contributions.sort(key=lambda x: x[3], reverse=True)
            
            # Log top influencers
            self.logger.info("Top 3 Score Drivers:")
            for i, (component, score, contribution, influence) in enumerate(contributions[:3]):
                direction = "bullish" if score > 50 else "bearish" if score < 50 else "neutral"
                self.logger.info(f"{i+1}. {component}: {score:.1f} ({direction}) - Impact: {influence:.1f}")
                
            # Identify conflicting signals
            bullish_components = [c for c, s, _, _ in contributions if s > 60]
            bearish_components = [c for c, s, _, _ in contributions if s < 40]
            
            if bullish_components and bearish_components:
                self.logger.warning("⚠️  Mixed Signals Detected:")
                self.logger.warning(f"   Bullish: {', '.join(bullish_components)}")
                self.logger.warning(f"   Bearish: {', '.join(bearish_components)}")
                
        except Exception as e:
            self.logger.error(f"Error logging component influence: {str(e)}")
            
    def _log_threshold_alerts(self, final_score: float, component_scores: Dict[str, float], symbol: str) -> None:
        """Log alerts when scores cross significant thresholds."""
        try:
            alerts = []
            
            # Overall score threshold alerts
            if final_score >= 75:
                alerts.append("STRONG BULLISH signal - Consider aggressive long positioning")
            elif final_score <= 25:
                alerts.append("STRONG BEARISH signal - Consider aggressive short positioning")
            elif 48 <= final_score <= 52:
                alerts.append("NEUTRAL zone - Wait for clearer directional bias")
                
            # Component-specific alerts
            oir_score = component_scores.get('oir', 50)
            if oir_score >= 75:
                alerts.append("OIR shows strong buying pressure - Academic #1 predictor bullish")
            elif oir_score <= 25:
                alerts.append("OIR shows strong selling pressure - Academic #1 predictor bearish")
                
            depth_score = component_scores.get('depth', 50)
            if depth_score >= 80:
                alerts.append("Excellent market depth - Low slippage expected")
            elif depth_score <= 30:
                alerts.append("⚠️ Poor market depth - High slippage risk")
                
            liquidity_score = component_scores.get('liquidity', 50)
            if liquidity_score <= 35:
                alerts.append("🚨 Low liquidity warning - Reduce position sizes")
                
            # Log alerts
            if alerts:
                self.logger.info("\n--- Trading Alerts ---")
                for alert in alerts:
                    self.logger.info(alert)
                    
        except Exception as e:
            self.logger.error(f"Error logging threshold alerts: {str(e)}")
            
    def _calculate_confidence_level(self, component_scores: Dict[str, float]) -> float:
        """Calculate confidence level based on component consistency and data quality."""
        try:
            # Factor 1: Component consistency (lower variance = higher confidence)
            scores = list(component_scores.values())
            if len(scores) > 1:
                score_variance = np.var(scores)
                consistency_factor = max(0, 100 - (score_variance / 10))  # Normalize variance
            else:
                consistency_factor = 50
                
            # Factor 2: Academic metric strength (OIR and DI are most reliable)
            academic_factor = 50
            oir_score = component_scores.get('oir', 50)
            di_score = component_scores.get('di', 50)
            
            if oir_score is not None and di_score is not None:
                # Higher confidence when academic metrics agree
                oir_deviation = abs(oir_score - 50)
                di_deviation = abs(di_score - 50)
                academic_factor = min(100, 50 + (oir_deviation + di_deviation) / 2)
                
            # Factor 3: Data quality (based on successful calculations)
            data_quality_factor = (len(component_scores) / len(self.component_weights)) * 100
            
            # Weighted average
            confidence = (
                consistency_factor * 0.4 +
                academic_factor * 0.4 +
                data_quality_factor * 0.2
            )
            
            return float(np.clip(confidence, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence level: {str(e)}")
            return 50.0
            
    def _get_confidence_label(self, confidence: float) -> str:
        """Get confidence level label."""
        if confidence >= 80:
            return "Very High"
        elif confidence >= 65:
            return "High"
        elif confidence >= 50:
            return "Moderate"
        elif confidence >= 35:
            return "Low"
        else:
            return "Very Low"
    
    async def _send_manipulation_alert(self, symbol: str, manipulation_result: Dict[str, Any]) -> None:
        """Send alert for detected market manipulation.
        
        Args:
            symbol: Trading symbol
            manipulation_result: Manipulation detection results
        """
        try:
            severity = manipulation_result['severity']
            manipulation_type = manipulation_result['manipulation_type']
            likelihood = manipulation_result['overall_likelihood']
            
            # Build alert message
            alert_msg = (
                f"🚨 Market Manipulation Detected on {symbol}\n"
                f"Type: {manipulation_type.upper()}\n"
                f"Likelihood: {likelihood:.1%}\n"
                f"Severity: {severity}\n"
            )
            
            # Add type-specific details
            if manipulation_type == 'spoofing':
                spoofing_data = manipulation_result.get('spoofing', {})
                alert_msg += (
                    f"Volatility Ratio: {spoofing_data.get('volatility_ratio', 0):.2f}\n"
                    f"Execution Ratio: {spoofing_data.get('execution_ratio', 0):.2%}\n"
                    f"Reversals: {spoofing_data.get('reversals', 0)}\n"
                )
            elif manipulation_type == 'layering':
                layering_data = manipulation_result.get('layering', {})
                bid_likelihood = layering_data.get('bid_side', {}).get('likelihood', 0)
                ask_likelihood = layering_data.get('ask_side', {}).get('likelihood', 0)
                alert_msg += (
                    f"Bid Side Likelihood: {bid_likelihood:.1%}\n"
                    f"Ask Side Likelihood: {ask_likelihood:.1%}\n"
                )
            
            # Alert details
            alert_details = {
                'type': 'market_manipulation',
                'symbol': symbol,
                'manipulation_type': manipulation_type,
                'likelihood': likelihood,
                'severity': severity,
                'timestamp': manipulation_result.get('timestamp'),
                'spoofing': manipulation_result.get('spoofing', {}),
                'layering': manipulation_result.get('layering', {}),
                'confidence': manipulation_result.get('confidence', 0)
            }
            
            # Send alert
            await self.alert_manager.send_alert(
                level=severity,
                message=alert_msg,
                details=alert_details
            )
            
            self.logger.info(f"Manipulation alert sent for {symbol}: {manipulation_type} ({likelihood:.1%})")
            
        except Exception as e:
            self.logger.error(f"Error sending manipulation alert: {str(e)}")
            self.logger.debug(f"Alert error details: {traceback.format_exc()}")

    def _log_component_specific_alerts(self, component_scores: Dict[str, float], 
                                     alerts: List[str], indicator_name: str) -> None:
        """Log Orderbook Indicators specific alerts."""
        # Depth alerts
        depth_score = component_scores.get('depth', 50)
        if depth_score >= 80:
            alerts.append("Depth Extremely Strong - Excellent liquidity support")
        elif depth_score <= 20:
            alerts.append("❌ Depth Extremely Weak - Poor liquidity, high slippage risk")
        
        # Imbalance alerts
        imbalance_score = component_scores.get('imbalance', 50)
        if imbalance_score >= 75:
            alerts.append("Imbalance Strongly Bullish - Heavy buy-side pressure")
        elif imbalance_score <= 25:
            alerts.append("Imbalance Strongly Bearish - Heavy sell-side pressure")
        
        # OIR (Order Imbalance Ratio) alerts
        oir_score = component_scores.get('oir', 50)
        if oir_score >= 80:
            alerts.append("OIR Extremely Bullish - Strong buy order dominance")
        elif oir_score <= 20:
            alerts.append("OIR Extremely Bearish - Strong sell order dominance")
        
        # Liquidity alerts
        liquidity_score = component_scores.get('liquidity', 50)
        if liquidity_score >= 75:
            alerts.append("Liquidity Excellent - Tight spreads, deep markets")
        elif liquidity_score <= 25:
            alerts.append("❌ Liquidity Poor - Wide spreads, shallow markets")
        
        # MPI (Market Pressure Index) alerts
        mpi_score = component_scores.get('mpi', 50)
        if mpi_score >= 80:
            alerts.append("MPI Extremely High - Intense buying pressure")
        elif mpi_score <= 20:
            alerts.append("MPI Extremely Low - Intense selling pressure")
        
        # Absorption/Exhaustion alerts
        absorption_score = component_scores.get('absorption_exhaustion', 50)
        if absorption_score >= 75:
            alerts.append("Absorption Strong - Good demand absorption capacity")
        elif absorption_score <= 25:
            alerts.append("⚠️ Exhaustion Detected - Supply/demand fatigue")
        
        # DI (Depth Imbalance) alerts
        di_score = component_scores.get('di', 50)
        if di_score >= 75:
            alerts.append("DI Strongly Bullish - Asymmetric depth favoring bulls")
        elif di_score <= 25:
            alerts.append("DI Strongly Bearish - Asymmetric depth favoring bears")

    # ========================================================================
    # INTEGRATED MANIPULATION DETECTION METHODS
    # ========================================================================
    
    def _analyze_manipulation_integrated(self, orderbook: Dict[str, Any], 
                                       trades: List[Dict[str, Any]], 
                                       previous_orderbook: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Integrated manipulation analysis with all detection methods"""
        if not self.manipulation_enabled:
            return self._get_default_manipulation_result()
        
        # Update historical data
        self._update_manipulation_history(orderbook, trades, previous_orderbook)
        
        # Need minimum history for analysis
        if len(self.orderbook_history) < 3:
            return self._get_default_manipulation_result()
        
        # Track order lifecycle for enhanced detection
        self._track_order_lifecycle_integrated(orderbook, previous_orderbook)
        
        # Analyze trade patterns
        trade_patterns = self._analyze_trade_patterns_integrated(trades)
        
        # Run all detection algorithms
        spoofing_result = self._detect_spoofing_integrated(orderbook, trades)
        layering_result = self._detect_layering_integrated(orderbook)
        wash_result = self._detect_wash_trading_integrated(trades)
        fake_liquidity_result = self._detect_fake_liquidity_integrated()
        iceberg_result = self._detect_iceberg_orders_integrated(orderbook, trades)
        
        # Correlate trades with order changes
        correlation_result = self._correlate_trades_with_orders_integrated(trades)
        
        # Calculate overall likelihood with enhanced weighting
        overall_likelihood = self._calculate_enhanced_likelihood_integrated(
            spoofing_result, layering_result, wash_result, 
            fake_liquidity_result, correlation_result
        )
        
        # Determine primary manipulation type
        manipulation_type = self._determine_manipulation_type_integrated(
            spoofing_result, layering_result, wash_result, fake_liquidity_result
        )
        
        # Calculate confidence
        confidence = self._calculate_manipulation_confidence_integrated(correlation_result)
        
        # Update metrics
        if overall_likelihood > 0.7:
            self.manipulation_detection_count += 1
            self.last_manipulation_detection = datetime.utcnow()
        
        return {
            'overall_likelihood': overall_likelihood,
            'manipulation_type': manipulation_type,
            'spoofing': spoofing_result,
            'layering': layering_result,
            'wash_trading': wash_result,
            'fake_liquidity': fake_liquidity_result,
            'iceberg_orders': iceberg_result,
            'trade_correlation': correlation_result,
            'trade_patterns': trade_patterns,
            'confidence': confidence,
            'severity': self._get_manipulation_severity(overall_likelihood),
            'timestamp': datetime.utcnow().isoformat(),
            'detection_count': self.manipulation_detection_count,
            'advanced_metrics': {
                'correlation_accuracy': self.correlation_accuracy,
                'tracked_orders': sum(len(orders) for orders in self.order_lifecycles.values()),
                'phantom_orders': len(self.phantom_orders),
                'iceberg_candidates': sum(len(v) for v in self.iceberg_candidates.values())
            }
        }
    
    def _update_manipulation_history(self, orderbook: Dict[str, Any], 
                                   trades: List[Dict[str, Any]], 
                                   previous_orderbook: Optional[Dict[str, Any]]) -> None:
        """Update historical data for manipulation detection"""
        timestamp = datetime.utcnow()
        
        # Store orderbook snapshot
        snapshot = {
            'timestamp': timestamp,
            'bids': orderbook.get('bids', [])[:25],
            'asks': orderbook.get('asks', [])[:25],
            'mid_price': self._calculate_mid_price_manipulation(orderbook),
            'spread': self._calculate_spread_manipulation(orderbook),
            'total_bid_volume': sum(float(b[1]) for b in orderbook.get('bids', [])[:20]),
            'total_ask_volume': sum(float(a[1]) for a in orderbook.get('asks', [])[:20])
        }
        self.orderbook_history.append(snapshot)
        
        # Calculate volume delta
        if previous_orderbook:
            delta = self._calculate_volume_delta_manipulation(orderbook, previous_orderbook)
            self.delta_history.append({
                'timestamp': timestamp,
                'bid_delta': delta['bid_delta'],
                'ask_delta': delta['ask_delta'],
                'net_delta': delta['net_delta']
            })
            
            total_volume = snapshot['total_bid_volume'] + snapshot['total_ask_volume']
            self.volume_history.append(total_volume)
        
        # Update trade history
        if trades:
            for trade in trades[-10:]:
                self.trade_history.append({
                    'timestamp': timestamp,
                    'price': float(trade.get('price', 0)),
                    'size': float(trade.get('size', 0)),
                    'side': trade.get('side', 'unknown'),
                    'id': trade.get('id', '')
                })
        
        # Store price for trend analysis
        self.price_history.append(snapshot['mid_price'])
    
    def _track_order_lifecycle_integrated(self, orderbook: Dict[str, Any], 
                                        previous_orderbook: Optional[Dict[str, Any]]) -> None:
        """Track individual order lifecycles for enhanced pattern detection"""
        if not previous_orderbook:
            return
        
        current_time = datetime.utcnow()
        
        # Track both sides
        for side_name, current_orders, previous_orders in [
            ('bid', orderbook.get('bids', []), previous_orderbook.get('bids', [])),
            ('ask', orderbook.get('asks', []), previous_orderbook.get('asks', []))
        ]:
            self._track_side_lifecycle_integrated(
                current_orders, previous_orders, side_name, current_time
            )
        
        # Clean up old orders
        self._cleanup_old_orders_integrated(current_time)
    
    def _track_side_lifecycle_integrated(self, current_orders: List[List[float]], 
                                       previous_orders: List[List[float]], 
                                       side: str, current_time: datetime) -> None:
        """Track lifecycle for one side of the orderbook"""
        current_dict = {price: size for price, size in current_orders[:20]}
        previous_dict = {price: size for price, size in previous_orders[:20]}
        
        # Check for new or updated orders
        for price, size in current_dict.items():
            order_id = f"{side}_{price}"
            
            if price not in previous_dict:
                # New order appeared - create lifecycle entry
                if price not in self.order_lifecycles:
                    self.order_lifecycles[price] = {}
                
                self.order_lifecycles[price][order_id] = {
                    'order_id': order_id,
                    'price': price,
                    'size': size,
                    'side': side,
                    'first_seen': current_time,
                    'last_seen': current_time,
                    'updates': [],
                    'executed': False,
                    'execution_ratio': 0.0,
                    'lifetime_ms': 0.0
                }
            elif abs(previous_dict[price] - size) > 0.01:
                # Order size changed
                if price in self.order_lifecycles and order_id in self.order_lifecycles[price]:
                    order = self.order_lifecycles[price][order_id]
                    order['updates'].append((current_time, size))
                    order['last_seen'] = current_time
                    order['lifetime_ms'] = (current_time - order['first_seen']).total_seconds() * 1000
        
        # Check for disappeared orders (potential phantoms)
        for price, size in previous_dict.items():
            if price not in current_dict and price in self.order_lifecycles:
                order_id = f"{side}_{price}"
                if order_id in self.order_lifecycles[price]:
                    order = self.order_lifecycles[price][order_id]
                    order['lifetime_ms'] = (current_time - order['first_seen']).total_seconds() * 1000
                    
                    # Check if it was a phantom order (disappeared quickly without execution)
                    if order['lifetime_ms'] < 5000 and not order['executed']:
                        self.phantom_orders.append({
                            'order': order,
                            'disappeared_at': current_time
                        })
                    
                    # Move to completed orders
                    self.completed_orders.append(order)
                    del self.order_lifecycles[price][order_id]
    
    def _cleanup_old_orders_integrated(self, current_time: datetime) -> None:
        """Remove orders older than 30 seconds"""
        cutoff_time = current_time - timedelta(seconds=30)
        
        for price_level in list(self.order_lifecycles.keys()):
            for order_id in list(self.order_lifecycles[price_level].keys()):
                order = self.order_lifecycles[price_level][order_id]
                if order['last_seen'] < cutoff_time:
                    self.completed_orders.append(order)
                    del self.order_lifecycles[price_level][order_id]
            
            # Remove empty price levels
            if not self.order_lifecycles[price_level]:
                del self.order_lifecycles[price_level]
    
    def _analyze_trade_patterns_integrated(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trade patterns for suspicious activity"""
        if not trades:
            return {'clusters': [], 'velocity': 0, 'pattern_score': 0}
        
        current_time = datetime.utcnow()
        
        # Calculate trade velocity
        recent_trades = [t for t in trades if t.get('timestamp', 0) > 
                        (current_time - timedelta(seconds=5)).timestamp() * 1000]
        velocity = len(recent_trades) / 5.0  # Trades per second
        self.trade_velocity.append(velocity)
        
        # Identify trade clusters
        clusters = self._identify_trade_clusters_integrated(trades)
        if clusters:
            self.trade_clusters.extend(clusters[-5:])  # Keep recent clusters
        
        # Calculate pattern score
        pattern_score = self._calculate_trade_pattern_score_integrated(clusters, velocity)
        
        return {
            'clusters': clusters[-3:] if clusters else [],  # Last 3 clusters
            'velocity': velocity,
            'avg_velocity': np.mean(list(self.trade_velocity)) if self.trade_velocity else 0,
            'pattern_score': pattern_score,
            'burst_detected': velocity > np.mean(list(self.trade_velocity)) * 3 if len(self.trade_velocity) > 1 else False
        }
    
    def _identify_trade_clusters_integrated(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify clusters of related trades"""
        if not trades:
            return []
        
        clusters = []
        current_cluster = []
        cluster_threshold_ms = 1000  # 1 second
        
        sorted_trades = sorted(trades, key=lambda x: x.get('timestamp', 0))
        
        for trade in sorted_trades:
            if not current_cluster:
                current_cluster.append(trade)
            else:
                time_diff = trade.get('timestamp', 0) - current_cluster[-1].get('timestamp', 0)
                if time_diff <= cluster_threshold_ms:
                    current_cluster.append(trade)
                else:
                    if len(current_cluster) >= 3:
                        clusters.append(self._create_trade_cluster_integrated(current_cluster))
                    current_cluster = [trade]
        
        # Final cluster
        if len(current_cluster) >= 3:
            clusters.append(self._create_trade_cluster_integrated(current_cluster))
        
        return clusters
    
    def _create_trade_cluster_integrated(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a trade cluster summary"""
        prices = [float(t.get('price') or 0) for t in trades]
        volumes = [float(t.get('size') or 0) for t in trades]
        
        return {
            'trade_count': len(trades),
            'duration_ms': trades[-1].get('timestamp', 0) - trades[0].get('timestamp', 0),
            'total_volume': sum(volumes),
            'avg_price': np.mean(prices),
            'price_range': (min(prices), max(prices))
        }
    
    def _calculate_trade_pattern_score_integrated(self, clusters: List[Dict[str, Any]], velocity: float) -> float:
        """Calculate suspicious trade pattern score"""
        score = 0.0
        
        # High velocity
        if velocity > 10:
            score += 0.3
        
        # Clustered trading
        if clusters:
            avg_cluster_size = np.mean([c['trade_count'] for c in clusters])
            if avg_cluster_size > 10:
                score += 0.3
            
            avg_duration = np.mean([c['duration_ms'] for c in clusters])
            if avg_duration < 500:
                score += 0.2
        
        return min(score, 1.0)
    
    def _detect_spoofing_integrated(self, orderbook: Dict[str, Any], 
                                  trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect spoofing patterns with order lifecycle analysis"""
        if len(self.delta_history) < 5:
            return {'likelihood': 0.0, 'detected': False, 'indicators': {}}
        
        # Volume volatility analysis
        recent_deltas = [d['net_delta'] for d in list(self.delta_history)[-10:]]
        delta_std = np.std(recent_deltas) if len(recent_deltas) > 1 else 0
        delta_mean = abs(np.mean(recent_deltas)) if recent_deltas else 1
        volatility_ratio = delta_std / (delta_mean + 1e-6)
        
        # Phantom order analysis
        phantom_score = 0.0
        if self.phantom_orders:
            recent_phantoms = [p for p in self.phantom_orders 
                             if (datetime.utcnow() - p['disappeared_at']).total_seconds() < 30]
            
            if recent_phantoms:
                large_phantoms = [p for p in recent_phantoms 
                                if p['order']['size'] * p['order']['price'] > self.spoof_min_size_usd]
                
                if large_phantoms:
                    phantom_score = min(0.5 * (len(large_phantoms) / 5), 0.5)
        
        # Calculate likelihood
        likelihood = 0.0
        if volatility_ratio > self.spoof_volatility_threshold:
            likelihood += 0.35
        if phantom_score > 0:
            likelihood += phantom_score
        
        likelihood = min(likelihood, 1.0)
        
        return {
            'likelihood': likelihood,
            'detected': likelihood > 0.7,
            'volatility_ratio': volatility_ratio,
            'phantom_score': phantom_score,
            'indicators': {
                'high_volatility': volatility_ratio > self.spoof_volatility_threshold,
                'phantom_orders': phantom_score > 0
            }
        }
    
    def _detect_layering_integrated(self, orderbook: Dict[str, Any]) -> Dict[str, Any]:
        """Detect layering patterns in orderbook"""
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        results = {'bid_side': {}, 'ask_side': {}}
        
        for side_name, orders in [('bid_side', bids), ('ask_side', asks)]:
            if len(orders) < self.layer_min_count:
                results[side_name] = {'likelihood': 0.0, 'detected': False, 'layers_found': 0}
                continue
            
            layers_to_check = min(10, len(orders))
            prices = np.array([order[0] for order in orders[:layers_to_check]], dtype=float)
            sizes = np.array([order[1] for order in orders[:layers_to_check]], dtype=float)
            
            # Price gap uniformity
            price_gaps = np.diff(prices)
            if side_name == 'bid_side':
                price_gaps = -price_gaps
            
            gap_mean = np.mean(price_gaps)
            gap_std = np.std(price_gaps)
            gap_uniformity = gap_std / (gap_mean + 1e-6) if gap_mean > 0 else 1.0
            
            # Size uniformity
            size_mean = np.mean(sizes)
            size_std = np.std(sizes)
            size_uniformity = size_std / (size_mean + 1e-6)
            
            # Calculate likelihood
            likelihood = 0.0
            if gap_uniformity < 0.2:
                likelihood += 0.4
            if size_uniformity < self.layer_size_uniformity:
                likelihood += 0.3
            if np.mean(price_gaps / prices[:-1]) < self.layer_price_gap:
                likelihood += 0.3
            
            results[side_name] = {
                'likelihood': min(likelihood, 1.0),
                'detected': likelihood > 0.7,
                'gap_uniformity': gap_uniformity,
                'size_uniformity': size_uniformity
            }
        
        max_likelihood = max(results['bid_side']['likelihood'], results['ask_side']['likelihood'])
        
        return {
            'likelihood': max_likelihood,
            'detected': max_likelihood > 0.7,
            'bid_side': results['bid_side'],
            'ask_side': results['ask_side']
        }
    
    def _detect_wash_trading_integrated(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect wash trading patterns with fingerprint matching"""
        if len(trades) < 5:
            return {'likelihood': 0.0, 'detected': False, 'patterns': []}
        
        suspicious_patterns = []
        
        # Create trade fingerprints
        for trade in trades[-20:]:
            fingerprint = self._create_trade_fingerprint_integrated(trade)
            self.trade_fingerprints.append({
                'fingerprint': fingerprint,
                'trade': trade,
                'timestamp': trade.get('timestamp', 0)
            })
        
        # Look for matching patterns
        current_time = datetime.utcnow().timestamp() * 1000
        recent_fingerprints = [
            f for f in self.trade_fingerprints 
            if current_time - f['timestamp'] < 60000  # Last minute
        ]
        
        # Group by fingerprint
        fingerprint_groups = defaultdict(list)
        for item in recent_fingerprints:
            fingerprint_groups[item['fingerprint']].append(item)
        
        # Find suspicious patterns
        for fingerprint, group in fingerprint_groups.items():
            if len(group) >= 3:
                timestamps = sorted([g['timestamp'] for g in group])
                time_diffs = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
                
                if time_diffs:
                    avg_diff = np.mean(time_diffs)
                    std_diff = np.std(time_diffs)
                    
                    if std_diff < avg_diff * 0.2:  # Regular spacing
                        suspicious_patterns.append({
                            'pattern_count': len(group),
                            'regularity_score': 1 - (std_diff / (avg_diff + 1e-6))
                        })
        
        # Calculate likelihood
        likelihood = 0.0
        if suspicious_patterns:
            pattern_score = min(len(suspicious_patterns) * 0.2, 0.6)
            max_regularity = max(p['regularity_score'] for p in suspicious_patterns)
            regularity_score = max_regularity * 0.4
            likelihood = min(pattern_score + regularity_score, 1.0)
        
        return {
            'likelihood': likelihood,
            'detected': likelihood > 0.7,
            'pattern_count': len(suspicious_patterns),
            'patterns': suspicious_patterns[:3]
        }
    
    def _create_trade_fingerprint_integrated(self, trade: Dict[str, Any]) -> str:
        """Create fingerprint for trade matching"""
        price_rounded = round(float(trade.get('price') or 0), 1)
        size_rounded = round(float(trade.get('size') or 0), 2)
        fingerprint_str = f"{price_rounded}_{size_rounded}_{trade.get('side', 'unknown')}"
        return hashlib.md5(fingerprint_str.encode()).hexdigest()[:8]
    
    def _detect_fake_liquidity_integrated(self) -> Dict[str, Any]:
        """Detect fake liquidity patterns from phantom orders"""
        if len(self.orderbook_history) < 10:
            return {'likelihood': 0.0, 'detected': False, 'indicators': {}}
        
        # Analyze phantom order ratio
        phantom_ratio = 0.0
        if self.completed_orders:
            recent_completed = list(self.completed_orders)[-50:]
            phantom_count = sum(1 for o in recent_completed 
                              if o['lifetime_ms'] < 5000 and not o['executed'])
            phantom_ratio = phantom_count / len(recent_completed)
        
        # Calculate likelihood
        likelihood = 0.0
        if phantom_ratio > 0.3:
            likelihood += 0.7
        elif phantom_ratio > 0.2:
            likelihood += 0.4
        
        return {
            'likelihood': min(likelihood, 1.0),
            'detected': likelihood > 0.7,
            'phantom_ratio': phantom_ratio,
            'indicators': {
                'high_phantom_ratio': phantom_ratio > 0.3
            }
        }
    
    def _detect_iceberg_orders_integrated(self, orderbook: Dict[str, Any], 
                                        trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect iceberg orders through refill patterns"""
        if not trades or len(self.orderbook_history) < 5:
            return {'likelihood': 0.0, 'detected': False, 'candidates': []}
        
        iceberg_indicators = []
        
        # Track orders with multiple refills
        for price_level, orders in self.order_lifecycles.items():
            for order_id, order in orders.items():
                if len(order['updates']) >= 3:
                    sizes = [update[1] for update in order['updates']]
                    refills = sum(1 for i in range(1, len(sizes)) 
                                if sizes[i] > sizes[i-1] * self.iceberg_refill_threshold)
                    
                    if refills >= 2:
                        # Track as iceberg candidate
                        self.iceberg_candidates[price_level].append({
                            'order': order,
                            'refill_count': refills,
                            'timestamp': datetime.utcnow()
                        })
        
        # Clean old candidates
        current_time = datetime.utcnow()
        for price_level in list(self.iceberg_candidates.keys()):
            self.iceberg_candidates[price_level] = [
                c for c in self.iceberg_candidates[price_level]
                if (current_time - c['timestamp']).total_seconds() < 300
            ]
            if not self.iceberg_candidates[price_level]:
                del self.iceberg_candidates[price_level]
        
        # Calculate likelihood
        total_candidates = sum(len(v) for v in self.iceberg_candidates.values())
        likelihood = min(total_candidates * 0.2, 1.0)
        
        return {
            'likelihood': likelihood,
            'detected': likelihood > 0.6,
            'candidate_count': total_candidates,
            'total_refills': sum(sum(c['refill_count'] for c in candidates) 
                               for candidates in self.iceberg_candidates.values())
        }
    
    def _correlate_trades_with_orders_integrated(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Correlate trades with order book changes"""
        if not trades or len(self.orderbook_history) < 2:
            return {'correlation_score': 0.0, 'execution_ratio': 0.0, 'matched_trades': 0}
        
        matched_trades = 0
        total_trade_volume = sum(float(t.get('size') or 0) for t in trades[-10:])
        
        # Simple correlation based on trade execution vs order presence
        for trade in trades[-10:]:
            trade_price = float(trade.get('price') or 0)
            
            # Check if trade price matches recent order levels
            for price_level in self.order_lifecycles:
                if abs(price_level - trade_price) < trade_price * 0.0001:
                    matched_trades += 1
                    break
        
        match_ratio = matched_trades / len(trades[-10:]) if trades else 0
        correlation_score = match_ratio
        
        # Update accuracy metric
        self.correlation_accuracy = correlation_score * 0.1 + self.correlation_accuracy * 0.9
        
        return {
            'correlation_score': correlation_score,
            'match_ratio': match_ratio,
            'matched_trades': matched_trades,
            'accuracy_trend': self.correlation_accuracy
        }
    
    def _calculate_enhanced_likelihood_integrated(self, spoofing: Dict[str, Any], 
                                                layering: Dict[str, Any],
                                                wash: Dict[str, Any], 
                                                fake_liquidity: Dict[str, Any],
                                                correlation: Dict[str, Any]) -> float:
        """Calculate overall manipulation likelihood with enhanced weighting"""
        correlation_factor = 1.0 - (correlation.get('correlation_score', 0) * 0.3)
        
        weights = {
            'spoofing': 0.3 * correlation_factor,
            'layering': 0.25 * correlation_factor,
            'wash_trading': 0.25,
            'fake_liquidity': 0.2 * correlation_factor
        }
        
        # Normalize weights
        total_weight = sum(weights.values())
        weights = {k: v/total_weight for k, v in weights.items()}
        
        overall = (
            weights['spoofing'] * spoofing.get('likelihood', 0) +
            weights['layering'] * layering.get('likelihood', 0) +
            weights['wash_trading'] * wash.get('likelihood', 0) +
            weights['fake_liquidity'] * fake_liquidity.get('likelihood', 0)
        )
        
        return min(overall, 1.0)
    
    def _determine_manipulation_type_integrated(self, spoofing: Dict[str, Any],
                                              layering: Dict[str, Any],
                                              wash: Dict[str, Any],
                                              fake_liquidity: Dict[str, Any]) -> str:
        """Determine primary manipulation type"""
        likelihoods = {
            'spoofing': spoofing.get('likelihood', 0),
            'layering': layering.get('likelihood', 0),
            'wash_trading': wash.get('likelihood', 0),
            'fake_liquidity': fake_liquidity.get('likelihood', 0)
        }
        
        max_type = max(likelihoods.items(), key=lambda x: x[1])
        return max_type[0] if max_type[1] > 0.5 else 'none'
    
    def _calculate_manipulation_confidence_integrated(self, correlation_result: Dict[str, Any]) -> float:
        """Calculate confidence in manipulation detection"""
        base_confidence = 0.8  # Base confidence
        
        # Boost confidence if correlation is high
        correlation_boost = correlation_result.get('correlation_score', 0) * 0.2
        
        # Reduce confidence if insufficient history
        if len(self.orderbook_history) < 20:
            base_confidence *= 0.7
        
        return max(0.0, min(1.0, base_confidence + correlation_boost))
    
    def _get_manipulation_severity(self, likelihood: float) -> str:
        """Get severity level based on likelihood"""
        if likelihood >= 0.95:
            return 'CRITICAL'
        elif likelihood >= 0.85:
            return 'HIGH'
        elif likelihood >= 0.7:
            return 'MEDIUM'
        elif likelihood >= 0.5:
            return 'LOW'
        else:
            return 'NONE'
    
    def _get_default_manipulation_result(self) -> Dict[str, Any]:
        """Get default result when manipulation detection is disabled"""
        return {
            'overall_likelihood': 0.0,
            'manipulation_type': 'none',
            'spoofing': {'likelihood': 0.0, 'detected': False},
            'layering': {'likelihood': 0.0, 'detected': False},
            'wash_trading': {'likelihood': 0.0, 'detected': False},
            'fake_liquidity': {'likelihood': 0.0, 'detected': False},
            'iceberg_orders': {'likelihood': 0.0, 'detected': False},
            'trade_correlation': {'correlation_score': 0.0},
            'trade_patterns': {'clusters': [], 'velocity': 0, 'pattern_score': 0},
            'confidence': 0.0,
            'severity': 'NONE',
            'timestamp': datetime.utcnow().isoformat(),
            'detection_count': 0,
            'advanced_metrics': {
                'correlation_accuracy': 0.0,
                'tracked_orders': 0,
                'phantom_orders': 0,
                'iceberg_candidates': 0
            }
        }
    
    def _calculate_mid_price_manipulation(self, orderbook: Dict[str, Any]) -> float:
        """Calculate mid price for manipulation detection"""
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        if not bids or not asks:
            return 0.0
        
        return (float(bids[0][0]) + float(asks[0][0])) / 2
    
    def _calculate_spread_manipulation(self, orderbook: Dict[str, Any]) -> float:
        """Calculate spread for manipulation detection"""
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        if not bids or not asks:
            return 0.0
        
        return float(asks[0][0]) - float(bids[0][0])
    
    def _calculate_volume_delta_manipulation(self, current: Dict[str, Any],
                                           previous: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate volume changes for manipulation detection"""
        curr_bid_vol = sum(float(b[1]) for b in current.get('bids', [])[:10])
        curr_ask_vol = sum(float(a[1]) for a in current.get('asks', [])[:10])
        prev_bid_vol = sum(float(b[1]) for b in previous.get('bids', [])[:10])
        prev_ask_vol = sum(float(a[1]) for a in previous.get('asks', [])[:10])
        
        bid_delta = curr_bid_vol - prev_bid_vol
        ask_delta = curr_ask_vol - prev_ask_vol
        
        return {
            'bid_delta': bid_delta,
            'ask_delta': ask_delta,
            'net_delta': bid_delta - ask_delta
        }


# Academic Sources:
# OIR, DI, and AC metrics based on Josef Smutný's research:
# @https://dodo.is.cuni.cz/bitstream/handle/20.500.11956/200516/120505902.pdf?sequence=1&isAllowed=y