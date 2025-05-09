import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from src.utils.error_handling import handle_indicator_error
import time
from src.core.logger import Logger
from .base_indicator import BaseIndicator
from src.core.analysis.indicator_utils import log_score_contributions, log_component_analysis, log_final_score, log_calculation_details
import traceback

class SentimentIndicators(BaseIndicator):
    """
    A class to calculate various sentiment indicators based on market data.
    Each indicator provides a score from 1 (most bearish) to 100 (most bullish).
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[Logger] = None):
        """Initialize SentimentIndicators.
        
        Components and weights:
        - Funding Rate (17%): Analyzes funding rate trends and volatility
        - Long/Short Ratio (17%): Measures market positioning
        - Liquidations (17%): Tracks forced position closures
        - Market Activity (17%): Combined volume and open interest analysis
        - Risk Score (16%): Measures market risk
        - Volatility (16%): Measures historical volatility
        """
        # Set required attributes before calling super().__init__
        self.indicator_type = 'sentiment'
        
        # Default component weights
        default_weights = {
            'funding_rate': 0.17,
            'long_short_ratio': 0.17,
            'liquidations': 0.17,
            'market_activity': 0.17,
            'risk': 0.16,
            'volatility': 0.16
        }
        
        # Get sigmoid transformation parameters from config
        sigmoid_config = config.get('analysis', {}).get('indicators', {}).get('sentiment', {}).get('parameters', {}).get('sigmoid_transformation', {})
        self.default_sensitivity = sigmoid_config.get('default_sensitivity', 0.12)
        self.long_short_sensitivity = sigmoid_config.get('long_short_sensitivity', 0.12)
        self.funding_sensitivity = sigmoid_config.get('funding_sensitivity', 0.15)
        self.liquidation_sensitivity = sigmoid_config.get('liquidation_sensitivity', 0.10)
        
        # **** IMPORTANT: Must set component_weights BEFORE calling super().__init__ ****
        
        # Initialize component weights dictionary with defaults
        self.component_weights = default_weights.copy()
        
        # Now call parent class constructor
        super().__init__(config, logger)
        
        # Get sentiment specific config
        sentiment_config = config.get('analysis', {}).get('indicators', {}).get('sentiment', {})
        
        # Try to get weights from confluence section first (most accurate)
        confluence_weights = config.get('confluence', {}).get('weights', {}).get('sub_components', {}).get('sentiment', {})
        
        # Map config keys to internal keys
        config_to_internal = {
            'funding_rate': 'funding_rate',
            'long_short_ratio': 'long_short_ratio',
            'liquidation_events': 'liquidations',
            'volume_sentiment': 'volume_sentiment',
            'market_mood': 'market_mood',
            'risk_score': 'risk',
        }
        
        # Override defaults with weights from config
        if confluence_weights:
            # First, handle the funding_rate and funding_rate_volatility special case
            funding_rate_weight = confluence_weights.get('funding_rate', 0.15)
            volatility_weight = confluence_weights.get('funding_rate_volatility', 0.1)
            
            # Combine the weights
            combined_funding_weight = funding_rate_weight + volatility_weight
            self.component_weights['funding_rate'] = combined_funding_weight
            self.logger.debug(f"Combined funding rate weight: {combined_funding_weight} (rate: {funding_rate_weight} + volatility: {volatility_weight})")
            
            # Process other components
            for config_key, internal_key in config_to_internal.items():
                if config_key in confluence_weights and config_key != 'funding_rate':
                    self.component_weights[internal_key] = float(confluence_weights[config_key])
                    self.logger.debug(f"Using weight from config: {config_key} -> {internal_key}: {self.component_weights[internal_key]}")
        
        # Normalize weights to ensure they sum to 1.0
        weight_sum = sum(self.component_weights.values())
        if weight_sum != 0:
            for component in self.component_weights:
                self.component_weights[component] /= weight_sum
            self.logger.debug(f"Normalized weights (sum: {weight_sum}): {self.component_weights}")
        
        # Store the internal funding rate volatility weight (for use in calculation)
        self.funding_volatility_weight = 0.3  # 30% volatility, 70% raw rate
        self.logger.debug(f"Internal funding rate volatility weight: {self.funding_volatility_weight}")
        
        # Initialize parameters
        self.funding_threshold = sentiment_config.get('funding_threshold', 0.01)
        self.liquidation_threshold = sentiment_config.get('liquidation_threshold', 1000000)
        self.sentiment_window = sentiment_config.get('window', 20)
        
        # Initialize tracking variables
        self.sentiment_history = []
        self.last_update = 0
        
        # Cache for missing data
        self._missing_risk_data = False
        
        # Validate weights
        self._validate_weights()
        
        self.logger.info(f"Initialized {self.__class__.__name__} with config: {sentiment_config}")
        
        # Add cache for expensive operations
        self._cache = {
            'missing_risk_data': False,
            'last_funding_rate': None,
            'last_lsr': None,
            'last_calculation_time': 0
        }
        
        # Cache expiration time (10 minutes)
        self.cache_expiration = 10 * 60  # seconds
        
    def _validate_weights(self):
        """Validate that weights sum to 1.0"""
        comp_total = sum(self.component_weights.values())
        if not np.isclose(comp_total, 1.0, rtol=1e-5):
            self.logger.warning(f"Component weights sum to {comp_total}, normalizing")
            self.component_weights = {k: v/comp_total for k, v in self.component_weights.items()}
            self.logger.debug(f"Normalized weights: {self.component_weights}")
    def calculate_long_short_ratio(self, market_data: Dict[str, Any]) -> float:
        """Calculate long/short ratio score from market data.
        
        Args:
            market_data: Dictionary containing market and sentiment data
        
        Returns:
            float: Score between 0-100 indicating bullish/bearish bias
        """
        self.logger.debug("\n=== [LSR] Calculating Long/Short Ratio Score ===")
        try:
            # Check for various data formats
            long_short_data = None
            self.logger.debug(f"[LSR] Market data keys: {list(market_data.keys())}")
            if 'sentiment' in market_data and 'long_short_ratio' in market_data['sentiment']:
                long_short_data = market_data['sentiment']['long_short_ratio']
                self.logger.debug(f"[LSR] Found long_short_ratio in sentiment: {type(long_short_data)}")
            elif 'long_short_ratio' in market_data:
                long_short_data = market_data['long_short_ratio']
                self.logger.debug(f"[LSR] Found long_short_ratio at top level: {type(long_short_data)}")
            else:
                self.logger.warning("[LSR] No long_short_ratio found in market_data, defaulting to 50/50")
                return 50.0
                
            self.logger.debug(f"[LSR] Long/Short raw data: {long_short_data}")
            
            if isinstance(long_short_data, dict):
                long_ratio = float(long_short_data.get('long', 50.0))
                short_ratio = float(long_short_data.get('short', 50.0))
                self.logger.info(f"[LSR] Using long/short format - Long: {long_ratio}, Short: {short_ratio}")
            elif isinstance(long_short_data, (list, tuple)) and len(long_short_data) == 2:
                long_ratio, short_ratio = map(float, long_short_data)
                self.logger.info(f"[LSR] Using tuple/list format - Long: {long_ratio}, Short: {short_ratio}")
            else:
                self.logger.warning(f"[LSR] Unrecognized long_short_data format: {type(long_short_data)}, defaulting to 50/50")
                return 50.0
                
            total = long_ratio + short_ratio
            self.logger.debug(f"[LSR] Sum of ratios: {total}")
            
            if total == 0:
                self.logger.warning("[LSR] Both long and short ratios are zero, defaulting to 50.0")
                return 50.0
                
            long_percentage = (long_ratio / total) * 100
            self.logger.info(f"[LSR] Calculated long percentage: {long_percentage:.2f}% from {long_ratio}/{total}")
            score = max(0, min(100, long_percentage))
            self.logger.debug(f"[LSR] Final LSR Score: {score}")
            return score
        except Exception as e:
            self.logger.error(f"[LSR] Exception in calculate_long_short_ratio: {e}")
            return 50.0

    def calculate_funding_rate(self, market_data: Dict[str, Any]) -> float:
        """Calculate funding rate score (redirects to _calculate_funding_score)."""
        # Process sentiment data first
        sentiment = self._process_sentiment_data(market_data)
        # Use the canonical method
        return self._calculate_funding_score(sentiment)

    def calculate_funding_rate_volatility(self, market_data: Dict[str, Any]) -> float:
        """Calculate sentiment score based on funding rate volatility.
        
        Higher volatility (unstable funding rates) is considered bearish.
        Lower volatility (stable funding rates) is considered bullish.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: Score between 0-100
        """
        try:
            self.logger.debug("\n=== Calculating Funding Rate Volatility ===")
            
            # Extract funding rate history
            sentiment_data = market_data.get('sentiment', {})
            funding_history = sentiment_data.get('funding_history', [])
            
            # If no history is available, check if current funding rate is available
            if not funding_history or len(funding_history) < 2:
                self.logger.debug("Insufficient funding rate history")
                # If current funding rate is very close to zero, consider it stable (bullish)
                current_rate = abs(market_data.get('funding_rate', {}).get('fundingRate', 0.0))
                if isinstance(current_rate, str):
                    try:
                        current_rate = float(current_rate)
                    except:
                        current_rate = 0.0
                
                # If current rate is very small, consider it stable
                if current_rate < 0.0001:
                    self.logger.debug(f"Current funding rate is near zero ({current_rate}), considering stable")
                    return 60.0  # Slightly bullish due to stability
                
                self.logger.debug("No funding history available, using neutral score")
                return 50.0  # Neutral
            
            # Calculate volatility from historical funding rates
            try:
                # Try extracting rates in different formats
                if isinstance(funding_history[0], dict):
                    # Handle dict format
                    if 'rate' in funding_history[0]:
                        rates = [float(rate.get('rate', 0)) for rate in funding_history]
                    elif 'fundingRate' in funding_history[0]:
                        rates = [float(rate.get('fundingRate', 0)) for rate in funding_history]
                    else:
                        # Try to find the rate field
                        keys = funding_history[0].keys()
                        rate_key = next((k for k in keys if 'rate' in k.lower()), None)
                        if rate_key:
                            rates = [float(rate.get(rate_key, 0)) for rate in funding_history]
                        else:
                            self.logger.warning("Could not identify rate field in funding history")
                            return 50.0
                else:
                    # Handle direct array of values
                    rates = [float(rate) for rate in funding_history]
            except Exception as e:
                self.logger.error(f"Error extracting rates from funding history: {e}")
                return 50.0
            
            # Filter out any NaN or infinity values
            rates = [r for r in rates if not np.isnan(r) and not np.isinf(r)]
            
            if not rates or len(rates) < 2:
                self.logger.debug("Insufficient valid funding rates data")
                return 50.0
            
            # Calculate volatility metrics
            volatility = np.std(rates)
            mean_rate = np.mean(rates)
            abs_mean_rate = abs(mean_rate)
            
            self.logger.debug(f"Rates: {rates}")
            self.logger.debug(f"Volatility: {volatility:.6f}")
            self.logger.debug(f"Mean rate: {mean_rate:.6f}")
            
            # Account for the scale of the rates
            # A volatility of 0.001 is very different if mean_rate is 0.01 vs 0.0001
            if abs_mean_rate > 0:
                relative_volatility = volatility / (abs_mean_rate + 1e-10)
            else:
                relative_volatility = volatility * 1000  # Scale up when mean is near zero
            
            self.logger.debug(f"Relative volatility: {relative_volatility:.6f}")
            
            # Calculate volatility score (inverse - higher volatility = lower score)
            # Use scaled sigmoid-like function for smooth transition
            # Volatility threshold is set dynamically based on the mean rate
            threshold = max(0.0001, abs_mean_rate * 0.5)
            
            if relative_volatility <= threshold:
                # Low volatility
                volatility_score = 70 - (relative_volatility / threshold * 20)
            else:
                # High volatility
                volatility_score = 50 - min(30, (relative_volatility - threshold) * 50)
            
            self.logger.debug(f"Volatility threshold: {threshold:.6f}")
            self.logger.debug(f"Final volatility score: {volatility_score:.2f}")
            
            # Ensure final score is within bounds
            final_score = float(np.clip(volatility_score, 0, 100))
            
            return final_score
            
        except Exception as e:
            self.logger.error(f"Error calculating funding rate volatility score: {str(e)}")
            return 50.0

    def calculate_liquidation_events(self, market_data: Dict[str, Any]) -> float:
        """
        Calculate sentiment score based on liquidation events with reversal detection.
        
        Expected data structure in market_data:
        market_data = {
            'sentiment': {
                'liquidations': [
                    {
                        'side': 'long' or 'short',
                        'size': float,
                        'price': float,
                        'timestamp': int (milliseconds),
                        'source': str (optional)
                    },
                    ...
                ]
            }
        }
        
        Returns score 0-100 where:
        - 0-30: Strong bearish pressure
        - 30-45: Moderate bearish with potential reversal
        - 45-55: Neutral
        - 55-70: Moderate bullish with potential reversal
        - 70-100: Strong bullish pressure
        """
        try:
            self.logger.debug("\n=== Calculating Liquidation Events Score ===")
            self.logger.debug(f"Input market_data keys: {list(market_data.keys())}")
            
            sentiment_data = market_data.get('sentiment', {})
            liquidations = sentiment_data.get('liquidations', [])
            
            self.logger.debug(f"Liquidations data type: {type(liquidations)}")
            self.logger.debug(f"Liquidations data: {liquidations if isinstance(liquidations, dict) else f'List of {len(liquidations)} events' if isinstance(liquidations, list) else 'Invalid data'}")
            
            if not liquidations:
                self.logger.warning("No liquidation data available, returning neutral score")
                return 50.0

            # Process liquidations data
            try:
                if isinstance(liquidations, dict):
                    self.logger.debug("Processing dictionary liquidation data")
                    long_liq = float(liquidations.get('long', liquidations.get('longAmount', 0)))
                    short_liq = float(liquidations.get('short', liquidations.get('shortAmount', 0)))
                    self.logger.debug(f"Long liquidations: {long_liq}, Short liquidations: {short_liq}")
                elif isinstance(liquidations, list):
                    self.logger.debug("Processing list of liquidation events")
                    long_liq = sum(float(event.get('size', event.get('amount', 0))) 
                                 for event in liquidations if event.get('side', '').lower() == 'long')
                    short_liq = sum(float(event.get('size', event.get('amount', 0))) 
                                  for event in liquidations if event.get('side', '').lower() == 'short')
                    self.logger.debug(f"Total long liquidations: {long_liq}, Total short liquidations: {short_liq}")
                else:
                    self.logger.warning(f"Unexpected liquidation data format: {type(liquidations)}")
                    return 50.0
                
                # Calculate score based on liquidation ratio
                total_liq = long_liq + short_liq
                if total_liq > 0:
                    long_ratio = long_liq / total_liq
                    score = (1 - long_ratio) * 100  # More long liquidations = bearish
                    self.logger.debug(f"Liquidation ratio: {long_ratio:.4f}, Score: {score:.2f}")
                else:
                    self.logger.debug("Zero total liquidations")
                    return 50.0
                
                return float(np.clip(score, 0, 100))
                
            except Exception as e:
                self.logger.error(f"Error processing liquidation data: {str(e)}", exc_info=True)
                return 50.0
            
        except Exception as e:
            self.logger.error(f"Error calculating liquidation events score: {str(e)}", exc_info=True)
            return 50.0

    def calculate_volume_sentiment(self, market_data: Dict[str, Any]) -> float:
        """Calculate sentiment score based on buy/sell volume."""
        try:
            self.logger.debug("\n=== Calculating Volume Sentiment Score ===")
            self.logger.debug(f"Input market_data keys: {list(market_data.keys())}")
            
            # Dump market_data structure for debugging
            for key in ['volume', 'trades', 'sentiment']:
                if key in market_data:
                    self.logger.debug(f"{key} data: {market_data[key]}")
            
            # Check for volume information in sentiment data
            volume_data = {}
            
            # First try direct volume field
            if 'volume' in market_data:
                volume_data = market_data.get('volume', {})
            # Then try sentiment.volume_sentiment
            elif 'sentiment' in market_data and 'volume_sentiment' in market_data['sentiment']:
                volume_data = market_data['sentiment']['volume_sentiment']
            
            self.logger.debug(f"Volume data: {volume_data}")
            
            buy_volume_pct = volume_data.get('buy_volume_percent')
            
            self.logger.debug(f"Buy volume percentage: {buy_volume_pct}")
            
            # If buy volume percentage is directly available
            if buy_volume_pct is not None:
                self.logger.debug(f"Using provided buy volume percentage: {buy_volume_pct:.4f}")
                buy_volume_pct = float(buy_volume_pct)
                score = buy_volume_pct * 100
                return float(np.clip(score, 0, 100))
            
            # If we have buy and sell volumes directly
            buy_volume = volume_data.get('buy_volume')
            sell_volume = volume_data.get('sell_volume')
            
            if buy_volume is not None and sell_volume is not None:
                self.logger.debug(f"Using provided volumes - Buy: {buy_volume}, Sell: {sell_volume}")
                try:
                    buy_volume = float(buy_volume)
                    sell_volume = float(sell_volume)
                    total_volume = buy_volume + sell_volume
                    
                    if total_volume > 0:
                        buy_percentage = buy_volume / total_volume
                        self.logger.debug(f"Calculated buy percentage: {buy_percentage:.4f}")
                        raw_score = buy_percentage * 100
                        adjusted_score = self._adjust_volume_score(raw_score)
                        return float(np.clip(adjusted_score, 0, 100))
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Error processing volume data: {e}")
            
            # If not directly available, try to calculate from trades
            trades = market_data.get('trades', [])
            
            if not trades:
                self.logger.debug("No trades data for volume sentiment")
                return 50.0
            
            self.logger.debug(f"Calculating volume sentiment from {len(trades)} trades")
            
            # Calculate buy and sell volume
            buy_volume = 0.0
            sell_volume = 0.0
            
            for trade in trades:
                self.logger.debug(f"Processing trade: {trade}")
                
                # Skip invalid trades
                if 'side' not in trade or 'size' not in trade:
                    continue
                    
                try:
                    size = float(trade['size'])
                    side = trade['side'].lower()
                    
                    if side == 'buy':
                        buy_volume += size
                    elif side == 'sell':
                        sell_volume += size
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Error processing trade: {e}")
                    continue
                    
            total_volume = buy_volume + sell_volume
            
            if total_volume == 0:
                self.logger.debug("Zero total volume, returning neutral score")
                return 50.0
            
            # Calculate buy percentage
            buy_percentage = buy_volume / total_volume
            
            self.logger.debug(f"Buy volume: {buy_volume:.2f}, Sell volume: {sell_volume:.2f}")
            self.logger.debug(f"Buy percentage: {buy_percentage:.4f}")
            
            # Convert to a score from 0-100
            raw_score = buy_percentage * 100
            
            # Apply non-linear transformation for extreme values
            adjusted_score = self._adjust_volume_score(raw_score)
            
            self.logger.debug(f"Raw volume score: {raw_score:.2f}")
            self.logger.debug(f"Adjusted volume score: {adjusted_score:.2f}")
            
            return float(adjusted_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating volume sentiment: {str(e)}", exc_info=True)
            return 50.0
    
    def _adjust_volume_score(self, raw_score: float) -> float:
        """Apply non-linear adjustments to volume score."""
        try:
            if raw_score > 80:
                adjusted_score = 80 + (raw_score - 80) * 1.5
            elif raw_score < 20:
                adjusted_score = raw_score * 0.75
            else:
                deviation = (raw_score - 50) / 50
                sigmoid = 1 / (1 + np.exp(-4 * deviation))
                adjusted_score = 50 + (sigmoid - 0.5) * 60
                
            return float(np.clip(adjusted_score, 0, 100))
        except Exception as e:
            self.logger.error(f"Error adjusting volume score: {e}")
            return raw_score

    def _calculate_funding_score(self, sentiment_data: Dict[str, Any]) -> float:
        """Calculate sentiment score based on funding rate.
        
        Funding rate is a key sentiment indicator in perpetual futures markets.
        Negative funding rates typically indicate bullish sentiment (longs paying shorts)
        Positive funding rates typically indicate bearish sentiment (shorts paying longs)
        
        Note: Based on testing with Bybit API, funding rate is available in the 
        ticker data as 'fundingRate' field, and is provided as a decimal value (e.g. -0.0001382)
        which represents a percentage (-0.01382%).
        """
        try:
            self.logger.debug("\n=== Calculating Funding Rate Score ===")
            self.logger.debug(f"Input data type: {type(sentiment_data)}")
            
            # Log top-level keys for debugging
            if isinstance(sentiment_data, dict):
                self.logger.debug(f"Input data keys: {list(sentiment_data.keys())}")
                
                # Log specific funding-related data if available
                if 'funding_rate' in sentiment_data:
                    self.logger.debug(f"funding_rate data type: {type(sentiment_data['funding_rate'])}")
                    self.logger.debug(f"funding_rate value: {sentiment_data['funding_rate']}")
                if 'sentiment' in sentiment_data and isinstance(sentiment_data['sentiment'], dict):
                    self.logger.debug(f"sentiment keys: {list(sentiment_data['sentiment'].keys())}")
                    if 'funding_rate' in sentiment_data['sentiment']:
                        self.logger.debug(f"sentiment.funding_rate type: {type(sentiment_data['sentiment']['funding_rate'])}")
                        self.logger.debug(f"sentiment.funding_rate value: {sentiment_data['sentiment']['funding_rate']}")
            
            # Initialize funding rate to None
            funding_rate = None
            self.logger.debug("Starting funding rate extraction attempts...")
            
            # First check if funding_rate is directly available as a field
            if 'funding_rate' in sentiment_data:
                self.logger.debug("ATTEMPT 1: Direct funding_rate key found")
                # Handle if funding_rate is a dictionary
                if isinstance(sentiment_data['funding_rate'], dict):
                    self.logger.debug(f"funding_rate is a dict with keys: {list(sentiment_data['funding_rate'].keys())}")
                    if 'rate' in sentiment_data['funding_rate']:
                        try:
                            funding_rate = float(sentiment_data['funding_rate']['rate'])
                            self.logger.debug(f"SUCCESS: Found funding_rate['rate']: {funding_rate}")
                        except (ValueError, TypeError) as e:
                            self.logger.debug(f"CONVERSION ERROR: funding_rate['rate'] = {sentiment_data['funding_rate']['rate']}, error: {str(e)}")
                    elif 'fundingRate' in sentiment_data['funding_rate']:
                        try:
                            funding_rate = float(sentiment_data['funding_rate']['fundingRate'])
                            self.logger.debug(f"SUCCESS: Found funding_rate['fundingRate']: {funding_rate}")
                        except (ValueError, TypeError) as e:
                            self.logger.debug(f"CONVERSION ERROR: funding_rate['fundingRate'] = {sentiment_data['funding_rate']['fundingRate']}, error: {str(e)}")
                    else:
                        # Dictionary without 'rate' key - use a default value
                        self.logger.debug(f"WARNING: Found funding_rate dict without 'rate' or 'fundingRate' key: {sentiment_data['funding_rate']}")
                        funding_rate = 0.0001  # Default value
                        self.logger.debug(f"Using default funding_rate: {funding_rate}")
                else:
                    # Not a dictionary, try to convert directly
                    self.logger.debug(f"funding_rate is not a dict, type: {type(sentiment_data['funding_rate'])}")
                    try:
                        funding_rate = float(sentiment_data.get('funding_rate', 0))
                        self.logger.debug(f"SUCCESS: Found direct funding_rate: {funding_rate}")
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"CONVERSION ERROR: Could not convert funding_rate to float: {sentiment_data['funding_rate']}, error: {str(e)}")
                        funding_rate = 0.0001  # Default value
                        self.logger.debug(f"Using default funding_rate: {funding_rate}")
            # Then look for it in nested structures
            elif 'sentiment' in sentiment_data and 'funding_rate' in sentiment_data['sentiment']:
                self.logger.debug("ATTEMPT 2: Checking sentiment.funding_rate")
                # Handle if nested funding_rate is a dictionary
                if isinstance(sentiment_data['sentiment']['funding_rate'], dict):
                    self.logger.debug(f"sentiment.funding_rate is a dict with keys: {list(sentiment_data['sentiment']['funding_rate'].keys())}")
                    if 'rate' in sentiment_data['sentiment']['funding_rate']:
                        try:
                            funding_rate = float(sentiment_data['sentiment']['funding_rate']['rate'])
                            self.logger.debug(f"SUCCESS: Found sentiment.funding_rate['rate']: {funding_rate}")
                        except (ValueError, TypeError) as e:
                            self.logger.debug(f"CONVERSION ERROR: sentiment.funding_rate['rate'] = {sentiment_data['sentiment']['funding_rate']['rate']}, error: {str(e)}")
                    elif 'fundingRate' in sentiment_data['sentiment']['funding_rate']:
                        try:
                            funding_rate = float(sentiment_data['sentiment']['funding_rate']['fundingRate'])
                            self.logger.debug(f"SUCCESS: Found sentiment.funding_rate['fundingRate']: {funding_rate}")
                        except (ValueError, TypeError) as e:
                            self.logger.debug(f"CONVERSION ERROR: sentiment.funding_rate['fundingRate'] = {sentiment_data['sentiment']['funding_rate']['fundingRate']}, error: {str(e)}")
                    else:
                        # Dictionary without 'rate' key - use a default value
                        self.logger.debug(f"WARNING: Found nested funding_rate dict without 'rate' or 'fundingRate' key: {sentiment_data['sentiment']['funding_rate']}")
                        funding_rate = 0.0001  # Default value
                        self.logger.debug(f"Using default funding_rate: {funding_rate}")
                else:
                    self.logger.debug(f"sentiment.funding_rate is not a dict, type: {type(sentiment_data['sentiment']['funding_rate'])}")
                    try:
                        funding_rate = float(sentiment_data['sentiment']['funding_rate'])
                        self.logger.debug(f"SUCCESS: Found funding_rate in sentiment: {funding_rate}")
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"CONVERSION ERROR: Could not convert nested funding_rate to float: {sentiment_data['sentiment']['funding_rate']}, error: {str(e)}")
                        funding_rate = 0.0001  # Default value
                        self.logger.debug(f"Using default funding_rate: {funding_rate}")
            # Try to find it in funding history if available
            elif 'sentiment' in sentiment_data and 'funding_history' in sentiment_data['sentiment']:
                self.logger.debug("ATTEMPT 3: Checking sentiment.funding_history")
                funding_history = sentiment_data['sentiment']['funding_history']
                self.logger.debug(f"funding_history type: {type(funding_history)}, length: {len(funding_history) if isinstance(funding_history, list) else 'N/A'}")
                if isinstance(funding_history, list) and funding_history:
                    # Get the most recent entry
                    latest_funding = funding_history[0]
                    self.logger.debug(f"latest_funding type: {type(latest_funding)}")
                    if isinstance(latest_funding, dict):
                        self.logger.debug(f"latest_funding keys: {list(latest_funding.keys())}")
                    if isinstance(latest_funding, dict) and 'fundingRate' in latest_funding:
                        try:
                            funding_rate = float(latest_funding['fundingRate'])
                            self.logger.debug(f"SUCCESS: Found funding rate in history: {funding_rate}")
                        except (ValueError, TypeError) as e:
                            self.logger.debug(f"CONVERSION ERROR: history fundingRate = {latest_funding['fundingRate']}, error: {str(e)}")
            # Look in general data dictionaries
            elif isinstance(sentiment_data, dict):
                self.logger.debug("ATTEMPT 4: Searching through all keys for funding-related fields")
                for key in sentiment_data.keys():
                    if 'funding' in key.lower():
                        self.logger.debug(f"Found potential funding key: {key}, type: {type(sentiment_data[key])}")
                        if isinstance(sentiment_data[key], (int, float, str)):
                            try:
                                funding_rate = float(sentiment_data[key])
                                self.logger.debug(f"SUCCESS: Found funding rate in key '{key}': {funding_rate}")
                                break
                            except (ValueError, TypeError) as e:
                                self.logger.debug(f"CONVERSION ERROR: key '{key}' value = {sentiment_data[key]}, error: {str(e)}")
            # Check ticker for funding rate (common in exchange data from Bybit API)
            elif 'ticker' in sentiment_data:
                self.logger.debug("ATTEMPT 5: Checking ticker data")
                ticker = sentiment_data.get('ticker', {})
                if isinstance(ticker, dict):
                    self.logger.debug(f"ticker keys: {list(ticker.keys())}")
                    if 'fundingRate' in ticker:
                        try:
                            funding_rate = float(ticker.get('fundingRate', 0))
                            self.logger.debug(f"SUCCESS: Found funding rate in ticker: {funding_rate}")
                        except (ValueError, TypeError) as e:
                            self.logger.debug(f"CONVERSION ERROR: ticker.fundingRate = {ticker.get('fundingRate')}, error: {str(e)}")
            
            if funding_rate is None:
                self.logger.debug("No valid funding rate found after all attempts, returning neutral score")
                return 50.0
                
            # Normalize funding rate to 0-100 scale
            # Typical funding rates range from -0.1% to 0.1%
            # Convert to percentage for easier calculation
            funding_pct = funding_rate * 100
            
            self.logger.debug(f"SCORE CALCULATION: Funding rate: {funding_rate}, as percentage: {funding_pct}%")
            
            # Clip to reasonable range (-0.2% to 0.2%)
            funding_pct_clipped = max(-0.2, min(0.2, funding_pct))
            if funding_pct != funding_pct_clipped:
                self.logger.debug(f"Clipped funding percentage from {funding_pct}% to {funding_pct_clipped}%")
            
            # Map to 0-100 scale (inverted: negative funding = bullish)
            # -0.2% -> 100, 0% -> 50, 0.2% -> 0
            raw_score = 50 - (funding_pct_clipped * 250)
            self.logger.debug(f"Raw score calculation: 50 - ({funding_pct_clipped} * 250) = {raw_score}")
            
            # Apply sigmoid transformation with specific sensitivity for funding
            score = self._apply_sigmoid_transformation(raw_score, sensitivity=self.funding_sensitivity)
            
            self.logger.debug(f"FINAL: Funding rate score: {score:.2f} (rate: {funding_rate:.6f}, raw: {raw_score:.2f})")
            
            return float(score)
            
        except Exception as e:
            self.logger.error(f"Error calculating funding rate score: {str(e)}", exc_info=True)
            self.logger.error(f"Input data that caused error: {sentiment_data}")
            return 50.0

    def calculate_market_mood(self, market_data: Dict[str, Any]) -> float:
        """Calculate sentiment score based on overall market mood indicators."""
        try:
            self.logger.debug("\n=== Calculating Market Mood Score ===")
            
            # Check for market_mood data in sentiment or directly
            market_mood = None
            
            # Try different paths to market mood data
            if 'sentiment' in market_data and 'market_mood' in market_data['sentiment']:
                market_mood = market_data['sentiment']['market_mood']
                self.logger.debug(f"Found market_mood in sentiment: {market_mood}")
            elif 'market_mood' in market_data:
                market_mood = market_data['market_mood']
                self.logger.debug(f"Found direct market_mood: {market_mood}")
            
            if not market_mood or not isinstance(market_mood, dict):
                self.logger.debug("No valid market mood data available")
                return 50.0
            
            self.logger.debug(f"Market mood data: {market_mood}")

            # Set component weights
            weights = {
                'social_sentiment': 0.25,
                'fear_and_greed': 0.30,
                'search_trends': 0.15,
                'positive_mentions': 0.30,
                'risk_level': 0.20,  # Alternative component if available
                'max_leverage': 0.15  # Alternative component if available
            }
            
            scores = {}
            
            # Process each component
            for component, weight in weights.items():
                if component in market_mood:
                    try:
                        value = float(market_mood[component])
                        if component == 'positive_mentions':
                            # Convert to 0-100 scale
                            value = value * 100
                        elif component == 'risk_level':
                            # Inverse risk level (lower is better)
                            if isinstance(value, (int, float)) and value > 0:
                                # Assume risk levels are 1-10, higher = more risk
                                value = max(0, 100 - (value * 10))
                        elif component == 'max_leverage':
                            # Higher leverage = better market conditions
                            if isinstance(value, (int, float)) and value > 0:
                                # Map common leverage values (1-100) to score
                                value = min(100, value)
                        
                        scores[component] = np.clip(value, 0, 100)
                        self.logger.debug(f"{component}: raw={market_mood[component]}, processed={scores[component]:.2f}")
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Error processing {component}: {e}")
            
            if not scores:
                self.logger.debug("No valid component scores calculated")
                return 50.0
            
            # Calculate weighted average
            total_weight = sum(weights[comp] for comp in scores.keys())
            weighted_sum = sum(scores[comp] * weights[comp] for comp in scores.keys())
            
            if total_weight == 0:
                self.logger.debug("Zero total weight")
                return 50.0
            
            final_score = weighted_sum / total_weight
            
            self.logger.debug("\n=== Market Mood Score Breakdown ===")
            for component in scores:
                self.logger.debug(f"{component}: {scores[component]:.2f} × {weights[component]:.2f} = {scores[component] * weights[component]:.2f}")
            self.logger.debug(f"Final score: {final_score:.2f} (total weight: {total_weight:.2f})")
            
            return float(np.clip(final_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating market mood: {str(e)}", exc_info=True)
            return 50.0

    def _calculate_risk_score(self, sentiment_data: Dict[str, Any]) -> float:
        """Calculate risk score based on market-wide risk parameters."""
        try:
            # Debug the input structure
            self.logger.debug("\n=== Calculating Risk Score ===")
            self.logger.debug(f"Sentiment data keys: {list(sentiment_data.keys())}")
            
            # Get risk data from sentiment data
            risk_data = None
            
            # Try different paths to find risk data
            if 'risk_limit' in sentiment_data:
                risk_data = sentiment_data['risk_limit']
                self.logger.debug(f"Found risk_limit data: {type(risk_data)}")
            elif 'sentiment' in sentiment_data and 'risk_limit' in sentiment_data['sentiment']:
                risk_data = sentiment_data['sentiment']['risk_limit']
                self.logger.debug(f"Found risk_limit in sentiment: {type(risk_data)}")
            
            if not risk_data:
                self.logger.debug("No risk data available")
                return 50.0
            
            if not isinstance(risk_data, dict):
                self.logger.debug(f"Invalid risk data type: {type(risk_data)}")
                return 50.0
            
            # Print actual data structure for debugging
            if len(risk_data) > 0:
                self.logger.debug(f"Risk data keys: {list(risk_data.keys())}")
                if len(str(risk_data)) < 1000:  # Only log if not too large
                    self.logger.debug(f"Risk data: {risk_data}")
            
            # Extract risk levels from response structure
            risk_levels = []
            if 'result' in risk_data and 'list' in risk_data['result']:
                risk_levels = risk_data['result']['list']
                self.logger.debug(f"Found {len(risk_levels)} risk levels in result.list")
            elif 'levels' in risk_data:
                risk_levels = risk_data['levels']
                self.logger.debug(f"Found {len(risk_levels)} risk levels in levels")
            elif 'riskLimits' in risk_data:
                risk_levels = risk_data['riskLimits']
                self.logger.debug(f"Found {len(risk_levels)} risk levels in riskLimits")
            
            if not risk_levels:
                self.logger.debug("No risk levels available")
                return 50.0
            
            # Log first risk level for debugging
            if len(risk_levels) > 0:
                self.logger.debug(f"First risk level: {risk_levels[0]}")
            
            # Sort risk levels by ID to ensure proper ordering
            try:
                risk_levels = sorted(risk_levels, key=lambda x: int(x.get('id', 0)))
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Error sorting risk levels: {e}")
            
            # Get base tier (lowest risk tier)
            base_tier = risk_levels[0]
            
            # Extract key values with fallbacks
            initial_margin = 0.01  # Default 1%
            max_leverage = 100.0   # Default 100x
            
            try:
                # Try to extract initial margin
                if 'initialMargin' in base_tier:
                    initial_margin = float(base_tier['initialMargin'])
                    self.logger.debug(f"Extracted initialMargin: {initial_margin}")
                
                # Try to extract max leverage
                if 'maxLeverage' in base_tier:
                    max_leverage = float(base_tier['maxLeverage'])
                    self.logger.debug(f"Extracted maxLeverage: {max_leverage}")
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Error extracting risk parameters: {e}")
            
            # Calculate base risk score (40% weight)
            # Lower initial margin = better score
            base_score = 100 - (initial_margin * 100 * 10)  # Scale factor of 10 to make more sensitive
            base_score = max(0, min(100, base_score))
            
            # Calculate leverage score (30% weight)
            # Higher max leverage = better score
            leverage_score = (max_leverage / 100) * 100  # Normalize to 0-100
            leverage_score = max(0, min(100, leverage_score))
            
            # Calculate market risk score (30% weight)
            # Based on the number and distribution of risk tiers
            num_tiers = len(risk_levels)
            
            try:
                max_risk_limit = float(risk_levels[-1].get('riskLimitValue', 0))
                min_risk_limit = float(base_tier.get('riskLimitValue', 0))
                self.logger.debug(f"Risk limits - min: {min_risk_limit}, max: {max_risk_limit}, tiers: {num_tiers}")
            except (ValueError, TypeError, IndexError) as e:
                self.logger.warning(f"Error processing risk limits: {e}")
                max_risk_limit = 1_200_000_000  # Default large value
                min_risk_limit = 2_000_000      # Default small value
            
            # More tiers and higher max risk limit = better market depth = better score
            market_depth_score = min(100, (num_tiers / 35) * 100)  # Normalize against typical max of 35 tiers
            risk_limit_score = min(100, (max_risk_limit / 1_200_000_000) * 100)  # Normalize against 1.2B typical max
            market_risk_score = (market_depth_score * 0.5) + (risk_limit_score * 0.5)
            
            # Calculate weighted final score
            weights = {
                'base': 0.4,
                'leverage': 0.3,
                'market_risk': 0.3
            }
            
            final_score = (
                base_score * weights['base'] +
                leverage_score * weights['leverage'] +
                market_risk_score * weights['market_risk']
            )
            
            # Log detailed breakdown
            self.logger.debug("\n=== Risk Score Breakdown ===")
            self.logger.debug(f"Base Tier Initial Margin: {initial_margin:.4f}")
            self.logger.debug(f"Max Leverage: {max_leverage:.2f}x")
            self.logger.debug(f"Number of Risk Tiers: {num_tiers}")
            self.logger.debug(f"Max Risk Limit: {max_risk_limit:,.0f}")
            self.logger.debug(f"\nComponent Scores:")
            self.logger.debug(f"Base Score: {base_score:.2f} (weight: {weights['base']:.2f})")
            self.logger.debug(f"Leverage Score: {leverage_score:.2f} (weight: {weights['leverage']:.2f})")
            self.logger.debug(f"Market Risk Score: {market_risk_score:.2f} (weight: {weights['market_risk']:.2f})")
            self.logger.debug(f"Final Risk Score: {final_score:.2f}")
            
            return float(np.clip(final_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating risk score: {str(e)}")
            return 50.0

    def _calculate_volatility_score(self, volatility_data: Dict[str, Any]) -> float:
        """Calculate sentiment score based on historical volatility."""
        try:
            self.logger.debug("\n=== Calculating Volatility Score ===")
            
            # Log input data
            if isinstance(volatility_data, dict):
                self.logger.debug(f"Volatility data keys: {list(volatility_data.keys())}")
                if len(str(volatility_data)) < 1000:  # Only log if not too large
                    self.logger.debug(f"Volatility data: {volatility_data}")
            else:
                self.logger.debug(f"Volatility data type: {type(volatility_data)}")
            
            if not volatility_data or not isinstance(volatility_data, dict):
                self.logger.debug("No volatility data available, returning neutral score")
                return 50.0

            # Extract volatility value
            volatility = None
            
            # Try different keys that might contain the volatility value
            for key in ['value', 'volatility', 'historical_volatility']:
                if key in volatility_data:
                    try:
                        volatility = float(volatility_data[key])
                        self.logger.debug(f"Found volatility in key '{key}': {volatility}")
                        break
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Error converting volatility from key '{key}': {e}")
            
            if volatility is None:
                self.logger.debug("No valid volatility value found")
                return 50.0
                
            self.logger.debug(f"Raw volatility value: {volatility}")

            # Convert to percentage if needed (if value is in decimal form)
            if volatility < 1 and volatility > 0:
                volatility = volatility * 100
                self.logger.debug(f"Converted to percentage: {volatility}%")

            # Calculate score based on volatility ranges
            if volatility <= 30:
                # Low volatility (bullish) - map 0-30% to 80-100
                score = 80 + (30 - volatility) * (20/30)
                explanation = "Low volatility is bullish"
            elif volatility <= 60:
                # Medium volatility (neutral) - map 30-60% to 50-80
                score = 80 - ((volatility - 30) * (30/30))
                explanation = "Medium volatility is neutral to slightly bullish"
            else:
                # High volatility (bearish) - map >60% to 0-50
                score = max(0, 50 - ((volatility - 60) * (50/40)))
                explanation = "High volatility is bearish"

            score = float(np.clip(score, 0, 100))
            
            self.logger.debug(f"Volatility: {volatility:.2f}%, Score: {score:.2f} ({explanation})")
            return score

        except Exception as e:
            self.logger.error(f"Error calculating volatility score: {str(e)}")
            return 50.0

    def calculate_historical_volatility(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate historical volatility from OHLCV data."""
        try:
            # Get base timeframe data (1m)
            ohlcv_data = market_data.get('ohlcv', {})
            base_df = ohlcv_data.get('base')
            
            if not isinstance(base_df, pd.DataFrame) or base_df.empty:
                return None
                
            # Calculate returns
            returns = np.log(base_df['close'] / base_df['close'].shift(1))
            
            # Calculate annualized volatility (assuming 1m data)
            volatility = returns.std() * np.sqrt(525600)  # Annualized from 1-minute data
            
            return {
                'value': volatility,
                'window': len(base_df),
                'timeframe': '1m'
            }
        except Exception as e:
            self.logger.error(f"Error calculating historical volatility: {str(e)}")
            return None

    def _prepare_risk_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare risk data from market data."""
        try:
            ticker = market_data.get('ticker', {})
            
            # Extract values from ticker
            open_interest_value = float(ticker.get('openInterestValue', 0))
            max_leverage = float(ticker.get('maxLeverage', 100))
            
            # Calculate initial margin based on max leverage
            initial_margin = 1 / max_leverage if max_leverage > 0 else 0.01
            
            # Create base risk tier
            base_tier = {
                'id': 1,
                'initialMargin': initial_margin,
                'maxLeverage': max_leverage,
                'riskLimitValue': open_interest_value,
                'tier': 1
            }
            
            # Create risk data structure
            risk_data = {
                'levels': [base_tier]
            }
            
            # Add additional risk tiers if available
            if 'riskLimits' in market_data:
                additional_tiers = market_data['riskLimits']
                if isinstance(additional_tiers, list):
                    for i, tier in enumerate(additional_tiers, start=2):
                        tier['id'] = i
                        risk_data['levels'].append(tier)
            
            self.logger.debug(f"Prepared risk data with {len(risk_data['levels'])} tiers")
            return risk_data
            
        except Exception as e:
            self.logger.error(f"Error preparing risk data: {str(e)}")
            return None

    def _process_sentiment_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and normalize sentiment data from market_data."""
        try:
            self.logger.debug(f"Processing sentiment data from market_data with keys: {list(market_data.keys())}")
            
            # Create a copy of the sentiment data (avoid double nesting)
            sentiment_data = {}
            
            # First check if sentiment is directly in market_data
            if 'sentiment' in market_data:
                sentiment_data = market_data['sentiment'].copy() if isinstance(market_data['sentiment'], dict) else {}
                self.logger.debug(f"Found sentiment data with keys: {list(sentiment_data.keys())}")
            
            # Calculate historical volatility
            volatility_data = self.calculate_historical_volatility(market_data)
            if volatility_data:
                sentiment_data['volatility'] = volatility_data
                self.logger.debug(f"Added calculated volatility: {volatility_data}")
            
            # Prepare risk data
            risk_data = self._prepare_risk_data(market_data)
            if risk_data:
                sentiment_data['risk_limit'] = risk_data
                self.logger.debug(f"Added prepared risk data with {len(risk_data['levels'])} tiers")

            # Process long/short ratio from different formats
            if 'long_short_ratio' in market_data:
                lsr_data = market_data['long_short_ratio']
                self.logger.debug(f"Processing external long_short_ratio: {lsr_data}")
                
                if isinstance(lsr_data, dict) and 'list' in lsr_data:
                    # Get most recent entry from Bybit historical data
                    latest_lsr = lsr_data['list'][0] if lsr_data['list'] else None
                    if latest_lsr:
                        sentiment_data['long_short_ratio'] = latest_lsr
                        self.logger.debug(f"Using latest LSR data from list: {latest_lsr}")
                else:
                    sentiment_data['long_short_ratio'] = lsr_data
                    self.logger.debug(f"Using direct LSR data: {lsr_data}")
            
            # Add other required fields directly from market_data if not already in sentiment
            for field in ['liquidations', 'risk_limit', 'ticker']:
                if field in market_data and field not in sentiment_data:
                    sentiment_data[field] = market_data[field]
                    self.logger.debug(f"Added {field} from market_data")
            
            # Handle funding_rate specially since it might be in ticker data
            if 'funding_rate' not in sentiment_data:
                # Try direct value
                if 'funding_rate' in market_data:
                    sentiment_data['funding_rate'] = market_data['funding_rate']
                    self.logger.debug(f"Added funding_rate from market_data: {market_data['funding_rate']}")
                # Try from ticker
                elif 'ticker' in market_data:
                    ticker = market_data['ticker']
                    if isinstance(ticker, dict) and 'fundingRate' in ticker:
                        funding_rate = float(ticker['fundingRate'])
                        sentiment_data['funding_rate'] = funding_rate
                        self.logger.debug(f"Added funding_rate from ticker: {funding_rate}")
            
            self.logger.debug(f"Processed sentiment data: {sentiment_data}")
            return sentiment_data
        
        except Exception as e:
            self.logger.error(f"Error processing sentiment data: {str(e)}")
            # Return empty dict with minimal structure
            return {
                'funding_rate': None,
                'long_short_ratio': None,
                'liquidations': []
            }

    def _apply_sigmoid_transformation(self, value, sensitivity=None, center=50):
        """
        Apply sigmoid transformation to make values more sensitive around the center.
        
        Args:
            value: Raw value to transform
            sensitivity: Controls the steepness of the curve
            center: Center point of the transformation
            
        Returns:
            Transformed value
        """
        try:
            # Use provided sensitivity or default from config
            sensitivity = sensitivity or self.default_sensitivity
            
            # Normalize around center
            normalized = (value - center) / 50
            
            # Apply sigmoid with sensitivity parameter
            transformed = 1 / (1 + np.exp(-normalized / sensitivity))
            
            # Scale back to original range
            result = transformed * 100
            
            self.logger.debug(f"Sigmoid transformation: input={value:.2f}, sensitivity={sensitivity}, output={result:.2f}")
            
            return float(result)
        except Exception as e:
            self.logger.error(f"Error in sigmoid transformation: {str(e)}")
            return value  # Return original value on error

    def _log_component_breakdown(self, components: Dict[str, float], symbol: str = "") -> None:
        """Log detailed breakdown of sentiment components."""
        try:
            # First log the raw component details for debugging
            self.logger.debug("\n=== Sentiment Component Breakdown ===")
            for component, score in components.items():
                if component == 'sentiment':  # Skip the overall sentiment score in debug output
                    continue
                weight = self.component_weights.get(component, 0.0)
                weighted_score = score * weight
                self.logger.debug(f"{component}:")
                self.logger.debug(f"  Raw Score: {score:.2f}")
                self.logger.debug(f"  Weight: {weight:.2f}")
                self.logger.debug(f"  Weighted Score: {weighted_score:.2f}")
            self.logger.debug("================================")
            
            # Now create a nicely formatted table view
            # Create list of (component, score, weight, contribution) tuples for formatter
            # Exclude the 'sentiment' entry which is the final score, not a component
            contributions = []
            for component, score in components.items():
                # Skip the overall sentiment score in the breakdown table
                if component == 'sentiment':
                    continue
                    
                weight = self.component_weights.get(component, 0.0)
                contribution = score * weight
                contributions.append((component, score, weight, contribution))
            
            # Sort by contribution (highest first)
            contributions.sort(key=lambda x: x[3], reverse=True)
            
            # Use the fancy formatter
            from src.core.formatting.formatter import LogFormatter
            formatted_section = LogFormatter.format_score_contribution_section(
                "Sentiment Score Contribution Breakdown", 
                contributions, 
                symbol
            )
            
            # Log the formatted breakdown at INFO level for visibility
            self.logger.info(formatted_section)
            
        except Exception as e:
            self.logger.error(f"Error logging component breakdown: {str(e)}")

    def _get_component_interpretation(self, component: str, score: float) -> str:
        """Get detailed interpretation for each component."""
        try:
            if score >= 80:
                strength = "strongly bullish"
            elif score >= 60:
                strength = "moderately bullish"
            elif score <= 20:
                strength = "strongly bearish"
            elif score <= 40:
                strength = "moderately bearish"
            else:
                strength = "neutral"

            interpretations = {
                'long_short_ratio': f"Long/Short ratio indicating {strength} sentiment",
                'funding_rate': f"Funding rate showing {strength} market expectations",
                'funding_rate_volatility': f"Funding rate volatility suggesting {strength} market stability",
                'liquidation_events': f"Liquidation events indicating {strength} market pressure",
                'volume_sentiment': f"Volume analysis showing {strength} buying/selling pressure",
                'market_mood': f"Overall market mood is {strength}",
                'risk_score': f"Risk metrics suggesting {strength} market conditions"
            }
            
            return interpretations.get(component, f"Score is {strength}")
            
        except Exception as e:
            self.logger.error(f"Error getting component interpretation: {str(e)}")
            return "Interpretation unavailable"

    def _get_detailed_sentiment_interpretation(self, components: Dict[str, float], weighted_score: float) -> Dict[str, Any]:
        """Generate detailed interpretation of sentiment analysis results."""
        try:
            # Get individual component interpretations
            component_interpretations = {
                component: self._get_component_interpretation(component, score)
                for component, score in components.items()
            }

            # Determine overall bias
            if weighted_score >= 70:
                bias = "strongly bullish"
                signal = "strong_buy"
            elif weighted_score >= 60:
                bias = "moderately bullish"
                signal = "buy"
            elif weighted_score <= 30:
                bias = "strongly bearish"
                signal = "strong_sell"
            elif weighted_score <= 40:
                bias = "moderately bearish"
                signal = "sell"
            else:
                bias = "neutral"
                signal = "neutral"

            # Add risk assessment
            risk_level = "favorable" if components.get('risk_score', 50) > 60 else "unfavorable"
            
            return {
                "signal": signal,
                "bias": bias,
                "risk_level": risk_level,
                "summary": f"Market sentiment is {bias} with {risk_level} risk conditions",
                "component_interpretations": component_interpretations
            }
            
        except Exception as e:
            self.logger.error(f"Error generating detailed sentiment interpretation: {str(e)}")
            return {
                "signal": "error",
                "summary": "Unable to generate sentiment interpretation",
                "error": str(e)
            }

    def _get_default_scores(self, reason: str = 'UNKNOWN') -> Dict[str, Any]:
        """Return default scores when analysis fails."""
        timestamp = int(time.time() * 1000)
        return {
            'score': 50.0,
            'components': {
                'long_short_ratio': 50.0,
                'funding_rate': 50.0,
                'liquidations': 50.0,
                'volume_sentiment': 50.0,
                'market_mood': 50.0,
                'risk': 50.0
            },
            'interpretation': 'Analysis failed: ' + reason,
            'metadata': {
                'timestamp': timestamp,
                'status': 'ERROR',
                'error': reason,
                'calculation_time_ms': 0
            }
        }

    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate sentiment input data."""
        try:
            if not isinstance(data, dict):
                self.logger.error("Input data must be a dictionary")
                return False
            
            if 'sentiment' not in data:
                self.logger.debug("Creating empty sentiment data structure")
                data['sentiment'] = {
                    'funding_rate': None,
                    'long_short_ratio': None,
                    'liquidations': []
                }
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error validating sentiment data: {str(e)}")
            return False

    @property
    def required_data(self) -> List[str]:
        """Required data fields for sentiment analysis."""
        return ['sentiment', 'ohlcv']

    def reset_cache(self):
        """Reset the calculation cache."""
        self._cache = {
            'missing_risk_data': False,
            'last_funding_rate': None,
            'last_lsr': None,
            'last_calculation_time': 0
        }

    def _calculate_sync(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate sentiment indicators synchronously.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Dictionary containing sentiment scores, components, and interpretation
        """
        try:
            start_time = time.time()
            self.logger.debug(f"Calculating sentiment with input keys: {list(market_data.keys())}")
            
            # Process sentiment data from market data
            processed_data = self._process_sentiment_data(market_data)
            self.logger.debug(f"Processed sentiment data: {processed_data}")
            
            # Initialize component scores dictionary
            components = {}
            
            # Calculate funding rate score
            try:
                self.logger.debug("Calculating funding rate score...")
                funding_score = self._calculate_funding_score(processed_data)
                self.logger.debug(f"Funding rate score calculated: {funding_score}")
                components['funding_rate'] = funding_score
            except Exception as e:
                self.logger.error(f"Error calculating funding rate score: {str(e)}")
                components['funding_rate'] = 50.0
            
            # Calculate long/short ratio score
            try:
                self.logger.debug("Calculating long/short ratio score...")
                lsr_data = processed_data.get('long_short_ratio')
                self.logger.debug(f"LSR data for calculation: {lsr_data}")
                lsr_score = self._calculate_lsr_score(lsr_data)
                self.logger.debug(f"Long/short ratio score calculated: {lsr_score}")
                components['long_short_ratio'] = lsr_score
            except Exception as e:
                self.logger.error(f"Error calculating long/short ratio score: {str(e)}", exc_info=True)
                components['long_short_ratio'] = 50.0
            
            # Calculate market mood score
            try:
                self.logger.debug("Calculating market mood score...")
                mood_data = processed_data.get('market_mood')
                self.logger.debug(f"Market mood data for calculation: {mood_data}")
                mood_score = self._calculate_market_mood(processed_data)
                self.logger.debug(f"Market mood score calculated: {mood_score}")
                components['market_mood'] = mood_score
            except Exception as e:
                self.logger.error(f"Error calculating market mood score: {str(e)}")
                components['market_mood'] = 50.0
            
            # Calculate liquidation score
            try:
                self.logger.debug("Calculating liquidation score...")
                liquidation_score = self._calculate_liquidation_score(processed_data)
                self.logger.debug(f"Liquidation score calculated: {liquidation_score}")
                components['liquidations'] = liquidation_score
            except Exception as e:
                self.logger.error(f"Error calculating liquidation score: {str(e)}")
                components['liquidations'] = 50.0
                
            # Calculate volatility score
            try:
                self.logger.debug("Calculating volatility score...")
                volatility_data = processed_data.get('volatility')
                self.logger.debug(f"Volatility data for calculation: {volatility_data}")
                volatility_score = self._calculate_volatility_score(volatility_data)
                self.logger.debug(f"Volatility score calculated: {volatility_score}")
                components['volatility'] = volatility_score
            except Exception as e:
                self.logger.error(f"Error calculating volatility score: {str(e)}")
                components['volatility'] = 50.0
                
            # Calculate risk score
            try:
                self.logger.debug("Calculating risk score...")
                risk_score = self._calculate_risk_score(processed_data)
                self.logger.debug(f"Risk score calculated: {risk_score}")
                components['risk'] = risk_score
            except Exception as e:
                self.logger.error(f"Error calculating risk score: {str(e)}")
                components['risk'] = 50.0
                
            # Calculate market activity score (combines volume and open interest)
            try:
                self.logger.debug("Calculating market activity score...")
                market_activity_score = self._calculate_market_activity(market_data)
                self.logger.debug(f"Market activity score calculated: {market_activity_score}")
                components['market_activity'] = market_activity_score
            except Exception as e:
                self.logger.error(f"Error calculating market activity score: {str(e)}")
                components['market_activity'] = 50.0
                
            # Calculate open interest score (kept for backward compatibility)
            try:
                self.logger.debug("Calculating open interest score...")
                oi_data = processed_data.get('open_interest')
                self.logger.debug(f"Open interest data for calculation: {oi_data}")
                oi_score = self._calculate_open_interest_score(processed_data)
                self.logger.debug(f"Open interest score calculated: {oi_score}")
                components['open_interest'] = oi_score
            except Exception as e:
                self.logger.error(f"Error calculating open interest score: {str(e)}")
                components['open_interest'] = 50.0
                
            # Calculate the overall sentiment score as weighted average of components
            try:
                self.logger.debug("Calculating overall sentiment score...")
                sentiment_score = self._compute_weighted_score(components)
                self.logger.debug(f"Overall sentiment score calculated: {sentiment_score}")
            except Exception as e:
                self.logger.error(f"Error computing weighted sentiment score: {str(e)}")
                sentiment_score = 50.0
            
            # Log component breakdown
            self._log_component_breakdown(components, market_data.get('symbol', ''))
            
            # Add sentinel to components dictionary
            components['sentiment'] = sentiment_score
            
            # Generate interpretation
            interpretation = self._interpret_sentiment(sentiment_score, components)
            
            # Generate signals based on sentiment
            signals = self._generate_signals(components)
            
            # Calculate execution time
            end_time = time.time()
            execution_time_ms = (end_time - start_time) * 1000
            
            # Return result
            return {
                'score': sentiment_score,
                'components': components,
                'signals': signals,
                'interpretation': interpretation,
                'timestamp': end_time,
                'success': True,
                'metadata': {
                    'timestamp': int(end_time * 1000),
                    'status': 'SUCCESS',
                    'calculation_time_ms': execution_time_ms
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating sentiment: {str(e)}", exc_info=True)
            error_time = time.time()
            return {
                'score': 50.0, 
                'components': {'sentiment': 50.0},
                'signals': [],
                'interpretation': {
                    'sentiment': 'Neutral (default due to calculation error)',
                    'error': str(e)
                },
                'timestamp': error_time,
                'success': False,
                'metadata': {
                    'timestamp': int(error_time * 1000),
                    'status': 'ERROR',
                    'error': str(e),
                    'calculation_time_ms': 0
                }
            }

    # Original calculate method - keep for backwards compatibility
    def calculate(self, sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate sentiment indicators from market data.
        
        Args:
            sentiment_data: Dictionary containing market data
            
        Returns:
            Dictionary containing sentiment scores, components, and interpretation
        """
        return self._calculate_sync(sentiment_data)

    async def calculate(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async version of calculate method to ensure compatibility with confluence analyzer.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Dictionary containing sentiment scores, components, and interpretation
        """
        try:
            self.logger.debug("Running async calculate for sentiment indicators")
            self.logger.debug(f"Market data keys: {list(market_data.keys())}")
            if 'sentiment' in market_data:
                self.logger.debug(f"Sentiment keys: {list(market_data['sentiment'].keys())}")
                if 'long_short_ratio' in market_data['sentiment']:
                    self.logger.debug(f"Long/Short ratio data: {market_data['sentiment']['long_short_ratio']}")
                if 'funding_rate' in market_data['sentiment']:
                    self.logger.debug(f"Funding rate data: {market_data['sentiment']['funding_rate']}")
            
            # Call the synchronous calculate method
            result = self._calculate_sync(market_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in async sentiment calculation: {str(e)}", exc_info=True)
            error_time = time.time()
            return {
                'score': 50.0, 
                'components': {'sentiment': 50.0},
                'signals': [],
                'interpretation': {
                    'sentiment': 'Neutral (default due to calculation error)',
                    'error': str(e)
                },
                'timestamp': error_time,
                'success': False,
                'metadata': {
                    'timestamp': int(error_time * 1000),
                    'status': 'ERROR',
                    'error': str(e),
                    'calculation_time_ms': 0
                }
            }

    async def calculate_score(self, market_data: Dict[str, Any]) -> float:
        """
        Calculate sentiment score asynchronously - required for confluence analyzer.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: Overall sentiment score (0-100)
        """
        try:
            self.logger.debug("Running async calculate_score for sentiment indicators")
            
            # Call the regular calculate method which does all the heavy lifting
            result = await self.calculate(market_data)
            
            # Extract the overall score from the result
            score = result.get('score', 50.0)
            
            # Log detailed component breakdown using the standard format
            component_scores = result.get('components', {})
            if component_scores:
                from src.core.analysis.indicator_utils import log_score_contributions, log_final_score
                
                # Explicitly log the component breakdown details
                self._log_component_breakdown(component_scores, market_data.get('symbol', ''))
                
                # Get symbol from market data
                symbol = market_data.get('symbol', '')
                
                # Log component contributions
                log_score_contributions(
                    self.logger, 
                    f"{symbol} Sentiment Score Contribution Breakdown", 
                    component_scores, 
                    self.component_weights,
                    symbol=symbol,
                    final_score=score
                )
                
                # Log final score
                log_final_score(
                    self.logger,
                    "Sentiment",
                    score,
                    symbol=symbol
                )
            
            return float(score)
            
        except Exception as e:
            self.logger.error(f"Error in sentiment calculate_score: {str(e)}")
            return 50.0  # Default neutral score on error

    async def get_signals(self, sentiment_data: Dict[str, Any], existing_scores: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Extract trading signals from sentiment analysis.
        
        Args:
            sentiment_data: Dictionary containing sentiment data
            existing_scores: Optional pre-calculated scores from a previous call to calculate()
            
        Returns:
            List of signal dictionaries
        """
        try:
            # Use existing scores if provided to avoid redundant calculations
            if existing_scores and isinstance(existing_scores, dict):
                self.logger.debug("Using existing scores for signal generation")
                sentiment_scores = existing_scores
            else:
                # Calculate sentiment scores if not provided
                self.logger.debug("Calculating new scores for signal generation")
                sentiment_result = await self.calculate(sentiment_data)
                sentiment_scores = sentiment_result['components']
            
            signals = []
            sentiment_score = sentiment_scores.get('sentiment', 50.0)
            
            # Generate signals based on overall sentiment score
            if sentiment_score >= 75:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'STRONG',
                    'confidence': min(sentiment_score / 100, 0.95),
                    'reason': 'Strong bullish sentiment detected'
                })
            elif sentiment_score >= 60:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'MEDIUM',
                    'confidence': min(sentiment_score / 100, 0.8),
                    'reason': 'Moderate bullish sentiment detected'
                })
            elif sentiment_score <= 25:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'STRONG',
                    'confidence': min((100 - sentiment_score) / 100, 0.95),
                    'reason': 'Strong bearish sentiment detected'
                })
            elif sentiment_score <= 40:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'MEDIUM',
                    'confidence': min((100 - sentiment_score) / 100, 0.8),
                    'reason': 'Moderate bearish sentiment detected'
                })
            
            # Check for component-specific signals
            
            # Check funding rate signals
            funding_score = sentiment_scores.get('funding_rate', 50.0)
            if funding_score >= 80:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'MEDIUM',
                    'confidence': min(funding_score / 100, 0.85),
                    'reason': 'Highly negative funding rate (favors longs)',
                    'component': 'funding_rate'
                })
            elif funding_score <= 20:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'MEDIUM',
                    'confidence': min((100 - funding_score) / 100, 0.85),
                    'reason': 'Highly positive funding rate (favors shorts)',
                    'component': 'funding_rate'
                })
            
            # Check liquidation signals
            liquidation_score = sentiment_scores.get('liquidations', 50.0)
            if liquidation_score >= 75:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'MEDIUM',
                    'confidence': min(liquidation_score / 100, 0.8),
                    'reason': 'Major short liquidations detected',
                    'component': 'liquidations'
                })
            elif liquidation_score <= 25:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'MEDIUM',
                    'confidence': min((100 - liquidation_score) / 100, 0.8),
                    'reason': 'Major long liquidations detected',
                    'component': 'liquidations'
                })
            
            # Add volume signals
            volume_score = sentiment_scores.get('volume', 50.0)
            if volume_score >= 70:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'WEAK',
                    'confidence': min(volume_score / 100, 0.7),
                    'reason': 'Strong buying volume detected',
                    'component': 'volume'
                })
            elif volume_score <= 30:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'WEAK',
                    'confidence': min((100 - volume_score) / 100, 0.7),
                    'reason': 'Strong selling volume detected',
                    'component': 'volume'
                })
            
            # Combine similar signals
            combined_signals = self._combine_similar_signals(signals)
            
            return combined_signals
        
        except Exception as e:
            self.logger.error(f"Error generating sentiment signals: {str(e)}")
            return []

    def _get_signals_sync(self, sentiment_data: Dict[str, Any], existing_scores: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Synchronous version of get_signals method to be used in _calculate_sync.
        
        Args:
            sentiment_data: Dictionary containing sentiment data
            existing_scores: Optional pre-calculated scores from a previous call to calculate()
            
        Returns:
            List of signal dictionaries
        """
        try:
            # Use existing scores to avoid redundant calculations
            if existing_scores and isinstance(existing_scores, dict):
                self.logger.debug("Using existing scores for signal generation")
                sentiment_scores = existing_scores
            else:
                # For synchronous context, we'll use the synchronous calculate method
                self.logger.debug("Calculating new scores for signal generation")
                sentiment_result = self.calculate(sentiment_data)  # Use synchronous calculate
                sentiment_scores = sentiment_result.get('components', {})
            
            signals = []
            sentiment_score = sentiment_scores.get('sentiment', 50.0)
            
            # Generate signals based on overall sentiment score
            if sentiment_score >= 75:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'STRONG',
                    'confidence': min(sentiment_score / 100, 0.95),
                    'reason': 'Strong bullish sentiment detected'
                })
            elif sentiment_score >= 60:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'MEDIUM',
                    'confidence': min(sentiment_score / 100, 0.8),
                    'reason': 'Moderate bullish sentiment detected'
                })
            elif sentiment_score <= 25:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'STRONG',
                    'confidence': min((100 - sentiment_score) / 100, 0.95),
                    'reason': 'Strong bearish sentiment detected'
                })
            elif sentiment_score <= 40:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'MEDIUM',
                    'confidence': min((100 - sentiment_score) / 100, 0.8),
                    'reason': 'Moderate bearish sentiment detected'
                })
            
            # Check for component-specific signals
            
            # Check funding rate signals
            funding_score = sentiment_scores.get('funding_rate', 50.0)
            if funding_score >= 80:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'MEDIUM',
                    'confidence': min(funding_score / 100, 0.85),
                    'reason': 'Highly negative funding rate (favors longs)',
                    'component': 'funding_rate'
                })
            elif funding_score <= 20:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'MEDIUM',
                    'confidence': min((100 - funding_score) / 100, 0.85),
                    'reason': 'Highly positive funding rate (favors shorts)',
                    'component': 'funding_rate'
                })
            
            # Check liquidation signals
            liquidation_score = sentiment_scores.get('liquidations', 50.0)
            if liquidation_score >= 75:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'MEDIUM',
                    'confidence': min(liquidation_score / 100, 0.8),
                    'reason': 'Major short liquidations detected',
                    'component': 'liquidations'
                })
            elif liquidation_score <= 25:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'MEDIUM',
                    'confidence': min((100 - liquidation_score) / 100, 0.8),
                    'reason': 'Major long liquidations detected',
                    'component': 'liquidations'
                })
            
            # Add volume signals
            volume_score = sentiment_scores.get('volume', 50.0)
            if volume_score >= 70:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'WEAK',
                    'confidence': min(volume_score / 100, 0.7),
                    'reason': 'Strong buying volume detected',
                    'component': 'volume'
                })
            elif volume_score <= 30:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'WEAK',
                    'confidence': min((100 - volume_score) / 100, 0.7),
                    'reason': 'Strong selling volume detected',
                    'component': 'volume'
                })
            
            # Combine similar signals
            combined_signals = self._combine_similar_signals(signals)
            
            return combined_signals
        
        except Exception as e:
            self.logger.error(f"Error generating sentiment signals in sync mode: {str(e)}")
            return []

    def _combine_similar_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Combine signals with the same direction but different sources.
        
        Args:
            signals: List of signal dictionaries
            
        Returns:
            List of combined signals
        """
        if not signals:
            return []
            
        try:
            # Group signals by direction
            buy_signals = [s for s in signals if s['signal'] == 'BUY']
            sell_signals = [s for s in signals if s['signal'] == 'SELL']
            
            result = []
            
            # Combine buy signals if there are multiple
            if len(buy_signals) > 1:
                # Take the strongest signal
                strengths = {'STRONG': 3, 'MEDIUM': 2, 'WEAK': 1}
                strongest = max(buy_signals, key=lambda x: strengths.get(x.get('strength', 'WEAK'), 0))
                
                # Calculate average confidence
                avg_confidence = sum(s.get('confidence', 0) for s in buy_signals) / len(buy_signals)
                
                # Combine reasons
                reasons = [s.get('reason', '') for s in buy_signals]
                combined_reason = "; ".join(reasons)
                
                # Create combined signal
                combined_buy = {
                    'signal': 'BUY',
                    'strength': strongest.get('strength', 'MEDIUM'),
                    'confidence': min(avg_confidence + 0.05, 0.95),  # Slightly boost confidence for multiple signals
                    'reason': combined_reason,
                    'components': [s.get('component', 'multiple') for s in buy_signals]
                }
                
                result.append(combined_buy)
            elif len(buy_signals) == 1:
                result.append(buy_signals[0])
                
            # Combine sell signals if there are multiple
            if len(sell_signals) > 1:
                # Take the strongest signal
                strengths = {'STRONG': 3, 'MEDIUM': 2, 'WEAK': 1}
                strongest = max(sell_signals, key=lambda x: strengths.get(x.get('strength', 'WEAK'), 0))
                
                # Calculate average confidence
                avg_confidence = sum(s.get('confidence', 0) for s in sell_signals) / len(sell_signals)
                
                # Combine reasons
                reasons = [s.get('reason', '') for s in sell_signals]
                combined_reason = "; ".join(reasons)
                
                # Create combined signal
                combined_sell = {
                    'signal': 'SELL',
                    'strength': strongest.get('strength', 'MEDIUM'),
                    'confidence': min(avg_confidence + 0.05, 0.95),  # Slightly boost confidence for multiple signals
                    'reason': combined_reason,
                    'components': [s.get('component', 'multiple') for s in sell_signals]
                }
                
                result.append(combined_sell)
            elif len(sell_signals) == 1:
                result.append(sell_signals[0])
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error combining signals: {str(e)}")
            return signals

    def _get_volume_sentiment_ratio(self, market_data: Dict[str, Any]) -> float:
        """
        Calculate the buy/sell volume ratio from trades.
        
        Args:
            market_data: Dictionary containing market data with trades
            
        Returns:
            float: Ratio of buy volume to sell volume (>1 means more buys)
        """
        try:
            trades = market_data.get('trades', [])
            if not trades:
                return 1.0  # Neutral ratio
                
            # Sum buy and sell volumes
            buy_volume = 0.0
            sell_volume = 0.0
            
            for trade in trades:
                side = trade.get('side', '').lower()
                amount = float(trade.get('amount', trade.get('size', 0)))
                
                if side == 'buy':
                    buy_volume += amount
                elif side == 'sell':
                    sell_volume += amount
            
            # Calculate ratio
            if sell_volume == 0:
                return 2.0  # Cap at 2:1 for extreme cases
            elif buy_volume == 0:
                return 0.5  # Cap at 1:2 for extreme cases
            else:
                return buy_volume / sell_volume
                
        except Exception as e:
            self.logger.error(f"Error calculating volume sentiment ratio: {str(e)}")
            return 1.0  # Neutral on error
            
    def _compute_weighted_score(self, scores: Dict[str, float]) -> float:
        """Calculate weighted average of sentiment scores."""
        try:
            self.logger.debug(f"\n=== Computing Weighted Score ===")
            self.logger.debug(f"Component weights: {self.component_weights}")
            self.logger.debug(f"Available scores: {scores}")
            
            # Filter to use only components that are in both weights and scores
            valid_components = set(self.component_weights.keys()).intersection(set(scores.keys()))
            
            if not valid_components:
                self.logger.warning("No valid components found for weighted score calculation")
                return 50.0
            
            # Calculate total weight of valid components
            valid_weights = {comp: weight for comp, weight in self.component_weights.items() if comp in valid_components}
            total_weight = sum(valid_weights.values())
            
            if total_weight == 0:
                self.logger.warning("Total weight of valid components is zero")
                return 50.0
            
            # Calculate weighted sum
            weighted_sum = sum(scores[component] * weight for component, weight in valid_weights.items())
            
            # Normalize by total weight
            final_score = weighted_sum / total_weight
            
            self.logger.debug(f"Valid components: {valid_components}")
            self.logger.debug(f"Total weight: {total_weight:.4f}")
            self.logger.debug(f"Weighted sum: {weighted_sum:.4f}")
            self.logger.debug(f"Final score: {final_score:.4f}")
            
            return float(np.clip(final_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error computing weighted score: {str(e)}")
            # Return average of available scores if possible
            if scores:
                avg_score = sum(scores.values()) / len(scores)
                self.logger.warning(f"Falling back to simple average: {avg_score:.2f}")
                return float(np.clip(avg_score, 0, 100))
            return 50.0

    def _calculate_enhanced_metrics(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate enhanced metrics for sentiment analysis."""
        try:
            enhanced_metrics = {}
            
            # Extract OHLCV data if available
            ohlcv_data = market_data.get('ohlcv', {})
            
            # Calculate price change over last 24h
            if ohlcv_data and 'base' in ohlcv_data:
                df = ohlcv_data['base']
                if isinstance(df, pd.DataFrame) and len(df) > 24:
                    # Calculate price change
                    current_price = df['close'].iloc[-1]
                    price_24h_ago = df['close'].iloc[-25]  # 24 periods ago for 1-min data
                    
                    if price_24h_ago > 0:
                        price_change_pct = ((current_price - price_24h_ago) / price_24h_ago) * 100
                        enhanced_metrics['price_change_24h'] = round(price_change_pct, 2)
                    
                    # Calculate volatility (standard deviation of percent changes)
                    if len(df) > 30:
                        pct_changes = df['close'].pct_change().dropna()
                        volatility = pct_changes.std() * 100  # Convert to percentage
                        enhanced_metrics['volatility_24h'] = round(volatility, 2)
            
            # Determine market trend
            if 'price_change_24h' in enhanced_metrics:
                price_change = enhanced_metrics['price_change_24h']
                if price_change > 3:
                    enhanced_metrics['market_trend'] = 'bullish'
                elif price_change < -3:
                    enhanced_metrics['market_trend'] = 'bearish'
            else:
                    enhanced_metrics['market_trend'] = 'neutral'
            
            # Add fear & greed index if available from market_mood
            sentiment_data = market_data.get('sentiment', {})
            market_mood = sentiment_data.get('market_mood', {})
            
            if isinstance(market_mood, dict) and 'fear_and_greed' in market_mood:
                enhanced_metrics['fear_greed_index'] = market_mood['fear_and_greed']
            
            return enhanced_metrics
            
        except Exception as e:
            self.logger.warning(f"Error calculating enhanced metrics: {str(e)}")
            return {}

    def _calculate_liquidation_score(self, sentiment_data: Dict[str, Any]) -> float:
        """Calculate score based on liquidation events."""
        try:
            # Call the existing liquidation calculation method
            return self.calculate_liquidation_events(sentiment_data)
        except Exception as e:
            self.logger.error(f"Error calculating liquidation score: {str(e)}")
            return 50.0

    def _calculate_market_mood(self, sentiment_data: Dict[str, Any]) -> float:
        """Calculate score based on market mood."""
        try:
            # Call the existing market mood calculation method
            return self.calculate_market_mood(sentiment_data)
        except Exception as e:
            self.logger.error(f"Error calculating market mood score: {str(e)}")
            return 50.0

    def _safe_get(self, data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Safely get a value from a dictionary, handling nested keys."""
        try:
            if not isinstance(data, dict):
                return default
            
            # Handle nested keys
            keys = key.split('.')
            result = data
            for k in keys:
                if not isinstance(result, dict):
                    return default
                result = result.get(k, default)
                if result is None:
                    return default
            return result
        except Exception as e:
            self.logger.error(f"Error in _safe_get: {str(e)}")
            return default

    def _calculate_lsr_score(self, long_short_data: Any) -> float:
        self.logger.debug(f"[LSR] _calculate_lsr_score called with data: {long_short_data}")
        try:
            if not long_short_data:
                self.logger.warning("[LSR] No data provided to _calculate_lsr_score, returning 50.0")
                return 50.0
                
            if isinstance(long_short_data, dict):
                long_ratio = float(long_short_data.get('long', 50.0))
                short_ratio = float(long_short_data.get('short', 50.0))
                self.logger.info(f"[LSR] _calculate_lsr_score using dict - Long: {long_ratio}, Short: {short_ratio}")
            elif isinstance(long_short_data, (list, tuple)) and len(long_short_data) == 2:
                long_ratio, short_ratio = map(float, long_short_data)
                self.logger.info(f"[LSR] _calculate_lsr_score using tuple/list - Long: {long_ratio}, Short: {short_ratio}")
            else:
                self.logger.warning(f"[LSR] _calculate_lsr_score unrecognized format: {type(long_short_data)}, returning 50.0")
                return 50.0
                
            total = long_ratio + short_ratio
            self.logger.debug(f"[LSR] _calculate_lsr_score sum of ratios: {total}")
            
            if total == 0:
                self.logger.warning("[LSR] _calculate_lsr_score both ratios zero, returning 50.0")
                return 50.0
                
            long_percentage = (long_ratio / total) * 100
            self.logger.info(f"[LSR] _calculate_lsr_score calculated long percentage: {long_percentage:.2f}% from {long_ratio}/{total}")
            
            score = max(0, min(100, long_percentage))
            self.logger.debug(f"[LSR] _calculate_lsr_score final score: {score}")
            return score
        except Exception as e:
            self.logger.error(f"[LSR] Exception in _calculate_lsr_score: {e}")
            return 50.0

    def _calculate_open_interest_score(self, sentiment_data: Dict[str, Any]) -> float:
        """Calculate score based on open interest trend.
        
        Args:
            sentiment_data: Dictionary containing sentiment data
            
        Returns:
            Score between 0 and 100
        """
        try:
            self.logger.debug(f"\n=== Calculating Open Interest Score ===")
            
            # Check for open interest data
            oi_data = None
            
            # Try different paths to find open interest data
            if 'open_interest' in sentiment_data:
                oi_data = sentiment_data['open_interest']
                self.logger.debug(f"Found direct open_interest data: {type(oi_data)}")
            elif 'sentiment' in sentiment_data and 'open_interest' in sentiment_data['sentiment']:
                oi_data = sentiment_data['sentiment']['open_interest']
                self.logger.debug(f"Found open_interest in sentiment: {type(oi_data)}")
            elif 'ticker' in sentiment_data and 'openInterest' in sentiment_data['ticker']:
                # Extract from ticker
                ticker = sentiment_data['ticker']
                current_oi = float(ticker.get('openInterest', 0))
                oi_data = {
                    'current': current_oi,
                    'previous': current_oi * 0.98,  # Default to 2% less as previous
                    'timestamp': int(time.time() * 1000),
                    'history': []
                }
                self.logger.debug(f"Created OI data from ticker: {oi_data}")
            
            if not oi_data:
                self.logger.debug("No open interest data available")
                return 50.0
            
            # Log the OI data structure
            if len(str(oi_data)) < 1000:  # Only log if not too large
                self.logger.debug(f"Open interest data: {oi_data}")
            
            # Extract current and previous OI values
            current_oi = previous_oi = None
            
            if isinstance(oi_data, dict):
                current_oi = float(self._safe_get(oi_data, 'current', 0))
                previous_oi = float(self._safe_get(oi_data, 'previous', 0))
                self.logger.debug(f"Extracted OI values - current: {current_oi}, previous: {previous_oi}")
            
            # Handle case where we only have a single value
            if current_oi is None and isinstance(oi_data, (int, float)):
                current_oi = float(oi_data)
                previous_oi = current_oi * 0.98  # Assume 2% lower as default
                self.logger.debug(f"Using direct OI value: {current_oi}, estimated previous: {previous_oi}")
            
            # If we don't have valid OI data, return neutral
            if not current_oi or not previous_oi:
                self.logger.debug("Invalid OI values")
                return 50.0
            
            # Calculate OI change
            oi_change = 0
            if previous_oi > 0:
                oi_change = (current_oi - previous_oi) / previous_oi
                oi_change_pct = oi_change * 100
                self.logger.debug(f"OI change: {oi_change_pct:.2f}%")
            
            # Normalize the change to a score
            # Positive OI changes are bullish (price follows OI in strong trend)
            if oi_change > 0:
                # Cap at 20% change (normalization factor of 5)
                normalized_change = min(oi_change, 0.2) * 5
                score = 50 + (normalized_change * 50)  # Map to 50-100 range
                self.logger.debug(f"Positive OI change: normalized to {normalized_change:.4f}, score: {score:.2f} (bullish)")
                interpretation = "Strongly bullish (increasing open interest)"
            else:
                # Negative change, bearish
                # Cap at -20% change (normalization factor of 5)
                normalized_change = max(oi_change, -0.2) * 5
                score = 50 + (normalized_change * 50)  # Map to 0-50 range
                self.logger.debug(f"Negative OI change: normalized to {normalized_change:.4f}, score: {score:.2f} (bearish)")
                interpretation = "Bearish (decreasing open interest)"
            
            self.logger.debug(f"Open interest interpretation: {interpretation}")
            
            return float(np.clip(score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating open interest score: {str(e)}")
            return 50.0

    def _interpret_sentiment(self, overall_score: float, components: Dict[str, float]) -> Dict[str, str]:
        """Generate detailed interpretation of sentiment scores.
        
        Args:
            overall_score: The overall sentiment score
            components: Dictionary of component scores
            
        Returns:
            Dictionary of interpretations for each component
        """
        try:
            # Initialize interpretations dictionary
            interpretations = {}
            
            # Overall sentiment interpretation
            if overall_score >= 75:
                interpretations['sentiment'] = "Strongly bullish market sentiment"
            elif overall_score >= 60:
                interpretations['sentiment'] = "Bullish market sentiment"
            elif overall_score >= 40:
                interpretations['sentiment'] = "Neutral market sentiment"
            elif overall_score >= 25:
                interpretations['sentiment'] = "Bearish market sentiment"
            else:
                interpretations['sentiment'] = "Strongly bearish market sentiment"
                
            # Funding rate interpretation
            funding_score = components.get('funding_rate', 50)
            if funding_score >= 75:
                interpretations['funding_rate'] = "Very negative funding rate (strongly bullish)"
            elif funding_score >= 60:
                interpretations['funding_rate'] = "Negative funding rate (bullish)"
            elif funding_score >= 40:
                interpretations['funding_rate'] = "Neutral funding rate"
            elif funding_score >= 25:
                interpretations['funding_rate'] = "Positive funding rate (bearish)"
            else:
                interpretations['funding_rate'] = "Very positive funding rate (strongly bearish)"
                
            # Long/short ratio interpretation
            lsr_score = components.get('long_short_ratio', 50)
            if lsr_score >= 75:
                interpretations['long_short_ratio'] = "Strong long bias in trader positioning"
            elif lsr_score >= 60:
                interpretations['long_short_ratio'] = "Long bias in trader positioning"
            elif lsr_score >= 40:
                interpretations['long_short_ratio'] = "Balanced long/short positioning"
            elif lsr_score >= 25:
                interpretations['long_short_ratio'] = "Short bias in trader positioning"
            else:
                interpretations['long_short_ratio'] = "Strong short bias in trader positioning"
                
            # Market activity interpretation
            market_activity_score = components.get('market_activity', 50)
            if market_activity_score >= 75:
                interpretations['market_activity'] = "Very high market activity with strong participation (bullish)"
            elif market_activity_score >= 60:
                interpretations['market_activity'] = "Increasing market activity and participation (bullish)"
            elif market_activity_score >= 40:
                interpretations['market_activity'] = "Normal market activity and participation"
            elif market_activity_score >= 25:
                interpretations['market_activity'] = "Decreasing market activity and participation (bearish)"
            else:
                interpretations['market_activity'] = "Very low market activity with weak participation (bearish)"
                
            # Add more component interpretations as needed
            
            return interpretations
            
        except Exception as e:
            self.logger.error(f"Error interpreting sentiment: {str(e)}")
            return {"sentiment": "Neutral (error in interpretation)"}

    def _generate_signals(self, components: Dict[str, float]) -> List[Dict[str, Any]]:
        """Generate trading signals based on sentiment components.
        
        Args:
            components: Dictionary of sentiment component scores
            
        Returns:
            List of signal dictionaries
        """
        signals = []
        overall_score = components.get('sentiment', 50)
        
        # Generate signal based on overall sentiment
        if overall_score >= 70:
            signals.append({
                'type': 'SENTIMENT',
                'direction': 'BUY',
                'strength': (overall_score - 70) / 30 * 100,  # Normalize to 0-100
                'description': "Strong bullish market sentiment",
                'source': 'sentiment'
            })
        elif overall_score <= 30:
            signals.append({
                'type': 'SENTIMENT',
                'direction': 'SELL',
                'strength': (30 - overall_score) / 30 * 100,  # Normalize to 0-100
                'description': "Strong bearish market sentiment",
                'source': 'sentiment'
            })
            
        # Add more specific component signals
        funding_score = components.get('funding_rate', 50)
        if funding_score >= 70:
            signals.append({
                'type': 'FUNDING',
                'direction': 'BUY',
                'strength': (funding_score - 70) / 30 * 100,
                'description': "Negative funding rate suggests long opportunity",
                'source': 'funding_rate'
            })
        elif funding_score <= 30:
            signals.append({
                'type': 'FUNDING',
                'direction': 'SELL',
                'strength': (30 - funding_score) / 30 * 100,
                'description': "Positive funding rate suggests short opportunity",
                'source': 'funding_rate'
            })
        
        # Add market activity signals
        market_activity_score = components.get('market_activity', 50)
        if market_activity_score >= 70:
            signals.append({
                'type': 'MARKET_ACTIVITY',
                'direction': 'BUY',
                'strength': (market_activity_score - 70) / 30 * 100,
                'description': "Strong market activity and participation suggests bullish momentum",
                'source': 'market_activity'
            })
        elif market_activity_score <= 30:
            signals.append({
                'type': 'MARKET_ACTIVITY',
                'direction': 'SELL',
                'strength': (30 - market_activity_score) / 30 * 100,
                'description': "Weak market activity and participation suggests bearish momentum",
                'source': 'market_activity'
            })
            
        return signals

    def _calculate_market_activity(self, market_data: Dict[str, Any]) -> float:
        """Calculate market activity score based on volume and open interest."""
        try:
            self.logger.debug("\n=== Calculating Market Activity Score ===")
            
            ticker = market_data.get('ticker', {})
            if not ticker:
                return 50.0
                
            # Extract current volume and open interest
            volume = float(ticker.get('volume', 0))
            open_interest = float(ticker.get('openInterest', 0))
            
            # Calculate volume change (if previous volume available)
            volume_change = 0
            if hasattr(self, '_prev_volume') and self._prev_volume:
                volume_change = ((volume - self._prev_volume) / self._prev_volume) * 100
            self._prev_volume = volume
            
            # Calculate OI change (if previous OI available)
            oi_change = 0
            if hasattr(self, '_prev_oi') and self._prev_oi:
                oi_change = ((open_interest - self._prev_oi) / self._prev_oi) * 100
            self._prev_oi = open_interest
            
            # Calculate OI/Volume ratio
            oi_volume_ratio = open_interest / volume if volume > 0 else 1
            
            # Score components
            # Volume score: Based on volume change
            volume_score = 50 + (volume_change * 2)  # Each 1% change = 2 points
            volume_score = np.clip(volume_score, 0, 100)
            
            # OI score: Based on OI change
            oi_score = 50 + (oi_change * 2)  # Each 1% change = 2 points
            oi_score = np.clip(oi_score, 0, 100)
            
            # Ratio score: Optimal ratio is around 1.5
            ratio_score = 100 - abs(oi_volume_ratio - 1.5) * 20
            ratio_score = np.clip(ratio_score, 0, 100)
            
            # Log calculations
            self.logger.debug(f"Volume: {volume:,.1f}, Volume change: {volume_change:.1f}%")
            self.logger.debug(f"Open interest: {open_interest:,.1f}, OI change: {oi_change:.1f}%")
            self.logger.debug(f"OI/Volume ratio: {oi_volume_ratio:.2f}")
            self.logger.debug(f"Volume score: {volume_score:.2f}, OI score: {oi_score:.2f}, Ratio score: {ratio_score:.2f}")
            
            # Calculate final score with weights
            weights = {'volume': 0.4, 'oi': 0.4, 'ratio': 0.2}
            final_score = (
                volume_score * weights['volume'] +
                oi_score * weights['oi'] +
                ratio_score * weights['ratio']
            )
            
            self.logger.debug(f"Combined market activity score: {final_score:.2f}")
            return float(final_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating market activity score: {str(e)}")
            return 50.0
