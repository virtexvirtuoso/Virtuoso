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
from src.utils.error_handling import handle_indicator_error
from collections import deque
from .base_indicator import BaseIndicator
from ..core.logger import Logger
from datetime import datetime, timezone
import math
from src.core.analysis.indicator_utils import log_score_contributions, log_component_analysis, log_final_score, log_calculation_details

logger = logging.getLogger('OrderbookIndicators')

class MarketDataRepository(Protocol):
    async def get_orderbook(self, symbol: str) -> Dict[str, Any]: ...
    async def get_trades(self, symbol: str) -> List[Dict[str, Any]]: ...

class OrderbookIndicators(BaseIndicator):
    """Orderbook-based trading indicators that provide insights into market microstructure.
    
    This class calculates multiple orderbook-based metrics to evaluate market conditions
    and potential price direction. Each component provides unique insights into market
    microstructure and order flow dynamics.
    
    Components and weights:
    - Imbalance (25%): Measures the buy/sell pressure imbalance in the orderbook
    - MPI (20%): Market Pressure Index measuring buying/selling pressure
    - Depth (20%): Analyzes the distribution of liquidity through orderbook depth
    - Liquidity (10%): Measures overall market liquidity based on depth and spread
    - Absorption/Exhaustion (10%): Detects supply/demand absorption and market exhaustion
    - DOM Momentum (5%): Depth of Market momentum analyzing order flow velocity
    - Spread (5%): Evaluates the bid-ask spread relative to recent price action
    - OBPS (5%): Order Book Pressure Score capturing overall orderbook bias
    
    These components are weighted and combined to create an overall orderbook score
    that ranges from 0-100, where values above 50 indicate bullish bias and
    values below 50 indicate bearish bias.
    """

    indicator_type = 'orderbook'

    def __init__(self, config_data: Dict[str, Any] = None, logger=None):
        # Set required attributes before calling super().__init__
        self.indicator_type = 'orderbook'
        
        # Default component weights
        default_weights = {
            'imbalance': 0.25,
            'mpi': 0.20,
            'depth': 0.20,
            'liquidity': 0.10,
            'absorption_exhaustion': 0.10,
            'dom_momentum': 0.05,
            'spread': 0.05,
            'obps': 0.05
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
        
        # Validate weights
        self._validate_weights()
        
        self.logger.info(f"Initialized {self.__class__.__name__} with config: {self.config}")

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
            # Extract orderbook data from market_data
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                self.logger.warning("Empty orderbook detected")
                return 50.0  # Neutral imbalance
            
            # Convert to numpy arrays if they aren't already
            if not isinstance(bids, np.ndarray):
                bids = np.array(bids, dtype=float)
            if not isinstance(asks, np.ndarray):
                asks = np.array(asks, dtype=float)
                
            # 1. Dynamic depth and mid-price calculation
            levels = min(10, len(bids), len(asks))  # Use up to 10 levels
            
            # Ensure values are floats before calculation
            try:
                bid_price = float(bids[0, 0])
                ask_price = float(asks[0, 0])
                mid_price = (bid_price + ask_price) / 2
            except (ValueError, TypeError, IndexError) as e:
                self.logger.error(f"Error converting price to float: {str(e)}")
                return 50.0  # Return neutral score on error
            
            # Calculate spread and total depth with error handling
            try:
                spread = (asks[0, 0] - bids[0, 0]) / mid_price
                total_depth = np.sum(bids[:levels, 1]) + np.sum(asks[:levels, 1])
            except IndexError:
                self.logger.error("Invalid price/size data in orderbook")
                return 50.0
            
            # Update historical metrics
            self._update_historical_metrics(spread, total_depth)
            
            # Normalize spread using historical data with safety check
            normalized_spread = min(1.0, spread / (self.typical_spread + 1e-10)) if hasattr(self, 'typical_spread') else 0.5
            
            # 2. Volume-weighted imbalance with normalized weights
            level_weights = np.exp(-np.arange(levels) * 0.3)  # Slower decay
            level_weights /= np.sum(level_weights)  # Ensure weights sum to 1
            
            try:
                weighted_bid_volume = np.sum(bids[:levels, 1] * level_weights)
                weighted_ask_volume = np.sum(asks[:levels, 1] * level_weights)
                total_weighted_volume = weighted_bid_volume + weighted_ask_volume
            except (IndexError, ValueError) as e:
                self.logger.error(f"Error calculating weighted volumes: {str(e)}")
                return 50.0
            
            # Check for meaningful volume with logging
            if total_weighted_volume < 1e-6:
                self.logger.warning("Negligible total weighted volume detected")
                return 50.0  # Neutral if no meaningful volume
                
            weighted_imbalance = (weighted_bid_volume - weighted_ask_volume) / total_weighted_volume
            
            # 3. Price-sensitive imbalance with dynamic sensitivity
            try:
                bid_distances = np.abs(bids[:levels, 0] - mid_price) / mid_price
                ask_distances = np.abs(asks[:levels, 0] - mid_price) / mid_price
            except IndexError:
                self.logger.error("Error calculating price distances")
                return 50.0
            
            # Dynamic price sensitivity based on normalized spread
            price_sensitivity = 15 * min(1.5, 1 + normalized_spread)
            
            # Calculate and normalize price weights with epsilon
            bid_weights = np.exp(-bid_distances * price_sensitivity)
            ask_weights = np.exp(-ask_distances * price_sensitivity)
            
            # Ensure weights sum to 1 even under edge cases
            bid_weights = bid_weights / (np.sum(bid_weights) + 1e-10)
            ask_weights = ask_weights / (np.sum(ask_weights) + 1e-10)
            
            # Calculate price-weighted volumes with error handling
            try:
                price_weighted_bid = np.sum(bids[:levels, 1] * bid_weights)
                price_weighted_ask = np.sum(asks[:levels, 1] * ask_weights)
                total_price_weighted = price_weighted_bid + price_weighted_ask
            except (IndexError, ValueError) as e:
                self.logger.error(f"Error calculating price-weighted volumes: {str(e)}")
                return 50.0
            
            # Check for meaningful price-weighted volume with logging
            if total_price_weighted < 1e-6:
                self.logger.warning("Negligible price-weighted volume detected")
                price_sensitive_imbalance = 0.0
            else:
                price_sensitive_imbalance = (price_weighted_bid - price_weighted_ask) / total_price_weighted
            
            # 4. Combine metrics with dynamic weighting based on normalized spread
            price_weight = min(0.8, 0.5 + normalized_spread)  # Cap at 0.8 for stability
            volume_weight = 1 - price_weight
            
            # Use numpy's average for cleaner weighted combination
            final_imbalance = np.average(
                [weighted_imbalance, price_sensitive_imbalance],
                weights=[volume_weight, price_weight]
            )
            
            # 5. Apply sigmoid normalization for smoother distribution
            normalized_imbalance = 50 * (1 + np.tanh(2 * final_imbalance))
            
            # 6. Dynamic depth confidence calculation using historical depth
            depth_confidence = min(1.0, total_depth / (self.typical_depth + 1e-10)) if hasattr(self, 'typical_depth') else 0.5
            
            # 7. Final score calculation with confidence adjustment
            final_score = 50 + (normalized_imbalance - 50) * depth_confidence
            
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
            if not isinstance(orderbook, dict) or 'bids' not in orderbook or 'asks' not in orderbook:
                return {
                    'score': 50.0,
                    'bid_pressure': 0.0,
                    'ask_pressure': 0.0,
                    'imbalance': 0.0,
                    'ratio': 1.0
                }
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            # Use more levels for better precision
            levels_to_use = min(20, len(bids), len(asks))
            if levels_to_use == 0:
                return {'score': 50.0, 'bid_pressure': 0.0, 'ask_pressure': 0.0, 'imbalance': 0.0, 'ratio': 1.0}
            
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
            else:
                return {'score': 50.0, 'bid_pressure': 0.0, 'ask_pressure': 0.0, 'imbalance': 0.0, 'ratio': 1.0}
                
            # Calculate weighted pressure with detailed distance-based weighting
            for i in range(levels_to_use):
                if i < len(bids):
                    bid_price, bid_qty = float(bids[i][0]), float(bids[i][1])
                    # More weight to closer levels - quadratic decrease
                    price_factor = 1 - ((mid_price - bid_price) / mid_price)**2
                    # Apply greater weight to levels close to the mid price
                    bid_pressure += bid_qty * price_factor**2
                    
                if i < len(asks):
                    ask_price, ask_qty = float(asks[i][0]), float(asks[i][1])
                    # More weight to closer levels - quadratic decrease
                    price_factor = 1 - ((ask_price - mid_price) / mid_price)**2
                    # Apply greater weight to levels close to the mid price
                    ask_pressure += ask_qty * price_factor**2
            
            # Calculate pressure metrics
            if ask_pressure == 0:
                ratio = float('inf')
                imbalance = 1.0
            elif bid_pressure == 0:
                ratio = 0.0
                imbalance = -1.0
            else:
                ratio = bid_pressure / ask_pressure
                imbalance = (bid_pressure - ask_pressure) / (bid_pressure + ask_pressure)
                
            # Calculate volume concentration at top of book
            top_bid_levels = min(3, len(bids))
            top_ask_levels = min(3, len(asks))
            
            top_bid_vol = sum(float(bids[i][1]) for i in range(top_bid_levels))
            top_ask_vol = sum(float(asks[i][1]) for i in range(top_ask_levels))
            
            total_bid_vol = sum(float(bids[i][1]) for i in range(min(levels_to_use, len(bids))))
            total_ask_vol = sum(float(asks[i][1]) for i in range(min(levels_to_use, len(asks))))
            
            bid_concentration = top_bid_vol / total_bid_vol if total_bid_vol > 0 else 0
            ask_concentration = top_ask_vol / total_ask_vol if total_ask_vol > 0 else 0
            
            # Factor in concentration and spread
            # High concentration means more effective pressure
            bid_pressure_adjusted = bid_pressure * (1 + bid_concentration)
            ask_pressure_adjusted = ask_pressure * (1 + ask_concentration)
            
            # Recalculate imbalance with adjusted pressures
            if bid_pressure_adjusted + ask_pressure_adjusted > 0:
                imbalance_adjusted = (bid_pressure_adjusted - ask_pressure_adjusted) / (bid_pressure_adjusted + ask_pressure_adjusted)
            else:
                imbalance_adjusted = 0
                
            # Factor in spread - tighter spread means more conviction
            # Moderate impact: narrower spread increases importance of imbalance
            spread_factor = np.clip(1 - (spread_pct * 50), 0.5, 1.5)  # Limits impact
            
            # Calculate score based on imbalance with spread factor
            score = 50 * (1 + imbalance_adjusted * spread_factor)
            
            # Log significant data points for debugging
            self.logger.debug(f"\nOrderbook Pressure Analysis:")
            self.logger.debug(f"  Bid pressure: {bid_pressure:.2f}, Ask pressure: {ask_pressure:.2f}")
            self.logger.debug(f"  Adjusted - Bid: {bid_pressure_adjusted:.2f}, Ask: {ask_pressure_adjusted:.2f}")
            self.logger.debug(f"  Concentration - Bid: {bid_concentration:.2f}, Ask: {ask_concentration:.2f}")
            self.logger.debug(f"  Spread: {spread:.2f} ({spread_pct*100:.4f}%), Factor: {spread_factor:.2f}")
            self.logger.debug(f"  Imbalance: {imbalance:.4f}, Adjusted: {imbalance_adjusted:.4f}")
            self.logger.debug(f"  Final score: {score:.2f}")
            
            # Log significant imbalance
            if abs(imbalance_adjusted) > 0.3:
                self.logger.info(f"Significant orderbook imbalance: {imbalance_adjusted:.2f} ({'bid' if imbalance_adjusted > 0 else 'ask'} dominance)")
            
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
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return 50.0
                
            # Calculate spread
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            spread = (best_ask - best_bid) / best_bid
            
            # Calculate depth (volume within 1% of mid price)
            mid_price = (best_bid + best_ask) / 2
            depth_range = mid_price * 0.01
            
            bid_depth = sum(float(bid[1]) for bid in bids if float(bid[0]) >= mid_price - depth_range)
            ask_depth = sum(float(ask[1]) for ask in asks if float(ask[0]) <= mid_price + depth_range)
            
            total_depth = bid_depth + ask_depth
            
            # Normalize spread (lower is better)
            spread_score = 100 * (1 - min(spread * 200, 0.9))  # Cap at 90% reduction
            
            # Normalize depth (higher is better)
            # Use log scale to handle large variations in depth
            depth_score = 50 * (1 + min(math.log1p(total_depth) / 10, 1.0))
            
            # Combine with 60% weight on depth, 40% on spread
            liquidity_score = 0.6 * depth_score + 0.4 * spread_score
            
            return float(np.clip(liquidity_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating liquidity score: {str(e)}")
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
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return 50.0
                
            # Calculate best bid/ask
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid_price = (best_bid + best_ask) / 2
            
            # Calculate depth at different price levels
            levels = [0.001, 0.005, 0.01, 0.02, 0.05]  # 0.1%, 0.5%, 1%, 2%, 5%
            weights = [0.35, 0.25, 0.20, 0.15, 0.05]   # More weight to closer levels
            
            depth_scores = []
            
            for level, weight in zip(levels, weights):
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
                
            # Sum weighted scores
            final_depth_score = sum(depth_scores)
            
            return float(np.clip(final_depth_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating depth score: {str(e)}")
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
                
            # Check for required fields
            required_fields = ['symbol', 'exchange', 'timestamp']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                self.logger.error(f"Missing required fields: {missing_fields}")
                return False
                
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
            
            # Calculate component scores
            component_scores = {}
            
            # Imbalance Score
            imbalance_score = self._calculate_orderbook_imbalance(market_data)
            component_scores['imbalance'] = imbalance_score
            imbalance_ratio = self._get_imbalance_ratio(market_data)
            self.logger.info(f"Bid/Ask Imbalance: Ratio={imbalance_ratio:.4f}, Score={imbalance_score:.2f}")
            
            # Spread Score
            spread_result = self.calculate_spread_score(bids, asks)
            spread_score = spread_result['score']
            component_scores['spread'] = spread_score
            self.logger.info(f"Spread: {spread_score:.2f}, Relative={spread_result['relative_spread']:.6f}")
            
            # Depth Score
            depth_score = self._calculate_depth_score(market_data)
            component_scores['depth'] = depth_score
            depth_ratio = self._get_depth_ratio(market_data)
            self.logger.info(f"Depth Ratio: Value={depth_ratio:.4f}, Score={depth_score:.2f}")
            
            # Liquidity Score
            liquidity_score = self._calculate_liquidity_score(market_data)
            component_scores['liquidity'] = liquidity_score
            liquidity_ratio = self._get_liquidity_ratio(market_data)
            self.logger.info(f"Liquidity: Ratio={liquidity_ratio:.4f}, Score={liquidity_score:.2f}")
            
            # Absorption/Exhaustion Score
            absorption_result = self.calculate_absorption_exhaustion(bids, asks)
            absorption_score = absorption_result['combined_score']
            component_scores['absorption_exhaustion'] = absorption_score
            self.logger.info(f"Absorption/Exhaustion: Score={absorption_score:.2f}")
            
            # Market Pressure Index (MPI)
            pressure_data = self.calculate_pressure(orderbook)
            mpi_score = pressure_data['score']
            component_scores['mpi'] = mpi_score
            self.logger.info(f"Market Pressure Index: Score={mpi_score:.2f}, Imbalance={pressure_data['imbalance']:.4f}")
            
            # DOM Momentum Score
            dom_result = self.calculate_dom_momentum(bids, asks)
            dom_score = dom_result['score']
            component_scores['dom_momentum'] = dom_score
            self.logger.info(f"DOM Momentum: Score={dom_score:.2f}, Velocity={dom_result['flow_velocity']:.2f}")
            
            # OBPS Score
            obps_result = self.calculate_obps(bids, asks)
            obps_score = obps_result['score']
            component_scores['obps'] = obps_score
            self.logger.info(f"OBPS: Score={obps_score:.2f}, Ratio={obps_result['raw_ratio']:.4f}")
            
            # Prepare components dictionary
            component_scores = {
                'imbalance': imbalance_score,
                'mpi': mpi_score,
                'depth': depth_score,
                'liquidity': liquidity_score,
                'exhaustion': absorption_score,
                'dom_momentum': dom_score,
                'spread': spread_score,
                'obps': obps_score
            }
            
            # Calculate divergences if we have timeframe data
            divergences = {}
            timeframe_scores = {}
            
            # If we have OHLCV data, analyze timeframe divergences
            # Calculate final score using component weights
            final_score = self._compute_weighted_score(component_scores)
            
            # Log component contribution breakdown and final score
            self.log_indicator_results(final_score, component_scores, symbol)
            
            # Get signals
            signals = await self.get_signals(market_data)
            
            # Return standardized format
            return {
                'score': float(np.clip(final_score, 0, 100)),
                'components': component_scores,
                'signals': signals,
                'metadata': {
                    'timestamp': int(time.time() * 1000),
                    'component_weights': self.component_weights,
                    'raw_values': {
                        'imbalance_ratio': float(imbalance_ratio),
                        'spread': float(spread_result['relative_spread']),
                        'depth_ratio': float(depth_ratio),
                        'liquidity_ratio': float(liquidity_ratio),
                        'absorption': float(absorption_result['absorption_score']),
                        'exhaustion': float(absorption_result['exhaustion_score']),
                        'mpi_imbalance': float(pressure_data['imbalance']),
                        'dom_velocity': float(dom_result['flow_velocity']),
                        'obps_ratio': float(obps_result['raw_ratio'])
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

